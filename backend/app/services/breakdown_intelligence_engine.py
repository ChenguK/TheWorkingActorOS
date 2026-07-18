from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import BreakdownParseRun, BreakdownSection, Opportunity
from app.services.breakdown_details_service import BreakdownDetailsService, ROLE_COLON_PATTERN, ROLE_HEADING_PATTERN


SECTION_TYPES = (
    "Production Details",
    "Audition Information",
    "Preparation",
    "Roles",
    "Character Descriptions",
    "Dates",
    "Locations",
    "Submission Instructions",
    "Contact",
    "Additional Notes",
)


class BreakdownIntelligenceEngine:
    parser_version = "breakdown-intelligence-v1"

    def __init__(self, db: Session | None = None) -> None:
        self.db = db

    def parse(self, text: str, parse_mode: str = "Standard Parse") -> dict[str, Any]:
        cleaned_text = self.clean_visible_content(text)
        lines = [line.strip() for line in re.split(r"[\n\r]+", cleaned_text) if line.strip()]
        sections = self.detect_sections(lines, parse_mode=parse_mode)
        details = BreakdownDetailsService().from_text(cleaned_text)
        overall_confidence = self._overall_confidence(sections, details, parse_mode)
        return {
            "parser_version": self.parser_version,
            "parse_mode": parse_mode,
            "cleaned_text": cleaned_text,
            "sections": sections,
            "details": details,
            "overall_confidence": overall_confidence,
            "actor_summary": self._actor_summary(details, overall_confidence),
        }

    def run_for_opportunity(self, opportunity: Opportunity, text: str, parse_mode: str) -> dict[str, Any]:
        if self.db is None:
            raise RuntimeError("A database session is required to persist parse runs")
        now = datetime.now(timezone.utc)
        run = BreakdownParseRun(
            breakdown_id=opportunity.id,
            parser_version=self.parser_version,
            parse_mode=parse_mode,
            started_at=now,
            status="running",
        )
        self.db.add(run)
        self.db.flush()
        try:
            parsed = self.parse(text, parse_mode=parse_mode)
            opportunity.breakdown_sections.clear()
            for section in parsed["sections"]:
                opportunity.breakdown_sections.append(
                    BreakdownSection(
                        section_type=section["section_type"],
                        heading=section.get("heading"),
                        raw_text=section["raw_text"],
                        parsed_json=section.get("parsed_json", {}),
                        confidence_score=section["confidence_score"],
                        display_order=section["display_order"],
                    )
                )
            run.status = "succeeded"
            run.completed_at = datetime.now(timezone.utc)
            run.overall_confidence = parsed["overall_confidence"]
            opportunity.source_metadata = {
                **(opportunity.source_metadata or {}),
                "breakdown_parser_version": self.parser_version,
                "breakdown_parse_mode": parse_mode,
                "breakdown_parse_confidence": parsed["overall_confidence"],
                "last_breakdown_parse_at": run.completed_at.isoformat(),
            }
            if parsed["overall_confidence"] < 70:
                opportunity.manual_review_required = True
                opportunity.confidence_level = "Low"
                opportunity.source_metadata = {
                    **opportunity.source_metadata,
                    "needs_deep_parse": True,
                    "needs_review_reason": "Breakdown parse confidence is below 70%.",
                }
            else:
                opportunity.source_metadata = {**opportunity.source_metadata, "needs_deep_parse": False}
            self.db.flush()
            return parsed
        except Exception as exc:
            run.status = "failed"
            run.completed_at = datetime.now(timezone.utc)
            run.error_message = str(exc)
            self.db.flush()
            raise

    def clean_visible_content(self, text: str) -> str:
        value = re.sub(r"(?is)<(script|style|noscript|svg).*?</\1>", " ", text)
        value = re.sub(r"(?i)<br\s*/?>", "\n", value)
        value = re.sub(r"(?i)</(p|div|li|h1|h2|h3|h4|section|article|tr)>", "\n", value)
        value = re.sub(r"<[^>]+>", " ", value)
        value = html.unescape(value)
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in value.splitlines()]
        noise = re.compile(r"^(menu|search|advertisement|privacy policy|terms of use|sign up|log in|share)$", re.I)
        return "\n".join(line for line in lines if line and not noise.match(line))

    def detect_sections(self, lines: list[str], parse_mode: str = "Standard Parse") -> list[dict[str, Any]]:
        sections: list[dict[str, Any]] = []
        current_heading = "Breakdown"
        current_lines: list[str] = []

        def flush() -> None:
            if not current_lines:
                return
            raw_text = "\n".join(current_lines).strip()
            section_type = self.classify_section(current_heading, raw_text)
            sections.append(
                {
                    "section_type": section_type,
                    "heading": current_heading,
                    "raw_text": raw_text,
                    "parsed_json": self._section_json(section_type, raw_text),
                    "confidence_score": self._section_confidence(section_type, raw_text),
                    "display_order": len(sections),
                }
            )

        for line in lines:
            if self._is_heading(line, parse_mode=parse_mode):
                flush()
                current_heading = line
                current_lines = []
            else:
                current_lines.append(line)
        flush()

        if not sections and lines:
            raw_text = "\n".join(lines)
            sections.append(
                {
                    "section_type": "Additional Notes",
                    "heading": "Breakdown",
                    "raw_text": raw_text,
                    "parsed_json": {},
                    "confidence_score": 35,
                    "display_order": 0,
                }
            )
        return sections

    def classify_section(self, heading: str, raw_text: str) -> str:
        text = f"{heading} {raw_text}".lower()
        normalized_heading = heading.lower().strip(":")
        if normalized_heading in {"audition date", "other dates", "dates"}:
            return "Dates"
        if normalized_heading in {"location", "audition location", "rehearsal location", "performance location"}:
            return "Locations"
        if normalized_heading in {"preparation", "prepare"}:
            return "Preparation"
        if ROLE_HEADING_PATTERN.match(heading) or ROLE_COLON_PATTERN.match(heading) or re.search(r"\b(role|character|seeking|cast)\b", text):
            return "Roles" if ROLE_HEADING_PATTERN.match(heading) or ROLE_COLON_PATTERN.match(heading) or "seeking" in text else "Character Descriptions"
        if re.search(r"\b(project|production|director|producer|casting office|union|rate|contract)\b", text):
            return "Production Details"
        if re.search(r"\b(audition|self[- ]?tape|callback|eco cast|appointment|virtual|in[- ]person)\b", text):
            return "Audition Information"
        if re.search(r"\b(prepare|sides|song|monologue|bring|rehearsal|wardrobe)\b", text):
            return "Preparation"
        if re.search(r"\b(deadline|due|dates?|shoot|rehearsal|performance)\b", text):
            return "Dates"
        if re.search(r"\b(location|venue|studio|address|shoots in|rehearses in)\b", text):
            return "Locations"
        if re.search(r"\b(submit|submission|send|email|instructions|headshot|resume)\b", text):
            return "Submission Instructions"
        if re.search(r"\b(contact|email|phone|casting director)\b", text):
            return "Contact"
        return "Additional Notes"

    def _is_heading(self, line: str, parse_mode: str) -> bool:
        if ROLE_HEADING_PATTERN.match(line) or ROLE_COLON_PATTERN.match(line):
            return True
        if len(line) > 90:
            return False
        if re.search(r":$", line) and len(line.split()) <= 7:
            return True
        known = {
            "production details",
            "audition information",
            "preparation",
            "roles",
            "character descriptions",
            "dates",
            "locations",
            "submission instructions",
            "contact",
            "additional notes",
            "audition date",
            "location",
            "audition location",
            "rehearsal location",
            "performance location",
            "personnel",
            "other dates",
            "other",
            "breakdown",
            "seeking",
        }
        if line.lower().strip(":") in known:
            return True
        return parse_mode in {"Deep Parse", "Manual Paste Reparse"} and bool(re.match(r"^[A-Z][A-Za-z /&'-]{2,45}$", line)) and len(line.split()) <= 5

    def _section_json(self, section_type: str, raw_text: str) -> dict[str, Any]:
        if section_type == "Roles":
            return {"role_signal": True, "requirements": self._requirement_terms(raw_text)}
        if section_type == "Preparation":
            return {"preparation": raw_text}
        if section_type == "Locations":
            lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
            return {"location_name": lines[0] if lines else None, "address": ", ".join(lines[1:]) if len(lines) > 1 else None}
        if section_type == "Dates":
            return {"dates": re.findall(r"\b(?:\d{1,2}/\d{1,2}/\d{2,4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2})\b", raw_text, flags=re.I)}
        if section_type == "Contact":
            return {"emails": re.findall(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", raw_text)}
        if section_type == "Submission Instructions":
            return {"submission_signal": True}
        return {}

    def _requirement_terms(self, text: str) -> list[str]:
        terms = []
        for pattern in ["female", "male", "nonbinary", "soprano", "alto", "tenor", "baritone", "dance", "movement", "martial arts", "self-tape"]:
            if re.search(rf"\b{re.escape(pattern)}\b", text, flags=re.I):
                terms.append(pattern)
        return terms

    def _section_confidence(self, section_type: str, raw_text: str) -> int:
        score = 45
        if section_type in SECTION_TYPES:
            score += 15
        if len(raw_text.split()) >= 12:
            score += 15
        if self._section_json(section_type, raw_text):
            score += 15
        return min(100, score)

    def _overall_confidence(self, sections: list[dict[str, Any]], details: dict[str, Any], parse_mode: str) -> int:
        score = 30
        section_types = {section["section_type"] for section in sections}
        score += min(25, len(section_types) * 4)
        if details["production_details"]:
            score += 12
        if details["role_details"].get("available_roles"):
            score += 20
        elif details["role_details"]:
            score += 8
        if details.get("submission_instructions"):
            score += 8
        if parse_mode == "Deep Parse":
            score += 5
        return max(0, min(100, score))

    def _actor_summary(self, details: dict[str, Any], confidence: int) -> str:
        role = details["role_details"].get("role_name", "Role")
        project_type = details["production_details"].get("project_type", "project")
        audition = details["role_details"].get("audition_type", "audition details unknown")
        return f"{role} in a {str(project_type).lower()} with {str(audition).lower()} audition info. Parse confidence: {confidence}%."
