from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import NotFoundError
from app.db.models import ActorProfile
from app.schemas.intelligence import (
    ActorRelationshipCreate,
    ActorRelationshipRead,
    ActorRelationshipUpdate,
    ArchetypePerformanceDashboardRead,
    AuditionReadinessRead,
    AuditionJournalEntryCreate,
    AuditionJournalEntryRead,
    AuditionJournalEntryUpdate,
    AuditionPreparationBriefRead,
    CallbackEventCreate,
    CallbackEventRead,
    CallbackEventUpdate,
    CareerPathSimulationCreate,
    CareerPathSimulationRead,
    CastingContactCreate,
    CastingContactRead,
    CastingOfficeAnalyticsRead,
    CastingOfficeCreate,
    CastingOfficeRead,
    CommunicationLogCreate,
    CommunicationLogRead,
    CommunicationLogUpdate,
    DreamRoleReadinessRead,
    DreamRoleTargetCreate,
    DreamRoleTargetRead,
    DreamRoleTargetUpdate,
    IndustryTrendDashboardRead,
    IntelligenceDashboardRead,
    MaterialCreationPlanCreate,
    MaterialCreationPlanRead,
    MaterialCreationPlanUpdate,
    QuarterlyCareerReviewCreate,
    QuarterlyCareerReviewRead,
    RelationshipAnalyticsRead,
    RoleSimilarityRead,
    SceneCandidateFindRequest,
    SceneCandidateRead,
    SceneCandidateUpdate,
    SelfTapeAnalyticsRead,
    SelfTapeCreate,
    SelfTapeRead,
    SelfTapeUpdate,
    ScriptSourceCreate,
    ScriptSourceRead,
    ScriptSourceUpdate,
)
from app.services.intelligence_service import IntelligenceService
from app.services.executive_intelligence_service import ExecutiveIntelligenceService

router = APIRouter()


def get_actor(db: Session) -> ActorProfile:
    actor = db.scalars(select(ActorProfile).limit(1)).first()
    if not actor:
        raise NotFoundError("Create an actor profile before running intelligence features")
    return actor


def empty_dashboard() -> dict:
    performance = {
        "metrics": [],
        "best_performing_archetypes": [],
        "underused_archetypes": [],
        "overused_archetypes": [],
        "high_potential_stretch_archetypes": [],
    }
    return {
        "archetype_performance": performance,
        "casting_office_analytics": [],
        "role_similarity": [],
    }


@router.get("/dashboard", response_model=IntelligenceDashboardRead)
def get_intelligence_dashboard(db: Session = Depends(get_db)):
    actor = db.scalars(select(ActorProfile).limit(1)).first()
    if not actor:
        return empty_dashboard()
    return IntelligenceService(db).dashboard(actor)


@router.get("/materials/performance")
def get_material_performance(db: Session = Depends(get_db)):
    return ExecutiveIntelligenceService(db).material_performance()


@router.get("/archetypes/performance", response_model=ArchetypePerformanceDashboardRead)
def get_archetype_performance(db: Session = Depends(get_db)):
    actor = db.scalars(select(ActorProfile).limit(1)).first()
    if not actor:
        return empty_dashboard()["archetype_performance"]
    return IntelligenceService(db).archetype_performance(actor)


@router.get("/readiness/opportunities", response_model=list[AuditionReadinessRead])
def list_audition_readiness(db: Session = Depends(get_db)):
    actor = db.scalars(select(ActorProfile).limit(1)).first()
    if not actor:
        return []
    return IntelligenceService(db).audition_readiness_for_all(actor)


@router.get("/readiness/opportunities/{opportunity_id}", response_model=AuditionReadinessRead)
def get_audition_readiness(opportunity_id: UUID, db: Session = Depends(get_db)):
    return IntelligenceService(db).audition_readiness(get_actor(db), opportunity_id)


def _empty_casting_patterns() -> dict:
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


@router.get("/casting-patterns", response_model=IndustryTrendDashboardRead)
def get_casting_patterns(db: Session = Depends(get_db)):
    actor = db.scalars(select(ActorProfile).limit(1)).first()
    if not actor:
        return _empty_casting_patterns()
    return IntelligenceService(db).industry_trends(actor)


@router.get("/trends", response_model=IndustryTrendDashboardRead, include_in_schema=False)
def get_industry_trends(db: Session = Depends(get_db)):
    return get_casting_patterns(db)


@router.get("/casting-offices", response_model=list[CastingOfficeRead])
def list_casting_offices(db: Session = Depends(get_db)):
    return IntelligenceService(db).list_casting_offices()


@router.post("/casting-offices", response_model=CastingOfficeRead, status_code=201)
def create_casting_office(payload: CastingOfficeCreate, db: Session = Depends(get_db)):
    return IntelligenceService(db).create_casting_office(payload)


@router.post("/casting-contacts", response_model=CastingContactRead, status_code=201)
def create_casting_contact(payload: CastingContactCreate, db: Session = Depends(get_db)):
    return IntelligenceService(db).create_casting_contact(payload)


@router.get("/relationships", response_model=list[ActorRelationshipRead])
def list_relationships(db: Session = Depends(get_db)):
    return IntelligenceService(db).list_relationships()


@router.post("/relationships", response_model=ActorRelationshipRead, status_code=201)
def create_relationship(payload: ActorRelationshipCreate, db: Session = Depends(get_db)):
    return IntelligenceService(db).create_relationship(payload)


@router.patch("/relationships/{relationship_id}", response_model=ActorRelationshipRead)
def update_relationship(
    relationship_id: UUID,
    payload: ActorRelationshipUpdate,
    db: Session = Depends(get_db),
):
    return IntelligenceService(db).update_relationship(relationship_id, payload)


@router.delete("/relationships/{relationship_id}", status_code=204)
def delete_relationship(relationship_id: UUID, db: Session = Depends(get_db)):
    IntelligenceService(db).delete_relationship(relationship_id)
    return None


@router.get("/relationships/analytics", response_model=RelationshipAnalyticsRead)
def get_relationship_analytics(db: Session = Depends(get_db)):
    return IntelligenceService(db).relationship_analytics()


@router.get("/casting-offices/analytics", response_model=list[CastingOfficeAnalyticsRead])
def get_casting_office_analytics(db: Session = Depends(get_db)):
    actor = db.scalars(select(ActorProfile).limit(1)).first()
    if not actor:
        return []
    return IntelligenceService(db).casting_office_analytics(actor)


@router.get("/self-tapes", response_model=list[SelfTapeRead])
def list_self_tapes(db: Session = Depends(get_db)):
    return IntelligenceService(db).list_self_tapes()


@router.post("/self-tapes", response_model=SelfTapeRead, status_code=201)
def create_self_tape(payload: SelfTapeCreate, db: Session = Depends(get_db)):
    return IntelligenceService(db).create_self_tape(payload)


@router.patch("/self-tapes/{tape_id}", response_model=SelfTapeRead)
def update_self_tape(tape_id: UUID, payload: SelfTapeUpdate, db: Session = Depends(get_db)):
    return IntelligenceService(db).update_self_tape(tape_id, payload)


@router.delete("/self-tapes/{tape_id}", status_code=204)
def delete_self_tape(tape_id: UUID, db: Session = Depends(get_db)):
    IntelligenceService(db).delete_self_tape(tape_id)
    return None


@router.get("/self-tapes/analytics", response_model=SelfTapeAnalyticsRead)
def get_self_tape_analytics(db: Session = Depends(get_db)):
    return IntelligenceService(db).self_tape_analytics()


@router.get("/audition-journal", response_model=list[AuditionJournalEntryRead])
def list_audition_journal(db: Session = Depends(get_db)):
    return IntelligenceService(db).list_journal_entries()


@router.post("/audition-journal", response_model=AuditionJournalEntryRead, status_code=201)
def create_audition_journal_entry(payload: AuditionJournalEntryCreate, db: Session = Depends(get_db)):
    return IntelligenceService(db).create_journal_entry(payload)


@router.patch("/audition-journal/{entry_id}", response_model=AuditionJournalEntryRead)
def update_audition_journal_entry(
    entry_id: UUID,
    payload: AuditionJournalEntryUpdate,
    db: Session = Depends(get_db),
):
    return IntelligenceService(db).update_journal_entry(entry_id, payload)


@router.delete("/audition-journal/{entry_id}", status_code=204)
def delete_audition_journal_entry(entry_id: UUID, db: Session = Depends(get_db)):
    IntelligenceService(db).delete_journal_entry(entry_id)
    return None


@router.get("/callback-events", response_model=list[CallbackEventRead])
def list_callback_events(db: Session = Depends(get_db)):
    return IntelligenceService(db).list_callback_events()


@router.post("/callback-events", response_model=CallbackEventRead, status_code=201)
def create_callback_event(payload: CallbackEventCreate, db: Session = Depends(get_db)):
    return IntelligenceService(db).create_callback_event(payload)


@router.patch("/callback-events/{event_id}", response_model=CallbackEventRead)
def update_callback_event(event_id: UUID, payload: CallbackEventUpdate, db: Session = Depends(get_db)):
    return IntelligenceService(db).update_callback_event(event_id, payload)


@router.delete("/callback-events/{event_id}", status_code=204)
def delete_callback_event(event_id: UUID, db: Session = Depends(get_db)):
    IntelligenceService(db).delete_callback_event(event_id)
    return None


@router.get("/communication-logs", response_model=list[CommunicationLogRead])
def list_communication_logs(db: Session = Depends(get_db)):
    return IntelligenceService(db).list_communication_logs()


@router.post("/communication-logs", response_model=CommunicationLogRead, status_code=201)
def create_communication_log(payload: CommunicationLogCreate, db: Session = Depends(get_db)):
    return IntelligenceService(db).create_communication_log(payload)


@router.patch("/communication-logs/{log_id}", response_model=CommunicationLogRead)
def update_communication_log(log_id: UUID, payload: CommunicationLogUpdate, db: Session = Depends(get_db)):
    return IntelligenceService(db).update_communication_log(log_id, payload)


@router.delete("/communication-logs/{log_id}", status_code=204)
def delete_communication_log(log_id: UUID, db: Session = Depends(get_db)):
    IntelligenceService(db).delete_communication_log(log_id)
    return None


@router.get("/roles/similar", response_model=list[RoleSimilarityRead])
def get_role_similarity(db: Session = Depends(get_db)):
    actor = db.scalars(select(ActorProfile).limit(1)).first()
    if not actor:
        return []
    return IntelligenceService(db).role_similarity(actor)


@router.post("/opportunities/{opportunity_id}/prepare", response_model=AuditionPreparationBriefRead)
def prepare_audition(
    opportunity_id: UUID, submission_id: UUID | None = None, db: Session = Depends(get_db)
):
    return IntelligenceService(db).prepare_audition(opportunity_id, submission_id)


@router.post("/materials/plan", response_model=MaterialCreationPlanRead, status_code=201)
def create_material_plan(payload: MaterialCreationPlanCreate, db: Session = Depends(get_db)):
    return IntelligenceService(db).create_material_plan(payload)


@router.patch("/materials/plans/{plan_id}", response_model=MaterialCreationPlanRead)
def update_material_plan(plan_id: UUID, payload: MaterialCreationPlanUpdate, db: Session = Depends(get_db)):
    try:
        return IntelligenceService(db).update_material_plan(plan_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/scripts/sources", response_model=list[ScriptSourceRead])
def list_script_sources(db: Session = Depends(get_db)):
    return IntelligenceService(db).list_script_sources()


@router.post("/scripts/sources", response_model=ScriptSourceRead, status_code=201)
def create_script_source(payload: ScriptSourceCreate, db: Session = Depends(get_db)):
    try:
        return IntelligenceService(db).create_script_source(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/scripts/sources/{source_id}", response_model=ScriptSourceRead)
def update_script_source(source_id: UUID, payload: ScriptSourceUpdate, db: Session = Depends(get_db)):
    try:
        return IntelligenceService(db).update_script_source(source_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/scripts/find-scenes", response_model=list[SceneCandidateRead], status_code=201)
def find_scene_candidates(payload: SceneCandidateFindRequest, db: Session = Depends(get_db)):
    return IntelligenceService(db).find_scene_candidates(payload)


@router.patch("/scripts/scene-candidates/{candidate_id}", response_model=SceneCandidateRead)
def update_scene_candidate(candidate_id: UUID, payload: SceneCandidateUpdate, db: Session = Depends(get_db)):
    try:
        return IntelligenceService(db).update_scene_candidate(candidate_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/career/simulate", response_model=CareerPathSimulationRead, status_code=201)
def simulate_career_path(payload: CareerPathSimulationCreate, db: Session = Depends(get_db)):
    return IntelligenceService(db).simulate_career_path(get_actor(db), payload)


@router.get("/career/quarterly-reviews", response_model=list[QuarterlyCareerReviewRead])
def list_quarterly_reviews(db: Session = Depends(get_db)):
    actor = db.scalars(select(ActorProfile).limit(1)).first()
    if not actor:
        return []
    return IntelligenceService(db).list_quarterly_reviews(actor)


@router.post("/career/quarterly-reviews", response_model=QuarterlyCareerReviewRead, status_code=201)
def generate_quarterly_review(payload: QuarterlyCareerReviewCreate, db: Session = Depends(get_db)):
    return IntelligenceService(db).generate_quarterly_review(get_actor(db), payload)


@router.get("/dream-targets", response_model=list[DreamRoleTargetRead])
def list_dream_targets(db: Session = Depends(get_db)):
    actor = db.scalars(select(ActorProfile).limit(1)).first()
    if not actor:
        return []
    return IntelligenceService(db).list_dream_targets(actor)


@router.post("/dream-targets", response_model=DreamRoleTargetRead, status_code=201)
def create_dream_target(payload: DreamRoleTargetCreate, db: Session = Depends(get_db)):
    return IntelligenceService(db).create_dream_target(get_actor(db), payload)


@router.get("/dream-targets/readiness", response_model=list[DreamRoleReadinessRead])
def get_dream_target_readiness(db: Session = Depends(get_db)):
    actor = db.scalars(select(ActorProfile).limit(1)).first()
    if not actor:
        return []
    return IntelligenceService(db).dream_target_readiness(actor)


@router.patch("/dream-targets/{target_id}", response_model=DreamRoleTargetRead)
def update_dream_target(target_id: UUID, payload: DreamRoleTargetUpdate, db: Session = Depends(get_db)):
    return IntelligenceService(db).update_dream_target(target_id, payload)


@router.delete("/dream-targets/{target_id}", status_code=204)
def delete_dream_target(target_id: UUID, db: Session = Depends(get_db)):
    IntelligenceService(db).delete_dream_target(target_id)
    return None
