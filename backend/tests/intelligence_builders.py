from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from app.db.models import ActorProfile, BreakdownRole, Opportunity
from app.services.opportunity_intelligence_service import (
    DEFAULT_EXCLUDED_ROLE_TYPES,
    DEFAULT_INCLUDED_ROLE_TYPES,
)


FIXED_ACTOR_ID = UUID("10000000-0000-0000-0000-000000000001")
FIXED_OPPORTUNITY_ID = UUID("20000000-0000-0000-0000-000000000001")
FIXED_RECOMMENDATION_ID = UUID("30000000-0000-0000-0000-000000000001")


@dataclass(frozen=True)
class IntelligenceScoringContext:
    """Test-only shape anticipated by the design; it has no production behavior."""

    goals: tuple[str, ...] = ()
    dream_targets: tuple[str, ...] = ()
    watchlist_matches: tuple[str, ...] = ()
    submission_status: str | None = None
    feedback_type: str | None = None
    travel_preference: str | None = None


def fixed_as_of() -> datetime:
    return datetime.fromisoformat("2026-08-02T12:00:00+00:00")


def actor_profile(**overrides: Any) -> ActorProfile:
    values = {
        "id": FIXED_ACTOR_ID,
        "name": "Test Actor",
        "sag_status": "SAG-AFTRA",
        "union_status": "SAG-AFTRA",
        "current_location": "Philadelphia, PA",
        "playable_age_min": 30,
        "playable_age_max": 40,
        "skills": ["Stage Combat"],
        "gender_identities": ["Woman"],
        "gender_expression": "Female Presenting",
        "ethnicities": ["African American"],
        "racial_identities": ["Black"],
        "nationalities": [],
        "languages": ["English"],
        "accents": [],
        "disability_identities": [],
        "included_role_types": list(DEFAULT_INCLUDED_ROLE_TYPES),
        "excluded_role_types": list(DEFAULT_EXCLUDED_ROLE_TYPES),
    }
    values.update(overrides)
    return ActorProfile(**values)


def opportunity(**overrides: Any) -> Opportunity:
    values = {
        "id": FIXED_OPPORTUNITY_ID,
        "role": "Detective",
        "project": "Test Procedural",
        "project_type": "Television",
        "role_type": "Guest Star",
        "union": "SAG-AFTRA",
        "location": "Philadelphia, PA",
        "description": "A detailed acting notice for a grounded detective role. " * 5,
        "original_post_url": "https://example.test/casting/detective",
        "normalized_key": "test-procedural|detective|philadelphia",
        "status": "open",
        "breakdown_classification": "Acting Role",
        "audition_type": "Self-Tape",
        "visibility_status": "visible",
        "priority": "Medium",
        "source_reliability_score": 0.9,
        "is_duplicate": False,
        "demographic_match_status": "Match",
        "source_metadata": {
            "provider": "test-provider",
            "breakdown_parse_confidence": 92,
            "trust_verification": {"status": "Verified", "reasons": ["test evidence"]},
            "discovery": {"run_id": "test-run", "candidate_index": 0},
        },
        "production_details": {"project_type": "Television", "provider_marker": "keep"},
        "role_details": {"language": "English", "private_test_marker": "keep"},
        "extracted_facts": {"provider_evidence": {"title": "Bounded test evidence"}},
        "ai_inference": {"classification_version": "test-v1"},
        "urgency_score": 7,
        "quality_score": 11,
    }
    values.update(overrides)
    item = Opportunity(**values)
    item.breakdown_roles = list(overrides.get("breakdown_roles", []))
    item.submissions = list(overrides.get("submissions", []))
    return item


def parsed_role(**overrides: Any) -> BreakdownRole:
    values = {
        "id": UUID("21000000-0000-0000-0000-000000000001"),
        "breakdown_id": FIXED_OPPORTUNITY_ID,
        "role_name": "Detective",
        "role_type": "Guest Star",
        "character_description": "Grounded detective who leads the investigation.",
        "language_requirements": "English",
        "union_status": "SAG-AFTRA",
        "fit_status": "Strong Fit",
        "fit_score": 90,
        "confidence_score": 92,
        "extracted_facts": {"source": "test parser"},
        "ai_inference": {},
    }
    values.update(overrides)
    return BreakdownRole(**values)


def scoring_context(**overrides: Any) -> IntelligenceScoringContext:
    values = {
        "goals": ("Television Guest Star",),
        "dream_targets": ("Test Procedural",),
        "watchlist_matches": ("Detective",),
        "submission_status": None,
        "feedback_type": "This Fits Me",
        "travel_preference": "Local or self-tape",
    }
    values.update(overrides)
    return IntelligenceScoringContext(**values)


def opportunity_snapshot(item: Opportunity) -> dict[str, Any]:
    """Snapshot every mapped scalar for future read-only scorer assertions."""

    return {
        attribute.key: deepcopy(getattr(item, attribute.key))
        for attribute in Opportunity.__mapper__.column_attrs
    }


def boundary_snapshot(item: Opportunity) -> dict[str, Any]:
    """Snapshot state outside ordinary score projections."""

    fields = (
        "visibility_status",
        "status",
        "breakdown_classification",
        "hidden_by_rule",
        "hidden_reason",
        "rejection_reason",
        "highlighted_text_as_rejection_reason",
        "manual_review_required",
        "original_post_url",
        "normalized_key",
        "is_duplicate",
        "source_metadata",
        "production_details",
        "role_details",
        "extracted_facts",
        "ai_inference",
    )
    return {field: deepcopy(getattr(item, field)) for field in fields}
