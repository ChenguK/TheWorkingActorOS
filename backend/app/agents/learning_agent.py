from __future__ import annotations

from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ActorProfile, CallbackEvent, LearningInsight, RecommendationFeedback, Submission


POSITIVE_STATUSES = {"Requested", "Self-Tape Callback", "In-Person Callback", "Pinned", "Booked"}
OUTCOME_STATUSES = {"Requested", "Self-Tape Callback", "In-Person Callback", "Pinned", "Booked", "Passed", "No Response"}
MIN_OUTCOME_SUBMISSIONS = 10


class LearningAgent:
    def __init__(self, db: Session) -> None:
        self.db = db

    def analyze(self, actor: ActorProfile) -> LearningInsight:
        submissions = list(
            self.db.scalars(select(Submission).where(Submission.actor_profile_id == actor.id))
        )
        submissions = [
            submission
            for submission in submissions
            if not submission.opportunity or not submission.opportunity.is_demo_data
        ]
        outcome_count = len([submission for submission in submissions if submission.current_status in OUTCOME_STATUSES])
        positive_assets: Counter[str] = Counter()
        status_counts: Counter[str] = Counter()
        callback_progression: Counter[str] = Counter()
        fit_feedback: Counter[str] = Counter()
        stretch_feedback: Counter[str] = Counter()
        negative_feedback: Counter[str] = Counter()
        saved_for_later: Counter[str] = Counter()
        for submission in submissions:
            status_counts[submission.current_status] += 1
            if submission.current_status in POSITIVE_STATUSES:
                for asset in submission.assets:
                    positive_assets.update(asset.archetype_names)
        for event in self.db.scalars(select(CallbackEvent)).all():
            callback_progression[event.event_type] += 1
        feedback_rows = list(
            self.db.scalars(select(RecommendationFeedback).where(RecommendationFeedback.actor_profile_id == actor.id))
        )
        feedback_rows = [
            feedback
            for feedback in feedback_rows
            if not feedback.opportunity or not feedback.opportunity.is_demo_data
        ]
        for feedback in feedback_rows:
            target = {
                "This Fits Me": fit_feedback,
                "Interesting Stretch": stretch_feedback,
                "Not My Type": negative_feedback,
                "Save For Later": saved_for_later,
            }.get(feedback.feedback_type)
            if target is None:
                continue
            reasons = feedback.fit_reasons or [feedback.feedback_type]
            for reason in reasons:
                target.update([str(reason)])
        boosted = [name for name, _ in positive_assets.most_common(5)]
        user_boosted = [name for name, _ in fit_feedback.most_common(8)]
        user_stretch = [name for name, _ in stretch_feedback.most_common(8)]
        user_suppressed = [name for name, _ in negative_feedback.most_common(8)]
        trends = {
            "status_counts": dict(status_counts),
            "callback_progression": dict(callback_progression),
            "highest_performing_archetypes": boosted,
            "submission_count": len(submissions),
            "outcome_submission_count": outcome_count,
            "data_sufficiency": "Configured" if outcome_count >= MIN_OUTCOME_SUBMISSIONS else "Insufficient Data",
            "user_feedback_count": len(feedback_rows),
            "user_fit_feedback": dict(fit_feedback),
            "user_stretch_feedback": dict(stretch_feedback),
            "user_not_my_type_feedback": dict(negative_feedback),
            "user_saved_for_later_feedback": dict(saved_for_later),
        }
        weights = {
            "boosted_archetypes": boosted,
            "user_boosted_reasons": user_boosted,
            "user_stretch_reasons": user_stretch,
            "user_suppressed_reasons": user_suppressed,
            "saved_for_later_reasons": [name for name, _ in saved_for_later.most_common(8)],
            "user_feedback_weight": 3,
            "inferred_feedback_weight": 1,
            "callback_progression": dict(callback_progression),
            "callback_statuses": sorted(POSITIVE_STATUSES),
        }
        if outcome_count < MIN_OUTCOME_SUBMISSIONS:
            explanation = (
                "Insufficient Data. Track more submissions to unlock this insight. "
                f"Learning insights need at least {MIN_OUTCOME_SUBMISSIONS} tracked submissions with outcomes; "
                f"{outcome_count} currently qualify."
            )
        else:
            explanation = (
                "Learning weights combine manually entered outcomes with optional actor feedback. "
                "Actor-selected feedback is weighted more heavily than inferred assumptions. "
                f"Strongest user-stated fit signals: {', '.join(user_boosted) if user_boosted else 'not enough direct feedback yet'}. "
                f"Strongest outcome archetype signals: {', '.join(boosted) if boosted else 'not enough outcome data yet'}."
            )
        insight = LearningInsight(
            actor_profile_id=actor.id,
            trends=trends,
            recommendation_weights=weights,
            explanation=explanation,
        )
        self.db.add(insight)
        self.db.commit()
        self.db.refresh(insight)
        return insight
