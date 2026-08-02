from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    ActorProfile,
    Asset,
    CareerDevelopmentTask,
    ChiefOfStaffState,
    MaterialGapAlert,
    Opportunity,
    OutcomeNudge,
    RecommendationFeedback,
    SelfTapeWorkflow,
    SourceResearchItem,
    Submission,
    SubmissionAutomationQueue,
    TravelPreference,
)
from app.agents.executive_agent import ExecutiveAgent
from app.core.constants import CALLBACK_STATUSES, OPEN_SUBMISSION_STATUSES
from app.repositories.opportunity import MAIN_BREAKDOWN_CLASSIFICATIONS
from app.services.opportunity_intelligence_service import OpportunityIntelligenceService
from app.services.opportunity_intelligence_summary import (
    serialize_command_center_intelligence,
)
from app.services.opportunity_score import (
    FeedbackScoringEntry,
    OpportunityScore,
    OpportunityScoringContext,
    WatchListScoringMatch,
    build_opportunity_ranking_entry,
    rank_opportunity_entries,
)
from app.services.operations_service import OperationsService


POSITIVE_OUTCOMES = set(CALLBACK_STATUSES)
COMMAND_CENTER_DISPLAY_LIMIT = 8
COMMAND_CENTER_CANDIDATE_LIMIT = 100
SUPPORTED_RECOMMENDATION_FEEDBACK = (
    "This Fits Me",
    "Not My Type",
    "Interesting Stretch",
    "Save For Later",
)


def real_breakdown_filter():
    return Opportunity.is_demo_data.is_(False)


class CommandCenterService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def snapshot(self, *, as_of: datetime | None = None) -> dict:
        self.refresh_signals()
        OperationsService(self.db).today_platform_check_ins()
        now = as_of or datetime.now(timezone.utc)
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        actor = self.db.scalars(select(ActorProfile).limit(1)).first()
        since_at = self._last_visit_at(actor, now)
        result = self.read_snapshot(actor=actor, as_of=now, since_at=since_at)
        self.record_visit(actor, now)
        return result

    def read_snapshot(
        self,
        *,
        actor: ActorProfile | None,
        as_of: datetime,
        since_at: datetime,
    ) -> dict:
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        if since_at.tzinfo is None or since_at.utcoffset() is None:
            raise ValueError("since_at must be timezone-aware")
        now = as_of
        soon = now + timedelta(days=14)
        visible_opportunities = self._ranked_opportunity_batch(
            self.read_opportunity_candidates(), actor, as_of=now
        )
        queued = list(
            self.db.scalars(
                select(SubmissionAutomationQueue)
                .where(SubmissionAutomationQueue.approval_status.in_(["Pending Approval", "Approved"]))
                .order_by(SubmissionAutomationQueue.created_at.desc())
                .limit(8)
            )
        )
        deadlines = [
            item
            for item in self.db.scalars(
                self._opportunity_candidate_statement()
            )
            if self._has_deadline_between(item, now, soon)
        ]
        nudges = list(
            self.db.scalars(
                select(OutcomeNudge)
                .where(OutcomeNudge.status == "Open")
                .order_by(OutcomeNudge.due_at.asc().nullslast(), OutcomeNudge.created_at.desc())
                .limit(8)
            )
        )
        tasks = list(
            self.db.scalars(
                select(CareerDevelopmentTask)
                .where(CareerDevelopmentTask.status != "Completed")
                .order_by(CareerDevelopmentTask.created_at.desc())
                .limit(8)
            )
        )
        gaps = list(
            self.db.scalars(
                select(MaterialGapAlert)
                .where(MaterialGapAlert.status == "Open")
                .order_by(MaterialGapAlert.created_at.desc())
                .limit(8)
            )
        )
        asset_performance = self.asset_performance()
        platform_check_ins = OperationsService(self.db).read_today_platform_check_ins(
            as_of=now
        )
        since_last_visit = self._since_last_visit(since_at, asset_performance)
        priorities = ExecutiveAgent(self.db).read_top_priorities(as_of=now)
        return {
            "today_opportunities": [
                self._opportunity_card(item, score)
                for item, score in visible_opportunities
            ],
            "executive_priorities": priorities,
            "chief_of_staff_priorities": priorities,
            "since_last_visit": since_last_visit,
            "upcoming_attention": [self._deadline_card(item) for item in sorted(deadlines, key=self._deadline_sort)[:5]],
            "today_career_recommendation": self._today_career_recommendation(tasks, gaps),
            "platform_check_ins": platform_check_ins,
            "queued_submissions": [self._queue_card(item) for item in queued],
            "upcoming_deadlines": [self._deadline_card(item) for item in sorted(deadlines, key=self._deadline_sort)[:8]],
            "outcome_nudges": [self._nudge_card(item) for item in nudges],
            "career_tasks": [self._task_card(item) for item in tasks],
            "material_gaps": [self._gap_card(item) for item in gaps],
            "asset_performance": asset_performance,
        }

    def read_opportunity_candidates(self) -> list[Opportunity]:
        return list(
            self.db.scalars(
                self._opportunity_candidate_statement()
                .options(
                    selectinload(Opportunity.breakdown_roles),
                    selectinload(Opportunity.submissions),
                )
                .order_by(Opportunity.created_at.desc(), Opportunity.id.asc())
                .limit(COMMAND_CENTER_CANDIDATE_LIMIT)
            )
        )

    def _ranked_opportunities(
        self,
        candidates: list[Opportunity],
        actor: ActorProfile | None,
        *,
        as_of: datetime,
    ) -> list[Opportunity]:
        return [
            opportunity
            for opportunity, _score in self._ranked_opportunity_batch(
                candidates, actor, as_of=as_of
            )
        ]

    def _ranked_opportunity_batch(
        self,
        candidates: list[Opportunity],
        actor: ActorProfile | None,
        *,
        as_of: datetime,
    ) -> list[tuple[Opportunity, OpportunityScore | None]]:
        if not candidates:
            return []
        if actor is None:
            return [
                (candidate, None)
                for candidate in sorted(
                    candidates,
                    key=lambda item: (-item.urgency_score, -item.quality_score),
                )[:COMMAND_CENTER_DISPLAY_LIMIT]
            ]

        contexts = self._read_scoring_contexts(candidates, actor)
        intelligence = OpportunityIntelligenceService(self.db)
        entries = []
        candidates_by_id = {}
        scores_by_id = {}
        for candidate in candidates:
            score = intelligence.score(
                candidate,
                actor,
                contexts[candidate.id],
                as_of=as_of,
            )
            entries.append(
                build_opportunity_ranking_entry(candidate, score, as_of=as_of)
            )
            candidates_by_id[candidate.id] = candidate
            scores_by_id[candidate.id] = score
        ranked = rank_opportunity_entries(entries)
        return [
            (
                candidates_by_id[entry.opportunity_id],
                scores_by_id[entry.opportunity_id],
            )
            for entry in ranked[:COMMAND_CENTER_DISPLAY_LIMIT]
        ]

    def _read_scoring_contexts(
        self,
        candidates: list[Opportunity],
        actor: ActorProfile,
    ) -> dict[UUID, OpportunityScoringContext]:
        candidate_ids = [candidate.id for candidate in candidates]
        feedback_rank = (
            select(
                RecommendationFeedback.id.label("feedback_id"),
                func.row_number()
                .over(
                    partition_by=RecommendationFeedback.opportunity_id,
                    order_by=(
                        RecommendationFeedback.created_at.desc(),
                        RecommendationFeedback.id.asc(),
                    ),
                )
                .label("feedback_rank"),
            )
            .where(RecommendationFeedback.actor_profile_id == actor.id)
            .where(RecommendationFeedback.opportunity_id.in_(candidate_ids))
            .where(
                RecommendationFeedback.feedback_type.in_(
                    SUPPORTED_RECOMMENDATION_FEEDBACK
                )
            )
            .subquery()
        )
        feedback_rows = self.db.scalars(
            select(RecommendationFeedback)
            .join(
                feedback_rank,
                feedback_rank.c.feedback_id == RecommendationFeedback.id,
            )
            .where(feedback_rank.c.feedback_rank == 1)
        ).all()
        feedback_by_opportunity = {
            feedback.opportunity_id: FeedbackScoringEntry(
                key=str(feedback.id),
                feedback_type=feedback.feedback_type,
                created_at=self._aware_timestamp(feedback.created_at),
            )
            for feedback in feedback_rows
        }
        travel = self.db.scalars(
            select(TravelPreference)
            .where(TravelPreference.actor_profile_id == actor.id)
            .order_by(TravelPreference.created_at.desc(), TravelPreference.id.asc())
            .limit(1)
        ).first()
        travel_limit = travel.audition_max_drive_time / 60 if travel else None
        return {
            candidate.id: self._build_scoring_context(
                candidate,
                feedback=feedback_by_opportunity.get(candidate.id),
                audition_travel_limit_hours=travel_limit,
            )
            for candidate in candidates
        }

    @classmethod
    def _build_scoring_context(
        cls,
        opportunity: Opportunity,
        *,
        feedback: FeedbackScoringEntry | None = None,
        audition_travel_limit_hours: float | None = None,
    ) -> OpportunityScoringContext:
        watchlist_matches = []
        for value in opportunity.watchlist_match_names or []:
            if not isinstance(value, dict):
                continue
            priority = value.get("priority")
            key = value.get("id") or value.get("title")
            if priority not in {"High", "Medium", "Low"} or not isinstance(
                key, str
            ):
                continue
            key = key.strip()
            if not key or len(key) > 120:
                continue
            watchlist_matches.append(
                WatchListScoringMatch(key=key, priority=priority)
            )
        return OpportunityScoringContext(
            watchlist_matches=tuple(watchlist_matches),
            submission_status=cls._latest_submission_status(opportunity.submissions),
            feedback_entries=(feedback,) if feedback else (),
            audition_travel_limit_hours=audition_travel_limit_hours,
        )

    @classmethod
    def _latest_submission_status(cls, submissions: list[Submission]) -> str | None:
        if not submissions:
            return None
        selected = min(
            submissions,
            key=lambda submission: (
                -cls._aware_timestamp(
                    submission.submitted_at
                    or submission.updated_at
                    or submission.created_at
                ).timestamp(),
                str(submission.id),
            ),
        )
        return selected.current_status

    @staticmethod
    def _aware_timestamp(value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    @staticmethod
    def _opportunity_candidate_statement():
        return (
            select(Opportunity)
            .where(Opportunity.visibility_status == "visible")
            .where(
                Opportunity.breakdown_classification.in_(
                    MAIN_BREAKDOWN_CLASSIFICATIONS
                )
            )
            .where(real_breakdown_filter())
        )

    def refresh_signals(self) -> None:
        intelligence = OpportunityIntelligenceService(self.db)
        for opportunity in self.db.scalars(select(Opportunity).where(Opportunity.is_demo_data.is_(False))):
            intelligence.enrich(opportunity)
        self._ensure_outcome_nudges()
        self._ensure_material_gap_alerts()
        self.db.commit()

    def asset_performance(self) -> list[dict]:
        assets = list(self.db.scalars(select(Asset)))
        submissions = [
            submission
            for submission in self.db.scalars(
                select(Submission).options(
                    selectinload(Submission.assets),
                    selectinload(Submission.opportunity),
                )
            )
            if not submission.opportunity or not submission.opportunity.is_demo_data
        ]
        rows = []
        for asset in assets:
            linked = [submission for submission in submissions if asset in submission.assets]
            positive = [submission for submission in linked if submission.current_status in POSITIVE_OUTCOMES]
            rows.append(
                {
                    "asset_id": asset.id,
                    "asset_name": asset.asset_name,
                    "asset_type": asset.asset_type,
                    "submissions": len(linked),
                    "positive_outcomes": len(positive),
                    "callback_rate": round((len(positive) / len(linked)) if linked else 0, 2),
                }
            )
        return sorted(rows, key=lambda item: (item["positive_outcomes"], item["submissions"]), reverse=True)

    def list_self_tapes(self) -> list[SelfTapeWorkflow]:
        return list(self.db.scalars(select(SelfTapeWorkflow).order_by(SelfTapeWorkflow.created_at.desc())))

    def _ensure_outcome_nudges(self) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        submissions = [
            submission
            for submission in self.db.scalars(
                select(Submission).where(Submission.current_status.in_(OPEN_SUBMISSION_STATUSES))
            )
            if not submission.opportunity or not submission.opportunity.is_demo_data
        ]
        existing = {
            item.submission_id
            for item in self.db.scalars(select(OutcomeNudge).where(OutcomeNudge.status == "Open"))
        }
        for submission in submissions:
            marker = submission.submitted_at or submission.created_at
            marker = marker if marker.tzinfo else marker.replace(tzinfo=timezone.utc)
            if submission.id in existing or marker > cutoff:
                continue
            self.db.add(
                OutcomeNudge(
                    submission_id=submission.id,
                    nudge_type="Outcome Check",
                    message="Update this submission outcome so the Learning Agent can improve future recommendations.",
                    due_at=datetime.now(timezone.utc) + timedelta(days=1),
                )
            )

    def _ensure_material_gap_alerts(self) -> None:
        actor = self.db.scalars(select(ActorProfile).limit(1)).first()
        if not actor:
            return
        assets = list(self.db.scalars(select(Asset).where(Asset.actor_profile_id == actor.id)))
        represented = {name for asset in assets for name in asset.archetype_names}
        target_archetypes = ["Attorney", "Detective", "Executive", "Journalist", "Political Leader"]
        existing = {
            item.archetype
            for item in self.db.scalars(
                select(MaterialGapAlert).where(
                    MaterialGapAlert.actor_profile_id == actor.id,
                    MaterialGapAlert.status == "Open",
                )
            )
        }
        for archetype in target_archetypes:
            if archetype in represented or archetype in existing:
                continue
            self.db.add(
                MaterialGapAlert(
                    actor_profile_id=actor.id,
                    archetype=archetype,
                    gap_type="Missing Archetype Coverage",
                    message=f"The asset library does not currently represent {archetype}.",
                    priority="High" if archetype in {"Attorney", "Executive"} else "Medium",
                    recommended_action=f"Create a headshot or reel scene that supports {archetype} submissions.",
                )
            )

    def _last_visit_at(self, actor: ActorProfile | None, now: datetime) -> datetime:
        state = self._chief_of_staff_state(actor)
        if state and state.last_dashboard_visit_at:
            value = state.last_dashboard_visit_at
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return now - timedelta(days=7)

    def record_visit(self, actor: ActorProfile | None, now: datetime) -> None:
        state = self._chief_of_staff_state(actor)
        if not state:
            state = ChiefOfStaffState(actor_profile_id=actor.id if actor else None)
            self.db.add(state)
        state.last_dashboard_visit_at = now
        self.db.commit()

    def _chief_of_staff_state(self, actor: ActorProfile | None) -> ChiefOfStaffState | None:
        query = select(ChiefOfStaffState)
        if actor:
            query = query.where(ChiefOfStaffState.actor_profile_id == actor.id)
        else:
            query = query.where(ChiefOfStaffState.actor_profile_id.is_(None))
        return self.db.scalars(query.limit(1)).first()

    def _since_last_visit(self, since_at: datetime, asset_performance: list[dict]) -> list[dict]:
        changes: list[dict] = []
        new_film_tv = self._new_visible_breakdowns(since_at, ["film", "tv", "television", "streaming", "series"])
        if new_film_tv:
            changes.append(
                {
                    "message": f"{new_film_tv} new Film/TV breakdown{'s' if new_film_tv != 1 else ''} matched your profile.",
                    "category": "Breakdowns",
                    "target_path": "/breakdowns",
                }
            )
        new_theater = self._new_visible_breakdowns(since_at, ["theater", "theatre", "musical", "play", "stage"])
        if new_theater:
            changes.append(
                {
                    "message": f"{new_theater} new theater breakdown{'s' if new_theater != 1 else ''} matched your profile.",
                    "category": "Breakdowns",
                    "target_path": "/breakdowns",
                }
            )
        travel_count = self.db.scalar(
            select(func.count())
            .select_from(Opportunity)
            .where(Opportunity.is_demo_data.is_(False))
            .where(Opportunity.visibility_status == "travel_exception")
            .where(Opportunity.created_at >= since_at)
        )
        if travel_count:
            changes.append(
                {
                    "message": f"{travel_count} breakdown{'s were' if travel_count != 1 else ' was'} just outside your in-person audition travel preference.",
                    "category": "Travel Exceptions",
                    "target_path": "/breakdowns",
                }
            )
        source_count = self.db.scalar(
            select(func.count())
            .select_from(SourceResearchItem)
            .where(SourceResearchItem.deleted.is_(False))
            .where(SourceResearchItem.status.in_(["Suggested", "Researching"]))
            .where(SourceResearchItem.created_at >= since_at)
        )
        if source_count:
            changes.append(
                {
                    "message": f"{source_count} new breakdown source{'s are' if source_count != 1 else ' is'} awaiting your approval.",
                    "category": "Sources",
                    "target_path": "/breakdowns",
                }
            )
        top_asset = next((asset for asset in asset_performance if asset["positive_outcomes"] > 0), None)
        if top_asset:
            changes.append(
                {
                    "message": f"{top_asset['asset_name']} currently has the strongest tracked callback signal.",
                    "category": "Materials",
                    "target_path": "/materials",
                }
            )
        return changes

    def _new_visible_breakdowns(self, since_at: datetime, terms: list[str]) -> int:
        rows = self.db.scalars(
            select(Opportunity)
            .where(Opportunity.visibility_status == "visible")
            .where(Opportunity.breakdown_classification.in_(MAIN_BREAKDOWN_CLASSIFICATIONS))
            .where(Opportunity.created_at >= since_at)
            .where(real_breakdown_filter())
        )
        count = 0
        for item in rows:
            text = " ".join(
                str(value or "")
                for value in [
                    item.project_type,
                    item.category,
                    item.project,
                    item.production_details.get("project_type"),
                ]
            ).lower()
            if any(term in text for term in terms):
                count += 1
        return count

    def _today_career_recommendation(
        self, tasks: list[CareerDevelopmentTask], gaps: list[MaterialGapAlert]
    ) -> dict | None:
        high_gap = next((gap for gap in gaps if gap.priority == "High"), None)
        if high_gap:
            return {
                "title": high_gap.recommended_action,
                "reason": high_gap.message,
                "target_path": "/materials",
            }
        high_task = next((task for task in tasks if task.priority == "High"), None)
        if high_task:
            return {
                "title": high_task.title,
                "reason": high_task.reason or high_task.description,
                "target_path": "/career",
            }
        return None

    def _has_deadline_between(self, opportunity: Opportunity, start: datetime, end: datetime) -> bool:
        for value in [opportunity.submission_deadline, opportunity.audition_deadline]:
            if not value:
                continue
            value = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
            if start <= value <= end:
                return True
        return False

    def _deadline_sort(self, opportunity: Opportunity) -> datetime:
        values = [item for item in [opportunity.submission_deadline, opportunity.audition_deadline] if item]
        if not values:
            return datetime.max.replace(tzinfo=timezone.utc)
        return min(item if item.tzinfo else item.replace(tzinfo=timezone.utc) for item in values)

    def _opportunity_card(
        self,
        opportunity: Opportunity,
        score: OpportunityScore | None,
    ) -> dict:
        return {
            **self._opportunity_base_card(opportunity),
            "intelligence": (
                serialize_command_center_intelligence(score)
                if score is not None
                else None
            ),
        }

    def _opportunity_base_card(self, opportunity: Opportunity) -> dict:
        return {
            "id": opportunity.id,
            "role": opportunity.role,
            "project": opportunity.project,
            "original_post_url": opportunity.original_post_url,
            "priority": opportunity.priority,
            "urgency_score": opportunity.urgency_score,
            "quality_score": opportunity.quality_score,
            "confidence_level": opportunity.confidence_level,
            "risk_level": opportunity.risk_level,
        }

    def _deadline_card(self, opportunity: Opportunity) -> dict:
        return {
            **self._opportunity_base_card(opportunity),
            "submission_deadline": opportunity.submission_deadline,
            "audition_deadline": opportunity.audition_deadline,
        }

    def _queue_card(self, item: SubmissionAutomationQueue) -> dict:
        return {
            "id": item.id,
            "opportunity_id": item.opportunity_id,
            "approval_status": item.approval_status,
            "automation_status": item.automation_status,
            "adapter_key": item.adapter_key,
        }

    def _nudge_card(self, nudge: OutcomeNudge) -> dict:
        return {
            "id": nudge.id,
            "submission_id": nudge.submission_id,
            "nudge_type": nudge.nudge_type,
            "message": nudge.message,
            "due_at": nudge.due_at,
        }

    def _task_card(self, task: CareerDevelopmentTask) -> dict:
        return {
            "id": task.id,
            "title": task.title,
            "priority": task.priority,
            "status": task.status,
            "estimated_impact": task.estimated_impact,
            "related_archetype": task.related_archetype,
        }

    def _gap_card(self, gap: MaterialGapAlert) -> dict:
        return {
            "id": gap.id,
            "archetype": gap.archetype,
            "gap_type": gap.gap_type,
            "priority": gap.priority,
            "message": gap.message,
            "recommended_action": gap.recommended_action,
        }
