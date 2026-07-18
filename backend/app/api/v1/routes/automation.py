from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, not_, or_, select
from sqlalchemy.orm import Session

from app.automation.discovery.service import DiscoveryAutomationService
from app.automation.queue.service import SubmissionAutomationService
from app.core.database import get_db
from app.db.models import ActorProfile, Opportunity
from app.schemas.agent import DiscoveryPluginRead, SubmissionAutomationQueueRead
from app.schemas.discovery import (
    DiscoverySettingsRead,
    DiscoverySettingsUpdate,
    DiscoveryProviderSettingsRead,
    DiscoveryProviderSettingsUpdate,
    SourceResearchItemCreate,
    SourceResearchReject,
    SourceResearchItemRead,
    SourceResearchItemUpdate,
)
from app.schemas.opportunity import OpportunityRead
from app.services.source_research_service import SourceResearchService
from app.services.capability_service import CapabilityService
from app.services.opportunity_intelligence_service import OpportunityIntelligenceService

router = APIRouter()


@router.get("/capabilities")
def capabilities(db: Session = Depends(get_db)):
    return CapabilityService(db).snapshot()


@router.get("/discovery/plugins", response_model=list[DiscoveryPluginRead])
def list_discovery_plugins(db: Session = Depends(get_db)):
    return DiscoveryAutomationService(db).list_plugins()


@router.get("/discovery/providers", response_model=list[DiscoveryProviderSettingsRead])
def list_discovery_providers(db: Session = Depends(get_db)):
    return DiscoveryAutomationService(db).list_provider_settings()


@router.get("/discovery/settings", response_model=DiscoverySettingsRead)
def get_discovery_settings(db: Session = Depends(get_db)):
    return DiscoveryAutomationService(db).get_settings()


@router.patch("/discovery/settings", response_model=DiscoverySettingsRead)
def update_discovery_settings(payload: DiscoverySettingsUpdate, db: Session = Depends(get_db)):
    return DiscoveryAutomationService(db).update_settings(payload)


@router.patch("/discovery/providers/{provider_key}", response_model=DiscoveryProviderSettingsRead)
def update_discovery_provider(
    provider_key: str,
    payload: DiscoveryProviderSettingsUpdate,
    db: Session = Depends(get_db),
):
    try:
        return DiscoveryAutomationService(db).update_provider_settings(provider_key, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Discovery provider not found") from exc


@router.post("/discovery/providers/{provider_key}/health-check", response_model=DiscoveryProviderSettingsRead)
def discovery_provider_health_check(provider_key: str, db: Session = Depends(get_db)):
    try:
        return DiscoveryAutomationService(db).health_check(provider_key)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Discovery provider not found") from exc


@router.get("/source-research", response_model=list[SourceResearchItemRead])
def list_source_research(db: Session = Depends(get_db)):
    return SourceResearchService(db).list()


@router.get("/source-research/archive", response_model=list[SourceResearchItemRead], include_in_schema=False)
def list_source_research_archive(db: Session = Depends(get_db)):
    return SourceResearchService(db).archive()


@router.post("/source-research", response_model=SourceResearchItemRead, status_code=201)
def create_source_research(payload: SourceResearchItemCreate, db: Session = Depends(get_db)):
    try:
        return SourceResearchService(db).create(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/source-research/find-new", response_model=list[SourceResearchItemRead])
def find_new_source_research(mode: str | None = None, db: Session = Depends(get_db)):
    return SourceResearchService(db).find_new_sources(mode)


@router.patch("/source-research/{item_id}", response_model=SourceResearchItemRead)
def update_source_research(
    item_id: UUID, payload: SourceResearchItemUpdate, db: Session = Depends(get_db)
):
    try:
        return SourceResearchService(db).update(item_id, payload)
    except ValueError as exc:
        message = str(exc)
        status_code = 400 if "needs" in message.lower() else 404
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.post("/source-research/{item_id}/reject", response_model=SourceResearchItemRead)
def reject_source_research(
    item_id: UUID, payload: SourceResearchReject | None = None, db: Session = Depends(get_db)
):
    try:
        reason = payload.rejection_reason if payload else None
        return SourceResearchService(db).reject(item_id, reason)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Source research item not found") from exc


@router.post("/source-research/{item_id}/restore", response_model=SourceResearchItemRead, include_in_schema=False)
def restore_source_research(item_id: UUID, db: Session = Depends(get_db)):
    try:
        return SourceResearchService(db).restore(item_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Source research item not found") from exc


@router.post("/source-research/{item_id}/add-to-discovery", response_model=SourceResearchItemRead)
def add_source_to_discovery(item_id: UUID, db: Session = Depends(get_db)):
    try:
        return SourceResearchService(db).add_to_discovery(item_id)
    except ValueError as exc:
        message = str(exc)
        status_code = 400 if "needs" in message.lower() else 404
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.delete("/source-research/{item_id}", status_code=204)
def delete_source_research(item_id: UUID, db: Session = Depends(get_db)):
    try:
        SourceResearchService(db).delete(item_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Source research item not found") from exc
    return None


@router.post("/discovery/run")
def run_discovery(
    mode: str = "All",
    search_modes: list[str] = Query(default=["Match My Profile", "Match My Archetypes"]),
    specific_archetype: str | None = None,
    db: Session = Depends(get_db),
):
    return DiscoveryAutomationService(db).run_all(
        discovery_mode=mode,
        search_modes=search_modes,
        specific_archetype=specific_archetype,
    )


@router.post("/discovery/run/{implementation_key}")
def run_discovery_source(
    implementation_key: str,
    mode: str = "All",
    search_modes: list[str] = Query(default=["Match My Profile", "Match My Archetypes"]),
    specific_archetype: str | None = None,
    db: Session = Depends(get_db),
):
    return DiscoveryAutomationService(db).run_source(
        implementation_key,
        discovery_mode=mode,
        search_modes=search_modes,
        specific_archetype=specific_archetype,
    )


@router.post("/travel/recalculate")
def recalculate_travel_exceptions(db: Session = Depends(get_db)):
    actor = db.scalars(select(ActorProfile).limit(1)).first()
    service = OpportunityIntelligenceService(db)
    rows = list(
        db.scalars(
            select(Opportunity)
            .where(Opportunity.is_demo_data.is_(False))
            .where(Opportunity.visibility_status.in_(["hidden", "travel_exception", "visible"]))
        )
    )
    counts = {
        "processed": 0,
        "visible": 0,
        "travel_exception": 0,
        "needs_audition_location": 0,
        "discarded": 0,
    }
    for opportunity in rows:
        before = opportunity.visibility_status
        service.apply_audition_visibility(opportunity)
        service.apply_hard_eligibility(opportunity, actor)
        if before != opportunity.visibility_status or opportunity.audition_type in {"Self-Tape", "Virtual", "In-Person"}:
            counts["processed"] += 1
        if opportunity.visibility_status == "visible":
            counts["visible"] += 1
        elif opportunity.visibility_status == "travel_exception":
            counts["travel_exception"] += 1
        elif opportunity.hidden_by_rule == "audition_location_needs_info":
            counts["needs_audition_location"] += 1
        elif opportunity.visibility_status == "discarded":
            counts["discarded"] += 1
    db.commit()
    return counts


@router.get("/opportunities/hidden", response_model=list[OpportunityRead])
def list_hidden_opportunities(developer_debug: bool = False, db: Session = Depends(get_db)):
    hidden_query = (
        select(Opportunity)
        .where(Opportunity.is_demo_data.is_(False))
        .where(Opportunity.visibility_status.in_(["hidden", "travel_exception"]))
        .where(
            (Opportunity.original_post_url.is_(None))
            | (~Opportunity.original_post_url.ilike("%example.com%"))
        )
        .where(
            not_(
                and_(
                    Opportunity.visibility_status == "travel_exception",
                    or_(
                        Opportunity.original_post_url.is_(None),
                        Opportunity.original_post_url == "",
                        Opportunity.original_post_url.ilike("%example.com%"),
                    ),
                )
            )
        )
    )
    if not developer_debug:
        hidden_query = hidden_query.where(
            or_(
                Opportunity.hidden_by_rule.is_(None),
                Opportunity.hidden_by_rule.notin_(
                    [
                        "dealbreaker_role_type",
                        "dealbreaker_demographic_mismatch",
                        "dealbreaker_eligibility",
                        "user_rejected",
                    ]
                ),
            )
        )
    return list(
        db.scalars(
            hidden_query.order_by(Opportunity.created_at.desc())
        )
    )


@router.get("/submission-queue", response_model=list[SubmissionAutomationQueueRead])
def list_submission_queue(db: Session = Depends(get_db)):
    return SubmissionAutomationService(db).list()


@router.post(
    "/submission-queue/from-recommendation/{recommendation_id}",
    response_model=SubmissionAutomationQueueRead,
)
def queue_from_recommendation(recommendation_id: UUID, db: Session = Depends(get_db)):
    return SubmissionAutomationService(db).queue_from_recommendation(recommendation_id)


@router.post("/submission-queue/{queue_id}/approve", response_model=SubmissionAutomationQueueRead)
def approve_queue_item(queue_id: UUID, db: Session = Depends(get_db)):
    return SubmissionAutomationService(db).approve(queue_id)


@router.post("/submission-queue/{queue_id}/reject", response_model=SubmissionAutomationQueueRead)
def reject_queue_item(queue_id: UUID, db: Session = Depends(get_db)):
    return SubmissionAutomationService(db).reject(queue_id)


@router.post("/submission-queue/{queue_id}/execute", response_model=SubmissionAutomationQueueRead)
def execute_queue_item(queue_id: UUID, db: Session = Depends(get_db)):
    return SubmissionAutomationService(db).execute(queue_id)
