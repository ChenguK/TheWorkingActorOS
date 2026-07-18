from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from html.parser import HTMLParser
import re
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.db.models import (
    ActorProfile,
    ActorRelationship,
    Asset,
    AuditionJournalEntry,
    AuditionPreparationBrief,
    CallbackEvent,
    CareerDevelopmentTask,
    CareerPathSimulation,
    CastingContact,
    CastingOffice,
    CommunicationLog,
    BreakdownRole,
    DreamRoleTarget,
    MaterialCreationPlan,
    Opportunity,
    ProfessionalEquipmentProfile,
    QuarterlyCareerReview,
    SceneCandidate,
    SelfTape,
    ScriptSource,
    Submission,
)
from app.repositories.opportunity import MAIN_BREAKDOWN_CLASSIFICATIONS
from app.services.actor_work_event_service import ActorWorkEventService
from app.services.watch_list_service import WatchListService
from app.services.workflow_connector_service import WorkflowConnectorService
from app.schemas.intelligence import (
    ActorRelationshipCreate,
    ActorRelationshipUpdate,
    CallbackEventCreate,
    CallbackEventUpdate,
    CommunicationLogCreate,
    CommunicationLogUpdate,
    AuditionJournalEntryCreate,
    AuditionJournalEntryUpdate,
    CareerPathSimulationCreate,
    CastingContactCreate,
    CastingOfficeCreate,
    DreamRoleTargetCreate,
    DreamRoleTargetUpdate,
    MaterialCreationPlanCreate,
    MaterialCreationPlanUpdate,
    QuarterlyCareerReviewCreate,
    SceneCandidateFindRequest,
    SceneCandidateUpdate,
    ScriptSourceCreate,
    ScriptSourceUpdate,
    SelfTapeCreate,
    SelfTapeUpdate,
)


CALLBACK_STATUSES = {"Requested", "Self-Tape Callback", "In-Person Callback", "Pinned", "Booked"}
MIN_ARCHETYPE_SUBMISSIONS = 5
MIN_CASTING_OFFICE_SUBMISSIONS = 3
EARLY_CASTING_PATTERN_ACTIVITY = 5
EMERGING_CASTING_PATTERN_ACTIVITY = 10
EMERGING_CASTING_PATTERN_SUBMISSIONS = 3
STRONGER_CASTING_PATTERN_ACTIVITY = 20
STRONGER_CASTING_PATTERN_OUTCOMES = 5
STRETCH_ARCHETYPES = ["Attorney", "Detective", "Executive", "Journalist", "Political Leader", "University Dean"]
RIGHTS_SAFE_STATUSES = {"Public Domain", "Royalty-Free", "Original / User-Owned", "Licensed"}
SCRIPT_RIGHTS_STATUSES = RIGHTS_SAFE_STATUSES | {"Permission Required", "Unknown"}
PRIMARY_SCENE_RESULT_TYPES = {"Specific Scene", "Specific Monologue"}
RESOURCE_SCENE_RESULT_TYPES = {"Script Library", "Resource Guide"}
HIDDEN_SCENE_RESULT_TYPES = {"Music / Sound Library", "Dead / Fetch Failed", "Not Useful"}
SIMILAR_ROLE_MAP = {
    "hospital administrator": ["Attorney", "Principal", "University Dean", "Executive Director", "Judge", "Political Staffer"],
    "nurse": ["Hospital Administrator", "Medical Director", "Social Worker", "Parent", "Teacher"],
    "mom": ["Teacher", "Principal", "Neighbor", "Best Friend", "Hospital Administrator"],
    "parent": ["Teacher", "Principal", "Neighbor", "Best Friend", "Hospital Administrator"],
    "attorney": ["Judge", "Political Staffer", "Corporate Executive", "Detective", "University Dean"],
    "detective": ["Investigator", "Federal Agent", "Journalist", "Attorney", "Political Staffer"],
    "executive": ["Corporate Executive", "Executive Director", "Principal", "Political Leader", "University Dean"],
}


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._hidden_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self._hidden_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"} and self._hidden_depth:
            self._hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._hidden_depth:
            text = " ".join(data.split())
            if text:
                self.parts.append(text)


class IntelligenceService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def dashboard(self, actor: ActorProfile) -> dict:
        return {
            "archetype_performance": self.archetype_performance(actor),
            "casting_office_analytics": self.casting_office_analytics(actor),
            "role_similarity": self.role_similarity(actor),
        }

    def audition_readiness_for_all(self, actor: ActorProfile) -> list[dict]:
        opportunities = list(
            self.db.scalars(
                select(Opportunity)
                .where(Opportunity.is_demo_data.is_(False))
                .where(Opportunity.visibility_status == "visible")
                .where(Opportunity.breakdown_classification.in_(MAIN_BREAKDOWN_CLASSIFICATIONS))
                .order_by(Opportunity.updated_at.desc())
            )
        )
        return [self.audition_readiness(actor, opportunity.id) for opportunity in opportunities]

    def audition_readiness(self, actor: ActorProfile, opportunity_id: UUID) -> dict:
        opportunity = self.db.scalar(
            select(Opportunity)
            .where(Opportunity.id == opportunity_id)
            .options(selectinload(Opportunity.breakdown_roles).selectinload(BreakdownRole.character_profile))
        )
        if not opportunity or opportunity.is_demo_data:
            raise NotFoundError("Opportunity not found")
        assets = list(self.db.scalars(select(Asset).where(Asset.actor_profile_id == actor.id)))
        role = self._best_breakdown_role(opportunity)
        character_profile = role.character_profile if role else None
        character_archetypes = self._character_archetypes(character_profile)
        character_confidence = self._character_archetype_confidence(character_profile)
        character_ready = bool(character_archetypes) and character_confidence >= 50
        inferred = character_archetypes[0] if character_ready else self._infer_archetype(
            f"{opportunity.role} {opportunity.project} {opportunity.description} {opportunity.category or ''}".lower()
        )
        role_text = self._readiness_role_text(opportunity, role, character_archetypes).lower()
        breakdown = {
            "headshot_fit": self._asset_fit(assets, "Headshot", role_text, inferred, 15),
            "reel_fit": self._asset_fit(assets, "Reel", role_text, inferred, 15),
            "slate_fit": self._asset_fit(assets, "Slate", role_text, inferred, 10),
            "resume_fit": self._asset_fit(assets, "Resume", role_text, inferred, 10),
            "archetype_fit": self._archetype_fit(assets, role_text, inferred, 20),
            "travel_fit": self._travel_fit(opportunity, 15),
            "similar_role_performance": self._similar_role_performance(actor, opportunity, 15, inferred),
        }
        missing = []
        if breakdown["headshot_fit"] < 10:
            missing.append(f"{inferred} headshot")
        if breakdown["reel_fit"] < 10:
            missing.append(f"{inferred} reel footage")
        if breakdown["slate_fit"] < 7:
            missing.append("Current slate variation")
        if breakdown["resume_fit"] < 7:
            missing.append("Resume aligned to this role category")
        score = min(100, sum(breakdown.values()))
        label = self._readiness_label(score, role, character_ready)
        archetype_label = ", ".join(character_archetypes[:5]) if character_archetypes else inferred
        parsing_note = (
            "Readiness is based on parsed Character Intelligence archetypes."
            if character_ready
            else "Readiness needs better character parsing."
        )
        return {
            "opportunity_id": opportunity.id,
            "opportunity_label": f"{opportunity.role} · {opportunity.project}",
            "readiness_label": label,
            "readiness_percentage": score,
            "score_breakdown": breakdown,
            "missing_materials": missing,
            "character_archetypes": character_archetypes,
            "character_parsing_confidence": character_confidence,
            "character_parsing_status": "Ready" if character_ready else "Needs Better Character Parsing",
            "debug_score_available": True,
            "explanation": (
                f"{label}: evaluated against {archetype_label}. {parsing_note} "
                "Materials, travel, and similar-role history are considered after the character fit is understood."
            ),
        }

    def archetype_performance(self, actor: ActorProfile) -> dict:
        metrics: dict[str, Counter] = defaultdict(Counter)
        assets = list(self.db.scalars(select(Asset).where(Asset.actor_profile_id == actor.id)))
        represented = Counter(name for asset in assets for name in asset.archetype_names)
        submissions = self._submissions(actor)
        for submission in submissions:
            archetypes = {name for asset in submission.assets for name in asset.archetype_names} or {"Uncategorized"}
            for archetype in archetypes:
                metrics[archetype]["submissions"] += 1
                metrics[archetype][self._status_key(submission.current_status)] += 1
        rows = []
        for archetype, counts in metrics.items():
            callbacks = sum(counts[key] for key in ["requested", "self_tape_callbacks", "in_person_callbacks", "pinned", "booked"])
            submissions_count = counts["submissions"]
            if submissions_count >= MIN_ARCHETYPE_SUBMISSIONS:
                rows.append(
                    {
                        "archetype": archetype,
                        "submissions": submissions_count,
                        "requested": counts["requested"],
                        "self_tape_callbacks": counts["self_tape_callbacks"],
                        "in_person_callbacks": counts["in_person_callbacks"],
                        "pinned": counts["pinned"],
                        "booked": counts["booked"],
                        "passed": counts["passed"],
                        "no_response": counts["no_response"],
                        "callback_rate": round(callbacks / submissions_count, 2) if submissions_count else 0,
                        "booking_rate": round(counts["booked"] / submissions_count, 2) if submissions_count else 0,
                    }
                )
        rows.sort(key=lambda item: (item["booking_rate"], item["callback_rate"], item["submissions"]), reverse=True)
        best = [item["archetype"] for item in rows if item["callback_rate"] > 0][:5]
        underused = [name for name, count in represented.items() if count > 0 and not any(row["archetype"] == name for row in rows)]
        overused = [item["archetype"] for item in rows if item["submissions"] >= 5 and item["callback_rate"] < 0.2]
        high_potential = [name for name in STRETCH_ARCHETYPES if name not in represented][:5]
        return {
            "metrics": rows,
            "best_performing_archetypes": best,
            "underused_archetypes": underused[:5],
            "overused_archetypes": overused[:5],
            "high_potential_stretch_archetypes": high_potential,
        }

    def list_casting_offices(self) -> list[CastingOffice]:
        return list(self.db.scalars(select(CastingOffice).order_by(CastingOffice.name.asc())))

    def create_casting_office(self, payload: CastingOfficeCreate) -> CastingOffice:
        office = CastingOffice(**payload.model_dump())
        self.db.add(office)
        self.db.commit()
        self.db.refresh(office)
        return office

    def create_casting_contact(self, payload: CastingContactCreate) -> CastingContact:
        if not self.db.get(CastingOffice, payload.casting_office_id):
            raise NotFoundError("Casting office not found")
        contact = CastingContact(**payload.model_dump())
        self.db.add(contact)
        self.db.commit()
        self.db.refresh(contact)
        return contact

    def list_relationships(self) -> list[ActorRelationship]:
        return list(
            self.db.scalars(
                select(ActorRelationship)
                .options(
                    selectinload(ActorRelationship.linked_opportunities),
                    selectinload(ActorRelationship.linked_submissions),
                )
                .order_by(ActorRelationship.updated_at.desc())
            )
        )

    def create_relationship(self, payload: ActorRelationshipCreate) -> ActorRelationship:
        data = payload.model_dump(exclude={"linked_opportunity_ids", "linked_submission_ids"})
        relationship = ActorRelationship(**data)
        self._sync_relationship_links(
            relationship,
            payload.linked_opportunity_ids,
            payload.linked_submission_ids,
        )
        self.db.add(relationship)
        self.db.commit()
        self.db.refresh(relationship)
        return relationship

    def update_relationship(self, relationship_id: UUID, payload: ActorRelationshipUpdate) -> ActorRelationship:
        relationship = self._relationship_or_404(relationship_id)
        data = payload.model_dump(
            exclude_unset=True,
            exclude={"linked_opportunity_ids", "linked_submission_ids"},
        )
        for key, value in data.items():
            setattr(relationship, key, value)
        if payload.linked_opportunity_ids is not None or payload.linked_submission_ids is not None:
            self._sync_relationship_links(
                relationship,
                payload.linked_opportunity_ids if payload.linked_opportunity_ids is not None else relationship.linked_opportunity_ids,
                payload.linked_submission_ids if payload.linked_submission_ids is not None else relationship.linked_submission_ids,
            )
        self.db.commit()
        self.db.refresh(relationship)
        return relationship

    def delete_relationship(self, relationship_id: UUID) -> None:
        relationship = self._relationship_or_404(relationship_id)
        self.db.delete(relationship)
        self.db.commit()

    def relationship_analytics(self) -> dict:
        rows = []
        for relationship in self.list_relationships():
            submissions = relationship.linked_submissions
            opportunities = relationship.linked_opportunities
            callbacks = [item for item in submissions if item.current_status in CALLBACK_STATUSES]
            pins = [item for item in submissions if item.current_status == "Pinned"]
            bookings = [item for item in submissions if item.current_status == "Booked"]
            repeat_projects = len({item.project for item in opportunities})
            total = len(submissions)
            callback_rate = round(len(callbacks) / total, 2) if total else 0
            booking_rate = round(len(bookings) / total, 2) if total else 0
            signal = "Develop" if callback_rate or booking_rate or pins else "Track"
            if booking_rate:
                signal = "High-value booking relationship"
            elif callback_rate >= 0.5 or pins:
                signal = "Strong callback relationship"
            rows.append(
                {
                    "relationship_id": relationship.id,
                    "name": relationship.name,
                    "role_title": relationship.role_title,
                    "company_office": relationship.company_office,
                    "relationship_strength": relationship.relationship_strength,
                    "submissions": total,
                    "callbacks": len(callbacks),
                    "pins": len(pins),
                    "bookings": len(bookings),
                    "repeat_opportunities": repeat_projects,
                    "callback_rate": callback_rate,
                    "booking_rate": booking_rate,
                    "correlation_signal": signal,
                }
            )
        rows.sort(key=lambda item: (item["booking_rate"], item["callback_rate"], item["repeat_opportunities"]), reverse=True)
        return {
            "rows": rows,
            "strongest_relationships": [item["name"] for item in rows if item["correlation_signal"] != "Track"][:5],
            "relationship_agent_explanation": "The Relationship Agent correlates manually linked relationships with submission outcomes, callbacks, pins, bookings, and repeat project exposure. This is directional private career intelligence, not a prompt to ask casting for rejection feedback.",
        }

    def casting_office_analytics(self, actor: ActorProfile) -> list[dict]:
        rows = []
        grouped: dict[UUID | None, list[Submission]] = defaultdict(list)
        for submission in self._submissions(actor):
            office_id = submission.opportunity.casting_office_id if submission.opportunity else None
            grouped[office_id].append(submission)
        for office_id, submissions in grouped.items():
            office = self.db.get(CastingOffice, office_id) if office_id else None
            callbacks = [item for item in submissions if item.current_status in CALLBACK_STATUSES]
            bookings = [item for item in submissions if item.current_status == "Booked"]
            materials = Counter(asset.asset_name for item in callbacks for asset in item.assets)
            stretch_callbacks = [
                item
                for item in callbacks
                if item.opportunity and any(role.lower() in item.opportunity.role.lower() for role in STRETCH_ARCHETYPES)
            ]
            total = len(submissions)
            if total < MIN_CASTING_OFFICE_SUBMISSIONS:
                continue
            rows.append(
                {
                    "casting_office_id": office_id,
                    "casting_office": office.name if office else "Unassigned",
                    "submissions": total,
                    "callbacks": len(callbacks),
                    "bookings": len(bookings),
                    "callback_rate": round(len(callbacks) / total, 2) if total else 0,
                    "booking_rate": round(len(bookings) / total, 2) if total else 0,
                    "best_materials": [name for name, _ in materials.most_common(5)],
                    "stretch_response_signal": "Positive" if stretch_callbacks else "Not enough data",
                }
            )
        return sorted(rows, key=lambda item: (item["booking_rate"], item["callback_rate"]), reverse=True)

    def industry_trends(self, actor: ActorProfile) -> dict:
        opportunities = list(
            self.db.scalars(
                select(Opportunity)
                .where(Opportunity.is_demo_data.is_(False))
                .where(Opportunity.breakdown_classification.in_(MAIN_BREAKDOWN_CLASSIFICATIONS))
                .order_by(Opportunity.created_at.desc())
            )
        )
        submissions = self._submissions(actor)
        pattern_stage = self._casting_pattern_stage(opportunities, submissions)
        if pattern_stage["stage"] == "Add Data First":
            payload = self._empty_trends()
            payload.update(pattern_stage)
            return payload
        assets = list(self.db.scalars(select(Asset).where(Asset.actor_profile_id == actor.id)))
        represented = {name.lower() for asset in assets for name in asset.archetype_names}
        submitted_opportunities = [item.opportunity for item in submissions if item.opportunity]
        callback_submissions = [item for item in submissions if item.current_status in CALLBACK_STATUSES and item.opportunity]
        booked_submissions = [item for item in submissions if item.current_status == "Booked" and item.opportunity]
        outcome_submissions = [item for item in submissions if item.current_status in {"Requested", "Self-Tape Callback", "In-Person Callback", "Pinned", "Booked", "Passed", "No Response"}]
        categories = {
            "role_type": Counter(self._role_bucket(item.role, item.description) for item in opportunities),
            "archetype": Counter(self._opportunity_archetype(item) for item in opportunities),
            "project_type": Counter(item.category or "Uncategorized" for item in opportunities),
            "union_status": Counter(item.union for item in opportunities),
            "location": Counter(item.location for item in opportunities),
            "audition_type": Counter(item.audition_type for item in opportunities),
            "submission_source": Counter(item.source.name if item.source else item.source_type or "Manual" for item in opportunities),
            "submitted_project_type": Counter(item.category or "Uncategorized" for item in submitted_opportunities),
            "callback_archetype": Counter(self._opportunity_archetype(item.opportunity) for item in callback_submissions if item.opportunity),
            "booking_archetype": Counter(self._opportunity_archetype(item.opportunity) for item in booked_submissions if item.opportunity),
        }
        payload = {}
        insights = []
        for key, counter in categories.items():
            rows = []
            for label, count in counter.most_common(6):
                action = None
                if key == "archetype" and str(label).lower() not in represented:
                    action = f"Consider creating material for {label}."
                rows.append(
                    {
                        "trend_type": key,
                        "label": str(label),
                        "count": count,
                        "insight": self._casting_pattern_row_insight(key, str(label), count),
                        "recommended_action": action,
                    }
                )
            payload[key] = rows
        top_archetype = categories["archetype"].most_common(1)
        top_project = categories["project_type"].most_common(1)
        top_audition_type = categories["audition_type"].most_common(1)
        top_callback_archetype = categories["callback_archetype"].most_common(1)
        top_submission_source = categories["submission_source"].most_common(2)
        submitted_projects = categories["submitted_project_type"].most_common(2)
        if top_archetype:
            insights.append(f"You are seeing more {top_archetype[0][0]} roles than other archetypes in your tracked breakdowns.")
        if top_audition_type:
            insights.append(f"{top_audition_type[0][0]} auditions are the most common audition format in your tracked activity.")
        if submitted_projects:
            insights.append(f"You are submitting more to {submitted_projects[0][0]} than other project types.")
        elif top_project:
            insights.append(f"You are tracking more {top_project[0][0]} breakdowns than other project types.")
        if top_archetype:
            name = top_archetype[0][0]
            if str(name).lower() not in represented:
                insights.append(f"{name} roles are showing up in your activity, but matching materials look underrepresented.")
            else:
                insights.append(f"{name} roles are showing up in your activity and your asset library has some coverage.")
        if top_callback_archetype:
            insights.append(f"Your strongest callback activity is connected to {top_callback_archetype[0][0]}.")
        if len(top_submission_source) >= 2:
            first, second = top_submission_source[0], top_submission_source[1]
            insights.append(f"{first[0]} is producing more tracked activity than {second[0]} in your current data.")
        if not outcome_submissions and pattern_stage["stage"] == "Early Signals":
            insights.append("These are early signals from tracked activity. Add outcomes to reveal what is actually converting.")
        payload.update(pattern_stage)
        payload["insights"] = insights
        return payload

    def _casting_pattern_stage(self, opportunities: list[Opportunity], submissions: list[Submission]) -> dict:
        tracked_activity = len(opportunities) + len(submissions)
        outcome_count = len(
            [
                item for item in submissions
                if item.current_status in {"Requested", "Self-Tape Callback", "In-Person Callback", "Pinned", "Booked", "Passed", "No Response"}
            ]
        )
        submission_count = len(submissions)
        if tracked_activity >= STRONGER_CASTING_PATTERN_ACTIVITY or outcome_count >= STRONGER_CASTING_PATTERN_OUTCOMES:
            stage = "Stronger Patterns"
        elif tracked_activity >= EMERGING_CASTING_PATTERN_ACTIVITY or submission_count >= EMERGING_CASTING_PATTERN_SUBMISSIONS:
            stage = "Emerging Patterns"
        elif tracked_activity >= EARLY_CASTING_PATTERN_ACTIVITY:
            stage = "Early Signals"
        else:
            stage = "Add Data First"
        return {
            "pattern_stage": stage,
            "stage": stage,
            "tracked_breakdowns_or_auditions": tracked_activity,
            "submission_count": submission_count,
            "outcome_count": outcome_count,
            "unlock_message": (
                "Add or track a few more auditions to unlock casting pattern insights."
                if stage == "Add Data First"
                else f"{stage}: based only on your tracked breakdowns, auditions, submissions, callbacks, bookings, goals, archetypes, and materials."
            ),
        }

    def _empty_trends(self) -> dict:
        return {
            "role_type": [],
            "archetype": [],
            "project_type": [],
            "union_status": [],
            "location": [],
            "audition_type": [],
            "submission_source": [],
            "submitted_project_type": [],
            "callback_archetype": [],
            "booking_archetype": [],
            "insights": [],
            "pattern_stage": "Add Data First",
            "stage": "Add Data First",
            "tracked_breakdowns_or_auditions": 0,
            "submission_count": 0,
            "outcome_count": 0,
            "unlock_message": "Add or track a few more auditions to unlock casting pattern insights.",
        }

    def list_quarterly_reviews(self, actor: ActorProfile) -> list[QuarterlyCareerReview]:
        return list(
            self.db.scalars(
                select(QuarterlyCareerReview)
                .where(QuarterlyCareerReview.actor_profile_id == actor.id)
                .order_by(QuarterlyCareerReview.year.desc(), QuarterlyCareerReview.quarter.desc())
            )
        )

    def generate_quarterly_review(self, actor: ActorProfile, payload: QuarterlyCareerReviewCreate) -> QuarterlyCareerReview:
        submissions = self._submissions(actor)
        quarter_submissions = [
            item for item in submissions if self._in_quarter(item.created_at or item.submitted_at, payload.year, payload.quarter)
        ]
        callbacks = [item for item in quarter_submissions if item.current_status in CALLBACK_STATUSES]
        bookings = [item for item in quarter_submissions if item.current_status == "Booked"]
        pins = [item for item in quarter_submissions if item.current_status == "Pinned"]
        performance = self.archetype_performance(actor)
        self_tape_data = self.self_tape_analytics()
        recommended = []
        for archetype in performance["high_potential_stretch_archetypes"][:3]:
            recommended.append(f"Create or refresh {archetype} materials")
        report = {
            "submissions": len(quarter_submissions),
            "callbacks": len(callbacks),
            "bookings": len(bookings),
            "pins": len(pins),
            "top_archetypes": performance["best_performing_archetypes"],
            "underused_materials": [item.title for item in self_tape_data["underused_tapes"]],
            "recommended_materials": recommended,
            "next_quarter_strategy": [
                "Prioritize offices and archetypes with callback traction.",
                "Close the highest-impact material gaps before increasing submission volume.",
                "Keep one deliberate stretch-role lane active each week.",
            ],
        }
        record = QuarterlyCareerReview(
            actor_profile_id=actor.id,
            year=payload.year,
            quarter=payload.quarter,
            report=report,
            explanation="Quarterly review is generated from submission statuses, asset usage signals, self-tape outcomes, and archetype performance.",
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def list_dream_targets(self, actor: ActorProfile) -> list[DreamRoleTarget]:
        return list(
            self.db.scalars(
                select(DreamRoleTarget)
                .where(DreamRoleTarget.actor_profile_id == actor.id)
                .order_by(DreamRoleTarget.updated_at.desc())
            )
        )

    def create_dream_target(self, actor: ActorProfile, payload: DreamRoleTargetCreate) -> DreamRoleTarget:
        record = DreamRoleTarget(actor_profile_id=actor.id, **payload.model_dump())
        self.db.add(record)
        self.db.flush()
        WorkflowConnectorService(self.db).after_dream_target_saved(actor, record)
        WatchListService(self.db).refresh_all()
        self.db.commit()
        self.db.refresh(record)
        return record

    def update_dream_target(self, target_id: UUID, payload: DreamRoleTargetUpdate) -> DreamRoleTarget:
        record = self.db.get(DreamRoleTarget, target_id)
        if not record:
            raise NotFoundError("Dream target not found")
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(record, key, value)
        actor = self.db.get(ActorProfile, record.actor_profile_id)
        if actor:
            WorkflowConnectorService(self.db).after_dream_target_saved(actor, record)
            WatchListService(self.db).refresh_all()
        self.db.commit()
        self.db.refresh(record)
        return record

    def delete_dream_target(self, target_id: UUID) -> None:
        record = self.db.get(DreamRoleTarget, target_id)
        if not record:
            raise NotFoundError("Dream target not found")
        self.db.delete(record)
        self.db.commit()

    def dream_target_readiness(self, actor: ActorProfile) -> list[dict]:
        tasks = list(
            self.db.scalars(
                select(CareerDevelopmentTask).order_by(CareerDevelopmentTask.updated_at.desc())
            )
        )
        assets = list(self.db.scalars(select(Asset).where(Asset.actor_profile_id == actor.id)))
        results = []
        for target in self.list_dream_targets(actor):
            text = " ".join(
                [
                    target.name,
                    target.description or "",
                    " ".join(target.target_archetypes),
                    " ".join(target.target_genres),
                    " ".join(target.target_offices),
                ]
            )
            inferred = target.target_archetypes[0] if target.target_archetypes else self._infer_archetype(text)
            material_score = sum(
                [
                    self._asset_fit(assets, "Headshot", text, inferred, 20),
                    self._asset_fit(assets, "Reel", text, inferred, 20),
                    self._asset_fit(assets, "Slate", text, inferred, 10),
                    self._asset_fit(assets, "Resume", text, inferred, 15),
                ]
            )
            history_score = min(20, len([item for item in self._submissions(actor) if inferred.lower() in f"{item.opportunity.role} {item.opportunity.description}".lower()]) * 5)
            relationship_score = 15 if any(office.lower() in (target.name + " " + " ".join(target.target_offices)).lower() for office in [row.name for row in self.list_casting_offices()]) else 0
            score = min(100, material_score + history_score + relationship_score)
            missing = self._target_missing_materials(assets, text, inferred)
            related_tasks = [
                {
                    "id": str(task.id),
                    "title": task.title,
                    "status": task.status,
                    "priority": task.priority,
                }
                for task in tasks
                if inferred.lower() in f"{task.title} {task.description} {task.related_archetype or ''}".lower()
            ][:5]
            results.append(
                {
                    "target": target,
                    "current_readiness_score": score,
                    "missing_materials": missing,
                    "recommended_actions": [f"Create {item}" for item in missing] or ["Maintain current materials and track outcomes."],
                    "related_career_development_tasks": related_tasks,
                    "explanation": f"{target.name} readiness reflects {inferred} material coverage, similar-role history, and related relationship signals.",
                }
            )
        return results

    def list_self_tapes(self) -> list[SelfTape]:
        return list(self.db.scalars(select(SelfTape).order_by(SelfTape.date_created.desc())))

    def create_self_tape(self, payload: SelfTapeCreate) -> SelfTape:
        self._validate_optional_links(payload.linked_opportunity_id, payload.linked_submission_id)
        record = SelfTape(**payload.model_dump())
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def update_self_tape(self, tape_id: UUID, payload: SelfTapeUpdate) -> SelfTape:
        record = self.db.get(SelfTape, tape_id)
        if not record:
            raise NotFoundError("Self-tape not found")
        data = payload.model_dump(exclude_unset=True)
        self._validate_optional_links(data.get("linked_opportunity_id"), data.get("linked_submission_id"))
        for key, value in data.items():
            setattr(record, key, value)
        self.db.commit()
        self.db.refresh(record)
        return record

    def delete_self_tape(self, tape_id: UUID) -> None:
        record = self.db.get(SelfTape, tape_id)
        if not record:
            raise NotFoundError("Self-tape not found")
        self.db.delete(record)
        self.db.commit()

    def self_tape_analytics(self) -> dict:
        tapes = self.list_self_tapes()
        by_archetype = Counter(archetype for tape in tapes for archetype in tape.archetypes)
        by_outcome = Counter(tape.outcome or "Untracked" for tape in tapes)
        positive = {"Requested", "Self-Tape Callback", "In-Person Callback", "Pinned", "Booked"}
        best = [tape for tape in tapes if tape.outcome in positive]
        underused = [tape for tape in tapes if not tape.linked_submission_id and not tape.outcome]
        return {
            "by_archetype": [{"archetype": name, "count": count} for name, count in by_archetype.most_common()],
            "by_outcome": [{"outcome": name, "count": count} for name, count in by_outcome.most_common()],
            "best_performing_tapes": best[:6],
            "underused_tapes": underused[:6],
        }

    def list_journal_entries(self) -> list[AuditionJournalEntry]:
        return list(self.db.scalars(select(AuditionJournalEntry).order_by(AuditionJournalEntry.date.desc())))

    def create_journal_entry(self, payload: AuditionJournalEntryCreate) -> AuditionJournalEntry:
        self._validate_optional_links(payload.opportunity_id, payload.submission_id)
        entry = AuditionJournalEntry(**payload.model_dump())
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def update_journal_entry(self, entry_id: UUID, payload: AuditionJournalEntryUpdate) -> AuditionJournalEntry:
        entry = self.db.get(AuditionJournalEntry, entry_id)
        if not entry:
            raise NotFoundError("Audition journal entry not found")
        data = payload.model_dump(exclude_unset=True)
        self._validate_optional_links(data.get("opportunity_id"), data.get("submission_id"))
        for key, value in data.items():
            setattr(entry, key, value)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def delete_journal_entry(self, entry_id: UUID) -> None:
        entry = self.db.get(AuditionJournalEntry, entry_id)
        if not entry:
            raise NotFoundError("Audition journal entry not found")
        self.db.delete(entry)
        self.db.commit()

    def list_callback_events(self) -> list[CallbackEvent]:
        return list(self.db.scalars(select(CallbackEvent).order_by(CallbackEvent.created_at.desc())))

    def create_callback_event(self, payload: CallbackEventCreate) -> CallbackEvent:
        self._validate_optional_links(payload.opportunity_id, payload.submission_id)
        event = CallbackEvent(**payload.model_dump())
        self.db.add(event)
        if event.submission_id:
            submission = self.db.get(Submission, event.submission_id)
            if submission and submission.current_status not in {"Pinned", "Booked"}:
                submission.current_status = "Self-Tape Callback" if event.is_virtual else "In-Person Callback"
        self.db.flush()
        ActorWorkEventService(self.db).callback_added(
            event_name=event.event_name,
            opportunity=event.opportunity,
            opportunity_id=event.opportunity_id,
            submission_id=event.submission_id,
            notes=event.preparation_notes or event.notes,
            event_datetime=event.event_datetime,
        )
        self.db.commit()
        self.db.refresh(event)
        return event

    def update_callback_event(self, event_id: UUID, payload: CallbackEventUpdate) -> CallbackEvent:
        event = self.db.get(CallbackEvent, event_id)
        if not event:
            raise NotFoundError("Callback event not found")
        data = payload.model_dump(exclude_unset=True)
        self._validate_optional_links(data.get("opportunity_id"), data.get("submission_id"))
        for key, value in data.items():
            setattr(event, key, value)
        if event.outcome:
            ActorWorkEventService(self.db).callback_completed(
                event_name=event.event_name,
                outcome=event.outcome,
                opportunity_id=event.opportunity_id,
                submission_id=event.submission_id,
                event_datetime=event.event_datetime,
            )
        self.db.commit()
        self.db.refresh(event)
        return event

    def delete_callback_event(self, event_id: UUID) -> None:
        event = self.db.get(CallbackEvent, event_id)
        if not event:
            raise NotFoundError("Callback event not found")
        self.db.delete(event)
        self.db.commit()

    def list_communication_logs(self) -> list[CommunicationLog]:
        return list(self.db.scalars(select(CommunicationLog).order_by(CommunicationLog.date.desc(), CommunicationLog.created_at.desc())))

    def create_communication_log(self, payload: CommunicationLogCreate) -> CommunicationLog:
        record = CommunicationLog(**payload.model_dump())
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def update_communication_log(self, log_id: UUID, payload: CommunicationLogUpdate) -> CommunicationLog:
        record = self.db.get(CommunicationLog, log_id)
        if not record:
            raise NotFoundError("Communication log not found")
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(record, key, value)
        self.db.commit()
        self.db.refresh(record)
        return record

    def delete_communication_log(self, log_id: UUID) -> None:
        record = self.db.get(CommunicationLog, log_id)
        if not record:
            raise NotFoundError("Communication log not found")
        self.db.delete(record)
        self.db.commit()

    def role_similarity(self, actor: ActorProfile) -> list[dict]:
        submissions = [
            item
            for item in self._submissions(actor)
            if item.current_status in CALLBACK_STATUSES and item.opportunity
        ]
        results = []
        seen = set()
        for submission in submissions:
            role = submission.opportunity.role
            key = role.lower()
            if key in seen:
                continue
            seen.add(key)
            suggestions = self._similar_roles(role, submission.opportunity.description)
            results.append(
                {
                    "source_role": role,
                    "similar_roles": suggestions,
                    "explanation": "Similar roles are inferred from callback/booking outcomes, role language, and adjacent authority/career archetypes.",
                }
            )
        return results[:8]

    def prepare_audition(self, opportunity_id: UUID, submission_id: UUID | None = None) -> AuditionPreparationBrief:
        opportunity = self.db.get(Opportunity, opportunity_id)
        if not opportunity or opportunity.is_demo_data:
            raise NotFoundError("Opportunity not found")
        text = f"{opportunity.role} {opportunity.description}".lower()
        tone = "procedural drama" if any(word in text for word in ["detective", "hospital", "legal", "attorney"]) else "grounded contemporary"
        equipment = self.db.scalars(select(ProfessionalEquipmentProfile).limit(1)).first()
        brief = {
            "character_analysis": f"{opportunity.role} is likely defined by status, pressure, and the project world of {opportunity.project}.",
            "objective": "Win the immediate scene while revealing competence, need, and point of view.",
            "obstacles": ["Time pressure", "Conflicting agendas", "What the character cannot openly say"],
            "relationships": "Identify who has power, who needs something, and what history exists before the scene starts.",
            "tone": tone,
            "wardrobe_suggestions": self._wardrobe(opportunity.role),
            "research_topics": self._research_topics(opportunity.role),
            "comparable_shows_or_films": self._comparables(opportunity.role),
            "self_tape_notes": ["Frame chest-up unless instructions differ", "Keep eyeline consistent", "Use clean sound and a neutral background"],
            "home_audition_capabilities": self._equipment_notes(equipment),
            "questions_to_ask_agent_or_casting": [
                "Is there a preferred tone or reference show?",
                "Are there wardrobe or slate requirements?",
                "Is the role local hire or travel-supported?",
            ],
        }
        record = AuditionPreparationBrief(
            opportunity_id=opportunity.id,
            submission_id=submission_id,
            brief=brief,
            explanation="Generated from role title, description, project context, audition logistics, and actor-facing preparation heuristics.",
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def _equipment_notes(self, equipment: ProfessionalEquipmentProfile | None) -> list[str]:
        if not equipment:
            return ["No home audition capabilities profile saved yet."]
        notes = []
        if equipment.cameras:
            notes.append(f"Camera options saved: {', '.join(equipment.cameras[:3])}.")
        if equipment.audio_equipment:
            notes.append(f"Audio options saved: {', '.join(equipment.audio_equipment[:3])}.")
        if equipment.reader_availability:
            notes.append(f"Reader availability: {equipment.reader_availability}.")
        if equipment.internet_upload_speed:
            notes.append(f"Upload speed: {equipment.internet_upload_speed}.")
        if equipment.home_audition_space:
            notes.append(f"Home audition space: {equipment.home_audition_space}.")
        return notes or ["Saved capabilities profile has limited detail."]

    def create_material_plan(self, payload: MaterialCreationPlanCreate) -> MaterialCreationPlan:
        archetype = payload.target_archetype or self._infer_archetype(payload.missing_asset)
        plan = {
            "scene_concept": f"A focused {archetype} scene where the character must make a high-stakes decision under pressure.",
            "length": "60-90 seconds",
            "tone": "grounded, network/cable procedural",
            "character_type": archetype,
            "conflict": "The character must hold authority while revealing a personal stake.",
            "suggested_wardrobe": self._wardrobe(archetype),
            "comparable_shows": self._comparables(archetype),
            "why_this_material_helps": f"It gives casting a clean, immediate sample for {archetype} and adjacent authority roles.",
            "supported_role_types": self._similar_roles(archetype, "")[:6],
        }
        record = MaterialCreationPlan(
            career_task_id=payload.career_task_id,
            missing_asset=payload.missing_asset,
            target_archetype=archetype,
            plan=plan,
            explanation="Plan is grounded in the missing asset request, current stretch archetype map, and casting material conventions.",
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def update_material_plan(self, plan_id: UUID, payload: MaterialCreationPlanUpdate) -> MaterialCreationPlan:
        record = self.db.get(MaterialCreationPlan, plan_id)
        if not record:
            raise NotFoundError("Material creation plan not found")
        data = payload.model_dump(exclude_unset=True)
        if data.get("plan_status") not in {None, "Pending Review", "Approved", "Denied"}:
            raise ValueError("Unsupported material plan status")
        for key, value in data.items():
            setattr(record, key, value)
        self.db.commit()
        self.db.refresh(record)
        return record

    def list_script_sources(self) -> list[ScriptSource]:
        return list(self.db.scalars(select(ScriptSource).order_by(ScriptSource.approved.desc(), ScriptSource.name.asc())))

    def create_script_source(self, payload: ScriptSourceCreate) -> ScriptSource:
        self._validate_rights_status(payload.rights_status)
        record = ScriptSource(**payload.model_dump())
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def update_script_source(self, source_id: UUID, payload: ScriptSourceUpdate) -> ScriptSource:
        record = self.db.get(ScriptSource, source_id)
        if not record:
            raise NotFoundError("Script source not found")
        data = payload.model_dump(exclude_unset=True)
        if "rights_status" in data and data["rights_status"] is not None:
            self._validate_rights_status(data["rights_status"])
        for key, value in data.items():
            setattr(record, key, value)
        self.db.commit()
        self.db.refresh(record)
        return record

    def find_scene_candidates(self, payload: SceneCandidateFindRequest) -> list[SceneCandidate]:
        task = self.db.get(CareerDevelopmentTask, payload.career_task_id) if payload.career_task_id else None
        material_plan_id = getattr(payload, "material_plan_id", None)
        plan = self.db.get(MaterialCreationPlan, material_plan_id) if material_plan_id else None
        if plan and plan.plan_status != "Approved":
            return []
        plan_data = plan.plan if plan else {}
        archetype = (
            payload.target_archetype
            or (plan.target_archetype if plan and plan.target_archetype else None)
            or str(plan_data.get("character_type") or plan_data.get("target_archetype") or "")
            or (task.related_archetype if task and task.related_archetype else None)
        )
        goal = payload.material_goal or (plan.missing_asset if plan else None) or (task.title if task else None)
        archetype = archetype or self._infer_archetype(goal or "Actor reel scene")
        goal = goal or f"{archetype} reel scene"
        if getattr(payload, "generate_original_only", False):
            candidate = self._original_scene_candidate(archetype, goal, task.id if task else payload.career_task_id)
            self.db.add(candidate)
            self.db.commit()
            self.db.refresh(candidate)
            return [candidate]
        approved_sources = list(self.db.scalars(select(ScriptSource).where(ScriptSource.approved.is_(True))))
        candidates = []
        for source in approved_sources:
            candidate = self._candidate_from_source(source, archetype, goal, task.id if task else payload.career_task_id)
            if candidate.result_type not in HIDDEN_SCENE_RESULT_TYPES:
                candidates.append(candidate)
        candidates.extend(self._parallel_scene_candidates(archetype, goal, task.id if task else payload.career_task_id))
        candidates = [candidate for candidate in candidates if candidate.result_type not in HIDDEN_SCENE_RESULT_TYPES]
        primary_candidates = [candidate for candidate in candidates if candidate.result_type in PRIMARY_SCENE_RESULT_TYPES]
        safe_primary_candidates = [candidate for candidate in primary_candidates if candidate.rights_status in RIGHTS_SAFE_STATUSES]
        if not safe_primary_candidates:
            candidates.append(self._original_scene_candidate(archetype, goal, task.id if task else payload.career_task_id))
        for candidate in candidates:
            self.db.add(candidate)
        self.db.commit()
        for candidate in candidates:
            self.db.refresh(candidate)
        return candidates

    def update_scene_candidate(self, candidate_id: UUID, payload: SceneCandidateUpdate) -> SceneCandidate:
        candidate = self.db.get(SceneCandidate, candidate_id)
        if not candidate:
            raise NotFoundError("Scene candidate not found")
        data = payload.model_dump(exclude_unset=True)
        if data.get("action_status") not in {None, "Candidate", "Saved", "Permission Requested", "Original Brief"}:
            raise ValueError("Unsupported scene candidate status")
        for key, value in data.items():
            setattr(candidate, key, value)
        self.db.commit()
        self.db.refresh(candidate)
        return candidate

    def _parallel_scene_candidates(self, archetype: str, goal: str, career_task_id: UUID | None) -> list[SceneCandidate]:
        settings = get_settings()
        if settings.web_search_provider.lower() != "parallel" or not settings.parallel_api_key:
            return []
        try:
            from parallel import Parallel
        except Exception:
            return []

        objective = self._scene_search_objective(archetype, goal)
        queries = self._scene_search_queries(archetype, goal)
        try:
            response = Parallel(api_key=settings.parallel_api_key).search(
                search_queries=queries,
                mode="advanced",
                advanced_settings={"max_results": 8},
                objective=objective,
            )
        except Exception:
            return []

        candidates: list[SceneCandidate] = []
        seen_urls: set[str] = set()
        for result in self._parallel_result_items(response):
            url = str(result.get("url") or result.get("link") or result.get("source_url") or "").strip()
            title = str(result.get("title") or result.get("name") or "Scene source").strip()
            snippet = str(result.get("snippet") or result.get("description") or result.get("text") or "").strip()
            if not url or not title:
                continue
            normalized_url = self._normalized_url(url)
            if normalized_url in seen_urls:
                continue
            seen_urls.add(normalized_url)
            visible_text, fetch_failed = self._fetch_visible_text(url)
            classification_text = " ".join([title, snippet, visible_text])
            result_type = self._classify_scene_result_type(title, classification_text, url, fetch_failed=fetch_failed)
            if result_type in HIDDEN_SCENE_RESULT_TYPES:
                continue
            rights_status = self._classify_scene_rights(title, classification_text, url)
            if result_type == "Rights Unknown":
                rights_status = "Unknown"
            if self._looks_like_copyrighted_film_tv_script(title, classification_text, url) and rights_status == "Unknown":
                continue
            candidates.append(
                SceneCandidate(
                    career_task_id=career_task_id,
                    title=title[:255],
                    result_type=result_type,
                    rights_status=rights_status,
                    source_url=url,
                    logline=snippet[:800] or f"Research this scene source for a short {archetype} reel scene.",
                    scene_brief=self._scene_brief(archetype, goal, self._rights_note_for_status(rights_status)),
                    action_status="Candidate",
                    notes="Found through Parallel public web search. Confirm usage rights before filming or publishing.",
                )
            )
        return candidates

    def _scene_search_objective(self, archetype: str, goal: str) -> str:
        related_values = [self._role_label(value) for value in self._similar_roles(archetype, "")[:4]]
        related = ", ".join(value for value in related_values if value)
        return (
            "Find short acting scenes or monologues suitable for a 60-90 second reel clip "
            f"for a Black woman actor playing {archetype}"
            f"{', ' + related if related else ''}. "
            f"Material goal: {goal}. "
            "Prioritize royalty-free, public-domain, original actor practice scenes, licensed scene libraries, "
            "or script platforms where permission can be requested. Exclude copyrighted film and TV scripts unless "
            "rights are clearly available. Return sources with clear rights or permission context."
        )

    def _role_label(self, value) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            return str(value.get("role") or value.get("title") or value.get("archetype") or "")
        return str(value or "")

    def _scene_search_queries(self, archetype: str, goal: str) -> list[str]:
        core = f"{archetype} {goal}".strip()
        return [
            f"specific acting scene {core} showreel rights",
            f"specific monologue {core} royalty free actor reel",
            f"royalty free acting scene {core} 60 90 seconds",
            f"actor practice scene {core} permission allowed",
            f"public domain monologue scene {core}",
            f"original acting scenes for reels {core}",
            f"licensed script scene permission request {core}",
        ]

    def _parallel_result_items(self, response) -> list[dict]:
        items: list[dict] = []

        def visit(value):
            if isinstance(value, dict):
                if any(key in value for key in ("url", "link", "source_url")):
                    items.append(value)
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)
            elif hasattr(value, "model_dump"):
                visit(value.model_dump())
            elif hasattr(value, "__dict__"):
                visit(vars(value))

        visit(response)
        return items

    def _fetch_visible_text(self, url: str) -> tuple[str, bool]:
        try:
            request = Request(url, headers={"User-Agent": "The Working Actor OS scene research"})
            with urlopen(request, timeout=8) as response:
                content_type = response.headers.get("content-type", "")
                if "text/html" not in content_type and "text/plain" not in content_type:
                    return "", True
                body = response.read(400_000).decode("utf-8", errors="ignore")
        except Exception:
            return "", True
        if "<" not in body:
            return " ".join(body.split())[:20_000], False
        parser = _VisibleTextParser()
        try:
            parser.feed(body)
        except Exception:
            return "", True
        return " ".join(parser.parts)[:20_000], False

    def _classify_scene_result_type(self, title: str, text: str, url: str, fetch_failed: bool = False) -> str:
        combined = " ".join([title, text, url]).lower()
        domain = urlparse(url).netloc.lower().removeprefix("www.")
        if fetch_failed:
            return "Dead / Fetch Failed"
        if any(term in combined for term in ["stock music", "music library", "sound effects", "sfx library", "stock footage"]):
            return "Music / Sound Library"
        if "proudmusiclibrary.com" in domain:
            return "Music / Sound Library"
        if any(term in combined for term in ["casting breakdown", "casting call", "seeking actors", "submit headshot"]):
            return "Not Useful"
        if any(term in combined for term in ["acting class", "workshop", "seminar"]) and not any(term in combined for term in ["scene text", "monologue text", "script excerpt"]):
            return "Not Useful"
        if "actoncue.com" in domain and not self._contains_specific_scene_text(combined):
            return "Resource Guide"
        if "stagemilk.com" in domain and not self._contains_specific_scene_text(combined):
            return "Script Library"
        if "auditionscript" in domain and "script" not in combined:
            return "Dead / Fetch Failed"
        if self._contains_specific_monologue_text(combined):
            return "Specific Monologue"
        if self._contains_specific_scene_text(combined):
            return "Specific Scene"
        if any(term in combined for term in ["scene library", "monologue library", "script library", "practice scenes", "acting scripts"]):
            return "Script Library"
        if any(term in combined for term in ["resource guide", "best sites", "where to find", "list of resources", "guide to"]):
            return "Resource Guide"
        if "rights unknown" in combined:
            return "Rights Unknown"
        return "Not Useful"

    def _contains_specific_scene_text(self, text: str) -> bool:
        scene_signals = [
            "character 1:",
            "character 2:",
            "actor 1:",
            "actor 2:",
            "dialogue:",
            "two person scene",
            "2 person scene",
            "scene excerpt",
            "short scene",
            "practice scene",
        ]
        return any(signal in text for signal in scene_signals) and len(text.split()) > 12

    def _contains_specific_monologue_text(self, text: str) -> bool:
        monologue_signals = ["monologue", "solo piece", "one person scene"]
        return any(signal in text for signal in monologue_signals) and len(text.split()) > 12

    def _classify_scene_rights(self, title: str, snippet: str, url: str) -> str:
        text = " ".join([title, snippet, url]).lower()
        if re.search(r"\b(public domain|gutenberg|wikimedia|creative commons|cc0)\b", text):
            return "Public Domain"
        if re.search(r"\b(royalty[- ]free|free to use|usage rights included|commercial use allowed)\b", text):
            return "Royalty-Free"
        if re.search(r"\b(original scene|original monologue|actor practice scene|practice scenes)\b", text):
            return "Original / User-Owned"
        if re.search(r"\b(licensed|license|licence|rights included)\b", text):
            return "Licensed"
        if re.search(r"\b(permission|required|request rights|contact author|rights holder)\b", text):
            return "Permission Required"
        return "Unknown"

    def _looks_like_copyrighted_film_tv_script(self, title: str, snippet: str, url: str) -> bool:
        text = " ".join([title, snippet, url]).lower()
        risky_terms = ["screenplay pdf", "movie script", "tv script", "film script", "episode script", "transcript"]
        rights_terms = ["public domain", "royalty-free", "licensed", "permission", "creative commons"]
        return any(term in text for term in risky_terms) and not any(term in text for term in rights_terms)

    def _rights_note_for_status(self, status: str) -> str:
        if status in RIGHTS_SAFE_STATUSES:
            return f"{status} source found. Confirm terms before filming or publishing."
        if status == "Permission Required":
            return "Permission may be requestable, but usage is not cleared until granted."
        return "Rights are unknown. Treat this as a research lead only."

    def _normalized_url(self, url: str) -> str:
        parsed = urlparse(url)
        return parsed._replace(fragment="", query="").geturl().rstrip("/").lower()

    def simulate_career_path(self, actor: ActorProfile, payload: CareerPathSimulationCreate) -> CareerPathSimulation:
        performance = self.archetype_performance(actor)
        assets = list(self.db.scalars(select(Asset).where(Asset.actor_profile_id == actor.id)))
        represented = {name for asset in assets for name in asset.archetype_names}
        target_archetypes = performance["best_performing_archetypes"][:3] or ["Authority Figure", "Executive", "Attorney"]
        needed = [name for name in ["Attorney Reel Scene", "Executive Headshot", "Detective Self-Tape"] if self._infer_archetype(name) not in represented]
        tasks = [
            {"title": f"Build {item}", "priority": "High" if index == 0 else "Medium"}
            for index, item in enumerate(needed)
        ]
        result = {
            "target_role_categories": ["Recurring Guest Star", "Procedural Authority", "Professional Decision Maker"],
            "needed_materials": needed,
            "submission_strategy": "Prioritize strong-match roles while reserving a weekly lane for stretch authority submissions.",
            "recommended_archetypes": target_archetypes + [name for name in STRETCH_ARCHETYPES if name not in target_archetypes][:3],
            "development_tasks": tasks,
            "timeline": [
                {"period": "0-3 months", "focus": "Refresh materials and submit to strong-match roles consistently."},
                {"period": "3-9 months", "focus": "Add stretch scenes and track callback response by office/archetype."},
                {"period": "9-24 months", "focus": "Double down on offices and archetypes with callback traction."},
            ],
        }
        record = CareerPathSimulation(
            actor_profile_id=actor.id,
            goal=payload.goal,
            result=result,
            explanation="Simulation is grounded in current assets, submission outcomes, callback/booking history, and stretch-role gaps.",
        )
        self.db.add(record)
        for task in tasks:
            self.db.add(
                CareerDevelopmentTask(
                    title=task["title"],
                    description=f"Career simulator task for goal: {payload.goal}",
                    priority=task["priority"],
                    estimated_impact="High",
                    related_archetype=self._infer_archetype(task["title"]),
                    target_role_types=result["target_role_categories"],
                    supported_archetypes=result["recommended_archetypes"],
                    reason=record.explanation,
                    created_by_agent=True,
                )
            )
        self.db.commit()
        self.db.refresh(record)
        return record

    def _submissions(self, actor: ActorProfile) -> list[Submission]:
        submissions = list(
            self.db.scalars(
                select(Submission)
                .where(Submission.actor_profile_id == actor.id)
                .options(
                    selectinload(Submission.assets),
                    selectinload(Submission.opportunity).selectinload(Opportunity.casting_office),
                )
            )
        )
        return [
            submission
            for submission in submissions
            if not submission.opportunity or not submission.opportunity.is_demo_data
        ]

    def _status_key(self, status: str) -> str:
        return {
            "Requested": "requested",
            "Self-Tape Callback": "self_tape_callbacks",
            "In-Person Callback": "in_person_callbacks",
            "Pinned": "pinned",
            "Booked": "booked",
            "Passed": "passed",
            "No Response": "no_response",
        }.get(status, "submitted")

    def _similar_roles(self, role: str, description: str) -> list[dict]:
        text = f"{role} {description}".lower()
        roles: list[str] = []
        for key, values in SIMILAR_ROLE_MAP.items():
            if key in text:
                roles.extend(values)
        if not roles:
            roles = ["Attorney", "Principal", "Executive Director", "Journalist", "Detective", "Political Staffer"]
        unique = []
        for item in roles:
            if item not in unique:
                unique.append(item)
        return [
            {
                "role": item,
                "confidence": "High" if index < 3 else "Medium",
                "why": f"{item} shares authority, stakes, tone, or institutional context with {role}.",
            }
            for index, item in enumerate(unique[:8])
        ]

    def _infer_archetype(self, value: str) -> str:
        text = value.lower()
        for archetype in STRETCH_ARCHETYPES + ["Authority Figure"]:
            if archetype.lower() in text:
                return archetype
        return "Authority Figure"

    def _wardrobe(self, role: str) -> list[str]:
        text = role.lower()
        if "attorney" in text or "judge" in text:
            return ["Tailored blazer", "Minimal jewelry", "Clean professional palette"]
        if "detective" in text or "investigator" in text:
            return ["Structured jacket", "Subdued colors", "Practical hair and makeup"]
        if "executive" in text or "dean" in text or "principal" in text:
            return ["Polished business layer", "Strong neckline", "Authority-forward styling"]
        return ["Simple fitted layer", "Camera-friendly solid color", "Avoid distracting patterns"]

    def _research_topics(self, role: str) -> list[str]:
        text = role.lower()
        if "attorney" in text or "judge" in text:
            return ["Courtroom procedure", "Legal status behavior", "Professional stakes in legal dramas"]
        if "detective" in text:
            return ["Interview tactics", "Case pressure", "Procedural pacing"]
        if "hospital" in text or "nurse" in text:
            return ["Hospital hierarchy", "Patient advocacy", "Medical procedural tone"]
        return ["Project genre", "Professional vocabulary", "Power dynamics in the scene"]

    def _comparables(self, role: str) -> list[str]:
        text = role.lower()
        if "attorney" in text or "judge" in text:
            return ["The Good Wife", "Law & Order", "Suits"]
        if "detective" in text or "investigator" in text:
            return ["The Rookie", "FBI", "Bosch"]
        if "hospital" in text or "nurse" in text:
            return ["Grey's Anatomy", "The Resident", "Chicago Med"]
        return ["The Morning Show", "Madam Secretary", "This Is Us"]

    def _relationship_or_404(self, relationship_id: UUID) -> ActorRelationship:
        relationship = self.db.get(ActorRelationship, relationship_id)
        if not relationship:
            raise NotFoundError("Relationship not found")
        return relationship

    def _sync_relationship_links(
        self,
        relationship: ActorRelationship,
        opportunity_ids: list[UUID],
        submission_ids: list[UUID],
    ) -> None:
        opportunities = list(
            self.db.scalars(
                select(Opportunity)
                .where(Opportunity.id.in_(opportunity_ids))
                .where(Opportunity.is_demo_data.is_(False))
            )
        ) if opportunity_ids else []
        submissions = list(self.db.scalars(select(Submission).where(Submission.id.in_(submission_ids)))) if submission_ids else []
        if len(opportunities) != len(set(opportunity_ids)):
            raise NotFoundError("One or more linked opportunities were not found")
        if len(submissions) != len(set(submission_ids)):
            raise NotFoundError("One or more linked submissions were not found")
        relationship.linked_opportunities = opportunities
        relationship.linked_submissions = submissions

    def _validate_optional_links(
        self,
        opportunity_id: UUID | None = None,
        submission_id: UUID | None = None,
    ) -> None:
        if opportunity_id:
            opportunity = self.db.get(Opportunity, opportunity_id)
            if not opportunity or opportunity.is_demo_data:
                raise NotFoundError("Linked opportunity not found")
        if submission_id and not self.db.get(Submission, submission_id):
            raise NotFoundError("Linked submission not found")

    def _asset_fit(self, assets: list[Asset], asset_type: str, text: str, archetype: str, max_score: int) -> int:
        candidates = [asset for asset in assets if asset.asset_type == asset_type]
        if not candidates:
            return 0
        for asset in candidates:
            searchable = " ".join([asset.asset_name, asset.description or "", *asset.tags, *asset.archetype_names]).lower()
            if archetype.lower() in searchable or any(word in searchable for word in text.split() if len(word) > 5):
                return max_score
        return max_score // 2

    def _archetype_fit(self, assets: list[Asset], text: str, archetype: str, max_score: int) -> int:
        represented = {name.lower() for asset in assets for name in asset.archetype_names}
        if archetype.lower() in represented:
            return max_score
        if any(name in text for name in represented):
            return max_score // 2
        return 0

    def _travel_fit(self, opportunity: Opportunity, max_score: int) -> int:
        if opportunity.audition_type in {"Self-Tape", "Virtual", "Unknown"}:
            return max_score
        hours = opportunity.audition_drive_time or opportunity.audition_travel_hours
        if hours is None:
            return max_score // 2
        if hours <= 2:
            return max_score
        return 0

    def _similar_role_performance(self, actor: ActorProfile, opportunity: Opportunity, max_score: int, archetype: str | None = None) -> int:
        archetype = archetype or self._infer_archetype(f"{opportunity.role} {opportunity.description}")
        matches = [
            item for item in self._submissions(actor)
            if item.opportunity and archetype.lower() in f"{item.opportunity.role} {item.opportunity.description}".lower()
        ]
        if not matches:
            return 0
        positives = [item for item in matches if item.current_status in CALLBACK_STATUSES]
        return min(max_score, 5 + len(positives) * 5)

    def _opportunity_archetype(self, opportunity: Opportunity) -> str:
        for role in opportunity.breakdown_roles or []:
            profile = role.character_profile
            if profile and profile.primary_archetypes:
                return str(profile.primary_archetypes[0])
        return self._infer_archetype(f"{opportunity.role} {opportunity.description}")

    def _casting_pattern_row_insight(self, key: str, label: str, count: int) -> str:
        templates = {
            "role_type": "{label} appears in {count} tracked breakdowns or auditions.",
            "archetype": "{label} appears in {count} tracked roles.",
            "project_type": "You are tracking {count} {label} breakdowns or auditions.",
            "union_status": "{count} tracked items are marked {label}.",
            "location": "{count} tracked items are connected to {label}.",
            "audition_type": "{label} appears as the audition type on {count} tracked items.",
            "submission_source": "{label} is connected to {count} tracked items.",
            "submitted_project_type": "You submitted to {count} {label} projects.",
            "callback_archetype": "{label} is connected to {count} callback-or-better outcomes.",
            "booking_archetype": "{label} is connected to {count} bookings.",
        }
        template = templates.get(key, "{label} appears in {count} tracked items.")
        return template.format(label=label, count=count)

    def _validate_rights_status(self, status: str) -> None:
        if status not in SCRIPT_RIGHTS_STATUSES:
            raise ValueError("Unsupported rights status")

    def _candidate_from_source(
        self, source: ScriptSource, archetype: str, goal: str, career_task_id: UUID | None
    ) -> SceneCandidate:
        visible_text = ""
        fetch_failed = False
        if source.url:
            visible_text, fetch_failed = self._fetch_visible_text(source.url)
        result_type = self._classify_scene_result_type(
            source.name,
            " ".join([source.source_type, source.notes or "", visible_text]),
            source.url or "",
            fetch_failed=fetch_failed if source.url else False,
        )
        if result_type == "Not Useful" and source.source_type.lower() in {"licensed database", "rights-request platform", "practice scene library", "royalty-free scenes", "public domain"}:
            result_type = "Script Library"
        safe_note = (
            "Rights status suggests this may be usable, but the actor should still confirm usage rights before filming or publishing."
            if source.rights_status in RIGHTS_SAFE_STATUSES
            else "Permission is not confirmed. Treat this as a research lead only."
        )
        return SceneCandidate(
            script_source_id=source.id,
            career_task_id=career_task_id,
            title=f"{archetype} scene lead from {source.name}",
            result_type=result_type,
            rights_status=source.rights_status,
            source_url=source.url,
            logline=f"Research {source.name} for a short {archetype} scene that supports {goal}.",
            scene_brief=self._scene_brief(archetype, goal, safe_note),
            action_status="Candidate",
            notes=safe_note,
        )

    def _original_scene_candidate(self, archetype: str, goal: str, career_task_id: UUID | None) -> SceneCandidate:
        return SceneCandidate(
            career_task_id=career_task_id,
            title=f"Original {archetype} scene brief",
            result_type="Specific Scene",
            rights_status="Original / User-Owned",
            logline=f"Original scene brief for a {archetype} material goal.",
            scene_brief=self._scene_brief(
                archetype,
                goal,
                "Original scene brief — not a copied script.",
            ),
            action_status="Original Brief",
            notes="Original scene brief — not a copied script.",
        )

    def _scene_brief(self, archetype: str, goal: str, rights_note: str) -> dict:
        return {
            "label": rights_note,
            "character_type": archetype,
            "tone": "Grounded, actor-forward, reel-friendly",
            "conflict": "The character wants control of the moment, but the other person forces an emotional reveal.",
            "relationship": "Two-person scene with a clear personal or professional stake.",
            "setting": "Simple interior that can be filmed cleanly at home or in a neutral room.",
            "length": "60-90 seconds",
            "dialogue_goals": [
                "Show active listening and behavior between lines.",
                "Give the character a clear turn or reveal.",
                "Avoid exposition-heavy dialogue.",
            ],
            "supported_archetypes": [archetype, *self._similar_roles(archetype, "")[:4]],
            "usage_warning": "Always confirm usage rights before filming or publishing a scene from an existing script.",
        }

    def _best_breakdown_role(self, opportunity: Opportunity) -> BreakdownRole | None:
        roles = list(opportunity.breakdown_roles or [])
        if not roles:
            return None
        fit_rank = {
            "Strong Fit": 0,
            "Possible Fit": 1,
            "Stretch Fit": 2,
            "Needs Review": 3,
            "Not Fit": 4,
        }
        return sorted(roles, key=lambda role: (fit_rank.get(role.fit_status, 5), -(role.fit_score or 0)))[0]

    def _character_archetypes(self, profile) -> list[str]:
        if not profile:
            return []
        seen = set()
        archetypes = []
        for archetype in [*(profile.primary_archetypes or []), *(profile.secondary_archetypes or [])]:
            key = str(archetype).strip().lower()
            if key and key not in seen:
                seen.add(key)
                archetypes.append(str(archetype).strip())
        return archetypes

    def _character_archetype_confidence(self, profile) -> int:
        if not profile:
            return 0
        scores = profile.archetype_confidence_scores or []
        confidences = [
            int(item.get("confidence", 0))
            for item in scores
            if isinstance(item, dict) and str(item.get("archetype", "")).strip()
        ]
        if confidences:
            return max(confidences)
        return 60 if (profile.primary_archetypes or profile.secondary_archetypes) else 0

    def _readiness_role_text(self, opportunity: Opportunity, role: BreakdownRole | None, archetypes: list[str]) -> str:
        role_parts = []
        if role:
            role_parts = [
                role.role_name,
                role.billing or "",
                role.role_type or "",
                role.character_description or "",
                role.vocal_requirements or "",
                role.dance_requirements or "",
                role.movement_requirements or "",
                role.special_skills or "",
            ]
        return " ".join(
            [
                opportunity.role,
                opportunity.project,
                opportunity.description or "",
                opportunity.category or "",
                *role_parts,
                *archetypes,
            ]
        )

    def _readiness_label(self, score: int, role: BreakdownRole | None, character_ready: bool) -> str:
        if role and role.fit_status == "Not Fit":
            return "Not Recommended"
        if role and role.fit_status == "Stretch Fit":
            return "Stretch"
        if not character_ready:
            return "Needs Materials"
        if score >= 85:
            return "Ready"
        if score >= 70:
            return "Mostly Ready"
        if score >= 50:
            return "Needs Materials"
        return "Not Recommended"

    def _role_bucket(self, role: str, description: str) -> str:
        text = f"{role} {description}".lower()
        if any(word in text for word in ["detective", "attorney", "judge", "hospital", "doctor", "nurse", "federal", "police"]):
            return "Procedural Drama"
        if any(word in text for word in ["mom", "parent", "neighbor", "teacher", "friend"]):
            return "Family / Community"
        if any(word in text for word in ["executive", "ceo", "political", "staffer", "principal", "dean"]):
            return "Authority / Leadership"
        if "comedy" in text:
            return "Comedy"
        return "General"

    def _in_quarter(self, value: datetime | None, year: int, quarter: int) -> bool:
        if value is None:
            return False
        return value.year == year and ((value.month - 1) // 3 + 1) == quarter

    def _target_missing_materials(self, assets: list[Asset], text: str, archetype: str) -> list[str]:
        missing = []
        if self._asset_fit(assets, "Headshot", text, archetype, 10) < 8:
            missing.append(f"{archetype} headshot")
        if self._asset_fit(assets, "Reel", text, archetype, 10) < 8:
            missing.append(f"{archetype} reel scene")
        if self._asset_fit(assets, "Slate", text, archetype, 10) < 6:
            missing.append(f"{archetype} slate variation")
        if self._asset_fit(assets, "Resume", text, archetype, 10) < 6:
            missing.append("resume credits or formatting for this target")
        return missing
