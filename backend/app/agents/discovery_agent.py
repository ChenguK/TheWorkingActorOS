from __future__ import annotations

import re
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.automation.discovery.service import DiscoveryAutomationService
from app.db.models import Opportunity


class DiscoveryAgent:
    def __init__(self, db: Session) -> None:
        self.db = db

    def run(
        self,
        discovery_mode: str = "All",
        search_modes: list[str] | str | None = None,
        specific_archetype: str | None = None,
    ) -> dict:
        automation_result = DiscoveryAutomationService(self.db).run_all(
            discovery_mode=discovery_mode,
            search_modes=search_modes,
            specific_archetype=specific_archetype,
        )
        opportunities = list(self.db.scalars(select(Opportunity).where(Opportunity.is_demo_data.is_(False))))
        keys = Counter(self._key(item) for item in opportunities)
        updated = 0
        for opportunity in opportunities:
            normalized_key = self._key(opportunity)
            opportunity.normalized_key = normalized_key
            opportunity.category = self._category(opportunity)
            opportunity.source_reliability_score = self._source_reliability(opportunity)
            opportunity.is_duplicate = keys[normalized_key] > 1
            opportunity.audition_type = self._audition_type(opportunity)
            updated += 1
        self.db.commit()
        return {
            "updated": updated,
            "duplicates": sum(1 for item in opportunities if item.is_duplicate),
            "automation": automation_result,
        }

    def _key(self, opportunity: Opportunity) -> str:
        value = f"{opportunity.project} {opportunity.role} {opportunity.location}"
        return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")

    def _category(self, opportunity: Opportunity) -> str:
        text = f"{opportunity.project} {opportunity.role} {opportunity.description}".lower()
        if "commercial" in text:
            return "Commercial"
        if "series" in text or "tv" in text or "episode" in text:
            return "Television"
        if "feature" in text or "film" in text:
            return "Film"
        if "theater" in text or "stage" in text:
            return "Theater"
        return "General Casting"

    def _source_reliability(self, opportunity: Opportunity) -> float:
        if not opportunity.source:
            return 0.7
        name = opportunity.source.name.lower()
        if any(source in name for source in ["actors access", "casting networks", "casting frontier"]):
            return 0.95
        if any(source in name for source in ["linkedin", "production", "company"]):
            return 0.8
        if any(source in name for source in ["instagram", "facebook", "threads"]):
            return 0.65
        return 0.7

    def _audition_type(self, opportunity: Opportunity) -> str:
        text = opportunity.description.lower()
        if any(term in text for term in ["self tape", "self-tape", "eco cast", "video audition"]):
            return "Self-Tape"
        if "virtual" in text or "zoom" in text:
            return "Virtual"
        if any(term in text for term in ["in-person audition", "in person audition", "live audition"]):
            return "In-Person"
        return opportunity.audition_type or "Unknown"
