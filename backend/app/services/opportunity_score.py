from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import math
import re
from typing import Iterable

from app.automation.discovery.classification import REJECTED_CLASSIFICATIONS
from app.db.models import ActorProfile, Opportunity


OPPORTUNITY_SCORING_VERSION = 1
OPPORTUNITY_SCORE_BASELINE = 50
POSITIVE_CONTRIBUTOR_LIMIT = 3
NEGATIVE_CONTRIBUTOR_LIMIT = 3
MAX_SCORE_EXPLANATION_LENGTH = 500
MAX_FACTOR_ID_LENGTH = 120
CRITICAL_OPPORTUNITY_FIELDS = (
    "project",
    "role",
    "description",
    "project_type_or_category",
    "audition_type",
    "location",
    "actionable_deadline",
)


class ScoreCategory(str, Enum):
    MATCH_QUALITY = "match_quality"
    CAREER_VALUE = "career_value"
    PRACTICALITY = "practicality"
    CONFIDENCE = "confidence"
    ACTOR_INTEREST = "actor_interest"


SCORE_CATEGORY_ORDER = (
    ScoreCategory.MATCH_QUALITY,
    ScoreCategory.CAREER_VALUE,
    ScoreCategory.PRACTICALITY,
    ScoreCategory.CONFIDENCE,
    ScoreCategory.ACTOR_INTEREST,
)
SCORE_CATEGORY_CAPS = {
    ScoreCategory.MATCH_QUALITY: (-35, 30),
    ScoreCategory.CAREER_VALUE: (-10, 20),
    ScoreCategory.PRACTICALITY: (-25, 20),
    ScoreCategory.CONFIDENCE: (-20, 15),
    ScoreCategory.ACTOR_INTEREST: (-20, 15),
}
HARD_OVERRIDE_REASON_ORDER = (
    "user_rejected",
    "deadline_expired",
    "classification_rejected",
    "demographic_incompatible",
    "excluded_role_type",
    "availability_conflict",
    "hard_travel_limit",
    "discarded",
)
HARD_OVERRIDE_EXPLANATIONS = {
    "user_rejected": "The actor explicitly rejected this opportunity.",
    "deadline_expired": "The opportunity deadline is expired.",
    "classification_rejected": "The opportunity has a rejected non-acting classification.",
    "demographic_incompatible": "Existing eligibility data proves a demographic incompatibility.",
    "excluded_role_type": "Existing eligibility data proves the role type is excluded.",
    "availability_conflict": "Existing eligibility data proves a required-date availability conflict.",
    "hard_travel_limit": "Existing eligibility data proves the audition exceeds the hard travel limit.",
    "discarded": "The opportunity is explicitly discarded by an existing eligibility decision.",
}

_FACTOR_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_.-]*$")
_ALLOWED_FEEDBACK_TYPES = {
    "This Fits Me",
    "Not My Type",
    "Interesting Stretch",
    "Save For Later",
}


def _require_plain_text(value: str, *, field_name: str, maximum: int) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be non-empty text")
    if value != value.strip():
        raise ValueError(f"{field_name} must not contain leading or trailing whitespace")
    if len(value) > maximum:
        raise ValueError(f"{field_name} must be at most {maximum} characters")
    if any(ord(character) < 32 and character not in {"\t"} for character in value):
        raise ValueError(f"{field_name} must be bounded plain text")


def _require_string_tuple(values: tuple[str, ...], *, field_name: str) -> None:
    if not isinstance(values, tuple):
        raise ValueError(f"{field_name} must be a tuple")
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError(f"{field_name} must contain only non-empty strings")


@dataclass(frozen=True)
class ScoreFactor:
    id: str
    category: ScoreCategory
    points: int
    explanation: str
    priority: int

    def __post_init__(self) -> None:
        _require_plain_text(self.id, field_name="factor id", maximum=MAX_FACTOR_ID_LENGTH)
        if not _FACTOR_ID_PATTERN.fullmatch(self.id):
            raise ValueError(
                "factor id must use lowercase letters, numbers, dots, underscores, or hyphens"
            )
        if not isinstance(self.category, ScoreCategory):
            raise ValueError("factor category is unsupported")
        if isinstance(self.points, bool) or not isinstance(self.points, int):
            raise ValueError("factor points must be an integer")
        _require_plain_text(
            self.explanation,
            field_name="factor explanation",
            maximum=MAX_SCORE_EXPLANATION_LENGTH,
        )
        if (
            isinstance(self.priority, bool)
            or not isinstance(self.priority, int)
            or self.priority < 0
        ):
            raise ValueError("factor priority must be a non-negative integer")

    def as_dict(self) -> dict[str, str | int]:
        return {
            "id": self.id,
            "category": self.category.value,
            "points": self.points,
            "explanation": self.explanation,
            "priority": self.priority,
        }


@dataclass(frozen=True)
class OpportunityScoringContext:
    career_goal_matches: tuple[str, ...] = ()
    dream_target_matches: tuple[str, ...] = ()
    watchlist_matches: tuple[str, ...] = ()
    requested_archetypes: tuple[str, ...] = ()
    submission_status: str | None = None
    feedback_type: str | None = None
    audition_travel_limit_hours: float | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "career_goal_matches",
            "dream_target_matches",
            "watchlist_matches",
            "requested_archetypes",
        ):
            _require_string_tuple(getattr(self, field_name), field_name=field_name)
        if self.submission_status is not None:
            _require_plain_text(
                self.submission_status,
                field_name="submission_status",
                maximum=80,
            )
        if self.feedback_type is not None and self.feedback_type not in _ALLOWED_FEEDBACK_TYPES:
            raise ValueError("feedback_type is unsupported")
        limit = self.audition_travel_limit_hours
        if limit is not None and (
            isinstance(limit, bool)
            or not isinstance(limit, (int, float))
            or not math.isfinite(limit)
            or limit < 0
        ):
            raise ValueError("audition_travel_limit_hours must be a finite non-negative number")


@dataclass(frozen=True)
class CategoryScore:
    category: ScoreCategory
    raw_subtotal: int
    capped_subtotal: int
    factors: tuple[ScoreFactor, ...]

    def as_dict(self) -> dict:
        return {
            "category": self.category.value,
            "raw_subtotal": self.raw_subtotal,
            "capped_subtotal": self.capped_subtotal,
            "factors": [factor.as_dict() for factor in self.factors],
        }


@dataclass(frozen=True)
class ScoreConfidence:
    level: str
    summary: str

    def as_dict(self) -> dict[str, str]:
        return {"level": self.level, "summary": self.summary}


@dataclass(frozen=True)
class ScoreExplanation:
    summary: str

    def as_dict(self) -> dict[str, str]:
        return {"summary": self.summary}


@dataclass(frozen=True)
class OpportunityScore:
    opportunity_id: str
    scoring_version: int
    overall_score: int
    baseline_score: int
    categories: tuple[CategoryScore, ...]
    positive_contributors: tuple[ScoreFactor, ...]
    negative_contributors: tuple[ScoreFactor, ...]
    hard_override: bool
    hard_override_reason: str | None
    confidence: ScoreConfidence
    explanation: ScoreExplanation

    def as_dict(self) -> dict:
        return {
            "opportunity_id": self.opportunity_id,
            "scoring_version": self.scoring_version,
            "overall_score": self.overall_score,
            "baseline_score": self.baseline_score,
            "categories": [category.as_dict() for category in self.categories],
            "positive_contributors": [factor.as_dict() for factor in self.positive_contributors],
            "negative_contributors": [factor.as_dict() for factor in self.negative_contributors],
            "hard_override": self.hard_override,
            "hard_override_reason": self.hard_override_reason,
            "confidence": self.confidence.as_dict(),
            "explanation": self.explanation.as_dict(),
        }


def build_opportunity_score(
    *,
    opportunity_id: str,
    factors: Iterable[ScoreFactor] = (),
    hard_override_reason: str | None = None,
) -> OpportunityScore:
    ordered_factors = _ordered_factors(factors)
    if hard_override_reason is not None and hard_override_reason not in HARD_OVERRIDE_REASON_ORDER:
        raise ValueError("hard override reason is unsupported")

    categories = tuple(
        _category_score(category, ordered_factors) for category in SCORE_CATEGORY_ORDER
    )
    positive = tuple(
        sorted(
            (factor for factor in ordered_factors if factor.points > 0),
            key=lambda factor: (-factor.points, factor.priority, factor.id),
        )[:POSITIVE_CONTRIBUTOR_LIMIT]
    )
    negative = tuple(
        sorted(
            (factor for factor in ordered_factors if factor.points < 0),
            key=lambda factor: (-abs(factor.points), factor.priority, factor.id),
        )[:NEGATIVE_CONTRIBUTOR_LIMIT]
    )

    if hard_override_reason is not None:
        override_explanation = HARD_OVERRIDE_EXPLANATIONS[hard_override_reason]
        return OpportunityScore(
            opportunity_id=opportunity_id,
            scoring_version=OPPORTUNITY_SCORING_VERSION,
            overall_score=0,
            baseline_score=OPPORTUNITY_SCORE_BASELINE,
            categories=categories,
            positive_contributors=positive,
            negative_contributors=negative,
            hard_override=True,
            hard_override_reason=hard_override_reason,
            confidence=ScoreConfidence(
                level="Not Scored",
                summary="Detailed confidence factors were not evaluated because a proven hard eligibility override applies.",
            ),
            explanation=ScoreExplanation(summary=override_explanation),
        )

    total = OPPORTUNITY_SCORE_BASELINE + sum(category.capped_subtotal for category in categories)
    overall_score = max(0, min(100, total))
    return OpportunityScore(
        opportunity_id=opportunity_id,
        scoring_version=OPPORTUNITY_SCORING_VERSION,
        overall_score=overall_score,
        baseline_score=OPPORTUNITY_SCORE_BASELINE,
        categories=categories,
        positive_contributors=positive,
        negative_contributors=negative,
        hard_override=False,
        hard_override_reason=None,
        confidence=ScoreConfidence(
            level="Not Scored",
            summary="Detailed confidence factors are not implemented in the version 1 scoring foundation.",
        ),
        explanation=ScoreExplanation(
            summary=(
                "The score equals the baseline plus bounded category contributions."
                if ordered_factors
                else "No detailed scoring factors apply yet; the score remains at the baseline."
            )
        ),
    )


def score_opportunity(
    opportunity: Opportunity,
    actor: ActorProfile,
    context: OpportunityScoringContext,
    *,
    as_of,
) -> OpportunityScore:
    if not isinstance(context, OpportunityScoringContext):
        raise ValueError("context must be an OpportunityScoringContext")
    if not isinstance(actor, ActorProfile):
        raise ValueError("actor must be an ActorProfile")
    if not isinstance(as_of, datetime) or as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("as_of must be timezone-aware")
    override = _hard_override_reason(opportunity)
    return build_opportunity_score(
        opportunity_id=str(opportunity.id),
        hard_override_reason=override,
    )


def _ordered_factors(factors: Iterable[ScoreFactor]) -> tuple[ScoreFactor, ...]:
    values = tuple(factors)
    if any(not isinstance(factor, ScoreFactor) for factor in values):
        raise ValueError("factors must contain only ScoreFactor values")
    ids = [factor.id for factor in values]
    if len(ids) != len(set(ids)):
        raise ValueError("factor ids must be unique")
    category_positions = {
        category: position for position, category in enumerate(SCORE_CATEGORY_ORDER)
    }
    return tuple(
        sorted(
            values,
            key=lambda factor: (
                category_positions[factor.category],
                factor.priority,
                factor.id,
            ),
        )
    )


def _category_score(
    category: ScoreCategory,
    ordered_factors: tuple[ScoreFactor, ...],
) -> CategoryScore:
    category_factors = tuple(factor for factor in ordered_factors if factor.category is category)
    raw_subtotal = sum(factor.points for factor in category_factors)
    minimum, maximum = SCORE_CATEGORY_CAPS[category]
    capped_subtotal = max(minimum, min(maximum, raw_subtotal))
    return CategoryScore(
        category=category,
        raw_subtotal=raw_subtotal,
        capped_subtotal=capped_subtotal,
        factors=category_factors,
    )


def _hard_override_reason(opportunity: Opportunity) -> str | None:
    metadata = opportunity.source_metadata or {}
    date_validation = metadata.get("date_validation") or {}
    if opportunity.hidden_by_rule == "user_rejected" or metadata.get("user_rejected") is True:
        return "user_rejected"
    if (
        opportunity.hidden_by_rule == "deadline_expired"
        or date_validation.get("status") == "Expired"
    ):
        return "deadline_expired"
    if opportunity.breakdown_classification in REJECTED_CLASSIFICATIONS:
        return "classification_rejected"
    if _has_proven_demographic_incompatibility(opportunity):
        return "demographic_incompatible"
    if opportunity.hidden_by_rule == "dealbreaker_role_type":
        return "excluded_role_type"
    if opportunity.hidden_by_rule == "dealbreaker_availability":
        return "availability_conflict"
    if opportunity.hidden_by_rule == "dealbreaker_audition_travel":
        return "hard_travel_limit"
    if opportunity.visibility_status == "discarded":
        return "discarded"
    return None


def _has_proven_demographic_incompatibility(opportunity: Opportunity) -> bool:
    if opportunity.demographic_match_status != "Not a Match":
        return False
    role_results = (opportunity.demographic_match_details or {}).get("role_results")
    if isinstance(role_results, list) and role_results:
        return all(
            isinstance(role, dict) and role.get("status") == "Not a Match" for role in role_results
        )
    return True
