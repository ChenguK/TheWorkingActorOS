from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.asset_analysis_agent import AssetAnalysisAgent
from app.agents.career_agent import CareerAgent
from app.agents.discovery_agent import DiscoveryAgent
from app.agents.executive_agent import ExecutiveAgent
from app.agents.learning_agent import LearningAgent
from app.agents.strategy_agent import StrategyAgent
from app.core.database import get_db
from app.core.errors import NotFoundError
from app.db.models import ActorProfile, AgentRecommendation, Asset, CareerDevelopmentTask, CareerSwotAnalysis, CastingGoal, Opportunity, RecommendationFeedback
from app.schemas.agent import (
    AgentRecommendationRead,
    CareerMemoryRead,
    CareerMemoryUpdate,
    CareerRecommendationRead,
    CareerDevelopmentTaskRead,
    CareerSwotAnalysisRead,
    CastingGoalCreate,
    CastingGoalRead,
    CastingGoalUpdate,
    ExecutiveBriefRead,
    ExecutivePriorityRead,
    LearningInsightRead,
    RecommendationFeedbackCreate,
    RecommendationFeedbackRead,
    RecommendationExplanation,
    RecommendedMaterialSubmissionCreate,
    WatchListCreate,
    WatchListRead,
    WatchListUpdate,
)
from app.schemas.asset import AssetRead
from app.schemas.submission import SubmissionCreate, SubmissionRead
from app.services.submission_service import SubmissionService
from app.services.watch_list_service import WatchListService
from app.services.workflow_connector_service import WorkflowConnectorService
from app.services.executive_intelligence_service import ExecutiveIntelligenceService

router = APIRouter()


def get_actor(db: Session) -> ActorProfile:
    actor = db.scalars(select(ActorProfile).limit(1)).first()
    if not actor:
        raise NotFoundError("Create an actor profile before running agents")
    return actor


@router.post("/discovery/run")
def run_discovery(
    mode: str = "All",
    search_modes: list[str] = Query(default=["Match My Profile", "Match My Archetypes"]),
    specific_archetype: str | None = None,
    db: Session = Depends(get_db),
):
    return DiscoveryAgent(db).run(
        discovery_mode=mode,
        search_modes=search_modes,
        specific_archetype=specific_archetype,
    )


@router.post("/assets/{asset_id}/analyze", response_model=AssetRead)
def analyze_asset(asset_id: UUID, db: Session = Depends(get_db)):
    asset = db.get(Asset, asset_id)
    if not asset:
        raise NotFoundError("Asset not found")
    return AssetAnalysisAgent(db).analyze(asset)


@router.post("/opportunities/{opportunity_id}/recommend", response_model=AgentRecommendationRead)
def recommend_opportunity(opportunity_id: UUID, db: Session = Depends(get_db)):
    actor = get_actor(db)
    opportunity = db.get(Opportunity, opportunity_id)
    if not opportunity or opportunity.is_demo_data:
        raise NotFoundError("Opportunity not found")
    return StrategyAgent(db).analyze(opportunity, actor)


@router.get("/recommendations", response_model=list[AgentRecommendationRead])
def list_recommendations(db: Session = Depends(get_db)):
    return list(
        db.scalars(
            select(AgentRecommendation)
            .join(Opportunity, AgentRecommendation.opportunity_id == Opportunity.id)
            .where(Opportunity.is_demo_data.is_(False))
            .order_by(AgentRecommendation.created_at.desc())
        )
    )


@router.post("/recommendations/{recommendation_id}/feedback", response_model=RecommendationFeedbackRead, status_code=201)
def create_recommendation_feedback(
    recommendation_id: UUID,
    payload: RecommendationFeedbackCreate,
    db: Session = Depends(get_db),
):
    recommendation = db.get(AgentRecommendation, recommendation_id)
    if not recommendation or (recommendation.opportunity and recommendation.opportunity.is_demo_data):
        raise NotFoundError("Recommendation not found")
    feedback = RecommendationFeedback(
        actor_profile_id=recommendation.actor_profile_id,
        opportunity_id=recommendation.opportunity_id,
        recommendation_id=recommendation.id,
        feedback_type=payload.feedback_type,
        fit_reasons=payload.fit_reasons,
        notes=payload.notes,
    )
    db.add(feedback)
    db.flush()
    actor = db.get(ActorProfile, recommendation.actor_profile_id)
    if actor:
        LearningAgent(db).analyze(actor)
    db.refresh(feedback)
    return feedback


@router.get("/executive/priorities", response_model=list[ExecutivePriorityRead])
def executive_priorities(db: Session = Depends(get_db)):
    return ExecutiveAgent(db).top_priorities()


@router.get("/chief-of-staff/priorities", response_model=list[ExecutivePriorityRead])
def chief_of_staff_priorities(db: Session = Depends(get_db)):
    return ExecutiveAgent(db).top_priorities()


@router.get("/career-memory", response_model=CareerMemoryRead)
def get_career_memory(db: Session = Depends(get_db)):
    actor = db.scalars(select(ActorProfile).limit(1)).first()
    return ExecutiveIntelligenceService(db).get_or_create_memory(actor)


@router.put("/career-memory", response_model=CareerMemoryRead)
def update_career_memory(payload: CareerMemoryUpdate, db: Session = Depends(get_db)):
    actor = db.scalars(select(ActorProfile).limit(1)).first()
    return ExecutiveIntelligenceService(db).update_memory(actor, payload)


@router.get("/executive/briefs", response_model=list[ExecutiveBriefRead])
def list_executive_briefs(db: Session = Depends(get_db)):
    return ExecutiveIntelligenceService(db).list_briefs()


@router.get("/chief-of-staff/briefs", response_model=list[ExecutiveBriefRead])
def list_chief_of_staff_briefs(db: Session = Depends(get_db)):
    return ExecutiveIntelligenceService(db).list_briefs()


@router.post("/executive/briefs/weekly", response_model=ExecutiveBriefRead, status_code=201)
def generate_weekly_brief(db: Session = Depends(get_db)):
    actor = db.scalars(select(ActorProfile).limit(1)).first()
    return ExecutiveIntelligenceService(db).generate_weekly_brief(actor)


@router.post("/chief-of-staff/briefs/weekly", response_model=ExecutiveBriefRead, status_code=201)
def generate_chief_of_staff_weekly_brief(db: Session = Depends(get_db)):
    actor = db.scalars(select(ActorProfile).limit(1)).first()
    return ExecutiveIntelligenceService(db).generate_weekly_brief(actor)


@router.get("/recommendations/{recommendation_id}/explanation", response_model=RecommendationExplanation)
def explain_recommendation(recommendation_id: UUID, db: Session = Depends(get_db)):
    recommendation = db.get(AgentRecommendation, recommendation_id)
    if not recommendation:
        raise NotFoundError("Recommendation not found")
    return RecommendationExplanation(
        score=recommendation.score,
        match_type=recommendation.match_type,
        score_breakdown=recommendation.score_breakdown,
        audition_type=recommendation.audition_type,
        audition_travel_hours=recommendation.audition_travel_hours,
        audition_decision=recommendation.audition_decision,
        audition_explanation=recommendation.audition_explanation,
        travel_explanation=recommendation.travel_explanation,
        archetype_explanation=recommendation.archetype_explanation,
        asset_explanation=recommendation.asset_explanation,
        submission_strategy_explanation=recommendation.submission_strategy_explanation,
        confidence_level=recommendation.confidence_level,
        risk_level=recommendation.risk_level,
        risk_explanation=recommendation.risk_explanation,
        explanation=recommendation.explanation,
    )


@router.post("/recommendations/{recommendation_id}/create-submission", response_model=SubmissionRead, status_code=201)
def create_submission_from_recommendation(
    recommendation_id: UUID,
    payload: RecommendedMaterialSubmissionCreate,
    db: Session = Depends(get_db),
):
    recommendation = db.get(AgentRecommendation, recommendation_id)
    if not recommendation:
        raise NotFoundError("Recommendation not found")
    recommended_asset_ids = [
        asset_id
        for asset_id in [
            recommendation.recommended_headshot_id,
            recommendation.recommended_reel_id,
            recommendation.recommended_resume_id,
            recommendation.recommended_slate_id,
        ]
        if asset_id
    ]
    final_asset_ids = payload.asset_ids if payload.asset_ids is not None else recommended_asset_ids
    notes = payload.notes or recommendation.recommended_note
    return SubmissionService(db).create(
        SubmissionCreate(
            actor_profile_id=recommendation.actor_profile_id,
            opportunity_id=recommendation.opportunity_id,
            asset_ids=final_asset_ids,
            current_status=payload.current_status,
            notes=notes,
        )
    )


@router.post("/learning/run", response_model=LearningInsightRead)
def run_learning(db: Session = Depends(get_db)):
    return LearningAgent(db).analyze(get_actor(db))


@router.post("/career/run", response_model=CareerRecommendationRead)
def run_career(db: Session = Depends(get_db)):
    return CareerAgent(db).analyze(get_actor(db))


@router.get("/career/swot", response_model=CareerSwotAnalysisRead | None)
def get_latest_career_swot(db: Session = Depends(get_db)):
    actor = db.scalars(select(ActorProfile).limit(1)).first()
    if not actor:
        return None
    return db.scalars(
        select(CareerSwotAnalysis)
        .where(CareerSwotAnalysis.actor_profile_id == actor.id)
        .order_by(CareerSwotAnalysis.created_at.desc())
        .limit(1)
    ).first()


@router.post("/career/swot", response_model=CareerSwotAnalysisRead)
def generate_career_swot(db: Session = Depends(get_db)):
    swot = CareerAgent(db).generate_swot(get_actor(db))
    db.add(swot)
    db.commit()
    db.refresh(swot)
    return swot


@router.get("/career/tasks", response_model=list[CareerDevelopmentTaskRead])
def list_career_tasks(db: Session = Depends(get_db)):
    return list(db.scalars(select(CareerDevelopmentTask).order_by(CareerDevelopmentTask.created_at.desc())))


@router.get("/casting-goals", response_model=list[CastingGoalRead])
def list_casting_goals(db: Session = Depends(get_db)):
    return list(
        db.scalars(
            select(CastingGoal).order_by(CastingGoal.status.asc(), CastingGoal.priority.desc(), CastingGoal.updated_at.desc())
        )
    )


@router.post("/casting-goals", response_model=CastingGoalRead, status_code=201)
def create_casting_goal(payload: CastingGoalCreate, db: Session = Depends(get_db)):
    actor = db.scalars(select(ActorProfile).limit(1)).first()
    data = payload.model_dump()
    if actor and not data.get("actor_profile_id"):
        data["actor_profile_id"] = actor.id
    goal = CastingGoal(**data)
    db.add(goal)
    db.flush()
    WorkflowConnectorService(db).after_casting_goal_saved(goal)
    WatchListService(db).refresh_all()
    db.commit()
    db.refresh(goal)
    return goal


@router.patch("/casting-goals/{goal_id}", response_model=CastingGoalRead)
def update_casting_goal(goal_id: UUID, payload: CastingGoalUpdate, db: Session = Depends(get_db)):
    goal = db.get(CastingGoal, goal_id)
    if not goal:
        raise NotFoundError("Casting goal not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(goal, key, value)
    WorkflowConnectorService(db).after_casting_goal_saved(goal)
    WatchListService(db).refresh_all()
    db.commit()
    db.refresh(goal)
    return goal


@router.delete("/casting-goals/{goal_id}", status_code=204)
def delete_casting_goal(goal_id: UUID, db: Session = Depends(get_db)):
    goal = db.get(CastingGoal, goal_id)
    if not goal:
        raise NotFoundError("Casting goal not found")
    db.delete(goal)
    db.commit()
    return None


@router.get("/watch-lists", response_model=list[WatchListRead])
def list_watch_lists(db: Session = Depends(get_db)):
    return WatchListService(db).list()


@router.post("/watch-lists", response_model=WatchListRead, status_code=201)
def create_watch_list(payload: WatchListCreate, db: Session = Depends(get_db)):
    return WatchListService(db).create(payload)


@router.patch("/watch-lists/{watch_list_id}", response_model=WatchListRead)
def update_watch_list(watch_list_id: UUID, payload: WatchListUpdate, db: Session = Depends(get_db)):
    try:
        return WatchListService(db).update(watch_list_id, payload)
    except ValueError as exc:
        raise NotFoundError("Watch List not found") from exc


@router.delete("/watch-lists/{watch_list_id}", status_code=204)
def delete_watch_list(watch_list_id: UUID, db: Session = Depends(get_db)):
    try:
        WatchListService(db).delete(watch_list_id)
    except ValueError as exc:
        raise NotFoundError("Watch List not found") from exc
    return None
