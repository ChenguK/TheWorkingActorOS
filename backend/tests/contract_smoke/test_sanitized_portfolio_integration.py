from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app.core.config import Settings
from app.db.models import (
    ActorJournalEntry,
    ActorProfile,
    AgentRecommendation,
    Archetype,
    Asset,
    AuditionCalendarEvent,
    AuditionJournalEntry,
    CallbackEvent,
    CareerMemory,
    CastingGoal,
    DreamRoleTarget,
    LearningInsight,
    Opportunity,
    RecommendationFeedback,
    Submission,
    SubmissionStatusHistory,
    TravelPreference,
    WatchList,
)
from app.db.models.submission import SubmissionAsset
from app.services.command_center_service import CommandCenterService
from app.services.opportunity_intelligence_service import OpportunityIntelligenceService
from app.services.portfolio_seed_ownership_service import (
    PORTFOLIO_PROFILE_ID,
    PortfolioSeedOwnershipService,
)
from app.services.sanitized_portfolio_manifest import (
    AGENT_RECOMMENDATION_ID,
    CAREER_MEMORY_ID,
    CASTING_GOAL_ID,
    OPPORTUNITY_IDS,
    RECOMMENDATION_FEEDBACK_ID,
    SUBMISSION_IDS,
)
from scripts.seed_sanitized_portfolio import run


pytestmark = pytest.mark.contract_smoke
AS_OF_A = datetime(2036, 5, 12, 16, 0, tzinfo=timezone.utc)
AS_OF_B = AS_OF_A + timedelta(days=90)
API = "/api/v1"


def settings() -> Settings:
    return Settings(
        _env_file=None,
        environment="development",
        sanitized_portfolio_seed_enabled=True,
    )


def owned_counts(session) -> dict[str, int]:
    opportunity_ids = tuple(
        item.id for item in PortfolioSeedOwnershipService(session).find_owned_opportunities()
    )
    return {
        "ActorProfile": int(session.get(ActorProfile, PORTFOLIO_PROFILE_ID) is not None),
        "TravelPreference": session.scalar(
            select(func.count())
            .select_from(TravelPreference)
            .where(TravelPreference.actor_profile_id == PORTFOLIO_PROFILE_ID)
        ),
        "Opportunity": len(opportunity_ids),
        "CastingGoal": session.scalar(
            select(func.count())
            .select_from(CastingGoal)
            .where(CastingGoal.actor_profile_id == PORTFOLIO_PROFILE_ID)
        ),
        "WatchList": session.scalar(
            select(func.count())
            .select_from(WatchList)
            .where(WatchList.actor_profile_id == PORTFOLIO_PROFILE_ID)
        ),
        "CareerMemory": session.scalar(
            select(func.count())
            .select_from(CareerMemory)
            .where(CareerMemory.actor_profile_id == PORTFOLIO_PROFILE_ID)
        ),
        "Submission": session.scalar(
            select(func.count())
            .select_from(Submission)
            .where(Submission.actor_profile_id == PORTFOLIO_PROFILE_ID)
        ),
        "SubmissionStatusHistory": session.scalar(
            select(func.count())
            .select_from(SubmissionStatusHistory)
            .where(SubmissionStatusHistory.submission_id.in_(SUBMISSION_IDS))
        ),
        "AuditionCalendarEvent": session.scalar(
            select(func.count())
            .select_from(AuditionCalendarEvent)
            .where(AuditionCalendarEvent.submission_id.in_(SUBMISSION_IDS))
        ),
        "AuditionJournalEntry": session.scalar(
            select(func.count())
            .select_from(AuditionJournalEntry)
            .where(AuditionJournalEntry.submission_id.in_(SUBMISSION_IDS))
        ),
        "ActorJournalEntry": session.scalar(
            select(func.count())
            .select_from(ActorJournalEntry)
            .where(ActorJournalEntry.linked_audition_id.in_(SUBMISSION_IDS))
        ),
        "AgentRecommendation": session.scalar(
            select(func.count())
            .select_from(AgentRecommendation)
            .where(AgentRecommendation.actor_profile_id == PORTFOLIO_PROFILE_ID)
        ),
        "RecommendationFeedback": session.scalar(
            select(func.count())
            .select_from(RecommendationFeedback)
            .where(RecommendationFeedback.actor_profile_id == PORTFOLIO_PROFILE_ID)
        ),
    }


EXPECTED_COUNTS = {
    "ActorProfile": 1,
    "TravelPreference": 1,
    "Opportunity": 7,
    "CastingGoal": 1,
    "WatchList": 1,
    "CareerMemory": 1,
    "Submission": 3,
    "SubmissionStatusHistory": 3,
    "AuditionCalendarEvent": 10,
    "AuditionJournalEntry": 3,
    "ActorJournalEntry": 3,
    "AgentRecommendation": 1,
    "RecommendationFeedback": 1,
}


def test_complete_graph_routes_reruns_and_command_center_contract(client, db) -> None:
    from app.core.database import SessionLocal

    db.close()
    run(execute=True, reset=False, settings=settings(), session_factory=SessionLocal, as_of=AS_OF_A)
    with SessionLocal() as fresh:
        assert owned_counts(fresh) == EXPECTED_COUNTS
        assert tuple(
            item.id for item in PortfolioSeedOwnershipService(fresh).find_owned_opportunities()
        ) == tuple(sorted(OPPORTUNITY_IDS))
        assert fresh.get(CastingGoal, CASTING_GOAL_ID).actor_profile_id == PORTFOLIO_PROFILE_ID
        assert fresh.get(CareerMemory, CAREER_MEMORY_ID).actor_profile_id == PORTFOLIO_PROFILE_ID
        assert fresh.get(AgentRecommendation, AGENT_RECOMMENDATION_ID).score == 91
        assert fresh.get(RecommendationFeedback, RECOMMENDATION_FEEDBACK_ID).recommendation_id == (
            AGENT_RECOMMENDATION_ID
        )
        assert all(
            fresh.get(Opportunity, item_id).is_demo_data is False
            and PortfolioSeedOwnershipService.is_portfolio_owned(fresh.get(Opportunity, item_id))
            for item_id in OPPORTUNITY_IDS
        )
        temporal = {
            "opportunities": {
                str(item_id): (
                    fresh.get(Opportunity, item_id).submission_deadline,
                    fresh.get(Opportunity, item_id).audition_deadline,
                    fresh.get(Opportunity, item_id).callback_date,
                    fresh.get(Opportunity, item_id).shoot_start_date,
                    fresh.get(Opportunity, item_id).shoot_end_date,
                )
                for item_id in OPPORTUNITY_IDS
            },
            "submissions": {
                str(item_id): fresh.get(Submission, item_id).submitted_at
                for item_id in SUBMISSION_IDS
            },
            "feedback": fresh.get(RecommendationFeedback, RECOMMENDATION_FEEDBACK_ID).created_at,
            "calendar": tuple(
                fresh.scalars(
                    select(AuditionCalendarEvent.start_datetime).order_by(AuditionCalendarEvent.id)
                )
            ),
            "audition_journal": tuple(
                fresh.scalars(select(AuditionJournalEntry.date).order_by(AuditionJournalEntry.id))
            ),
            "actor_journal": tuple(
                fresh.scalars(select(ActorJournalEntry.date).order_by(ActorJournalEntry.id))
            ),
        }
        assert fresh.scalar(select(func.count()).select_from(Asset)) == 0
        assert fresh.scalar(select(func.count()).select_from(SubmissionAsset)) == 0
        assert fresh.scalar(select(func.count()).select_from(CallbackEvent)) == 0
        assert fresh.scalar(select(func.count()).select_from(DreamRoleTarget)) == 0
        assert fresh.scalar(select(func.count()).select_from(Archetype)) == 0
        assert fresh.scalar(select(func.count()).select_from(LearningInsight)) == 0

    run(execute=True, reset=False, settings=settings(), session_factory=SessionLocal, as_of=AS_OF_A)
    run(execute=True, reset=False, settings=settings(), session_factory=SessionLocal, as_of=AS_OF_B)
    with SessionLocal() as fresh:
        assert owned_counts(fresh) == EXPECTED_COUNTS
        assert temporal == {
            "opportunities": {
                str(item_id): (
                    fresh.get(Opportunity, item_id).submission_deadline,
                    fresh.get(Opportunity, item_id).audition_deadline,
                    fresh.get(Opportunity, item_id).callback_date,
                    fresh.get(Opportunity, item_id).shoot_start_date,
                    fresh.get(Opportunity, item_id).shoot_end_date,
                )
                for item_id in OPPORTUNITY_IDS
            },
            "submissions": {
                str(item_id): fresh.get(Submission, item_id).submitted_at
                for item_id in SUBMISSION_IDS
            },
            "feedback": fresh.get(RecommendationFeedback, RECOMMENDATION_FEEDBACK_ID).created_at,
            "calendar": tuple(
                fresh.scalars(
                    select(AuditionCalendarEvent.start_datetime).order_by(AuditionCalendarEvent.id)
                )
            ),
            "audition_journal": tuple(
                fresh.scalars(select(AuditionJournalEntry.date).order_by(AuditionJournalEntry.id))
            ),
            "actor_journal": tuple(
                fresh.scalars(select(ActorJournalEntry.date).order_by(ActorJournalEntry.id))
            ),
        }

    routes = {
        "/actor-profile": 200,
        "/opportunities": 200,
        "/submissions": 200,
        "/operations/calendar/events": 200,
        "/journal": 200,
        "/intelligence/audition-journal": 200,
        "/agents/recommendations": 200,
        "/agents/career-memory": 200,
        "/command-center": 200,
        "/system/capabilities": 200,
    }
    payloads = {}
    for path, status in routes.items():
        response = client.get(f"{API}{path}")
        assert response.status_code == status, (path, response.text)
        payloads[path] = response.json()

    assert payloads["/actor-profile"]["id"] == str(PORTFOLIO_PROFILE_ID)
    assert len(payloads["/opportunities"]) == 5
    assert {item["id"] for item in payloads["/opportunities"]} < {
        str(item_id) for item_id in OPPORTUNITY_IDS
    }
    assert len(payloads["/submissions"]) == 3
    assert len(payloads["/operations/calendar/events"]) == 10
    assert len(payloads["/journal"]) == 3
    assert len(payloads["/intelligence/audition-journal"]) == 3
    assert len(payloads["/agents/recommendations"]) == 1

    command = payloads["/command-center"]
    cards = command["today_opportunities"]
    assert len(cards) == 5
    assert all(card.get("intelligence", {}).get("version") == 1 for card in cards)
    assert all(card["intelligence"]["overall_score"] != 91 for card in cards)
    assert cards[0]["role"] == "Forensic Analyst"
    assert (
        cards[0]["intelligence"]["overall_score"] != payloads["/agents/recommendations"][0]["score"]
    )

    with SessionLocal() as fresh:
        actor = fresh.get(ActorProfile, PORTFOLIO_PROFILE_ID)
        opportunities = [fresh.get(Opportunity, item_id) for item_id in OPPORTUNITY_IDS]
        strategy_score_before = fresh.get(AgentRecommendation, AGENT_RECOMMENDATION_ID).score
        contexts = CommandCenterService(fresh)._read_scoring_contexts(opportunities, actor)
        all_scores = {
            str(opportunity.id): OpportunityIntelligenceService(fresh)
            .score(
                opportunity,
                actor,
                contexts[opportunity.id],
                as_of=datetime.now(timezone.utc),
            )
            .as_dict()
            for opportunity in opportunities
        }
        assert (
            fresh.get(AgentRecommendation, AGENT_RECOMMENDATION_ID).score
            == strategy_score_before
            == 91
        )
    assert {
        opportunity.role: (
            all_scores[str(opportunity.id)]["overall_score"],
            all_scores[str(opportunity.id)]["suggested_action"]["action"],
            all_scores[str(opportunity.id)]["confidence"]["level"],
            all_scores[str(opportunity.id)]["hard_override"],
        )
        for opportunity in opportunities
    } == {
        "Forensic Analyst": (86, "save_for_later", "Low", False),
        "Public Defender": (72, "review_today", "Low", False),
        "Technology Founder": (80, "save_for_later", "Low", False),
        "Investigative Producer": (80, "review_today", "Low", False),
        "Community Organizer": (81, "review_today", "Medium", False),
        "Federal Investigator": (75, "review_today", "Medium", False),
        "Crisis Negotiator": (80, "save_for_later", "Low", False),
    }
    for card in cards:
        assert all_scores[card["id"]]["overall_score"] == card["intelligence"]["overall_score"]

    portfolio_payload = json.dumps(
        {key: value for key, value in payloads.items() if key != "/system/capabilities"},
        sort_keys=True,
    )
    command_size = len(json.dumps(command).encode())
    assert command_size < 100_000
    for prohibited in (
        "/Users/",
        "/tmp/",
        "example.com",
        "private-user",
        "postgresql://",
        "postgresql+psycopg://",
    ):
        assert prohibited.lower() not in portfolio_payload.lower()
    assert all(
        item["source_metadata"]["portfolio_seed"]["namespace"] == "sanitized-portfolio-v1"
        for item in payloads["/opportunities"]
    )
    vulnerable = " ".join(
        str(item.get(field, ""))
        for item in payloads["/opportunities"]
        for field in ("role", "project", "description", "source_type")
    )
    assert not re.search(r"\b(demo|example|sample|test)\b", vulnerable, re.IGNORECASE)

    print("SANITIZED_COMMAND_CENTER=" + json.dumps(cards, sort_keys=True))
    print(f"SANITIZED_COMMAND_CENTER_BYTES={command_size}")
    print(
        "SANITIZED_ALL_SCORES="
        + json.dumps(
            {
                str(opportunity.id): {
                    "role": opportunity.role,
                    "project": opportunity.project,
                    "score": all_scores[str(opportunity.id)]["overall_score"],
                    "action": all_scores[str(opportunity.id)]["suggested_action"],
                    "confidence": all_scores[str(opportunity.id)]["confidence"],
                    "hard_override": all_scores[str(opportunity.id)]["hard_override"],
                }
                for opportunity in opportunities
            },
            sort_keys=True,
        )
    )

    run(
        execute=True,
        reset=True,
        settings=settings(),
        session_factory=SessionLocal,
        as_of=AS_OF_B,
    )
    with SessionLocal() as fresh:
        assert owned_counts(fresh) == {name: 0 for name in EXPECTED_COUNTS}
