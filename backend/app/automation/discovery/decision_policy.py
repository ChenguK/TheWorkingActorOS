from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.automation.discovery.classification import REJECTED_CLASSIFICATIONS


PUBLIC_DISCOVERY_ACCEPT_CONFIDENCE = 70
PUBLIC_DISCOVERY_REVIEW_CONFIDENCE = 1
PUBLIC_DISCOVERY_UNUSABLE_CONFIDENCE = 0
PUBLIC_DISCOVERY_MAX_EXPLANATION_LENGTH = 240


class PublicDiscoveryOutcome(StrEnum):
    ACCEPT_VISIBLE = "accept_visible"
    REVIEW_HIDDEN = "review_hidden"
    REJECT_DISCARDED = "reject_discarded"


@dataclass(frozen=True)
class PublicDiscoveryDecision:
    outcome: PublicDiscoveryOutcome
    reason_code: str
    explanation: str
    supporting_reason_codes: tuple[str, ...] = ()
    parse_confidence: float | None = None

    def as_report_fields(self) -> dict[str, Any]:
        legacy_label = {
            PublicDiscoveryOutcome.ACCEPT_VISIBLE: "Accepted",
            PublicDiscoveryOutcome.REVIEW_HIDDEN: "Needs Review",
            PublicDiscoveryOutcome.REJECT_DISCARDED: "Rejected",
        }[self.outcome]
        fields: dict[str, Any] = {
            "decision": legacy_label,
            "outcome": self.outcome.value,
            "reason_code": self.reason_code,
            "explanation": self.explanation[:PUBLIC_DISCOVERY_MAX_EXPLANATION_LENGTH],
            "rejection_reason": (
                self.explanation[:PUBLIC_DISCOVERY_MAX_EXPLANATION_LENGTH]
                if self.outcome is PublicDiscoveryOutcome.REJECT_DISCARDED
                else None
            ),
        }
        if self.supporting_reason_codes:
            fields["supporting_reason_codes"] = list(self.supporting_reason_codes)
        if self.parse_confidence is not None:
            fields["parser_confidence"] = self.parse_confidence
        return fields


class PublicDiscoveryDecisionPolicy:
    _HARD_RULE_REASONS = {
        "breakdown_classification_rejected": "non_acting_job",
        "deadline_expired": "expired_notice",
        "dealbreaker_role_type": "excluded_role_type",
        "dealbreaker_demographic_mismatch": "hard_demographic_mismatch",
        "dealbreaker_audition_travel": "travel_limit_exceeded",
        "dealbreaker_availability": "required_date_unavailable",
        "dealbreaker_eligibility": "hard_eligibility_failure",
    }
    _REVIEW_RULE_REASONS = {
        "needs_date_review": "missing_deadline",
        "breakdown_classification_needs_review": "ambiguous_casting_content",
        "audition_location_needs_info": "travel_uncertain",
        "travel_exception": "travel_exception_review",
    }
    _MATERIAL_TRUST_WARNINGS = {
        "Breakdown Type Verification",
        "Role Eligibility Verification",
        "Audition Location Verification",
        "Date Verification",
        "Platform Verification",
        "Confidence Threshold",
        "External Link Verification",
    }

    def reject(self, reason_code: str, explanation: str) -> PublicDiscoveryDecision:
        return self._decision(PublicDiscoveryOutcome.REJECT_DISCARDED, reason_code, explanation)

    def review(self, reason_code: str, explanation: str) -> PublicDiscoveryDecision:
        return self._decision(PublicDiscoveryOutcome.REVIEW_HIDDEN, reason_code, explanation)

    def decide(self, item: Any, opportunity: Any) -> PublicDiscoveryDecision:
        hard = self._hard_failure(item, opportunity)
        if hard:
            return hard

        confidence = self._parse_confidence(opportunity)
        review_reasons: list[tuple[str, str]] = []
        rule = str(getattr(opportunity, "hidden_by_rule", None) or "")
        if rule in self._REVIEW_RULE_REASONS:
            review_reasons.append(
                (
                    self._REVIEW_RULE_REASONS[rule],
                    self._review_explanation(rule, opportunity),
                )
            )
        if getattr(opportunity, "visibility_status", None) == "hidden" and not rule:
            review_reasons.append(
                (
                    "existing_hidden_review",
                    "The candidate requires review before visible presentation.",
                )
            )
        if confidence is not None:
            if confidence <= PUBLIC_DISCOVERY_UNUSABLE_CONFIDENCE:
                return self.reject(
                    "unusable_parse_confidence",
                    "The candidate could not be parsed into usable casting information.",
                )
            if confidence < PUBLIC_DISCOVERY_ACCEPT_CONFIDENCE:
                review_reasons.append(
                    (
                        "medium_parse_confidence",
                        f"Parse confidence is below the {PUBLIC_DISCOVERY_ACCEPT_CONFIDENCE}% visible threshold.",
                    )
                )
        else:
            review_reasons.append(
                ("missing_parse_confidence", "Parse confidence is unavailable and requires review.")
            )

        if self._ambiguous_directness(item):
            review_reasons.append(
                (
                    "ambiguous_casting_content",
                    "The page discusses casting but does not clearly establish a direct actionable role notice.",
                )
            )
        if self._missing_role(item):
            review_reasons.append(
                ("missing_actionable_details", "A specific actionable role was not identified.")
            )
        if self._project_uncertain(item, opportunity):
            review_reasons.append(
                ("uncertain_project_type", "Project type is missing or uncertain.")
            )
        if self._missing_deadline(item, opportunity):
            review_reasons.append(
                ("missing_deadline", "No submission deadline was identified for the candidate.")
            )
        if self._missing_location(item, opportunity):
            review_reasons.append(
                ("missing_location", "A usable work or audition location was not identified.")
            )
        if self._union_uncertain(item, opportunity):
            review_reasons.append(
                (
                    "union_uncertain",
                    "Union status is missing or uncertain and requires actor review.",
                )
            )
        trust_warning = self._material_trust_warning(item, opportunity)
        if trust_warning:
            review_reasons.append(("trust_warning", trust_warning))

        if review_reasons:
            unique = self._unique_reasons(review_reasons)
            primary_code, primary_explanation = unique[0]
            return self._decision(
                PublicDiscoveryOutcome.REVIEW_HIDDEN,
                primary_code,
                primary_explanation,
                supporting=tuple(code for code, _ in unique[1:]),
                confidence=confidence,
            )
        return self._decision(
            PublicDiscoveryOutcome.ACCEPT_VISIBLE,
            "direct_eligible_notice",
            "Direct actionable acting notice passed current eligibility and trust checks.",
            confidence=confidence,
        )

    def _hard_failure(self, item: Any, opportunity: Any) -> PublicDiscoveryDecision | None:
        classification = str(getattr(item, "breakdown_classification", "") or "")
        if classification in REJECTED_CLASSIFICATIONS:
            code = "crew_or_staff_listing" if classification == "Crew Job" else "non_acting_job"
            return self.reject(code, "The candidate is not an actor-facing role notice.")
        rule = str(getattr(opportunity, "hidden_by_rule", None) or "")
        if rule in self._HARD_RULE_REASONS:
            return self.reject(
                self._hard_rule_code(rule, opportunity),
                self._hard_explanation(rule),
            )
        trust = (getattr(opportunity, "source_metadata", None) or {}).get(
            "trust_verification"
        ) or {}
        if trust.get("status") == "Blocked":
            return self.reject(
                "trust_blocked",
                "Current trust checks prove that this candidate cannot be presented as a public acting notice.",
            )
        return None

    def _parse_confidence(self, opportunity: Any) -> float | None:
        value = (getattr(opportunity, "source_metadata", None) or {}).get(
            "breakdown_parse_confidence"
        )
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def _ambiguous_directness(self, item: Any) -> bool:
        text = " ".join(
            str(value or "")
            for value in (
                getattr(item, "project", None),
                getattr(item, "role", None),
                getattr(item, "description", None),
            )
        ).casefold()
        resource_terms = ("article", "advice", "resource", "guide", "interview", "news")
        direct_terms = (
            "submission deadline",
            "submit by",
            "apply by",
            "submission instructions",
            "seeking actors",
            "seeking performers",
            "role:",
            "character:",
        )
        return any(term in text for term in resource_terms) and not any(
            term in text for term in direct_terms
        )

    def _missing_role(self, item: Any) -> bool:
        role = str(getattr(item, "role", None) or "").strip().casefold()
        return not role or role in {"performer", "actor", "unknown", "see source"}

    def _missing_deadline(self, item: Any, opportunity: Any) -> bool:
        if any(
            getattr(opportunity, name, None)
            for name in ("submission_deadline", "audition_deadline")
        ):
            return False
        role = getattr(item, "role_details", None) or {}
        production = getattr(item, "production_details", None) or {}
        return not any(
            role.get(key)
            for key in (
                "submission_deadline",
                "self_tape_due_date",
                "tape_due_date",
                "due_date",
            )
        ) and not production.get("submission_deadline")

    def _project_uncertain(self, item: Any, opportunity: Any) -> bool:
        production = getattr(item, "production_details", None) or {}
        value = (
            str(getattr(opportunity, "project_type", None) or production.get("project_type") or "")
            .strip()
            .casefold()
        )
        return value in {"", "unknown", "unspecified", "see source"}

    def _missing_location(self, item: Any, opportunity: Any) -> bool:
        values = [
            getattr(opportunity, "location", None),
            getattr(opportunity, "shoot_location", None),
            getattr(opportunity, "audition_location", None),
            getattr(item, "location", None),
        ]
        usable = [
            str(value).strip().casefold()
            for value in values
            if value and str(value).strip().casefold() not in {"unknown", "see source", "n/a"}
        ]
        return not usable

    def _union_uncertain(self, item: Any, opportunity: Any) -> bool:
        value = (
            str(getattr(opportunity, "union", None) or getattr(item, "union", None) or "")
            .strip()
            .casefold()
        )
        return value in {"", "unknown", "unspecified", "n/a", "none"}

    def _material_trust_warning(self, item: Any, opportunity: Any) -> str | None:
        trust = (getattr(opportunity, "source_metadata", None) or {}).get(
            "trust_verification"
        ) or {}
        checks = trust.get("checks") if isinstance(trust, dict) else None
        if not isinstance(checks, list):
            return None
        for check in checks:
            if (
                isinstance(check, dict)
                and check.get("status") == "warning"
                and check.get("name") in self._MATERIAL_TRUST_WARNINGS
            ):
                if check.get("name") == "Date Verification" and not self._missing_deadline(
                    item, opportunity
                ):
                    continue
                return "A material trust or verification warning requires review before visible presentation."
        return None

    def _hard_explanation(self, rule: str) -> str:
        return {
            "breakdown_classification_rejected": "The candidate is not an actor-facing role notice.",
            "deadline_expired": "The candidate deadline has expired.",
            "dealbreaker_role_type": "The role type is excluded by saved actor preferences.",
            "dealbreaker_demographic_mismatch": "The explicit role requirements do not match the saved actor profile.",
            "dealbreaker_audition_travel": "The required in-person audition exceeds the saved hard travel limit.",
            "dealbreaker_availability": "A required date conflicts with saved actor availability.",
            "dealbreaker_eligibility": "The candidate failed a proven hard eligibility requirement.",
        }[rule]

    def _hard_rule_code(self, rule: str, opportunity: Any) -> str:
        if rule != "dealbreaker_eligibility":
            return self._HARD_RULE_REASONS[rule]
        reason = str(getattr(opportunity, "hidden_reason", None) or "").casefold()
        if "language" in reason:
            return "required_language_missing"
        return "hard_eligibility_failure"

    def _review_explanation(self, rule: str, opportunity: Any) -> str:
        return {
            "needs_date_review": "Deadline information is ambiguous and requires review.",
            "breakdown_classification_needs_review": "Acting relevance is uncertain and requires review.",
            "audition_location_needs_info": "In-person audition travel cannot be verified yet.",
            "travel_exception": "The role may be relevant, but audition travel exceeds the saved preference.",
        }[rule]

    def _unique_reasons(self, reasons: list[tuple[str, str]]) -> list[tuple[str, str]]:
        seen: set[str] = set()
        return [reason for reason in reasons if not (reason[0] in seen or seen.add(reason[0]))]

    def _decision(
        self,
        outcome: PublicDiscoveryOutcome,
        reason_code: str,
        explanation: str,
        *,
        supporting: tuple[str, ...] = (),
        confidence: float | None = None,
    ) -> PublicDiscoveryDecision:
        plain = re.sub(r"<[^>]+>|[\x00-\x1f\x7f]", " ", str(explanation))
        plain = re.sub(r"\s+", " ", plain).strip()
        return PublicDiscoveryDecision(
            outcome=outcome,
            reason_code=reason_code,
            explanation=plain[:PUBLIC_DISCOVERY_MAX_EXPLANATION_LENGTH],
            supporting_reason_codes=supporting,
            parse_confidence=confidence,
        )
