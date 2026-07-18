from fastapi import APIRouter

from app.api.v1.routes import (
    actor_profiles,
    agents,
    assets,
    automation,
    career_development,
    command_center,
    dashboard,
    intelligence,
    journal,
    operations,
    opportunities,
    platform_imports,
    representation,
    submissions,
    supervised_breakdowns,
    system,
    travel_preferences,
)

api_router = APIRouter()
api_router.include_router(actor_profiles.router, prefix="/actor-profile", tags=["Actor Profile"])
api_router.include_router(agents.router, prefix="/agents", tags=["Agents"])
api_router.include_router(automation.router, prefix="/automation", tags=["Automation"])
api_router.include_router(
    career_development.router, prefix="/career-development", tags=["Career Development"]
)
api_router.include_router(command_center.router, prefix="/command-center", tags=["Command Center"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(intelligence.router, prefix="/intelligence", tags=["AI Intelligence"])
api_router.include_router(journal.router, prefix="/journal", tags=["Journal"])
api_router.include_router(operations.router, prefix="/operations", tags=["Actor Operations"])
api_router.include_router(travel_preferences.router, prefix="/travel-preferences", tags=["Travel"])
api_router.include_router(assets.router, prefix="/assets", tags=["Assets"])
api_router.include_router(opportunities.router, prefix="/opportunities", tags=["Opportunities"])
api_router.include_router(
    platform_imports.router, prefix="/platform-imports", tags=["Platform Imports"]
)
api_router.include_router(representation.router, prefix="/representation", tags=["Representation"])
api_router.include_router(submissions.router, prefix="/submissions", tags=["Submissions"])
api_router.include_router(system.router, prefix="/system", tags=["System"])
api_router.include_router(
    supervised_breakdowns.router,
    prefix="/supervised-breakdown-imports",
    tags=["Supervised Breakdown Imports"],
)
