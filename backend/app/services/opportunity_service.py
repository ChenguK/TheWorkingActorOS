from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError
from app.db.models import Opportunity, SelfTapeWorkflow, Submission
from app.repositories.opportunity import OpportunityRepository
from app.schemas.opportunity import OpportunityCreate, OpportunityUpdate
from app.services.breakdown_details_service import BreakdownDetailsService
from app.services.breakdown_intelligence_engine import BreakdownIntelligenceEngine
from app.services.breakdown_role_service import BreakdownRoleService
from app.services.character_intelligence_engine import CharacterIntelligenceEngine
from app.services.breakdown_deadline_service import BreakdownDeadlineService
from app.services.manual_override_service import ManualOverrideService
from app.services.opportunity_intelligence_service import OpportunityIntelligenceService
from app.services.trust_verification_service import TrustVerificationService
from app.services.actor_work_event_service import ActorWorkEventService


class OpportunityService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = OpportunityRepository(db)

    def list(self, q: str | None = None, include_hidden: bool = False) -> list[Opportunity]:
        opportunities = self.repo.search(q=q, include_hidden=include_hidden)
        changed = False
        for opportunity in opportunities:
            deadline_result = BreakdownDeadlineService().apply_to_opportunity(opportunity)
            if deadline_result.expired or deadline_result.needs_review:
                changed = True
                continue
            if not (opportunity.source_metadata or {}).get("trust_verification"):
                TrustVerificationService(self.db).verify(opportunity)
                changed = True
            if not opportunity.production_details or not opportunity.role_details or not opportunity.ai_summary:
                self._ensure_details(opportunity)
                BreakdownRoleService(self.db).sync_from_details(opportunity)
                CharacterIntelligenceEngine(self.db).run_for_opportunity(opportunity)
                TrustVerificationService(self.db).verify(opportunity)
                changed = True
            elif (opportunity.role_details or {}).get("available_roles") and not opportunity.breakdown_roles:
                BreakdownRoleService(self.db).sync_from_details(opportunity)
                CharacterIntelligenceEngine(self.db).run_for_opportunity(opportunity)
                changed = True
            elif opportunity.breakdown_roles and any(role.character_profile is None for role in opportunity.breakdown_roles):
                CharacterIntelligenceEngine(self.db).run_for_opportunity(opportunity)
                changed = True
        if changed:
            self.db.commit()
        if not include_hidden:
            opportunities = [
                opportunity
                for opportunity in opportunities
                if opportunity.visibility_status == "visible" and opportunity.hidden_by_rule not in {"deadline_expired", "needs_date_review"}
            ]
        return opportunities

    def create(self, payload: OpportunityCreate) -> Opportunity:
        opportunity = self.repo.add(Opportunity(**payload.model_dump()))
        self._apply_breakdown_parse(opportunity, opportunity.description, "Deep Parse")
        self._apply_manual_entry_defaults(opportunity)
        BreakdownDeadlineService().apply_to_opportunity(opportunity)
        BreakdownRoleService(self.db).sync_from_details(opportunity)
        OpportunityIntelligenceService(self.db).enrich(opportunity)
        TrustVerificationService(self.db).verify(opportunity)
        self._apply_manual_entry_defaults(opportunity)
        self._ensure_self_tape_workflow(opportunity)
        ActorWorkEventService(self.db).accepted_breakdown(opportunity)
        self.db.commit()
        return opportunity

    def get(self, opportunity_id) -> Opportunity:
        opportunity = self.repo.get(opportunity_id)
        if not (opportunity.source_metadata or {}).get("trust_verification"):
            TrustVerificationService(self.db).verify(opportunity)
            self.db.commit()
        return opportunity

    def update(self, opportunity_id, payload: OpportunityUpdate) -> Opportunity:
        opportunity = self.repo.get(opportunity_id)
        update_data = payload.model_dump(exclude_unset=True)
        reason = update_data.pop("override_reason", None)
        before = self._snapshot(opportunity, update_data.keys())
        opportunity = self.repo.apply_updates(
            opportunity, update_data
        )
        if payload.description is not None:
            self._apply_breakdown_parse(opportunity, opportunity.description, "Deep Parse")
        else:
            self._ensure_details(opportunity)
        self._apply_manual_entry_defaults(opportunity)
        BreakdownDeadlineService().apply_to_opportunity(opportunity)
        BreakdownRoleService(self.db).sync_from_details(opportunity)
        OpportunityIntelligenceService(self.db).enrich(opportunity)
        TrustVerificationService(self.db).verify(opportunity)
        self._apply_manual_entry_defaults(opportunity)
        self._ensure_self_tape_workflow(opportunity)
        ManualOverrideService(self.db).log_many(
            entity_type="Opportunity",
            entity_id=opportunity.id,
            before=before,
            after=self._snapshot(opportunity, before.keys()),
            reason=reason or "User edited breakdown.",
        )
        self.db.commit()
        return opportunity

    def delete(self, opportunity_id) -> None:
        opportunity = self.repo.get(opportunity_id)
        linked_submission_id = self.db.scalar(
            select(Submission.id).where(Submission.opportunity_id == opportunity.id).limit(1)
        )
        if linked_submission_id is not None:
            raise ConflictError(
                {
                    "code": "opportunity_has_submissions",
                    "message": "This opportunity cannot be permanently deleted because it has linked submissions. Reject or archive it instead.",
                }
            )
        self.repo.delete(opportunity)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            linked_submission_id = self.db.scalar(
                select(Submission.id).where(Submission.opportunity_id == opportunity.id).limit(1)
            )
            if linked_submission_id is not None:
                raise ConflictError(
                    {
                        "code": "opportunity_has_submissions",
                        "message": "This opportunity cannot be permanently deleted because it has linked submissions. Reject or archive it instead.",
                    }
                )
            raise

    def reject(self, opportunity_id, highlighted_text: str | None = None, reason: str | None = None) -> Opportunity:
        opportunity = self.repo.get(opportunity_id)
        before = self._snapshot(opportunity, ["visibility_status", "hidden_by_rule", "rejection_reason"])
        highlighted_text = (highlighted_text or "").strip() or None
        reason = (reason or "").strip() or None
        stored_reason = reason or self._reason_from_highlight(highlighted_text) or "Rejected by user."
        opportunity.visibility_status = "discarded"
        opportunity.hidden_by_rule = "user_rejected"
        opportunity.hidden_reason = stored_reason
        opportunity.rejection_reason = stored_reason
        opportunity.highlighted_text_as_rejection_reason = highlighted_text
        opportunity.status = "archived"
        opportunity.manual_review_required = False
        opportunity.source_metadata = {
            **(opportunity.source_metadata or {}),
            "user_rejected": True,
            "highlighted_text_as_rejection_reason": highlighted_text,
        }
        TrustVerificationService(self.db).verify(opportunity)
        ManualOverrideService(self.db).log_many(
            entity_type="Opportunity",
            entity_id=opportunity.id,
            before=before,
            after=self._snapshot(opportunity, before.keys()),
            reason=stored_reason,
        )
        self.db.commit()
        return opportunity

    def parse_breakdown_text(self, opportunity_id, raw_text: str) -> Opportunity:
        opportunity = self.repo.get(opportunity_id)
        parsed = self._apply_breakdown_parse(opportunity, raw_text, "Manual Paste Reparse")
        opportunity.description = raw_text
        self._apply_manual_entry_defaults(opportunity)
        BreakdownDeadlineService().apply_to_opportunity(opportunity)
        OpportunityIntelligenceService(self.db).enrich(opportunity)
        TrustVerificationService(self.db).verify(opportunity)
        self._apply_manual_entry_defaults(opportunity)
        self._ensure_self_tape_workflow(opportunity)
        self.db.commit()
        return opportunity

    def deep_parse(self, opportunity_id) -> Opportunity:
        opportunity = self.repo.get(opportunity_id)
        self._apply_breakdown_parse(opportunity, opportunity.description, "Deep Parse")
        self._apply_manual_entry_defaults(opportunity)
        BreakdownDeadlineService().apply_to_opportunity(opportunity)
        BreakdownRoleService(self.db).sync_from_details(opportunity)
        OpportunityIntelligenceService(self.db).enrich(opportunity)
        TrustVerificationService(self.db).verify(opportunity)
        self._apply_manual_entry_defaults(opportunity)
        self.db.commit()
        return opportunity

    def approve_as_acting_breakdown(self, opportunity_id) -> Opportunity:
        opportunity = self.repo.get(opportunity_id)
        before = self._snapshot(
            opportunity,
            [
                "breakdown_classification",
                "visibility_status",
                "hidden_by_rule",
                "hidden_reason",
                "manual_review_required",
                "rejection_reason",
            ],
        )
        opportunity.breakdown_classification = "Acting Role"
        opportunity.visibility_status = "visible"
        opportunity.hidden_by_rule = None
        opportunity.hidden_reason = None
        opportunity.manual_review_required = False
        opportunity.rejection_reason = None
        opportunity.source_metadata = {
            **(opportunity.source_metadata or {}),
            "user_approved_as_acting_breakdown": True,
            "missing_fields": self._missing_fields(opportunity),
        }
        OpportunityIntelligenceService(self.db).enrich(opportunity)
        TrustVerificationService(self.db).verify(opportunity)
        self._ensure_self_tape_workflow(opportunity)
        ActorWorkEventService(self.db).accepted_breakdown(opportunity)
        opportunity.visibility_status = "visible"
        opportunity.hidden_by_rule = None
        opportunity.hidden_reason = None
        opportunity.manual_review_required = False
        ManualOverrideService(self.db).log_many(
            entity_type="Opportunity",
            entity_id=opportunity.id,
            before=before,
            after=self._snapshot(opportunity, before.keys()),
            reason="User approved as acting breakdown.",
        )
        self.db.commit()
        return opportunity

    def _ensure_self_tape_workflow(self, opportunity: Opportunity) -> None:
        if opportunity.audition_type != "Self-Tape" or opportunity.is_demo_data:
            return
        existing = self.db.scalar(
            select(SelfTapeWorkflow)
            .where(SelfTapeWorkflow.opportunity_id == opportunity.id)
            .where(SelfTapeWorkflow.submission_id.is_(None))
        )
        role_details = opportunity.role_details or {}
        source_metadata = opportunity.source_metadata or {}
        tape_due_at = self._coerce_datetime(
            role_details.get("self_tape_due_date")
            or role_details.get("tape_due_date")
            or opportunity.audition_deadline
            or opportunity.submission_deadline
        )
        upload_link = (
            role_details.get("self_tape_submission_link")
            or source_metadata.get("self_tape_submission_link")
            or source_metadata.get("submission_link")
        )
        preparation = (
            role_details.get("preparation_instructions")
            or role_details.get("preparation")
            or (opportunity.production_details or {}).get("preparation")
        )
        if existing:
            existing.tape_due_at = tape_due_at or existing.tape_due_at
            existing.upload_link = upload_link or existing.upload_link
            existing.slate_requirements = preparation or existing.slate_requirements
            return
        self.db.add(
            SelfTapeWorkflow(
                opportunity_id=opportunity.id,
                status="Not Started",
                tape_due_at=tape_due_at,
                upload_link=upload_link,
                slate_requirements=preparation,
            )
        )

    def _coerce_datetime(self, value) -> datetime | None:
        if value is None or isinstance(value, datetime):
            return value
        if isinstance(value, str):
            normalized = value.strip()
            if not normalized:
                return None
            try:
                return datetime.fromisoformat(normalized.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None

    def _apply_breakdown_parse(self, opportunity: Opportunity, raw_text: str, parse_mode: str) -> dict:
        engine_result = BreakdownIntelligenceEngine(self.db).run_for_opportunity(
            opportunity, raw_text, parse_mode
        )
        parsed = engine_result["details"]
        opportunity.source_metadata = {
            **(opportunity.source_metadata or {}),
            "manual_paste_received_at": parsed["source_metadata"].get("parse_source"),
            "last_manual_parse_at": parsed["source_metadata"].get("parsed_at"),
            "actor_facing_parse_summary": engine_result.get("actor_summary"),
        }
        opportunity.production_details = {
            **(opportunity.production_details or {}),
            **parsed["production_details"],
        }
        if parsed["production_details"].get("project_type"):
            opportunity.project_type = parsed["production_details"]["project_type"]
        if parsed["production_details"].get("union_status"):
            opportunity.union = parsed["production_details"]["union_status"]
        opportunity.role_details = {
            **(opportunity.role_details or {}),
            **parsed["role_details"],
        }
        opportunity.extracted_facts = {
            **(opportunity.extracted_facts or {}),
            **parsed.get("extracted_facts", {}),
        }
        opportunity.ai_inference = {
            **(opportunity.ai_inference or {}),
            **parsed.get("ai_inference", {}),
        }
        if parsed["role_details"].get("audition_type"):
            opportunity.audition_type = parsed["role_details"]["audition_type"]
        if parsed["role_details"].get("audition_location_name") and not opportunity.audition_location:
            opportunity.audition_location = parsed["role_details"]["audition_location_name"]
        opportunity.ai_summary = parsed["ai_summary"]
        opportunity.breakdown_classification = parsed["breakdown_classification"]
        opportunity.rejection_reason = parsed["rejection_reason"]
        BreakdownRoleService(self.db).sync_from_details(opportunity)
        TrustVerificationService(self.db).verify(opportunity)
        return parsed

    def _snapshot(self, opportunity: Opportunity, field_names) -> dict:
        return {field: getattr(opportunity, field, None) for field in field_names}

    def _apply_manual_entry_defaults(self, opportunity: Opportunity) -> None:
        if opportunity.source_type not in {"Manual Entry", "Agent Submission", "Direct Email"}:
            return
        has_role_signal = bool(
            opportunity.project_type
            or opportunity.role
            or (opportunity.role_details or {}).get("character_description")
            or opportunity.description
        )
        if opportunity.breakdown_classification == "Unknown" and has_role_signal:
            opportunity.breakdown_classification = "Acting Role"
        protected_rules = {"user_rejected", "deadline_expired", "needs_date_review"}
        if not str(opportunity.hidden_by_rule or "").startswith("dealbreaker_") and opportunity.hidden_by_rule not in protected_rules:
            opportunity.visibility_status = "visible"
            opportunity.hidden_by_rule = None
            opportunity.hidden_reason = None
        missing_fields = self._missing_fields(opportunity)
        opportunity.manual_review_required = False
        opportunity.source_metadata = {
            **(opportunity.source_metadata or {}),
            "manual_entry_trusted": True,
            "missing_fields": missing_fields,
            "complete_breakdown_prompt": bool(missing_fields),
        }

    def _reason_from_highlight(self, highlighted_text: str | None) -> str | None:
        if not highlighted_text:
            return None
        lowered = highlighted_text.lower()
        if any(term in lowered for term in ["male", "man", "men", "he/him"]):
            return f"Demographic mismatch: {highlighted_text}"
        if any(term in lowered for term in ["background", "extra", "brand ambassador", "class", "workshop", "seminar"]):
            return f"Opted-out role type: {highlighted_text}"
        if any(term in lowered for term in ["age", "read", "20", "teen"]):
            return f"Playable age mismatch: {highlighted_text}"
        return f"Rejected based on highlighted breakdown text: {highlighted_text}"

    def _missing_fields(self, opportunity: Opportunity) -> list[str]:
        checks = {
            "Project type": opportunity.project_type or (opportunity.production_details or {}).get("project_type"),
            "Role billing": opportunity.role_type or (opportunity.role_details or {}).get("role_type"),
            "Audition type": opportunity.audition_type if opportunity.audition_type != "Unknown" else None,
            "Audition/Tape due date": opportunity.submission_deadline or opportunity.audition_deadline or (opportunity.role_details or {}).get("audition_date"),
            "Shoot/performance location": opportunity.location or (opportunity.production_details or {}).get("performance_location"),
            "Casting office": opportunity.casting_office_id or (opportunity.production_details or {}).get("casting_office"),
            "Union status": opportunity.union,
        }
        return [label for label, value in checks.items() if not value]

    def _ensure_details(self, opportunity: Opportunity) -> None:
        if opportunity.production_details and opportunity.role_details and opportunity.ai_summary:
            return
        details = BreakdownDetailsService().from_fields(
            role=opportunity.role,
            project=opportunity.project,
            union=opportunity.union,
            location=opportunity.location,
            description=opportunity.description,
            source_name=opportunity.source.name if opportunity.source else None,
            source_url=opportunity.original_post_url,
            source_type=opportunity.source_type,
            platform=opportunity.platform,
            category=opportunity.category,
            role_type=opportunity.role_type,
            project_type=opportunity.project_type,
            archetypes=opportunity.archetypes,
            audition_type=opportunity.audition_type,
            rate=opportunity.rate,
            shoot_location=opportunity.shoot_location,
            audition_location=opportunity.audition_location,
            travel_covered=opportunity.travel_covered,
            housing_covered=opportunity.housing_covered,
            submission_deadline=str(opportunity.submission_deadline) if opportunity.submission_deadline else None,
            audition_deadline=str(opportunity.audition_deadline) if opportunity.audition_deadline else None,
            callback_info=str(opportunity.callback_date) if opportunity.callback_date else None,
        )
        opportunity.source_metadata = {**details["source_metadata"], **(opportunity.source_metadata or {})}
        opportunity.production_details = {**details["production_details"], **(opportunity.production_details or {})}
        opportunity.role_details = {**details["role_details"], **(opportunity.role_details or {})}
        opportunity.extracted_facts = {**details.get("extracted_facts", {}), **(opportunity.extracted_facts or {})}
        opportunity.ai_inference = {**details.get("ai_inference", {}), **(opportunity.ai_inference or {})}
        opportunity.ai_summary = opportunity.ai_summary or details["ai_summary"]
