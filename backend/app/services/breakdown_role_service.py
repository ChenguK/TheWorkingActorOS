from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import BreakdownRole, CastingLanguage, Opportunity
from app.services.casting_language_parser import CastingLanguageParser


class BreakdownRoleService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def sync_from_details(self, opportunity: Opportunity) -> None:
        parsed_roles = (opportunity.role_details or {}).get("available_roles")
        if not isinstance(parsed_roles, list):
            parsed_roles = []

        fit_by_name = {
            str(item.get("role_name", "")).lower(): item
            for item in (opportunity.demographic_match_details or {}).get("role_results", [])
            if isinstance(item, dict)
        }

        opportunity.breakdown_roles.clear()
        for role in parsed_roles:
            if not isinstance(role, dict):
                continue
            role_name = str(role.get("role_name") or "").strip()
            if not role_name:
                continue
            fit = fit_by_name.get(role_name.lower())
            fit_status, fit_score, fit_explanation = self._fit_from_result(role, fit)
            compatibility_label = self._compatibility_label(fit, fit_status)
            age_min, age_max = self._age_bounds(role.get("age_range"))
            breakdown_role = BreakdownRole(
                role_name=role_name,
                role_type=role.get("role_type"),
                billing=role.get("billing") or role.get("role_type"),
                billing_or_role_type=role.get("role_type"),
                character_description=role.get("character_description"),
                gender_presentation=role.get("gender_presentation"),
                ethnicity_or_cultural_background=role.get("ethnicity"),
                playable_age_min=age_min,
                playable_age_max=age_max,
                height_requirements=role.get("height_requirement"),
                vocal_requirements=role.get("vocal_requirements"),
                dance_requirements=self._dance_requirements(role),
                movement_requirements=role.get("movement_requirements") or role.get("skills_required"),
                language_requirements=role.get("language_requirements"),
                special_skills=self._special_skills(role),
                preparation_notes=role.get("preparation_notes"),
                union_status=role.get("union_status") or opportunity.union,
                role_notes=role.get("role_requirement_text"),
                fit_status=fit_status,
                fit_score=fit_score,
                fit_explanation=fit_explanation,
                confidence_score=self._confidence_score(role, fit),
                extracted_facts=role.get("extracted_facts") or self._fallback_facts(role),
                ai_inference={
                    **(role.get("ai_inference") or {}),
                    "probable_fit": {
                        "value": fit_status,
                        "confidence": self._confidence_score(role, fit),
                        "explanation": fit_explanation,
                    },
                    "fit_score": {
                        "value": fit_score,
                        "confidence": self._confidence_score(role, fit),
                        "explanation": "Inferred from compatibility across demographics, character, logistics, materials, goals, availability, and learning history.",
                    },
                    "compatibility": {
                        "value": compatibility_label,
                        "confidence": self._confidence_score(role, fit),
                        "explanation": fit_explanation,
                        "details": (fit or {}).get("compatibility_details", {}),
                    },
                },
            )
            parsed_casting_language = CastingLanguageParser().parse_role(role)
            if parsed_casting_language:
                breakdown_role.casting_language = CastingLanguage(
                    breakdown=opportunity,
                    **parsed_casting_language.model_data(),
                )
            opportunity.breakdown_roles.append(breakdown_role)
        self.db.flush()

    def _fit_from_result(self, role: dict[str, Any], result: dict[str, Any] | None) -> tuple[str, int, str]:
        if not result:
            return "Needs Review", 0, "Role was parsed, but actor fit has not been evaluated yet."
        compatibility_label = result.get("compatibility_label")
        if compatibility_label:
            return (
                self._fit_status_from_compatibility(str(compatibility_label)),
                int(result.get("compatibility_score") or 0),
                str(result.get("compatibility_explanation") or "Compatibility was evaluated from saved profile and role requirements."),
            )
        status = result.get("status")
        checks = result.get("checks", [])
        mismatches = [
            check for check in checks if isinstance(check, dict) and check.get("status") == "Not a Match"
        ]
        review = [check for check in checks if isinstance(check, dict) and check.get("status") == "Needs Review"]
        matches = [check for check in checks if isinstance(check, dict) and check.get("status") == "Match"]
        fit_score = self._fit_score(matches=matches, review=review, mismatches=mismatches, role=role)
        if status == "Not a Match" or mismatches:
            reasons = "; ".join(
                check.get("explanation", "")
                for check in mismatches
                if isinstance(check, dict) and check.get("explanation")
            )
            return "Not Fit", fit_score, self._role_reason(role, reasons or "Explicit role requirements do not overlap the actor profile.")
        if review:
            reasons = "; ".join(
                check.get("explanation", "")
                for check in review
                if isinstance(check, dict) and check.get("explanation")
            )
            return "Needs Review", fit_score, self._role_reason(role, reasons or "Some role requirements need a human check.")
        if len(matches) >= 3:
            status_label = "Strong Fit" if fit_score >= 80 else "Possible Fit"
            return status_label, fit_score, self._match_reason(matches, role)
        if matches:
            return "Possible Fit", fit_score, self._match_reason(matches, role)
        return "Needs Review", fit_score, "The role has limited explicit eligibility requirements."

    def _compatibility_label(self, result: dict[str, Any] | None, fallback_status: str) -> str:
        if result and result.get("compatibility_label"):
            return str(result["compatibility_label"])
        return {
            "Strong Fit": "Strong Match",
            "Possible Fit": "Good Match",
            "Stretch Fit": "Stretch",
            "Not Fit": "Not Recommended",
            "Needs Review": "Low Fit",
        }.get(fallback_status, "Low Fit")

    def _fit_status_from_compatibility(self, label: str) -> str:
        return {
            "Excellent Match": "Strong Fit",
            "Strong Match": "Strong Fit",
            "Good Match": "Possible Fit",
            "Comfortable Stretch": "Possible Fit",
            "Stretch": "Stretch Fit",
            "Low Fit": "Needs Review",
            "Not Recommended": "Not Fit",
        }.get(label, "Needs Review")

    def _fit_score(self, *, matches: list[dict], review: list[dict], mismatches: list[dict], role: dict[str, Any]) -> int:
        if mismatches:
            return max(0, 25 - (len(mismatches) * 10))
        score = 35 + (len(matches) * 18)
        if role.get("vocal_requirements") or role.get("dance_requirements") or role.get("movement_requirements"):
            score -= 5
        if review:
            score -= 10
        return max(0, min(100, score))

    def _match_reason(self, matches: list[dict], role: dict[str, Any]) -> str:
        labels = [str(check.get("label")) for check in matches if isinstance(check, dict) and check.get("label")]
        summary = ", ".join(labels) if labels else "explicit role requirements"
        extra = []
        if role.get("vocal_requirements"):
            extra.append("vocal requirements should be reviewed against your materials")
        if role.get("archetypes"):
            extra.append(f"archetypes: {', '.join(role.get('archetypes'))}")
        suffix = f" Additional notes: {'; '.join(extra)}." if extra else ""
        return f"{summary} overlap your saved actor profile.{suffix}"

    def _role_reason(self, role: dict[str, Any], reason: str) -> str:
        requirements = [
            role.get("ethnicity"),
            role.get("gender_presentation"),
            f"reads {role.get('age_range')}" if role.get("age_range") else None,
            role.get("height_requirement"),
            role.get("vocal_requirements"),
            role.get("skills_required"),
        ]
        listed = ", ".join(str(item) for item in requirements if item)
        return f"{reason} Role requests: {listed}." if listed else reason

    def _age_bounds(self, age_range: Any) -> tuple[int | None, int | None]:
        text = str(age_range or "").lower()
        if not text:
            return None, None
        if "late teens" in text:
            return 17, 19
        if "mid teens" in text:
            return 15, 17
        if "early teens" in text:
            return 13, 15
        range_match = re.search(r"(\d{2})\s*(?:-|–|to)\s*(\d{2})", text)
        if range_match:
            first, second = int(range_match.group(1)), int(range_match.group(2))
            return min(first, second), max(first, second)
        age_match = re.search(r"\b(\d{2})\b", text)
        if age_match:
            age = int(age_match.group(1))
            return age, age
        return None, None

    def _dance_requirements(self, role: dict[str, Any]) -> str | None:
        skills = str(role.get("skills_required") or "")
        return skills if re.search(r"\b(dance|movement)\b", skills, flags=re.I) else None

    def _special_skills(self, role: dict[str, Any]) -> str | None:
        skills = str(role.get("skills_required") or "")
        special = [
            term
            for term in ["Brazilian Jiu-Jitsu", "judo", "grappling", "MMA", "stage combat", "guitar"]
            if re.search(rf"\b{re.escape(term)}\b", skills, flags=re.I)
            or re.search(rf"\b{re.escape(term)}\b", str(role.get("role_requirement_text") or ""), flags=re.I)
        ]
        return ", ".join(dict.fromkeys(special)) or skills or None

    def _confidence_score(self, role: dict[str, Any], result: dict[str, Any] | None) -> int:
        score = int(role.get("confidence_score") or 45)
        if result:
            score += 10
        if role.get("role_name") and role.get("character_description"):
            score += 10
        return max(0, min(100, score))

    def _fallback_facts(self, role: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in {
                "role_name": role.get("role_name"),
                "role_type": role.get("role_type"),
                "billing": role.get("billing"),
                "character_description": role.get("character_description"),
                "gender_presentation": role.get("gender_presentation"),
                "ethnicity_or_cultural_background": role.get("ethnicity"),
                "age_range": role.get("age_range"),
                "height_requirements": role.get("height_requirement"),
                "vocal_requirements": role.get("vocal_requirements"),
                "dance_requirements": role.get("dance_requirements"),
                "movement_requirements": role.get("movement_requirements"),
                "language_requirements": role.get("language_requirements"),
                "special_skills": role.get("special_skills"),
                "preparation_notes": role.get("preparation_notes"),
            }.items()
            if value not in [None, "", [], {}]
        }
