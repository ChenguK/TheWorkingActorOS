from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    ActorProfile,
    DiscoveryProviderSettings,
    Opportunity,
    SourceResearchItem,
    Submission,
)
from app.core.config import get_settings
from app.repositories.opportunity import MAIN_BREAKDOWN_CLASSIFICATIONS
from app.services.travel_service import TravelService


class CapabilityService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def snapshot(self) -> dict:
        return self.feature_states()

    def system_capabilities(self) -> dict:
        states = self.feature_states()
        flags = self.flags()
        return {
            "flags": flags,
            "states": states,
            "integrations": self.integration_statuses(flags),
            "labels": {
                "not_configured": "Not Configured",
                "needs_info": "Needs Info",
                "manual_override": "Manual Override",
                "user_entered_estimate": "User-entered estimate",
                "add_data_first": "Add Data First",
                "insufficient_data": "Insufficient Data",
                "dashboard_alerts_only": "Dashboard Alerts Only",
                "manual_check_in": "Manual Check-In",
                "suggested_tags": "Suggested Tags",
                "deterministic_recommendation": "Deterministic Recommendation",
            },
        }

    def integration_statuses(self, flags: dict[str, bool] | None = None) -> list[dict]:
        settings = get_settings()
        flags = flags or self.flags()
        supervised_browser_status = self._supervised_browser_status(settings)
        travel = TravelService(self.db).provider_status()
        openrouteservice_configured = bool(settings.openrouteservice_api_key)
        openrouteservice_active = str(settings.travel_provider or "manual").lower() in {
            "openrouteservice",
            "ors",
            "auto",
        }
        return [
            {
                "id": "travel_provider",
                "name": "Travel Provider",
                "status": "Configured" if flags["travel_provider_configured"] else "Not Configured",
                "configured": flags["travel_provider_configured"],
                "what_it_enables": "Drive-time calculation for audition and production travel.",
                "fallback_behavior": "Manual drive-time estimate.",
                "setup_instructions": (
                    "Set TRAVEL_PROVIDER to openrouteservice, mapbox, google, or auto in the backend .env, "
                    "then add the matching provider API key there. API keys are read only by the backend."
                ),
                "provider": travel["provider"],
            },
            {
                "id": "openrouteservice",
                "name": "OpenRouteService API",
                "status": "Configured"
                if openrouteservice_configured and openrouteservice_active
                else "Not Configured",
                "configured": openrouteservice_configured and openrouteservice_active,
                "what_it_enables": "Geocoding and drive-time estimates through OpenRouteService.",
                "fallback_behavior": "Manual drive-time estimate.",
                "setup_instructions": (
                    "Set TRAVEL_PROVIDER=openrouteservice and OPENROUTESERVICE_API_KEY in the backend .env, "
                    "then restart FastAPI. The key is never sent to the frontend."
                ),
            },
            {
                "id": "openai",
                "name": "OpenAI API",
                "status": "Configured" if flags["ai_configured"] else "Not Configured",
                "configured": flags["ai_configured"],
                "what_it_enables": "AI-assisted tagging, LLM parsing, character interpretation, and richer recommendation explanations.",
                "fallback_behavior": "Deterministic suggestions.",
                "setup_instructions": (
                    "Set OPENAI_API_KEY in the backend .env and restart FastAPI. The browser receives only configured/not configured status."
                ),
            },
            {
                "id": "scheduler",
                "name": "Scheduler",
                "status": "Configured" if flags["scheduler_configured"] else "Not Configured",
                "configured": flags["scheduler_configured"],
                "what_it_enables": "Recurring jobs such as scheduled discovery checks, weekly briefs, and background maintenance.",
                "fallback_behavior": "Dashboard alerts only and user-triggered refreshes.",
                "setup_instructions": "Set SCHEDULER_ENABLED=true in the backend .env after a scheduler worker is configured.",
            },
            {
                "id": "notifications",
                "name": "Notifications",
                "status": "Configured" if flags["notifications_configured"] else "Not Configured",
                "configured": flags["notifications_configured"],
                "what_it_enables": "Push, email, or SMS reminders for deadlines, check-ins, and calendar events.",
                "fallback_behavior": "Dashboard Alerts Only.",
                "setup_instructions": (
                    "Configure a scheduler and notification provider, then set NOTIFICATIONS_ENABLED=true in the backend .env."
                ),
            },
            {
                "id": "public_profile_import",
                "name": "Public Profile Import",
                "status": "Configured"
                if flags["public_profile_import_configured"]
                else "Not Configured",
                "configured": flags["public_profile_import_configured"],
                "what_it_enables": "User-triggered draft imports from public/shareable links, pasted text, PDFs, screenshots, CSV, or guided forms.",
                "fallback_behavior": "Manual Entry Required.",
                "setup_instructions": "Keep PUBLIC_PROFILE_IMPORT_ENABLED=true in the backend .env. Imports remain draft-first and user approved.",
            },
            {
                "id": "supervised_browser",
                "name": "Supervised Browser Import",
                "status": supervised_browser_status,
                "configured": flags["supervised_browser_available"],
                "what_it_enables": "A user-controlled local browser for manually navigating to one breakdown before importing visible page text.",
                "fallback_behavior": "Manual breakdown entry or pasted breakdown text.",
                "setup_instructions": (
                    "Available only when ENVIRONMENT is local development and SUPERVISED_BROWSER_ENABLED=true. "
                    "It is disabled in the sanitized portfolio demo."
                ),
            },
            {
                "id": "source_discovery",
                "name": "Source Discovery",
                "status": "Configured"
                if flags["source_discovery_configured"]
                else "Not Configured",
                "configured": flags["source_discovery_configured"],
                "what_it_enables": "User-triggered discovery against approved active public breakdown sources and configured public web search.",
                "fallback_behavior": "Manual breakdown entry and source approval workflow.",
                "setup_instructions": (
                    "Approve and activate at least one Breakdown Source, or set WEB_SEARCH_PROVIDER=parallel "
                    "and PARALLEL_API_KEY in the backend .env. Protected casting platforms are not scraped."
                ),
            },
            {
                "id": "parallel_public_web_search",
                "name": "Parallel Public Web Search",
                "status": "Configured"
                if self._public_web_search_configured()
                else "Not Configured",
                "configured": self._public_web_search_configured(),
                "what_it_enables": "User-triggered public web search for active public Film/TV acting breakdowns.",
                "fallback_behavior": "Only approved active sources are searched.",
                "setup_instructions": "Install parallel-web, then set WEB_SEARCH_PROVIDER=parallel and PARALLEL_API_KEY in the backend .env.",
            },
        ]

    def flags(self) -> dict[str, bool]:
        settings = get_settings()
        travel = TravelService(self.db).provider_status()
        return {
            "travel_provider_configured": bool(
                travel["configured"] and travel["provider"] != "manual"
            ),
            "ai_configured": bool(settings.openai_api_key),
            "scheduler_configured": bool(settings.scheduler_enabled),
            "notifications_configured": bool(
                settings.notifications_enabled and settings.scheduler_enabled
            ),
            "source_discovery_configured": self._source_discovery_configured(),
            "public_profile_import_configured": bool(settings.public_profile_import_enabled),
            "supervised_browser_available": settings.supervised_browser_available,
            "portfolio_demo": settings.is_portfolio_demo,
        }

    def feature_states(self) -> dict:
        actor = self.db.scalars(select(ActorProfile).limit(1)).first()
        submissions = self._count(Submission)
        outcome_submissions = self._outcome_submission_count()
        travel = TravelService(self.db).provider_status()
        flags = self.flags()
        data_threshold = {
            "industry_trends": self._casting_patterns_threshold_met(),
            "casting_office_intelligence": self._casting_office_threshold_met(actor),
            "material_performance": self._material_threshold_met(actor),
            "archetype_performance": self._archetype_threshold_met(actor),
            "learning_agent": outcome_submissions >= 10,
            "career_agent": bool(actor) and outcome_submissions >= 10,
            "chief_of_staff": bool(actor),
        }
        return {
            "drive_time_calculation": self._state(
                travel["state"],
                "Uses OpenRouteService, Mapbox, or Google when configured; otherwise manual drive-time estimates only.",
                "Manual Override",
            ),
            "geocoding": self._state(
                "Configured"
                if travel["configured"] and travel["provider"] != "manual"
                else "Not Configured",
                "Geocoding requires a configured travel provider API key.",
                "Connect Service",
            ),
            "source_discovery": self._state(
                "Configured" if flags["source_discovery_configured"] else "Not Configured",
                "Public discovery is user-triggered. Approved active sources are checked first; Parallel public web search runs only when configured.",
                "Manual Entry Required",
            ),
            "industry_trend_analysis": self._state(
                "Configured" if data_threshold["industry_trends"] else "Insufficient Data",
                "Your Casting Patterns appears after at least 5 tracked breakdowns, auditions, or submissions. It reflects only your own tracked activity.",
                "Insufficient Data",
            ),
            "archetype_performance": self._state(
                "Configured" if data_threshold["archetype_performance"] else "Insufficient Data",
                "Archetype performance appears after at least 5 submissions are tagged with the same archetype.",
                "Add Data First",
            ),
            "casting_office_intelligence": self._state(
                "Configured" if data_threshold["casting_office_intelligence"] else "Add Data First",
                "Casting office intelligence appears after at least 3 submissions are linked to the same casting office.",
                "Add Data First",
            ),
            "already_submitted_detection": self._state(
                "Configured" if submissions else "Add Data First",
                "Already-submitted detection works only for submissions tracked in this app.",
                "Add Data First",
            ),
            "material_performance_analytics": self._state(
                "Configured" if data_threshold["material_performance"] else "Insufficient Data",
                "Material performance appears after at least 5 submissions use the same material.",
                "Insufficient Data",
            ),
            "calendar_reminders": self._state(
                "Dashboard Alerts Only",
                "Calendar events exist in-app, but no email/push/background notification service is configured.",
                "Dashboard Alerts Only",
            ),
            "notification_reminders": self._state(
                "Configured" if flags["notifications_configured"] else "Not Configured",
                "Push/email/SMS notifications require a scheduler and notification provider.",
                "Dashboard Alerts Only",
            ),
            "public_profile_imports": self._state(
                "Configured" if flags["public_profile_import_configured"] else "Not Configured",
                "Imports are user-triggered, draft-first, and fall back to copy/paste or uploads when pages block fetching.",
                "Manual Entry Required",
            ),
            "supervised_browser": self._state(
                self._supervised_browser_status(get_settings()),
                (
                    "A user-controlled supervised browser is available only in local development."
                    if flags["supervised_browser_available"]
                    else "Remote supervised-browser execution is disabled. Use manual entry or pasted breakdown text."
                ),
                "Manual Entry Required",
            ),
            "ai_assisted_tagging": self._state(
                "Configured" if flags["ai_configured"] else "Not Configured",
                "Material tagging uses AI only when an AI provider is configured; otherwise it uses deterministic filename/type suggestions.",
                "Suggested Tags",
            ),
            "learning_agent_insights": self._state(
                "Configured" if data_threshold["learning_agent"] else "Insufficient Data",
                "Learning insights appear after at least 10 tracked submissions have outcomes.",
                "Track more submissions to unlock this insight.",
            ),
            "chief_of_staff_summaries": self._state(
                "Configured" if data_threshold["chief_of_staff"] else "Add Data First",
                "Chief of Staff prioritization needs actor profile data and tracked work.",
                "Add Data First",
            ),
            "career_agent_recommendations": self._state(
                "Configured" if data_threshold["career_agent"] else "Early Recommendation",
                "Career recommendations can start early, but become stronger after at least 10 tracked submissions with outcomes.",
                "Track more submissions to unlock this insight.",
            ),
        }

    def _state(self, state: str, explanation: str, fallback: str) -> dict:
        return {"state": state, "explanation": explanation, "safe_fallback": fallback}

    def _supervised_browser_status(self, settings) -> str:
        if settings.supervised_browser_available:
            return "Available Locally"
        if settings.is_portfolio_demo:
            return "Unavailable in Portfolio Demo"
        if settings.is_local_environment:
            return "Disabled by Configuration"
        return "Unavailable"

    def _count(self, model, *criteria) -> int:
        statement = select(func.count()).select_from(model)
        for criterion in criteria:
            statement = statement.where(criterion)
        return int(self.db.scalar(statement) or 0)

    def _source_discovery_configured(self) -> bool:
        active_provider = self.db.scalar(
            select(func.count())
            .select_from(DiscoveryProviderSettings)
            .where(DiscoveryProviderSettings.enabled.is_(True))
        )
        active_approved_source = self.db.scalar(
            select(func.count())
            .select_from(SourceResearchItem)
            .where(SourceResearchItem.deleted.is_(False))
            .where(SourceResearchItem.status == "Active")
            .where(SourceResearchItem.approved_by_user.is_(True))
        )
        return bool(
            (active_provider or 0) > 0
            or (active_approved_source or 0) > 0
            or self._public_web_search_configured()
        )

    def _public_web_search_configured(self) -> bool:
        settings = get_settings()
        return bool(
            str(settings.web_search_provider or "").lower() == "parallel"
            and settings.parallel_api_key
        )

    def _outcome_submission_count(self) -> int:
        return self._count(
            Submission,
            Submission.current_status.in_(
                [
                    "Requested",
                    "Self-Tape Callback",
                    "In-Person Callback",
                    "Pinned",
                    "Booked",
                    "Passed",
                    "No Response",
                ]
            ),
        )

    def _casting_patterns_threshold_met(self) -> bool:
        breakdown_count = self._count(
            Opportunity,
            Opportunity.is_demo_data.is_(False),
            Opportunity.breakdown_classification.in_(MAIN_BREAKDOWN_CLASSIFICATIONS),
        )
        submission_count = self._count(Submission)
        return breakdown_count + submission_count >= 5

    def _material_threshold_met(self, actor: ActorProfile | None) -> bool:
        if not actor:
            return False
        counts: dict[str, int] = {}
        for submission in self._actor_submissions_with_assets(actor):
            for asset in submission.assets:
                counts[str(asset.id)] = counts.get(str(asset.id), 0) + 1
        return any(count >= 5 for count in counts.values())

    def _archetype_threshold_met(self, actor: ActorProfile | None) -> bool:
        if not actor:
            return False
        counts: dict[str, int] = {}
        for submission in self._actor_submissions_with_assets(actor):
            for asset in submission.assets:
                for archetype in asset.archetype_names:
                    counts[archetype] = counts.get(archetype, 0) + 1
        return any(count >= 5 for count in counts.values())

    def _casting_office_threshold_met(self, actor: ActorProfile | None) -> bool:
        if not actor:
            return False
        rows = self.db.execute(
            select(Opportunity.casting_office_id, func.count(Submission.id))
            .select_from(Submission)
            .join(Opportunity, Submission.opportunity_id == Opportunity.id)
            .where(Submission.actor_profile_id == actor.id)
            .where(Opportunity.is_demo_data.is_(False))
            .where(Opportunity.casting_office_id.is_not(None))
            .group_by(Opportunity.casting_office_id)
        ).all()
        return any(int(count or 0) >= 3 for _, count in rows)

    def _actor_submissions_with_assets(self, actor: ActorProfile) -> list[Submission]:
        submissions = list(
            self.db.scalars(
                select(Submission)
                .where(Submission.actor_profile_id == actor.id)
                .options(selectinload(Submission.assets), selectinload(Submission.opportunity))
            )
        )
        return [
            submission
            for submission in submissions
            if not submission.opportunity or not submission.opportunity.is_demo_data
        ]
