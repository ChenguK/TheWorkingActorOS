from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from app.automation.discovery.contracts import NormalizedOpportunity
from app.db.models import Opportunity


USER_TIMEZONE = "America/New_York"
MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


@dataclass(frozen=True)
class DeadlineValidationResult:
    status: str
    reason: str | None = None
    parsed_dates: dict[str, str] = field(default_factory=dict)
    confidence: str = "High"

    @property
    def expired(self) -> bool:
        return self.status == "Expired"

    @property
    def needs_review(self) -> bool:
        return self.status == "Needs Date Review"

    def as_metadata(self) -> dict:
        return {
            "status": self.status,
            "reason": self.reason,
            "parsed_dates": self.parsed_dates,
            "confidence": self.confidence,
        }


class BreakdownDeadlineService:
    def __init__(self, user_timezone: str = USER_TIMEZONE) -> None:
        self.user_timezone = user_timezone

    def validate_normalized(
        self,
        item: NormalizedOpportunity,
        now: datetime | None = None,
    ) -> DeadlineValidationResult:
        facts = self._date_facts_from_normalized(item)
        return self.validate_facts(facts, now=now)

    def validate_opportunity(
        self,
        opportunity: Opportunity,
        now: datetime | None = None,
    ) -> DeadlineValidationResult:
        facts = self._date_facts_from_opportunity(opportunity)
        return self.validate_facts(facts, now=now)

    def validate_facts(self, facts: dict, now: datetime | None = None) -> DeadlineValidationResult:
        today = self._today(now)
        parsed_dates: dict[str, str] = {}
        uncertain: list[str] = []

        for field_name in ("submission_deadline", "expiration_date"):
            raw_value = self._first_present(facts, field_name)
            if raw_value in (None, ""):
                continue
            parsed = self._parse_date(raw_value, today)
            if parsed is None:
                uncertain.append(field_name)
                continue
            parsed_dates[field_name] = parsed.isoformat()
            if parsed < today:
                label = "submission deadline" if field_name == "submission_deadline" else "expiration date"
                return DeadlineValidationResult(
                    status="Expired",
                    reason=f"Rejected because the {label} has passed.",
                    parsed_dates=parsed_dates,
                    confidence="High",
                )

        for field_name in ("posted_date", "audition_date", "callback_date", "shoot_or_work_dates"):
            raw_value = self._first_present(facts, field_name)
            parsed = self._parse_date(raw_value, today) if raw_value else None
            if parsed:
                parsed_dates[field_name] = parsed.isoformat()

        if uncertain:
            return DeadlineValidationResult(
                status="Needs Date Review",
                reason="Needs Date Review: deadline text could not be parsed confidently. Posted, audition, and shoot dates were not treated as submission deadlines.",
                parsed_dates=parsed_dates,
                confidence="Low",
            )
        return DeadlineValidationResult(status="Valid", parsed_dates=parsed_dates, confidence="High")

    def apply_to_opportunity(self, opportunity: Opportunity, now: datetime | None = None) -> DeadlineValidationResult:
        result = self.validate_opportunity(opportunity, now=now)
        opportunity.source_metadata = {
            **(opportunity.source_metadata or {}),
            "date_validation": result.as_metadata(),
        }
        extracted = dict(opportunity.extracted_facts or {})
        extracted["dates"] = {
            **(extracted.get("dates") or {}),
            **result.parsed_dates,
        }
        opportunity.extracted_facts = extracted
        if result.expired:
            opportunity.visibility_status = "discarded"
            opportunity.status = "archived"
            opportunity.hidden_by_rule = "deadline_expired"
            opportunity.hidden_reason = result.reason
            opportunity.rejection_reason = result.reason
            opportunity.manual_review_required = False
        elif result.needs_review:
            opportunity.visibility_status = "hidden"
            opportunity.hidden_by_rule = "needs_date_review"
            opportunity.hidden_reason = result.reason
            opportunity.manual_review_required = True
        return result

    def _date_facts_from_normalized(self, item: NormalizedOpportunity) -> dict:
        metadata = item.source_metadata or {}
        production = item.production_details or {}
        role = item.role_details or {}
        return {
            "posted_date": metadata.get("posted_date") or metadata.get("discovered_at") or metadata.get("discovered_on"),
            "submission_deadline": (
                role.get("submission_deadline")
                or role.get("self_tape_due_date")
                or role.get("tape_due_date")
                or role.get("due_date")
                or production.get("submission_deadline")
            ),
            "expiration_date": metadata.get("expiration_date") or production.get("expiration_date") or role.get("expiration_date"),
            "audition_date": role.get("audition_date") or production.get("audition_date"),
            "callback_date": role.get("callback_date") or role.get("callback_info"),
            "shoot_or_work_dates": production.get("shoot_dates") or production.get("work_dates") or production.get("performance_dates"),
        }

    def _date_facts_from_opportunity(self, opportunity: Opportunity) -> dict:
        metadata = opportunity.source_metadata or {}
        production = opportunity.production_details or {}
        role = opportunity.role_details or {}
        extracted_dates = (opportunity.extracted_facts or {}).get("dates") or {}
        return {
            "posted_date": extracted_dates.get("posted_date") or metadata.get("posted_date") or metadata.get("discovered_at"),
            "submission_deadline": (
                opportunity.submission_deadline
                or extracted_dates.get("submission_deadline")
                or role.get("submission_deadline")
                or role.get("self_tape_due_date")
                or role.get("tape_due_date")
                or role.get("due_date")
                or production.get("submission_deadline")
            ),
            "expiration_date": extracted_dates.get("expiration_date") or metadata.get("expiration_date") or production.get("expiration_date"),
            "audition_date": opportunity.audition_deadline or extracted_dates.get("audition_date") or role.get("audition_date"),
            "callback_date": opportunity.callback_date or extracted_dates.get("callback_date") or role.get("callback_date") or role.get("callback_info"),
            "shoot_or_work_dates": extracted_dates.get("shoot_or_work_dates") or production.get("shoot_dates") or production.get("work_dates"),
        }

    def _today(self, now: datetime | None) -> date:
        tz = ZoneInfo(self.user_timezone)
        value = now or datetime.now(tz)
        if value.tzinfo is None:
            value = value.replace(tzinfo=tz)
        return value.astimezone(tz).date()

    def _first_present(self, facts: dict, field_name: str):
        value = facts.get(field_name)
        if isinstance(value, list):
            return next((item for item in value if item), None)
        return value

    def _parse_date(self, value, today: date) -> date | None:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value.astimezone(ZoneInfo(self.user_timezone)).date()
        if isinstance(value, date):
            return value
        if not value:
            return None
        text = str(value).strip()
        if not text or re.search(r"\b(tbd|unknown|see source|n/?a)\b", text, flags=re.I):
            return None
        iso_match = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", text)
        if iso_match:
            return self._safe_date(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))
        slash_match = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b", text)
        if slash_match:
            year = int(slash_match.group(3))
            if year < 100:
                year += 2000
            return self._safe_date(year, int(slash_match.group(1)), int(slash_match.group(2)))
        month_match = re.search(
            r"\b("
            + "|".join(MONTHS.keys())
            + r")\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?\b",
            text,
            flags=re.I,
        )
        if month_match:
            month = MONTHS[month_match.group(1).lower().rstrip(".")]
            day = int(month_match.group(2))
            year = int(month_match.group(3)) if month_match.group(3) else today.year
            return self._safe_date(year, month, day)
        return None

    def _safe_date(self, year: int, month: int, day: int) -> date | None:
        try:
            return date(year, month, day)
        except ValueError:
            return None
