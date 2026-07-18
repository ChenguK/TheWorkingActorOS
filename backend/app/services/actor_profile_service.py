from sqlalchemy.orm import Session

from app.db.models import ActorProfile, Opportunity
from app.repositories.actor_profile import ActorProfileRepository
from app.schemas.actor_profile import ActorProfileCreate, ActorProfileUpdate
from app.services.demographic_match_service import DemographicMatchService
from app.services.opportunity_intelligence_service import (
    DEFAULT_EXCLUDED_ROLE_TYPES,
    DEFAULT_INCLUDED_ROLE_TYPES,
    OpportunityIntelligenceService,
)
from app.services.workflow_connector_service import WorkflowConnectorService


class ActorProfileService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = ActorProfileRepository(db)

    def get_or_none(self) -> ActorProfile | None:
        return self.repo.get_single()

    def create_or_replace(self, payload: ActorProfileCreate) -> ActorProfile:
        existing = self.repo.get_single()
        data = payload.model_dump(exclude={"id", "created_at", "updated_at"})
        if existing:
            actor = self.repo.apply_updates(existing, data)
        else:
            actor = self.repo.add(ActorProfile(**data))
        self._ensure_role_preferences(actor)
        self._refresh_breakdown_eligibility(actor)
        WorkflowConnectorService(self.db).profile_changed(actor, set(data.keys()))
        self.db.commit()
        return actor

    def update(self, payload: ActorProfileUpdate) -> ActorProfile:
        actor = self.repo.get_single()
        if not actor:
            raise ValueError("Create an actor profile before updating it")
        data = payload.model_dump(exclude={"id", "created_at", "updated_at"}, exclude_unset=True)
        actor = self.repo.apply_updates(actor, data)
        self._ensure_role_preferences(actor)
        self._refresh_breakdown_eligibility(actor)
        WorkflowConnectorService(self.db).profile_changed(actor, set(data.keys()))
        self.db.commit()
        return actor

    def _ensure_role_preferences(self, actor: ActorProfile) -> None:
        if not actor.included_role_types:
            actor.included_role_types = DEFAULT_INCLUDED_ROLE_TYPES
        if not actor.excluded_role_types:
            actor.excluded_role_types = DEFAULT_EXCLUDED_ROLE_TYPES

    def _refresh_breakdown_eligibility(self, actor: ActorProfile) -> None:
        DemographicMatchService(self.db).refresh_all(actor)
        service = OpportunityIntelligenceService(self.db)
        for opportunity in self.db.query(Opportunity).filter(Opportunity.is_demo_data.is_(False)).all():
            service.enrich(opportunity)
