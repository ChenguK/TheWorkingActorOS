from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.automation.discovery.classification import REJECTED_CLASSIFICATIONS
from app.db.models import ActorProfile, AvailabilityBlock, CastingGoal, Opportunity, TravelPreference
from app.services.breakdown_role_service import BreakdownRoleService
from app.services.character_intelligence_engine import CharacterIntelligenceEngine
from app.services.breakdown_deadline_service import BreakdownDeadlineService
from app.services.demographic_match_service import DemographicMatchService
from app.services.opportunity_score import (
    OpportunityScore,
    OpportunityScoringContext,
    score_opportunity,
)
from app.services.travel_service import TravelEstimateResult, TravelService
from app.services.watch_list_service import WatchListService

DEFAULT_INCLUDED_ROLE_TYPES = [
    "Lead",
    "Supporting",
    "Principal",
    "Guest Star",
    "Co-Star",
    "Recurring",
    "Series Regular",
    "Voiceover",
    "Commercial Principal",
    "Theater Principal",
]

DEFAULT_EXCLUDED_ROLE_TYPES = [
    "Background",
    "Extra",
    "Ensemble",
    "Brand Ambassador",
    "Class",
    "Workshop",
    "Seminar",
    "Crew",
    "Staff Job",
    "Internship",
    "Administrative Job",
]


class OpportunityIntelligenceService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def score(
        self,
        opportunity: Opportunity,
        actor: ActorProfile,
        context: OpportunityScoringContext,
        *,
        as_of: datetime,
    ) -> OpportunityScore:
        return score_opportunity(opportunity, actor, context, as_of=as_of)

    def enrich(self, opportunity: Opportunity) -> Opportunity:
        user_rejection = self._user_rejection_snapshot(opportunity)
        try:
            return self._enrich(opportunity)
        finally:
            if user_rejection:
                self._restore_user_rejection(opportunity, user_rejection)

    def _enrich(self, opportunity: Opportunity) -> Opportunity:
        date_result = BreakdownDeadlineService().apply_to_opportunity(opportunity)
        if date_result.expired:
            opportunity.urgency_score = 0
            opportunity.quality_score = 0
            opportunity.quality_explanation = date_result.reason
            opportunity.confidence_level = "High"
            opportunity.risk_level = "High"
            opportunity.risk_explanation = date_result.reason
            return opportunity
        if date_result.needs_review:
            opportunity.urgency_score = 0
            opportunity.quality_score = 0
            opportunity.quality_explanation = date_result.reason
            opportunity.confidence_level = "Low"
            opportunity.risk_level = "High"
            opportunity.risk_explanation = date_result.reason
            return opportunity
        self.apply_audition_visibility(opportunity)
        if opportunity.breakdown_classification == "Unknown":
            opportunity.urgency_score = 0
            opportunity.quality_score = 0
            opportunity.quality_explanation = "This listing needs review before the app scores it as an acting breakdown."
            opportunity.confidence_level = "Low"
            opportunity.risk_level = "High"
            opportunity.risk_explanation = "Breakdown classification is unknown."
            return opportunity
        if opportunity.breakdown_classification in REJECTED_CLASSIFICATIONS:
            opportunity.urgency_score = 0
            opportunity.quality_score = 0
            opportunity.quality_explanation = opportunity.rejection_reason or "This listing is not an acting breakdown."
            opportunity.confidence_level = "Low"
            opportunity.risk_level = "High"
            opportunity.risk_explanation = opportunity.rejection_reason or "This listing is hidden because it is not an acting breakdown."
            return opportunity
        actor = self.db.scalars(select(ActorProfile).limit(1)).first()
        DemographicMatchService(self.db).apply(opportunity, actor)
        BreakdownRoleService(self.db).sync_from_details(opportunity)
        CharacterIntelligenceEngine(self.db).run_for_opportunity(opportunity)
        self.apply_hard_eligibility(opportunity, actor)
        WatchListService(self.db).apply_to_opportunity(opportunity)
        opportunity.urgency_score = self._urgency_score(opportunity)
        opportunity.quality_score, opportunity.quality_explanation = self._quality_score(opportunity)
        opportunity.confidence_level = self._confidence_level(opportunity)
        opportunity.risk_level, opportunity.risk_explanation = self._risk(opportunity)
        self._apply_goal_priority(opportunity)
        if opportunity.urgency_score >= 85 and opportunity.priority in {"Low", "Medium"}:
            opportunity.priority = "High"
        return opportunity

    def _user_rejection_snapshot(self, opportunity: Opportunity) -> dict | None:
        if opportunity.hidden_by_rule != "user_rejected":
            return None
        return {
            "visibility_status": opportunity.visibility_status,
            "status": opportunity.status,
            "hidden_by_rule": opportunity.hidden_by_rule,
            "hidden_reason": opportunity.hidden_reason,
            "rejection_reason": opportunity.rejection_reason or opportunity.hidden_reason,
            "highlighted_text_as_rejection_reason": opportunity.highlighted_text_as_rejection_reason,
            "manual_review_required": opportunity.manual_review_required,
        }

    def _restore_user_rejection(self, opportunity: Opportunity, snapshot: dict) -> None:
        for field, value in snapshot.items():
            setattr(opportunity, field, value)
        opportunity.source_metadata = {
            **(opportunity.source_metadata or {}),
            "user_rejected": True,
            "highlighted_text_as_rejection_reason": snapshot["highlighted_text_as_rejection_reason"],
        }

    def apply_hard_eligibility(self, opportunity: Opportunity, actor: ActorProfile | None = None) -> Opportunity:
        actor = actor or self.db.scalars(select(ActorProfile).limit(1)).first()
        hard_reasons = []
        travel_reasons = []
        role_type_reason = self._role_type_dealbreaker(opportunity, actor)
        if role_type_reason:
            hard_reasons.append(role_type_reason)
        demographic_reason = self._demographic_dealbreaker(opportunity)
        if demographic_reason:
            hard_reasons.append(demographic_reason)
        travel_reason = self._audition_travel_dealbreaker(opportunity, actor)
        if travel_reason:
            if travel_reason.startswith("Discarded because"):
                hard_reasons.append(travel_reason)
            else:
                travel_reasons.append(travel_reason)
        availability_reason = self._availability_conflict(opportunity, actor)
        if availability_reason:
            hard_reasons.append(availability_reason)

        if not hard_reasons and not travel_reasons:
            if opportunity.hidden_by_rule in {
                "dealbreaker_role_type",
                "dealbreaker_demographic_mismatch",
                "dealbreaker_audition_travel",
                "dealbreaker_availability",
                "dealbreaker_eligibility",
                "travel_exception",
            }:
                opportunity.visibility_status = "visible"
                opportunity.hidden_by_rule = None
                opportunity.hidden_reason = None
            if not opportunity.visibility_status:
                opportunity.visibility_status = "visible"
            return opportunity

        if hard_reasons:
            opportunity.visibility_status = "discarded"
            opportunity.hidden_by_rule = self._dealbreaker_rule_name(hard_reasons)
            opportunity.hidden_reason = " ".join(hard_reasons)
        else:
            opportunity.visibility_status = "travel_exception"
            opportunity.hidden_by_rule = "travel_exception"
            opportunity.hidden_reason = " ".join(travel_reasons)
        opportunity.rejection_reason = opportunity.hidden_reason
        opportunity.manual_review_required = False
        metadata = dict(opportunity.source_metadata or {})
        metadata["discarded_from_actor_views"] = opportunity.visibility_status == "discarded"
        metadata["travel_exception"] = opportunity.visibility_status == "travel_exception"
        metadata["dealbreaker_reasons"] = hard_reasons or travel_reasons
        opportunity.source_metadata = metadata
        return opportunity

    def apply_audition_visibility(self, opportunity: Opportunity) -> Opportunity:
        date_validation = (opportunity.source_metadata or {}).get("date_validation") or {}
        if date_validation.get("status") == "Expired":
            opportunity.visibility_status = "discarded"
            opportunity.hidden_by_rule = "deadline_expired"
            opportunity.hidden_reason = date_validation.get("reason") or "Rejected because the submission deadline has passed."
            opportunity.rejection_reason = opportunity.hidden_reason
            opportunity.manual_review_required = False
            return opportunity
        if date_validation.get("status") == "Needs Date Review":
            opportunity.visibility_status = "hidden"
            opportunity.hidden_by_rule = "needs_date_review"
            opportunity.hidden_reason = date_validation.get("reason") or "Needs Date Review before recommendation."
            opportunity.manual_review_required = True
            return opportunity
        actor = self.db.scalars(select(ActorProfile).limit(1)).first() if self.db else None
        threshold_hours = self._audition_threshold_hours(actor)
        audition_location = self._audition_location(opportunity)
        travel_estimate = self._audition_travel_estimate(opportunity, actor, audition_location)
        opportunity.audition_drive_time = travel_estimate.drive_hours if travel_estimate else None
        if opportunity.breakdown_classification in REJECTED_CLASSIFICATIONS:
            opportunity.visibility_status = "discarded"
            opportunity.hidden_by_rule = "breakdown_classification_rejected"
            opportunity.hidden_reason = opportunity.rejection_reason or "This listing is not an acting breakdown."
            opportunity.manual_review_required = False
            return opportunity
        if opportunity.breakdown_classification == "Unknown":
            if opportunity.source_type in {"Manual Entry", "Agent Submission", "Direct Email"}:
                opportunity.visibility_status = "visible"
                opportunity.hidden_by_rule = None
                opportunity.hidden_reason = None
                opportunity.manual_review_required = False
                return opportunity
            opportunity.visibility_status = "hidden"
            opportunity.hidden_by_rule = "breakdown_classification_needs_review"
            opportunity.hidden_reason = "Breakdown classification is unknown and requires manual review before scoring."
            opportunity.manual_review_required = True
            return opportunity
        if opportunity.audition_type == "In-Person":
            if not audition_location:
                self._mark_audition_needs_info(
                    opportunity,
                    "Needs audition location: this is an in-person audition, but the audition location was not found. "
                    "The app will not guess from shoot or performance location.",
                )
            elif opportunity.audition_drive_time is None:
                self._mark_audition_needs_info(
                    opportunity,
                    f"Needs audition location or user-entered estimate: audition location is {audition_location}, "
                    "but drive time from the saved current location could not be calculated.",
                )
            elif opportunity.audition_drive_time > threshold_hours:
                opportunity.visibility_status = "travel_exception"
                opportunity.hidden_by_rule = "travel_exception"
                opportunity.hidden_reason = self._travel_exception_reason(
                    audition_location,
                    opportunity.audition_drive_time,
                    threshold_hours,
                )
                opportunity.manual_review_required = False
                self._store_audition_travel_metadata(opportunity, audition_location, threshold_hours, travel_estimate)
            else:
                opportunity.visibility_status = "visible"
                opportunity.hidden_by_rule = None
                opportunity.hidden_reason = None
                opportunity.manual_review_required = False
        elif opportunity.audition_type in {"Self-Tape", "Virtual"}:
            opportunity.audition_drive_time = 0
            opportunity.audition_travel_hours = 0
            opportunity.visibility_status = "visible"
            opportunity.hidden_by_rule = None
            opportunity.hidden_reason = None
            opportunity.manual_review_required = False
        else:
            opportunity.visibility_status = "visible"
            opportunity.hidden_by_rule = None
            opportunity.hidden_reason = None
            opportunity.manual_review_required = True
        return opportunity

    def _urgency_score(self, opportunity: Opportunity) -> int:
        deadlines = [item for item in [opportunity.submission_deadline, opportunity.audition_deadline] if item]
        if not deadlines:
            return 20
        now = datetime.now(timezone.utc)
        soonest = min(deadline if deadline.tzinfo else deadline.replace(tzinfo=timezone.utc) for deadline in deadlines)
        hours = (soonest - now).total_seconds() / 3600
        if hours <= 0:
            return 100
        if hours <= 24:
            return 95
        if hours <= 72:
            return 80
        if hours <= 168:
            return 55
        return 25

    def _quality_score(self, opportunity: Opportunity) -> tuple[int, str]:
        score = 35
        reasons = []
        if opportunity.breakdown_roles and not any(
            role.fit_status in {"Strong Fit", "Possible Fit", "Stretch Fit"}
            for role in opportunity.breakdown_roles
        ):
            return 10, "Low priority because no parsed role currently fits the actor profile."
        if "SAG" in opportunity.union.upper():
            score += 15
            reasons.append("union-aligned")
        if opportunity.travel_covered:
            score += 10
            reasons.append("travel covered")
        if opportunity.housing_covered:
            score += 10
            reasons.append("housing covered")
        if opportunity.source_reliability_score >= 0.85:
            score += 15
            reasons.append("high-reliability source")
        elif opportunity.source_reliability_score >= 0.7:
            score += 8
            reasons.append("moderate-reliability source")
        if len(opportunity.description) >= 180:
            score += 10
            reasons.append("detailed role information")
        if opportunity.visibility_status in {"hidden", "travel_exception"}:
            score -= 25
            reasons.append("audition travel restriction")
        return max(0, min(100, score)), "Quality reflects " + (", ".join(reasons) if reasons else "limited available details") + "."

    def _apply_goal_priority(self, opportunity: Opportunity) -> None:
        project_text = " ".join(
            str(item or "")
            for item in [opportunity.project_type, opportunity.category, opportunity.production_details.get("project_type")]
        ).lower()
        if "theater" not in project_text and "musical" not in project_text:
            return
        actor = self.db.scalars(select(ActorProfile).limit(1)).first()
        if not actor:
            return
        goals = list(
            self.db.scalars(
                select(CastingGoal).where(CastingGoal.actor_profile_id == actor.id).where(CastingGoal.status == "Active")
            )
        )
        goal_text = " ".join(
            " ".join(
                [
                    goal.goal_type,
                    " ".join(str(item) for item in goal.target_project_types),
                    goal.title,
                ]
            )
            for goal in goals
        ).lower()
        if not any(term in goal_text for term in ["tv", "television", "film", "streaming"]):
            return
        if opportunity.breakdown_roles and not any(
            role.fit_status in {"Strong Fit", "Possible Fit", "Stretch Fit"}
            for role in opportunity.breakdown_roles
        ):
            opportunity.priority = "Low"
            opportunity.quality_explanation = (
                f"{opportunity.quality_explanation} Also marked low priority because active Casting Goals emphasize TV/film, "
                "this is theater/musical theater, and no parsed role fits."
            )

    def _confidence_level(self, opportunity: Opportunity) -> str:
        parse_confidence = (opportunity.source_metadata or {}).get("breakdown_parse_confidence")
        try:
            if parse_confidence is not None and float(parse_confidence) < 70:
                return "Low"
        except (TypeError, ValueError):
            pass
        known_fields = sum(
            bool(item)
            for item in [
                opportunity.role,
                opportunity.project,
                opportunity.location,
                opportunity.description,
                opportunity.audition_type,
                opportunity.submission_deadline,
            ]
        )
        if known_fields >= 5 and opportunity.source_reliability_score >= 0.75:
            return "High"
        if known_fields >= 4:
            return "Medium"
        return "Low"

    def _risk(self, opportunity: Opportunity) -> tuple[str, str]:
        if opportunity.visibility_status == "discarded":
            return "High", opportunity.hidden_reason or "This breakdown failed a hard eligibility rule."
        if opportunity.visibility_status in {"hidden", "travel_exception"}:
            return "High", opportunity.hidden_reason or "Audition feasibility rule keeps this out of main breakdowns."
        if opportunity.audition_type == "In-Person" and opportunity.audition_travel_hours is None:
            return "High", "In-person audition travel time is unknown."
        if not opportunity.travel_covered and not opportunity.housing_covered and opportunity.location:
            return "Medium", "Travel and housing coverage are not confirmed."
        return "Low", "Known logistics do not introduce major risk."

    def _role_type_dealbreaker(self, opportunity: Opportunity, actor: ActorProfile | None) -> str | None:
        excluded = self._normalized_role_preferences(
            actor.excluded_role_types if actor and actor.excluded_role_types else DEFAULT_EXCLUDED_ROLE_TYPES
        )
        included = self._normalized_role_preferences(actor.included_role_types if actor else [])
        role_texts = self._role_type_texts(opportunity)
        if not role_texts:
            return None
        matches = [text for text in role_texts if self._contains_any_role_type(text, excluded)]
        if matches and (not included or not any(self._contains_any_role_type(text, included) for text in role_texts)):
            return (
                "Rejected because the role type is currently excluded in Role Type Preferences "
                f"({', '.join(sorted(set(matches))[:3])})."
            )
        if matches and all(self._contains_any_role_type(text, excluded) for text in role_texts):
            return "Rejected because every parsed role is an opted-out role type."
        return None

    def _demographic_dealbreaker(self, opportunity: Opportunity) -> str | None:
        if opportunity.demographic_match_status != "Not a Match":
            return None
        role_results = (opportunity.demographic_match_details or {}).get("role_results")
        if isinstance(role_results, list) and role_results:
            role_names = [
                str(role.get("role_name", "Role"))
                for role in role_results
                if isinstance(role, dict) and role.get("status") == "Not a Match"
            ]
            if len(role_names) == len(role_results):
                return (
                    "Rejected because no parsed role overlaps the saved gender, playable age, "
                    "race/ethnicity, or cultural background preferences."
                )
            return None
        return (
            "Rejected because the breakdown includes explicit demographic requirements that do not "
            "overlap the saved actor profile."
        )

    def _audition_travel_dealbreaker(self, opportunity: Opportunity, actor: ActorProfile | None) -> str | None:
        if opportunity.audition_type != "In-Person":
            return None
        threshold_hours = self._audition_threshold_hours(actor)
        audition_location = self._audition_location(opportunity)
        travel_estimate = self._audition_travel_estimate(opportunity, actor, audition_location)
        opportunity.audition_drive_time = travel_estimate.drive_hours if travel_estimate else None
        if not audition_location:
            self._mark_audition_needs_info(
                opportunity,
                "Needs audition location: this is an in-person audition, but the audition location was not found. "
                "The app will not guess from shoot or performance location.",
            )
            return None
        if opportunity.audition_drive_time is None:
            self._mark_audition_needs_info(
                opportunity,
                f"Needs audition location or user-entered estimate: audition location is {audition_location}, "
                "but drive time from the saved current location could not be calculated.",
            )
            return None
        self._store_audition_travel_metadata(opportunity, audition_location, threshold_hours, travel_estimate)
        if opportunity.audition_drive_time > threshold_hours:
            if self._otherwise_strong_for_travel_exception(opportunity):
                return self._travel_exception_reason(audition_location, opportunity.audition_drive_time, threshold_hours)
            return (
                f"Discarded because the in-person audition is {opportunity.audition_drive_time:.1f} hours away, "
                f"which is outside the {threshold_hours:.1f}-hour audition travel preference and the breakdown "
                "is not otherwise strong enough to keep as a Travel Exception."
            )
        return None

    def _audition_location(self, opportunity: Opportunity) -> str | None:
        values = [
            opportunity.audition_location,
            opportunity.production_details.get("audition_location_name"),
            opportunity.production_details.get("audition_address"),
            opportunity.role_details.get("audition_location_name"),
            opportunity.role_details.get("audition_address"),
        ]
        combined = ", ".join(str(value).strip() for value in values if str(value or "").strip())
        return combined or None

    def _audition_travel_estimate(
        self,
        opportunity: Opportunity,
        actor: ActorProfile | None,
        audition_location: str | None,
    ) -> TravelEstimateResult | None:
        return TravelService(self.db).audition_travel(
            origin_text=actor.current_location if actor else None,
            audition_location=audition_location,
            audition_type=opportunity.audition_type,
            manual_drive_hours=opportunity.audition_travel_hours,
        )

    def _audition_threshold_hours(self, actor: ActorProfile | None) -> float:
        if not self.db or not actor:
            return 2.0
        travel = self.db.scalars(
            select(TravelPreference)
            .where(TravelPreference.actor_profile_id == actor.id)
            .limit(1)
        ).first()
        return (travel.audition_max_drive_time if travel else 120) / 60

    def _travel_exception_reason(self, audition_location: str, drive_time: float, threshold_hours: float) -> str:
        return (
            f"Audition location: {audition_location}. "
            f"Drive time: {drive_time:.1f} hours. "
            f"Threshold: {threshold_hours:.1f} hours. "
            "Reason: otherwise relevant role, but the in-person audition is outside the saved audition travel preference."
        )

    def _mark_audition_needs_info(self, opportunity: Opportunity, reason: str) -> None:
        opportunity.visibility_status = "hidden"
        opportunity.hidden_by_rule = "audition_location_needs_info"
        opportunity.hidden_reason = reason
        opportunity.manual_review_required = True
        metadata = dict(opportunity.source_metadata or {})
        metadata["needs_info"] = reason
        metadata["audition_travel_basis"] = "audition_location_only"
        opportunity.source_metadata = metadata

    def _store_audition_travel_metadata(
        self,
        opportunity: Opportunity,
        audition_location: str,
        threshold_hours: float,
        estimate: TravelEstimateResult | None,
    ) -> None:
        metadata = dict(opportunity.source_metadata or {})
        metadata["audition_travel"] = {
            "audition_location": audition_location,
            "drive_time_hours": opportunity.audition_drive_time,
            "drive_minutes": estimate.drive_minutes if estimate else None,
            "distance_miles": estimate.distance_miles if estimate else None,
            "threshold_hours": threshold_hours,
            "provider": estimate.provider if estimate else None,
            "confidence_score": estimate.confidence_score if estimate else None,
            "calculated_at": datetime.now(timezone.utc).isoformat(),
            "cached": estimate.cached if estimate else False,
            "provider_metadata": estimate.metadata if estimate else {},
            "basis": "audition_location" if estimate and estimate.provider != "manual_override" else "user_entered_estimate",
            "explanation": (
                "Audition travel is calculated from the audition location only. "
                "Shoot or performance location is not used unless the page explicitly identifies it as the audition location."
            ),
        }
        opportunity.source_metadata = metadata

    def _otherwise_strong_for_travel_exception(self, opportunity: Opportunity) -> bool:
        if opportunity.demographic_match_status not in {"Match", "Needs Review"}:
            return False
        if opportunity.breakdown_roles:
            return any(role.fit_status in {"Strong Fit", "Possible Fit", "Stretch Fit", None} for role in opportunity.breakdown_roles)
        return opportunity.breakdown_classification in {"Acting Role", "Theater Role", "Commercial Role", "Voiceover Role"}

    def _availability_conflict(self, opportunity: Opportunity, actor: ActorProfile | None) -> str | None:
        if not actor:
            return None
        candidate_dates = [
            opportunity.submission_deadline,
            opportunity.audition_deadline,
            opportunity.callback_date,
        ]
        if opportunity.shoot_start_date:
            candidate_dates.append(datetime.combine(opportunity.shoot_start_date, datetime.min.time(), tzinfo=timezone.utc))
        for candidate in [item for item in candidate_dates if item]:
            candidate = candidate if candidate.tzinfo else candidate.replace(tzinfo=timezone.utc)
            conflict = self.db.scalars(
                select(AvailabilityBlock)
                .where(AvailabilityBlock.actor_profile_id.in_([actor.id, None]))
                .where(AvailabilityBlock.start_date <= candidate)
                .where(AvailabilityBlock.end_date >= candidate)
                .limit(1)
            ).first()
            if conflict:
                opportunity.source_metadata = {
                    **(opportunity.source_metadata or {}),
                    "availability_conflict": {
                        "title": conflict.title,
                        "block_type": conflict.block_type,
                        "date": candidate.isoformat(),
                    },
                }
                return f"Availability conflict: {conflict.title} overlaps {candidate.date().isoformat()}."
        return None

    def _dealbreaker_rule_name(self, reasons: list[str]) -> str:
        text = " ".join(reasons).lower()
        if "role type" in text or "opted-out" in text:
            return "dealbreaker_role_type"
        if "2 hours" in text or "nyc" in text or "audition travel" in text:
            return "dealbreaker_audition_travel"
        if "availability conflict" in text:
            return "dealbreaker_availability"
        if "demographic" in text or "gender" in text or "playable age" in text:
            return "dealbreaker_demographic_mismatch"
        return "dealbreaker_eligibility"

    def _role_type_texts(self, opportunity: Opportunity) -> list[str]:
        texts = [
            opportunity.role_type,
            opportunity.category,
            opportunity.breakdown_classification,
            opportunity.role,
        ]
        for role in opportunity.breakdown_roles:
            texts.extend([role.role_type, role.billing, role.billing_or_role_type, role.role_name])
        return [str(text).strip().lower() for text in texts if text]

    def _normalized_role_preferences(self, values: list[str]) -> list[str]:
        normalized = []
        for value in values:
            text = str(value or "").strip().lower()
            if text:
                normalized.append(text)
        return normalized

    def _contains_any_role_type(self, text: str, preferences: list[str]) -> bool:
        text = text.lower()
        return any(self._role_type_matches(text, preference) for preference in preferences)

    def _role_type_matches(self, text: str, preference: str) -> bool:
        aliases = {
            "background": ["background", "bg"],
            "extra": ["extra", "extras"],
            "brand ambassador": ["brand ambassador", "promotional model"],
            "class": ["class", "classes"],
            "workshop": ["workshop", "workshops"],
            "seminar": ["seminar", "seminars"],
            "crew": ["crew"],
            "staff job": ["staff job", "staff position", "employment", "employee"],
            "administrative job": ["administrative", "admin job", "coordinator", "assistant"],
            "internship": ["internship", "intern"],
        }.get(preference, [preference])
        return any(alias in text for alias in aliases)
