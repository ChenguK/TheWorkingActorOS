from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import math
import re
from typing import Iterable

from app.automation.discovery.classification import REJECTED_CLASSIFICATIONS
from app.db.models import ActorProfile, BreakdownRole, Opportunity
from app.services.demographic_match_service import LANGUAGE_GROUPS


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
_ALLOWED_SUBMISSION_STATUSES = {
    "Submitted",
    "Requested",
    "Self-Tape Callback",
    "In-Person Callback",
    "Pinned",
    "Booked",
    "Passed",
    "No Response",
}
_WATCHLIST_POINTS = {"High": 8, "Medium": 5, "Low": 3}
_WATCHLIST_PRIORITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}
_FEEDBACK_POINTS = {
    "This Fits Me": ("interest.feedback.fits_me", 6, "Latest feedback says This Fits Me (+6)."),
    "Interesting Stretch": (
        "interest.feedback.interesting_stretch",
        4,
        "Latest feedback says Interesting Stretch (+4).",
    ),
    "Save For Later": (
        "interest.feedback.save_later",
        2,
        "Latest feedback says Save For Later (+2).",
    ),
    "Not My Type": ("interest.feedback.not_my_type", -8, "Latest feedback says Not My Type (-8)."),
}
_MISSING_SENTINELS = {"unknown", "see source", "n/a", "na", "none", "tbd", "not provided"}
_FIT_PRECEDENCE = {
    "strong fit": (0, "match.role_fit.strong", 18, "Strong Fit is the best parsed role fit (+18)."),
    "possible fit": (
        1,
        "match.role_fit.possible",
        10,
        "Possible Fit is the best parsed role fit (+10).",
    ),
    "stretch fit": (
        2,
        "match.role_fit.stretch",
        6,
        "Stretch Fit is the best parsed role fit (+6).",
    ),
    "needs review": (3, None, 0, None),
    "not fit": (4, "match.role_fit.none", -25, "Parsed roles exist, but none currently fit (-25)."),
}
_AMBIGUOUS_LANGUAGE_TERMS = ("preferred", "preference", "a plus", "helpful", "optional", "ideally")
_UNION_ALIASES = {
    "sag": "sag-aftra",
    "aftra": "sag-aftra",
    "sag aftra": "sag-aftra",
    "sag-aftra": "sag-aftra",
    "equity": "aea",
    "aea": "aea",
    "non union": "non-union",
    "non-union": "non-union",
    "union": "union",
    "both": "union-and-non-union",
    "union and non union": "union-and-non-union",
    "union and non-union": "union-and-non-union",
}
_ROLE_TYPE_ALIASES = {
    "co star": "co-star",
    "costar": "co-star",
    "guest-star": "guest star",
    "series-regular": "series regular",
    "voice over": "voiceover",
}


@dataclass(frozen=True)
class ScoringContextMatch:
    label: str
    active: bool = True

    def __post_init__(self) -> None:
        _require_plain_text(self.label, field_name="match label", maximum=120)
        if not isinstance(self.active, bool):
            raise ValueError("match active state must be boolean")


@dataclass(frozen=True)
class WatchListScoringMatch:
    key: str
    priority: str
    enabled: bool = True

    def __post_init__(self) -> None:
        _require_plain_text(self.key, field_name="watch-list key", maximum=120)
        if self.priority not in _WATCHLIST_POINTS:
            raise ValueError("watch-list priority is unsupported")
        if not isinstance(self.enabled, bool):
            raise ValueError("watch-list enabled state must be boolean")


@dataclass(frozen=True)
class FeedbackScoringEntry:
    key: str
    feedback_type: str
    created_at: datetime

    def __post_init__(self) -> None:
        _require_plain_text(self.key, field_name="feedback key", maximum=120)
        _require_plain_text(self.feedback_type, field_name="feedback type", maximum=80)
        if (
            not isinstance(self.created_at, datetime)
            or self.created_at.tzinfo is None
            or self.created_at.utcoffset() is None
        ):
            raise ValueError("feedback created_at must be timezone-aware")


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
    career_goal_matches: tuple[ScoringContextMatch, ...] = ()
    dream_target_matches: tuple[ScoringContextMatch, ...] = ()
    watchlist_matches: tuple[WatchListScoringMatch, ...] = ()
    requested_archetypes: tuple[str, ...] = ()
    stretch_archetype_matches: tuple[str, ...] = ()
    submission_status: str | None = None
    feedback_type: str | None = None
    feedback_entries: tuple[FeedbackScoringEntry, ...] = ()
    audition_travel_limit_hours: float | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "requested_archetypes",
            "stretch_archetype_matches",
        ):
            _require_string_tuple(getattr(self, field_name), field_name=field_name)
        for field_name in ("career_goal_matches", "dream_target_matches"):
            values = getattr(self, field_name)
            if not isinstance(values, tuple) or any(
                not isinstance(value, ScoringContextMatch) for value in values
            ):
                raise ValueError(f"{field_name} must contain only ScoringContextMatch values")
        if not isinstance(self.watchlist_matches, tuple) or any(
            not isinstance(value, WatchListScoringMatch) for value in self.watchlist_matches
        ):
            raise ValueError("watchlist_matches must contain only WatchListScoringMatch values")
        if not isinstance(self.feedback_entries, tuple) or any(
            not isinstance(value, FeedbackScoringEntry) for value in self.feedback_entries
        ):
            raise ValueError("feedback_entries must contain only FeedbackScoringEntry values")
        if self.submission_status is not None:
            _require_plain_text(
                self.submission_status,
                field_name="submission_status",
                maximum=80,
            )
            if self.submission_status not in _ALLOWED_SUBMISSION_STATUSES:
                raise ValueError("submission_status is unsupported")
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
    confidence_category = next(
        category for category in categories if category.category is ScoreCategory.CONFIDENCE
    )
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
        confidence=_score_confidence(confidence_category),
        explanation=ScoreExplanation(
            summary=(
                "The score equals the baseline plus bounded category contributions."
                if ordered_factors
                else "No detailed scoring factors apply yet; the score remains at the baseline."
            )
        ),
    )


def _score_confidence(category: CategoryScore) -> ScoreConfidence:
    if not category.factors:
        return ScoreConfidence(
            level="Not Scored",
            summary="Detailed confidence factors are not implemented in the version 1 scoring foundation.",
        )
    if category.capped_subtotal >= 10:
        level = "High"
    elif category.capped_subtotal >= 0:
        level = "Medium"
    else:
        level = "Low"
    return ScoreConfidence(
        level=level,
        summary=(
            f"{level} confidence: {len(category.factors)} bounded confidence factors "
            f"contribute {category.capped_subtotal:+d} points."
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
    factors = (
        ()
        if override
        else (
            *_match_and_career_factors(opportunity, actor, context),
            *_practicality_factors(opportunity, context, as_of),
            *_confidence_factors(opportunity),
            *_actor_interest_factors(context),
        )
    )
    return build_opportunity_score(
        opportunity_id=str(opportunity.id),
        factors=factors,
        hard_override_reason=override,
    )


def _match_and_career_factors(
    opportunity: Opportunity,
    actor: ActorProfile,
    context: OpportunityScoringContext,
) -> tuple[ScoreFactor, ...]:
    factors: list[ScoreFactor] = []
    best_role, fit_factor = _best_role_fit(opportunity)
    if fit_factor:
        factors.append(fit_factor)
    if opportunity.demographic_match_status == "Match":
        factors.append(
            ScoreFactor(
                id="match.demographic.confirmed",
                category=ScoreCategory.MATCH_QUALITY,
                points=8,
                explanation="Existing demographic matching confirms actor and role overlap (+8).",
                priority=20,
            )
        )
    if _has_preferred_role_type(opportunity, best_role, actor):
        factors.append(
            ScoreFactor(
                id="match.role_type.preferred",
                category=ScoreCategory.MATCH_QUALITY,
                points=4,
                explanation="The structured role type is explicitly included in actor preferences (+4).",
                priority=30,
            )
        )
    language_factor = _language_factor(best_role, actor)
    if language_factor:
        factors.append(language_factor)
    if _has_explicit_union_compatibility(opportunity, best_role, actor):
        factors.append(
            ScoreFactor(
                id="match.union.compatible",
                category=ScoreCategory.MATCH_QUALITY,
                points=3,
                explanation="Stored actor and role union states are explicitly compatible (+3).",
                priority=50,
            )
        )

    active_goals = _active_match_labels(context.career_goal_matches)
    if active_goals:
        factors.append(
            ScoreFactor(
                id="career.goal.active_match",
                category=ScoreCategory.CAREER_VALUE,
                points=8,
                explanation=f"Active career goal explicitly matches: {active_goals[0]} (+8).",
                priority=100,
            )
        )
    active_targets = _active_match_labels(context.dream_target_matches)
    if active_targets:
        factors.append(
            ScoreFactor(
                id="career.dream_target.match",
                category=ScoreCategory.CAREER_VALUE,
                points=7,
                explanation=f"Dream target explicitly matches: {active_targets[0]} (+7).",
                priority=110,
            )
        )
    if _is_stretch_fit(best_role) and (
        active_goals or _normalized_strings(context.stretch_archetype_matches)
    ):
        support = (
            _normalized_strings(context.stretch_archetype_matches)[0]
            if context.stretch_archetype_matches
            else active_goals[0]
        )
        factors.append(
            ScoreFactor(
                id="career.stretch.strategic",
                category=ScoreCategory.CAREER_VALUE,
                points=5,
                explanation=f"Stretch Fit has explicit strategic support: {support} (+5).",
                priority=130,
            )
        )
    return tuple(factors)


def _practicality_factors(
    opportunity: Opportunity,
    context: OpportunityScoringContext,
    as_of: datetime,
) -> tuple[ScoreFactor, ...]:
    factors: list[ScoreFactor] = []
    modality = _normalize_text(opportunity.audition_type)
    if modality in {"self-tape", "virtual"}:
        factors.append(
            _factor(
                "practicality.audition.remote",
                ScoreCategory.PRACTICALITY,
                8,
                "The audition is explicitly remote (+8).",
                200,
            )
        )
    elif modality == "in-person" and _is_proven_local(opportunity, context):
        factors.append(
            _factor(
                "practicality.travel.local",
                ScoreCategory.PRACTICALITY,
                4,
                "Stored audition travel is within the saved local threshold (+4).",
                210,
            )
        )
    if (
        opportunity.visibility_status == "travel_exception"
        or opportunity.hidden_by_rule == "travel_exception"
    ):
        factors.append(
            _factor(
                "practicality.travel.exception",
                ScoreCategory.PRACTICALITY,
                -15,
                "Existing eligibility state marks this as a travel exception (-15).",
                211,
            )
        )
    if opportunity.travel_covered is True:
        factors.append(
            _factor(
                "practicality.travel.covered",
                ScoreCategory.PRACTICALITY,
                4,
                "Production explicitly covers travel (+4).",
                220,
            )
        )
    if opportunity.housing_covered is True:
        factors.append(
            _factor(
                "practicality.housing.covered",
                ScoreCategory.PRACTICALITY,
                4,
                "Production explicitly covers housing (+4).",
                221,
            )
        )
    if _present_text(opportunity.rate):
        factors.append(
            _factor(
                "practicality.compensation.known",
                ScoreCategory.PRACTICALITY,
                3,
                "Compensation or rate is explicitly provided (+3).",
                230,
            )
        )
    factors.append(_deadline_factor(opportunity, as_of))
    return tuple(factors)


def _confidence_factors(opportunity: Opportunity) -> tuple[ScoreFactor, ...]:
    factors = [_parse_confidence_factor(opportunity)]
    trust = _trust_factor(opportunity)
    if trust:
        factors.append(trust)
    reliability = _source_reliability_factor(opportunity)
    if reliability:
        factors.append(reliability)
    completeness = _completeness_factor(opportunity)
    if completeness:
        factors.append(completeness)
    return tuple(factors)


def _actor_interest_factors(context: OpportunityScoringContext) -> tuple[ScoreFactor, ...]:
    factors = []
    enabled = [match for match in context.watchlist_matches if match.enabled]
    if enabled:
        selected = min(
            enabled,
            key=lambda match: (
                _WATCHLIST_PRIORITY_ORDER[match.priority],
                _normalize_text(match.key),
                match.key,
            ),
        )
        points = _WATCHLIST_POINTS[selected.priority]
        factors.append(
            _factor(
                f"interest.watchlist.{selected.priority.lower()}",
                ScoreCategory.ACTOR_INTEREST,
                points,
                f"Highest enabled watch-list match has {selected.priority} priority (+{points}).",
                400,
            )
        )
    if context.feedback_entries:
        selected = min(
            context.feedback_entries,
            key=lambda entry: (
                -entry.created_at.astimezone(timezone.utc).timestamp(),
                _normalize_text(entry.key),
                entry.key,
            ),
        )
        feedback = _FEEDBACK_POINTS.get(selected.feedback_type)
        if feedback:
            factor_id, points, explanation = feedback
            factors.append(
                _factor(factor_id, ScoreCategory.ACTOR_INTEREST, points, explanation, 410)
            )
    return tuple(factors)


def _factor(
    factor_id: str, category: ScoreCategory, points: int, explanation: str, priority: int
) -> ScoreFactor:
    return ScoreFactor(
        id=factor_id, category=category, points=points, explanation=explanation, priority=priority
    )


def _is_proven_local(opportunity: Opportunity, context: OpportunityScoringContext) -> bool:
    limit = context.audition_travel_limit_hours
    drive = opportunity.audition_drive_time
    return (
        limit is not None
        and isinstance(drive, (int, float))
        and not isinstance(drive, bool)
        and math.isfinite(drive)
        and drive >= 0
        and drive <= limit
        and opportunity.visibility_status != "travel_exception"
    )


def _deadline_factor(opportunity: Opportunity, as_of: datetime) -> ScoreFactor:
    valid = []
    for value in (opportunity.submission_deadline, opportunity.audition_deadline):
        if not isinstance(value, datetime):
            continue
        aware = (
            value
            if value.tzinfo and value.utcoffset() is not None
            else value.replace(tzinfo=timezone.utc)
        )
        remaining = (
            aware.astimezone(timezone.utc) - as_of.astimezone(timezone.utc)
        ).total_seconds()
        if remaining > 0:
            valid.append(remaining)
    if not valid:
        return _factor(
            "practicality.deadline.missing",
            ScoreCategory.PRACTICALITY,
            -5,
            "No future actionable submission or audition deadline is available (-5).",
            240,
        )
    seconds = min(valid)
    if seconds <= 24 * 3600:
        return _factor(
            "practicality.deadline.within_24h",
            ScoreCategory.PRACTICALITY,
            8,
            "The earliest actionable deadline is within 24 hours (+8).",
            240,
        )
    if seconds <= 72 * 3600:
        return _factor(
            "practicality.deadline.within_72h",
            ScoreCategory.PRACTICALITY,
            5,
            "The earliest actionable deadline is within 72 hours (+5).",
            240,
        )
    if seconds <= 168 * 3600:
        return _factor(
            "practicality.deadline.within_7d",
            ScoreCategory.PRACTICALITY,
            2,
            "The earliest actionable deadline is within seven days (+2).",
            240,
        )
    return _factor(
        "practicality.deadline.distant",
        ScoreCategory.PRACTICALITY,
        0,
        "The earliest actionable deadline is more than seven days away (0).",
        240,
    )


def _parse_confidence_factor(opportunity: Opportunity) -> ScoreFactor:
    raw = (opportunity.source_metadata or {}).get("breakdown_parse_confidence")
    value = _bounded_number(raw, 0, 100)
    if value is None:
        return _factor(
            "confidence.parser.missing",
            ScoreCategory.CONFIDENCE,
            -4,
            "Parser confidence is missing or invalid (-4).",
            300,
        )
    if value >= 85:
        return _factor(
            "confidence.parser.high",
            ScoreCategory.CONFIDENCE,
            6,
            "Parser confidence is at least 85 (+6).",
            300,
        )
    if value >= 70:
        return _factor(
            "confidence.parser.medium",
            ScoreCategory.CONFIDENCE,
            3,
            "Parser confidence is between 70 and 85 (+3).",
            300,
        )
    return _factor(
        "confidence.parser.low",
        ScoreCategory.CONFIDENCE,
        -6,
        "Parser confidence is below 70 (-6).",
        300,
    )


def _trust_factor(opportunity: Opportunity) -> ScoreFactor | None:
    status = _normalize_text(
        ((opportunity.source_metadata or {}).get("trust_verification") or {}).get("status")
    )
    if status in {"verified", "pass", "passing"}:
        return _factor(
            "confidence.trust.verified",
            ScoreCategory.CONFIDENCE,
            5,
            "Stored trust verification is passing (+5).",
            310,
        )
    if status in {"needs info", "review", "warning", "blocked"}:
        return _factor(
            "confidence.trust.review",
            ScoreCategory.CONFIDENCE,
            -5,
            "Stored trust verification requires review (-5).",
            310,
        )
    return None


def _source_reliability_factor(opportunity: Opportunity) -> ScoreFactor | None:
    value = _bounded_number(opportunity.source_reliability_score, 0, 1)
    if value is None:
        return None
    if value >= 0.85:
        return _factor(
            "confidence.source.high",
            ScoreCategory.CONFIDENCE,
            4,
            "Source reliability is at least 0.85 (+4).",
            320,
        )
    if value >= 0.70:
        return _factor(
            "confidence.source.medium",
            ScoreCategory.CONFIDENCE,
            2,
            "Source reliability is at least 0.70 (+2).",
            320,
        )
    if value < 0.50:
        return _factor(
            "confidence.source.low",
            ScoreCategory.CONFIDENCE,
            -4,
            "Source reliability is below 0.50 (-4).",
            320,
        )
    return None


def _completeness_factor(opportunity: Opportunity) -> ScoreFactor | None:
    values = (
        opportunity.project,
        opportunity.role,
        opportunity.description,
        opportunity.project_type or opportunity.category,
        opportunity.audition_type,
        opportunity.location,
        isinstance(opportunity.submission_deadline, datetime)
        or isinstance(opportunity.audition_deadline, datetime),
    )
    missing = sum(not _present_value(value) for value in values)
    if missing == 0:
        return _factor(
            "confidence.completeness.complete",
            ScoreCategory.CONFIDENCE,
            4,
            "All seven critical opportunity fields are present (+4).",
            330,
        )
    if missing >= 2:
        return _factor(
            "confidence.completeness.incomplete",
            ScoreCategory.CONFIDENCE,
            -5,
            f"{missing} of seven critical opportunity fields are missing (-5).",
            330,
        )
    return None


def _bounded_number(value, minimum: float, maximum: float) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and minimum <= number <= maximum else None


def _present_text(value) -> bool:
    text = _normalize_text(value)
    return bool(text) and text not in _MISSING_SENTINELS


def _present_value(value) -> bool:
    return _present_text(value) if isinstance(value, str) or value is None else True


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


def _best_role_fit(opportunity: Opportunity) -> tuple[BreakdownRole | None, ScoreFactor | None]:
    candidates = []
    has_unknown_fit = False
    for role in opportunity.breakdown_roles:
        normalized_fit = _normalize_text(role.fit_status)
        fit = _FIT_PRECEDENCE.get(normalized_fit)
        if fit is None:
            has_unknown_fit = True
            continue
        candidates.append((fit[0], _role_stable_key(role), role, fit))
    if not candidates:
        return None, None
    _, _, selected_role, selected_fit = min(candidates, key=lambda value: (value[0], value[1]))
    _, factor_id, points, explanation = selected_fit
    if factor_id == "match.role_fit.none" and has_unknown_fit:
        return selected_role, None
    if factor_id is None:
        return selected_role, None
    return selected_role, ScoreFactor(
        id=factor_id,
        category=ScoreCategory.MATCH_QUALITY,
        points=points,
        explanation=explanation,
        priority=10,
    )


def _role_stable_key(role: BreakdownRole) -> tuple[str, ...]:
    return tuple(
        _normalize_text(value)
        for value in (
            role.role_name,
            role.role_type,
            role.billing,
            role.billing_or_role_type,
            role.language_requirements,
            role.union_status,
        )
    )


def _has_preferred_role_type(
    opportunity: Opportunity,
    best_role: BreakdownRole | None,
    actor: ActorProfile,
) -> bool:
    preferences = {
        _normalize_role_type(value)
        for value in actor.included_role_types or []
        if str(value).strip()
    }
    if not preferences:
        return False
    candidates = [opportunity.role_type]
    if best_role:
        candidates.extend((best_role.role_type, best_role.billing, best_role.billing_or_role_type))
    return bool(
        preferences.intersection(_normalize_role_type(value) for value in candidates if value)
    )


def _language_factor(best_role: BreakdownRole | None, actor: ActorProfile) -> ScoreFactor | None:
    if best_role is None or not best_role.language_requirements:
        return None
    requirement = _normalize_text(best_role.language_requirements)
    if not requirement or any(term in requirement for term in _AMBIGUOUS_LANGUAGE_TERMS):
        return None
    required = _recognized_languages(requirement)
    if not required:
        return None
    actor_languages = {_canonical_language(value) for value in actor.languages or []}
    if required.issubset(actor_languages):
        return ScoreFactor(
            id="match.language.required_met",
            category=ScoreCategory.MATCH_QUALITY,
            points=4,
            explanation="All explicit required languages are present in the saved actor profile (+4).",
            priority=40,
        )
    return ScoreFactor(
        id="match.language.required_missing",
        category=ScoreCategory.MATCH_QUALITY,
        points=-8,
        explanation="At least one explicit required language is absent from the saved actor profile (-8).",
        priority=40,
    )


def _recognized_languages(requirement: str) -> set[str]:
    recognized = set()
    for group in LANGUAGE_GROUPS:
        terms = sorted((str(term) for term in group.terms), key=lambda value: (-len(value), value))
        if any(
            re.search(rf"\b{re.escape(_normalize_text(term))}\b", requirement) for term in terms
        ):
            recognized.add(_canonical_language(group.label))
    return recognized


def _canonical_language(value: str) -> str:
    normalized = _normalize_text(value)
    for group in LANGUAGE_GROUPS:
        labels = {_normalize_text(group.label), *(_normalize_text(term) for term in group.terms)}
        if normalized in labels:
            return _normalize_text(group.label)
    return normalized


def _has_explicit_union_compatibility(
    opportunity: Opportunity,
    best_role: BreakdownRole | None,
    actor: ActorProfile,
) -> bool:
    role_union = _canonical_union(
        best_role.union_status if best_role and best_role.union_status else opportunity.union
    )
    actor_unions = {
        union
        for union in (_canonical_union(actor.union_status), _canonical_union(actor.sag_status))
        if union is not None
    }
    if role_union is None or not actor_unions:
        return False
    if "union-and-non-union" in actor_unions:
        return role_union in {"sag-aftra", "aea", "union", "non-union"}
    return role_union in actor_unions


def _canonical_union(value: str | None) -> str | None:
    normalized = _normalize_text(value)
    if not normalized or normalized in {"unknown", "uncertain", "n/a", "na"}:
        return None
    return _UNION_ALIASES.get(normalized)


def _active_match_labels(matches: tuple[ScoringContextMatch, ...]) -> tuple[str, ...]:
    labels = {" ".join(match.label.split()) for match in matches if match.active}
    return tuple(sorted(labels, key=lambda value: (_normalize_text(value), value)))


def _normalized_strings(values: tuple[str, ...]) -> tuple[str, ...]:
    normalized = {" ".join(value.split()) for value in values}
    return tuple(sorted(normalized, key=lambda value: (_normalize_text(value), value)))


def _is_stretch_fit(role: BreakdownRole | None) -> bool:
    return role is not None and _normalize_text(role.fit_status) == "stretch fit"


def _normalize_role_type(value: str) -> str:
    normalized = _normalize_text(value).replace("–", "-")
    return _ROLE_TYPE_ALIASES.get(normalized, normalized)


def _normalize_text(value) -> str:
    return " ".join(str(value or "").casefold().split())


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
