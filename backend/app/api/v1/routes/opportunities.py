from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.strategy_agent import StrategyAgent
from app.core.database import get_db
from app.core.errors import NotFoundError
from app.db.models import ActorProfile
from app.schemas.agent import AgentRecommendationRead
from app.schemas.opportunity import BreakdownTextParse, MaterialOpportunityMatch, OpportunityCreate, OpportunityRead, OpportunityReject, OpportunityUpdate
from app.services.material_match_service import MaterialMatchService
from app.services.demographic_match_service import DemographicMatchService
from app.services.opportunity_service import OpportunityService
from app.services.executive_intelligence_service import ExecutiveIntelligenceService

router = APIRouter()


@router.get("", response_model=list[OpportunityRead])
def list_opportunities(
    q: str | None = None, include_hidden: bool = False, db: Session = Depends(get_db)
):
    return OpportunityService(db).list(q, include_hidden=include_hidden)


@router.post("", response_model=OpportunityRead, status_code=201)
def create_opportunity(payload: OpportunityCreate, db: Session = Depends(get_db)):
    return OpportunityService(db).create(payload)


@router.get("/material-matches", response_model=list[MaterialOpportunityMatch])
def material_matches(
    asset_id: UUID | None = None,
    include_hidden: bool = False,
    min_score: int = 15,
    db: Session = Depends(get_db),
):
    actor = db.scalars(select(ActorProfile).limit(1)).first()
    if not actor:
        raise NotFoundError("Create an actor profile before matching materials to opportunities")
    return MaterialMatchService(db).find_matches(
        actor=actor,
        asset_id=asset_id,
        include_hidden=include_hidden,
        min_score=min_score,
    )


@router.get("/{opportunity_id}", response_model=OpportunityRead)
def get_opportunity(opportunity_id: UUID, db: Session = Depends(get_db)):
    return OpportunityService(db).get(opportunity_id)


@router.get("/{opportunity_id}/submission-history")
def get_submission_history(opportunity_id: UUID, db: Session = Depends(get_db)):
    opportunity = OpportunityService(db).get(opportunity_id)
    return ExecutiveIntelligenceService(db).previous_submission_history(opportunity)


@router.get("/{opportunity_id}/similar")
def get_similar_breakdowns(opportunity_id: UUID, db: Session = Depends(get_db)):
    opportunity = OpportunityService(db).get(opportunity_id)
    return ExecutiveIntelligenceService(db).breakdown_similarity(opportunity)


@router.post("/{opportunity_id}/recommend", response_model=AgentRecommendationRead)
def recommend_opportunity(opportunity_id: UUID, db: Session = Depends(get_db)):
    actor = db.scalars(select(ActorProfile).limit(1)).first()
    if not actor:
        raise NotFoundError("Create an actor profile before running recommendations")
    opportunity = OpportunityService(db).get(opportunity_id)
    if opportunity.is_demo_data:
        raise NotFoundError("Opportunity not found")
    return StrategyAgent(db).analyze(opportunity, actor)


@router.post("/{opportunity_id}/demographic-check", response_model=OpportunityRead)
def refresh_demographic_check(opportunity_id: UUID, db: Session = Depends(get_db)):
    opportunity = OpportunityService(db).get(opportunity_id)
    DemographicMatchService(db).apply(opportunity)
    db.commit()
    db.refresh(opportunity)
    return opportunity


@router.post("/{opportunity_id}/parse-breakdown-text", response_model=OpportunityRead)
def parse_breakdown_text(
    opportunity_id: UUID, payload: BreakdownTextParse, db: Session = Depends(get_db)
):
    return OpportunityService(db).parse_breakdown_text(opportunity_id, payload.raw_text)


@router.post("/{opportunity_id}/deep-parse", response_model=OpportunityRead)
def deep_parse_breakdown(opportunity_id: UUID, db: Session = Depends(get_db)):
    return OpportunityService(db).deep_parse(opportunity_id)


@router.post("/{opportunity_id}/approve-acting-breakdown", response_model=OpportunityRead)
def approve_acting_breakdown(opportunity_id: UUID, db: Session = Depends(get_db)):
    return OpportunityService(db).approve_as_acting_breakdown(opportunity_id)


@router.post("/{opportunity_id}/reject", response_model=OpportunityRead)
def reject_opportunity(opportunity_id: UUID, payload: OpportunityReject, db: Session = Depends(get_db)):
    return OpportunityService(db).reject(
        opportunity_id,
        highlighted_text=payload.highlighted_text_as_rejection_reason,
        reason=payload.rejection_reason,
    )


@router.patch("/{opportunity_id}", response_model=OpportunityRead)
def update_opportunity(
    opportunity_id: UUID, payload: OpportunityUpdate, db: Session = Depends(get_db)
):
    return OpportunityService(db).update(opportunity_id, payload)


@router.delete("/{opportunity_id}", status_code=204)
def delete_opportunity(opportunity_id: UUID, db: Session = Depends(get_db)):
    OpportunityService(db).delete(opportunity_id)
