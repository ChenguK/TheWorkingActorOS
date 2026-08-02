from __future__ import annotations

import json

from app.services.opportunity_score import OpportunityScore, ScoreFactor, SuggestedAction


COMMAND_CENTER_INTELLIGENCE_VERSION = 1
COMMAND_CENTER_CONTRIBUTOR_LIMIT = 3
COMMAND_CENTER_INTELLIGENCE_MAX_BYTES = 2_048

ACTION_LABELS = {
    SuggestedAction.IGNORE: "Ignore",
    SuggestedAction.SAVE_FOR_LATER: "Save for Later",
    SuggestedAction.GOOD_STRETCH_ROLE: "Good Stretch Role",
    SuggestedAction.APPLY_NOW: "Apply Now",
    SuggestedAction.REVIEW_TODAY: "Review Today",
    SuggestedAction.LOW_PRIORITY: "Low Priority",
}
CONFIDENCE_SUMMARIES = {
    "High": "This recommendation is supported by strong and complete opportunity information.",
    "Medium": "This recommendation is supported, but some opportunity information may need review.",
    "Low": "Important opportunity details are missing or uncertain.",
    "Not Scored": "The available opportunity information produced a neutral recommendation.",
}
PUBLIC_FACTOR_EXPLANATIONS = {
    "match.role_fit.strong": "The strongest parsed role is a strong fit.",
    "match.role_fit.possible": "The strongest parsed role is a possible fit.",
    "match.role_fit.stretch": "The strongest parsed role is a stretch fit.",
    "match.role_fit.none": "The parsed roles do not currently indicate a fit.",
    "practicality.audition.remote": "The audition can be completed remotely.",
    "practicality.travel.local": "The opportunity is compatible with saved local-work preferences.",
    "practicality.travel.exception": "The opportunity requires additional travel review.",
    "practicality.travel.covered": "Travel support is listed.",
    "practicality.housing.covered": "Housing support is listed.",
    "practicality.compensation.known": "Compensation information is available.",
    "practicality.deadline.missing": "No actionable deadline is currently available.",
    "practicality.deadline.within_24h": "The deadline is within 24 hours.",
    "practicality.deadline.within_72h": "The deadline is within 72 hours.",
    "practicality.deadline.within_7d": "The deadline is within seven days.",
    "practicality.deadline.distant": "The deadline does not require immediate action.",
    "confidence.parser.missing": "Parsed opportunity details are unavailable.",
    "confidence.parser.high": "Parsed opportunity details have high confidence.",
    "confidence.parser.medium": "Parsed opportunity details have medium confidence.",
    "confidence.parser.low": "Parsed opportunity details have low confidence.",
    "confidence.trust.verified": "The opportunity passed the current trust checks.",
    "confidence.trust.review": "The opportunity needs additional trust review.",
    "confidence.source.high": "The source has high reliability.",
    "confidence.source.medium": "The source has medium reliability.",
    "confidence.source.low": "The source has low reliability.",
    "confidence.completeness.complete": "The important opportunity details are complete.",
    "confidence.completeness.incomplete": "Some important opportunity details are incomplete.",
}
PUBLIC_HARD_OVERRIDE_REASONS = {
    "user_rejected": "user_rejected",
    "deadline_expired": "expired",
    "classification_rejected": "rejected_classification",
    "demographic_incompatible": "profile_incompatibility",
    "excluded_role_type": "profile_incompatibility",
    "availability_conflict": "availability_conflict",
    "hard_travel_limit": "travel_limit",
    "discarded": "discarded",
}


def _serialize_contributor(factor: ScoreFactor) -> dict[str, str | int]:
    result: dict[str, str | int] = {"id": factor.id, "points": factor.points}
    explanation = PUBLIC_FACTOR_EXPLANATIONS.get(factor.id)
    if explanation is not None:
        result["explanation"] = explanation
    return result


def serialize_command_center_intelligence(score: OpportunityScore) -> dict:
    """Build the bounded actor-facing projection from one completed score."""
    summary = {
        "version": COMMAND_CENTER_INTELLIGENCE_VERSION,
        "overall_score": score.overall_score,
        "action": score.suggested_action.action.value,
        "action_label": ACTION_LABELS[score.suggested_action.action],
        "action_reason_code": score.suggested_action.reason_code,
        "confidence": {
            "level": score.confidence.level,
            "summary": CONFIDENCE_SUMMARIES[score.confidence.level],
        },
        "hard_override": score.hard_override,
        "hard_override_reason": PUBLIC_HARD_OVERRIDE_REASONS.get(score.hard_override_reason),
        "top_positive_contributors": [
            _serialize_contributor(factor)
            for factor in score.positive_contributors[:COMMAND_CENTER_CONTRIBUTOR_LIMIT]
        ],
        "top_negative_contributors": [
            _serialize_contributor(factor)
            for factor in score.negative_contributors[:COMMAND_CENTER_CONTRIBUTOR_LIMIT]
        ],
    }
    serialized_size = len(
        json.dumps(summary, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    if serialized_size > COMMAND_CENTER_INTELLIGENCE_MAX_BYTES:
        raise ValueError("command-center intelligence summary exceeds its size limit")
    return summary
