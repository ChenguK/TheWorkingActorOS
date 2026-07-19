from __future__ import annotations

import socket
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from .conftest import assert_safe_test_database


pytestmark = pytest.mark.contract_smoke
API = "/api/v1"


def create_actor(client):
    response = client.put(
        f"{API}/actor-profile",
        json={
            "name": "Contract Actor",
            "sag_status": "SAG-AFTRA",
            "union_status": "Union",
            "current_location": "New York, NY",
            "playable_age_min": 28,
            "playable_age_max": 38,
            "skills": ["Teleprompter"],
            "pronouns": None,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def create_opportunity(client):
    response = client.post(
        f"{API}/opportunities",
        json={
            "role": "DST Detective",
            "project": "Spring Forward",
            "union": "SAG-AFTRA",
            "location": "New York, NY",
            "description": "Deterministic contract breakdown.",
            "project_type": "Television",
            "role_type": "Guest Star",
            "audition_type": "Self-Tape",
            "audition_deadline": "2026-03-08T01:30:00-05:00",
            "callback_date": "2026-03-09T14:00:00-04:00",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_opportunity_create_synchronous_contract(client, db):
    from app.db.models import (
        ActorJournalEntry,
        AgentRecommendation,
        Asset,
        AuditionCalendarEvent,
        BreakdownParseRun,
        BreakdownRole,
        Opportunity,
        SelfTape,
        SelfTapeWorkflow,
        Submission,
        SubmissionAutomationQueue,
    )

    create_actor(client)
    before_intelligence = client.get(f"{API}/intelligence/dashboard").json()
    before_industry = client.get(f"{API}/intelligence/casting-patterns").json()
    before_material_performance = client.get(f"{API}/intelligence/materials/performance").json()
    before_operations = client.get(f"{API}/operations/dashboard").json()
    standard_response = client.post(
        f"{API}/opportunities",
        json={
            "role": "Neighbor",
            "project": "Visible Pilot",
            "union": "SAG-AFTRA",
            "location": "New York, NY",
            "description": "Television comedy. Neighbor, co-star, age 30-40.",
            "project_type": "Television",
            "role_type": "Co-Star",
            "audition_type": "Virtual",
        },
    )
    assert standard_response.status_code == 201, standard_response.text
    standard = standard_response.json()
    assert {"id", "visibility_status", "breakdown_roles", "breakdown_parse_runs", "source_metadata"} <= standard.keys()
    assert standard["visibility_status"] == "visible"
    assert standard["breakdown_parse_runs"]
    assert (standard["source_metadata"] or {}).get("trust_verification")
    standard_id = standard["id"]
    assert db.scalar(select(func.count()).select_from(Opportunity).where(Opportunity.id == standard_id)) == 1
    assert db.scalar(select(func.count()).select_from(BreakdownParseRun).where(BreakdownParseRun.breakdown_id == standard_id)) >= 1
    # Role rows are conditional on structured parser output; the stable response still exposes
    # both normalized role JSON and the persisted-role collection.
    assert isinstance(standard["role_details"], dict)
    assert isinstance(standard["breakdown_roles"], list)
    assert all(role["character_profile"] is not None for role in standard["breakdown_roles"])
    assert db.scalar(select(func.count()).select_from(BreakdownRole).where(BreakdownRole.breakdown_id == standard_id)) == len(standard["breakdown_roles"])
    journal = db.scalars(select(ActorJournalEntry).where(ActorJournalEntry.linked_breakdown_id == standard_id)).all()
    assert len(journal) == 1 and journal[0].event_type == "Accepted Breakdown"
    assert db.scalar(select(func.count()).select_from(SelfTapeWorkflow).where(SelfTapeWorkflow.opportunity_id == standard_id)) == 0
    assert db.scalar(select(func.count()).select_from(AuditionCalendarEvent).where(AuditionCalendarEvent.opportunity_id == standard_id)) == 0
    readiness = client.get(f"{API}/intelligence/readiness/opportunities").json()
    assert any(item["opportunity_id"] == standard_id for item in readiness)
    assert client.get(f"{API}/opportunities/material-matches").json() == []
    command_center = client.get(f"{API}/command-center").json()
    assert any(item["id"] == standard_id for item in command_center["today_opportunities"])
    assert client.get(f"{API}/intelligence/casting-patterns").json() != before_industry
    assert client.get(f"{API}/intelligence/dashboard").json() == before_intelligence
    assert client.get(f"{API}/intelligence/materials/performance").json() == before_material_performance
    assert client.get(f"{API}/operations/dashboard").json() == before_operations

    self_tape_response = client.post(
        f"{API}/opportunities",
        json={
            "role": "Detective",
            "project": "Tape Pilot",
            "union": "SAG-AFTRA",
            "location": "New York, NY",
            "description": "Television drama. Detective, guest star. Self-tape due July 30, 2026 at 6 PM ET.",
            "project_type": "Television",
            "role_type": "Guest Star",
            "audition_type": "Self-Tape",
            "audition_deadline": "2026-07-30T18:00:00-04:00",
        },
    )
    assert self_tape_response.status_code == 201, self_tape_response.text
    self_tape_id = self_tape_response.json()["id"]
    workflows = db.scalars(select(SelfTapeWorkflow).where(SelfTapeWorkflow.opportunity_id == self_tape_id)).all()
    assert len(workflows) == 1
    assert workflows[0].submission_id is None
    assert workflows[0].tape_due_at == datetime.fromisoformat(
    "2026-07-30T18:00:00-04:00"
)
    calendar = db.scalars(select(AuditionCalendarEvent).where(AuditionCalendarEvent.opportunity_id == self_tape_id)).all()
    assert len(calendar) == 1 and calendar[0].event_type == "Self-Tape Due"
    assert client.get(f"{API}/operations/dashboard").json() != before_operations
    assert len(db.scalars(select(ActorJournalEntry).where(ActorJournalEntry.linked_breakdown_id == self_tape_id)).all()) == 1

    # Re-running workflow synchronization for the same opportunity updates the owner row, not duplicates it.
    from app.services.opportunity_service import OpportunityService
    OpportunityService(db)._ensure_self_tape_workflow(db.get(Opportunity, self_tape_id))
    db.flush()
    assert db.scalar(select(func.count()).select_from(SelfTapeWorkflow).where(SelfTapeWorkflow.opportunity_id == self_tape_id)) == 1

    assert db.scalar(select(func.count()).select_from(Submission)) == 0
    assert db.scalar(select(func.count()).select_from(SubmissionAutomationQueue)) == 0
    assert db.scalar(select(func.count()).select_from(AgentRecommendation)) == 0
    assert db.scalar(select(func.count()).select_from(Asset)) == 0
    assert db.scalar(select(func.count()).select_from(SelfTape)) == 0


def test_opportunity_create_hidden_sparse_and_atomic_rollback(client, db, monkeypatch):
    from app.db.models import ActorJournalEntry, AuditionCalendarEvent, BreakdownParseRun, Opportunity, SelfTapeWorkflow
    from app.services.actor_work_event_service import ActorWorkEventService

    hidden_response = client.post(
        f"{API}/opportunities",
        json={
            "role": "Production Assistant",
            "project": "Crew Call",
            "union": "Non-Union",
            "location": "New York, NY",
            "description": "Seeking a production assistant for the camera crew. This is a crew job, not an acting role.",
            "audition_type": "Virtual",
            "submission_deadline": "2020-01-01T12:00:00-05:00",
        },
    )
    assert hidden_response.status_code == 201, hidden_response.text
    hidden = hidden_response.json()
    assert hidden["visibility_status"] == "discarded"
    assert hidden["hidden_by_rule"] == "deadline_expired"
    assert all(item["id"] != hidden["id"] for item in client.get(f"{API}/opportunities").json())
    assert any(item["id"] == hidden["id"] for item in client.get(f"{API}/opportunities", params={"include_hidden": True}).json())
    assert len(db.scalars(select(ActorJournalEntry).where(ActorJournalEntry.linked_breakdown_id == hidden["id"])).all()) == 1

    sparse_response = client.post(
        f"{API}/opportunities",
        json={"role": "Reader", "project": "Manual", "union": "Non-Union", "location": "Remote", "description": "Actor reader role."},
    )
    assert sparse_response.status_code == 201, sparse_response.text
    sparse = sparse_response.json()
    assert sparse["source_type"] == "Manual Entry" and sparse["audition_type"] == "Unknown"
    assert sparse["source_metadata"] is not None and sparse["production_details"] is not None and sparse["role_details"] is not None
    assert db.scalar(select(func.count()).select_from(SelfTapeWorkflow).where(SelfTapeWorkflow.opportunity_id == sparse["id"])) == 0

    before = {
        "opportunities": db.scalar(select(func.count()).select_from(Opportunity)),
        "workflows": db.scalar(select(func.count()).select_from(SelfTapeWorkflow)),
        "journal": db.scalar(select(func.count()).select_from(ActorJournalEntry)),
        "calendar": db.scalar(select(func.count()).select_from(AuditionCalendarEvent)),
        "parse_runs": db.scalar(select(func.count()).select_from(BreakdownParseRun)),
    }
    original = ActorWorkEventService.accepted_breakdown

    def fail_after_side_effects(self, opportunity):
        original(self, opportunity)
        raise RuntimeError("forced post-side-effect failure")

    monkeypatch.setattr(ActorWorkEventService, "accepted_breakdown", fail_after_side_effects)
    with pytest.raises(RuntimeError, match="forced post-side-effect failure"):
        client.post(
            f"{API}/opportunities",
            json={
                "role": "Rollback Role", "project": "Rollback Project", "union": "SAG-AFTRA",
                "location": "New York, NY", "description": "Self-tape due August 5, 2026 at 6 PM ET.",
                "audition_type": "Self-Tape", "audition_deadline": "2026-08-05T18:00:00-04:00",
            },
        )
    db.expire_all()
    after = {
        "opportunities": db.scalar(select(func.count()).select_from(Opportunity)),
        "workflows": db.scalar(select(func.count()).select_from(SelfTapeWorkflow)),
        "journal": db.scalar(select(func.count()).select_from(ActorJournalEntry)),
        "calendar": db.scalar(select(func.count()).select_from(AuditionCalendarEvent)),
        "parse_runs": db.scalar(select(func.count()).select_from(BreakdownParseRun)),
    }
    assert after == before


def test_strategy_generation_append_visibility_and_unaffected_owner_contract(client, db):
    from app.db.models import (
        ActorJournalEntry,
        AgentRecommendation,
        AuditionCalendarEvent,
        Opportunity,
        SelfTapeWorkflow,
        Submission,
        SubmissionAutomationQueue,
    )

    create_actor(client)
    opportunity = create_opportunity(client)
    opportunity_id = opportunity["id"]
    before = {
        "journal": db.scalar(select(func.count()).select_from(ActorJournalEntry)),
        "calendar": db.scalar(select(func.count()).select_from(AuditionCalendarEvent)),
        "workflows": db.scalar(select(func.count()).select_from(SelfTapeWorkflow)),
        "submissions": db.scalar(select(func.count()).select_from(Submission)),
        "queue": db.scalar(select(func.count()).select_from(SubmissionAutomationQueue)),
    }

    first = client.post(f"{API}/opportunities/{opportunity_id}/recommend")
    second = client.post(f"{API}/opportunities/{opportunity_id}/recommend")
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["id"] != second.json()["id"]
    assert db.scalar(
        select(func.count()).select_from(AgentRecommendation).where(
            AgentRecommendation.opportunity_id == opportunity_id
        )
    ) == 2
    refreshed = db.get(Opportunity, opportunity_id)
    db.refresh(refreshed)
    assert refreshed.visibility_status == "visible"
    assert any(item["id"] == opportunity_id for item in client.get(f"{API}/opportunities").json())
    assert {
        "journal": db.scalar(select(func.count()).select_from(ActorJournalEntry)),
        "calendar": db.scalar(select(func.count()).select_from(AuditionCalendarEvent)),
        "workflows": db.scalar(select(func.count()).select_from(SelfTapeWorkflow)),
        "submissions": db.scalar(select(func.count()).select_from(Submission)),
        "queue": db.scalar(select(func.count()).select_from(SubmissionAutomationQueue)),
    } == before

    refreshed.role_details = {**(refreshed.role_details or {}), "submission_deadline": "deadline unknown"}
    refreshed.submission_deadline = None
    db.commit()
    needs_review = client.post(f"{API}/opportunities/{opportunity_id}/recommend")
    assert needs_review.status_code == 200, needs_review.text
    db.expire_all()
    refreshed = db.get(Opportunity, opportunity_id)
    assert refreshed.visibility_status == "hidden"
    assert refreshed.hidden_by_rule == "needs_date_review"
    assert all(item["id"] != opportunity_id for item in client.get(f"{API}/opportunities").json())
    assert any(
        item["id"] == opportunity_id
        for item in client.get(f"{API}/opportunities", params={"include_hidden": True}).json()
    )
    assert db.scalar(
        select(func.count()).select_from(AgentRecommendation).where(
            AgentRecommendation.opportunity_id == opportunity_id
        )
    ) == 3


def test_recommendation_feedback_append_learning_rollback_and_response_contract(client, db, monkeypatch):
    from app.agents.learning_agent import LearningAgent
    from app.db.models import (
        ActorJournalEntry,
        ActorRelationship,
        AgentRecommendation,
        Asset,
        AuditionCalendarEvent,
        BreakdownRole,
        CharacterProfile,
        LearningInsight,
        RecommendationFeedback,
        SelfTape,
        SelfTapeWorkflow,
        Submission,
        SubmissionAutomationQueue,
        TravelPreference,
    )

    actor = create_actor(client)
    opportunity = create_opportunity(client)
    recommendation_response = client.post(f"{API}/opportunities/{opportunity['id']}/recommend")
    assert recommendation_response.status_code == 200, recommendation_response.text
    recommendation = recommendation_response.json()

    # Prove the response-level dependency rather than merely the model import: the
    # executive endpoint exposes the latest learning insight when it has a signal.
    db.add(
        LearningInsight(
            actor_profile_id=actor["id"],
            trends={"highest_performing_archetypes": ["Detective"]},
            recommendation_weights={},
            explanation="Prior learning signal",
        )
    )
    db.commit()
    priorities_before = client.get(f"{API}/agents/executive/priorities").json()
    assert any(item["category"] == "Analytics" for item in priorities_before)

    recommendation_before = client.get(f"{API}/agents/recommendations").json()
    response_owners_before = {
        "command_center": client.get(f"{API}/command-center").json(),
        "readiness": client.get(f"{API}/intelligence/readiness/opportunities").json(),
        "material_matches": client.get(f"{API}/opportunities/material-matches").json(),
        "intelligence_analytics": client.get(f"{API}/intelligence/dashboard").json(),
        "industry_analytics": client.get(f"{API}/intelligence/casting-patterns").json(),
        "material_performance": client.get(f"{API}/intelligence/materials/performance").json(),
            "career_swot": client.get(f"{API}/agents/career/swot").json(),
        "career_tasks": client.get(f"{API}/career-development/tasks").json(),
        "executive_briefs": client.get(f"{API}/agents/chief-of-staff/briefs").json(),
    }
    from app.db.models import Opportunity

    db.expire_all()
    persisted_opportunity = db.get(Opportunity, opportunity["id"])
    opportunity_before = {
        column.key: getattr(persisted_opportunity, column.key)
        for column in Opportunity.__table__.columns
    }
    unaffected_before = {
        "journal": db.scalar(select(func.count()).select_from(ActorJournalEntry)),
        "calendar": db.scalar(select(func.count()).select_from(AuditionCalendarEvent)),
        "workflows": db.scalar(select(func.count()).select_from(SelfTapeWorkflow)),
        "submissions": db.scalar(select(func.count()).select_from(Submission)),
        "queue": db.scalar(select(func.count()).select_from(SubmissionAutomationQueue)),
        "roles": db.scalar(select(func.count()).select_from(BreakdownRole)),
        "profiles": db.scalar(select(func.count()).select_from(CharacterProfile)),
        "relationships": db.scalar(select(func.count()).select_from(ActorRelationship)),
        "assets": db.scalar(select(func.count()).select_from(Asset)),
        "reusable_tapes": db.scalar(select(func.count()).select_from(SelfTape)),
        "preferences": db.scalar(select(func.count()).select_from(TravelPreference)),
    }
    payload = {
        "feedback_type": "This Fits Me",
        "fit_reasons": ["Grounded authority"],
        "notes": "Keep this signal",
    }
    first = client.post(f"{API}/agents/recommendations/{recommendation['id']}/feedback", json=payload)
    assert first.status_code == 201, first.text
    assert first.json()["recommendation_id"] == recommendation["id"]
    assert first.json()["fit_reasons"] == payload["fit_reasons"]

    db.expire_all()
    persisted_feedback = db.scalars(
        select(RecommendationFeedback).where(RecommendationFeedback.recommendation_id == recommendation["id"])
    ).all()
    persisted_insights = db.scalars(
        select(LearningInsight)
        .where(LearningInsight.actor_profile_id == actor["id"])
        .order_by(LearningInsight.created_at.asc())
    ).all()
    assert len(persisted_feedback) == 1
    assert len(persisted_insights) == 2
    assert persisted_insights[-1].trends["user_feedback_count"] == 1
    assert persisted_insights[-1].trends["user_fit_feedback"] == {"Grounded authority": 1}
    assert client.get(f"{API}/agents/recommendations").json() == recommendation_before
    db.expire_all()
    persisted_opportunity = db.get(Opportunity, opportunity["id"])
    assert {
        column.key: getattr(persisted_opportunity, column.key)
        for column in Opportunity.__table__.columns
    } == opportunity_before
    assert client.get(f"{API}/agents/executive/priorities").json() != priorities_before
    response_owners_after = {
        "command_center": client.get(f"{API}/command-center").json(),
        "readiness": client.get(f"{API}/intelligence/readiness/opportunities").json(),
        "material_matches": client.get(f"{API}/opportunities/material-matches").json(),
        "intelligence_analytics": client.get(f"{API}/intelligence/dashboard").json(),
        "industry_analytics": client.get(f"{API}/intelligence/casting-patterns").json(),
        "material_performance": client.get(f"{API}/intelligence/materials/performance").json(),
        "career_swot": client.get(f"{API}/agents/career/swot").json(),
        "career_tasks": client.get(f"{API}/career-development/tasks").json(),
        "executive_briefs": client.get(f"{API}/agents/chief-of-staff/briefs").json(),
    }
    assert response_owners_after["command_center"] != response_owners_before["command_center"]
    assert {
        owner: response
        for owner, response in response_owners_after.items()
        if owner != "command_center"
    } == {
        owner: response
        for owner, response in response_owners_before.items()
        if owner != "command_center"
    }
    assert {
        "journal": db.scalar(select(func.count()).select_from(ActorJournalEntry)),
        "calendar": db.scalar(select(func.count()).select_from(AuditionCalendarEvent)),
        "workflows": db.scalar(select(func.count()).select_from(SelfTapeWorkflow)),
        "submissions": db.scalar(select(func.count()).select_from(Submission)),
        "queue": db.scalar(select(func.count()).select_from(SubmissionAutomationQueue)),
        "roles": db.scalar(select(func.count()).select_from(BreakdownRole)),
        "profiles": db.scalar(select(func.count()).select_from(CharacterProfile)),
        "relationships": db.scalar(select(func.count()).select_from(ActorRelationship)),
        "assets": db.scalar(select(func.count()).select_from(Asset)),
        "reusable_tapes": db.scalar(select(func.count()).select_from(SelfTape)),
        "preferences": db.scalar(select(func.count()).select_from(TravelPreference)),
    } == unaffected_before

    retry = client.post(f"{API}/agents/recommendations/{recommendation['id']}/feedback", json=payload)
    assert retry.status_code == 201, retry.text
    assert retry.json()["id"] != first.json()["id"]
    db.expire_all()
    assert db.scalar(
        select(func.count()).select_from(RecommendationFeedback).where(
            RecommendationFeedback.recommendation_id == recommendation["id"]
        )
    ) == 2
    latest = db.scalars(
        select(LearningInsight)
        .where(LearningInsight.actor_profile_id == actor["id"])
        .order_by(LearningInsight.created_at.desc())
    ).first()
    assert latest.trends["user_feedback_count"] == 2
    assert latest.trends["user_fit_feedback"] == {"Grounded authority": 2}

    feedback_count = db.scalar(select(func.count()).select_from(RecommendationFeedback))
    insight_count = db.scalar(select(func.count()).select_from(LearningInsight))

    def fail_after_insight_flush(self, target_actor):
        self.db.add(
            LearningInsight(
                actor_profile_id=target_actor.id,
                trends={"forced": "rollback"},
                recommendation_weights={},
                explanation="Must not persist",
            )
        )
        self.db.flush()
        raise RuntimeError("forced feedback-learning rollback")

    monkeypatch.setattr(LearningAgent, "analyze", fail_after_insight_flush)
    with pytest.raises(RuntimeError, match="forced feedback-learning rollback"):
        client.post(f"{API}/agents/recommendations/{recommendation['id']}/feedback", json=payload)
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(RecommendationFeedback)) == feedback_count
    assert db.scalar(select(func.count()).select_from(LearningInsight)) == insight_count
    assert db.get(AgentRecommendation, recommendation["id"]) is not None


def controlled_deep_parse_result(_engine, _text, parse_mode="Deep Parse"):
    from app.services.breakdown_details_service import BreakdownDetailsService

    details = BreakdownDetailsService().from_text(
        "Deep Parse Pilot\nNEW DETECTIVE\nSelf-tape due August 20, 2026 at 6 PM ET."
    )
    details["production_details"] = {
        **details["production_details"],
        "project_title": "Deep Parse Pilot",
        "project_type": "Television",
        "union_status": "SAG-AFTRA",
    }
    details["role_details"] = {
        **details["role_details"],
        "audition_type": "Self-Tape",
        "submission_deadline": "August 20, 2026 at 6 PM ET.",
        "available_roles": [
            {
                "role_name": "New Detective",
                "role_type": "Guest Star",
                "character_description": "A precise authority figure with teleprompter skills.",
                "role_requirement_text": "NEW DETECTIVE / 28-38 / Any Gender / teleprompter",
                "age_range": "28-38",
                "skills_required": "Teleprompter",
                "confidence_score": 92,
            },
            {
                "role_name": "New Captain",
                "role_type": "Co-Star",
                "character_description": "A commanding precinct captain.",
                "role_requirement_text": "NEW CAPTAIN / 30-45 / Any Gender",
                "age_range": "30-45",
                "confidence_score": 88,
            },
        ],
    }
    details["extracted_facts"] = {"controlled_fact": "new-deep-parse-value"}
    details["ai_inference"] = {
        "controlled_inference": {
            "value": "authority",
            "confidence": 91,
            "explanation": "Deterministic contract fixture.",
        }
    }
    details["ai_summary"] = "Controlled deep-parse summary."
    details["breakdown_classification"] = "Acting Role"
    details["rejection_reason"] = None
    return {
        "parser_version": "contract-deep-parse-v1",
        "parse_mode": parse_mode,
        "cleaned_text": _text,
        "sections": [
            {
                "section_type": "Roles",
                "heading": "ROLES",
                "raw_text": "NEW DETECTIVE\nNEW CAPTAIN",
                "parsed_json": {"roles": ["New Detective", "New Captain"]},
                "confidence_score": 92,
                "display_order": 0,
            },
            {
                "section_type": "Dates",
                "heading": "DATES",
                "raw_text": "Self-tape due August 20, 2026 at 6 PM ET.",
                "parsed_json": {"submission_deadline": "2026-08-20T18:00:00-04:00"},
                "confidence_score": 90,
                "display_order": 1,
            },
        ],
        "details": details,
        "overall_confidence": 93,
        "actor_summary": "Controlled deep-parse actor summary.",
    }


def test_deep_parse_persistence_replacement_retry_and_owner_responses(client, db, monkeypatch):
    from app.db.models import (
        ActorJournalEntry,
        ActorRelationship,
        AgentRecommendation,
        Asset,
        AuditionCalendarEvent,
        BreakdownParseRun,
        BreakdownRole,
        BreakdownSection,
        CareerDevelopmentTask,
        CharacterProfile,
        ExecutiveBrief,
        Opportunity,
        SelfTape,
        SelfTapeWorkflow,
        Submission,
        SubmissionAutomationQueue,
        WatchList,
    )
    from app.services.breakdown_intelligence_engine import BreakdownIntelligenceEngine
    from app.services.breakdown_role_service import BreakdownRoleService

    actor = create_actor(client)
    created = create_opportunity(client)
    opportunity_id = created["id"]
    unrelated = create_opportunity(client)
    unrelated_id = unrelated["id"]
    opportunity = db.get(Opportunity, opportunity_id)
    opportunity.description = "Stale description with obsolete roles."
    opportunity.role_details = {
        "available_roles": [
            {"role_name": "Obsolete One", "role_type": "Lead"},
            {"role_name": "Obsolete Two", "role_type": "Supporting"},
        ]
    }
    opportunity.source_metadata = {"stale_parser": True, "trust_verification": {"status": "Stale"}}
    opportunity.extracted_facts = {"stale_fact": True}
    opportunity.ai_inference = {"stale_inference": True}
    opportunity.breakdown_classification = "Unknown"
    opportunity.visibility_status = "hidden"
    opportunity.hidden_by_rule = "needs_date_review"
    opportunity.hidden_reason = "Stale date review"
    opportunity.manual_review_required = True
    opportunity.submission_deadline = datetime(2026, 8, 20, 18, tzinfo=timezone(timedelta(hours=-4)))
    opportunity.audition_drive_time = 3
    opportunity.demographic_match_status = "Needs Review"
    opportunity.urgency_score = 1
    opportunity.quality_score = 2
    opportunity.priority = "Low"
    opportunity.risk_level = "High"
    opportunity.risk_explanation = "Stale risk"
    BreakdownRoleService(db).sync_from_details(opportunity)
    obsolete_role_ids = {role.id for role in opportunity.breakdown_roles}
    obsolete_section_ids = {section.id for section in opportunity.breakdown_sections}
    db.add_all([
        Asset(
            actor_profile_id=actor["id"], asset_name="Authority Headshot", asset_type="Headshot",
            local_file_path="/tmp/contract-headshot.jpg", tags=["detective"], archetype_names=["Authority Figure"],
            ai_suggested_tags=[], ai_suggested_archetypes=[], analysis_status="complete",
        ),
        WatchList(actor_profile_id=actor["id"], title="Authority Roles", category="Role", terms=["detective", "captain"], priority="High"),
        AuditionCalendarEvent(
            title="Linked callback", event_type="In-Person Callback", opportunity_id=opportunity.id,
            start_datetime=datetime.now(timezone.utc) + timedelta(days=1), location="New York", is_virtual=False,
        ),
        ActorRelationship(name="Contract Casting", role_title="Casting Director", linked_opportunities=[opportunity]),
        CareerDevelopmentTask(title="Unchanged task", description="Must survive deep parse", priority="Medium"),
        ExecutiveBrief(
            actor_profile_id=actor["id"], period_start=date(2026, 7, 1), period_end=date(2026, 7, 7),
            brief_type="Weekly", summary="Unchanged brief",
        ),
        SelfTape(
            title="Reusable contract tape", role_type="Guest Star", archetypes=["Authority Figure"],
            file_path="/tmp/reusable-contract-tape.mp4", linked_opportunity_id=opportunity.id,
            date_created=date(2026, 7, 1),
        ),
    ])
    db.commit()
    recommendation = client.post(f"{API}/opportunities/{opportunity_id}/recommend")
    assert recommendation.status_code == 200, recommendation.text
    submission = client.post(
        f"{API}/submissions",
        json={"actor_profile_id": actor["id"], "opportunity_id": opportunity_id, "current_status": "Self-Tape Callback"},
    )
    assert submission.status_code == 201, submission.text
    db.add(SubmissionAutomationQueue(
        submission_id=submission.json()["id"], opportunity_id=opportunity_id,
        recommendation_id=recommendation.json()["id"], adapter_key="contract", submission_mode="Assisted",
    ))
    db.commit()
    db.expire_all()
    opportunity = db.get(Opportunity, opportunity_id)
    opportunity.visibility_status = "hidden"
    opportunity.hidden_by_rule = "needs_date_review"
    opportunity.hidden_reason = "Stale date review"
    opportunity.manual_review_required = True
    opportunity.audition_drive_time = 3
    db.commit()

    tracked_models = [
        SelfTapeWorkflow, AgentRecommendation, ActorJournalEntry, AuditionCalendarEvent, Submission,
        SubmissionAutomationQueue, ActorRelationship, Asset, SelfTape, CareerDevelopmentTask, ExecutiveBrief,
    ]
    before_ids = {
        model.__tablename__: set(db.scalars(select(model.id)).all()) for model in tracked_models
    }
    before_versions = {
        model.__tablename__: {row.id: row.updated_at for row in db.scalars(select(model)).all()}
        for model in tracked_models
    }
    unrelated_role_ids = set(
        db.scalars(select(BreakdownRole.id).where(BreakdownRole.breakdown_id == unrelated_id))
    )
    before_readiness = client.get(f"{API}/intelligence/readiness/opportunities").json()
    before_materials = client.get(f"{API}/opportunities/material-matches").json()
    before_industry = client.get(f"{API}/intelligence/casting-patterns").json()
    before_command = client.get(f"{API}/command-center").json()
    before_operations = client.get(f"{API}/operations/dashboard").json()
    before_intelligence = client.get(f"{API}/intelligence/dashboard").json()
    before_material_performance = client.get(f"{API}/intelligence/materials/performance").json()
    parse_runs_before = db.scalar(select(func.count()).select_from(BreakdownParseRun).where(BreakdownParseRun.breakdown_id == opportunity_id))

    monkeypatch.setattr(BreakdownIntelligenceEngine, "parse", controlled_deep_parse_result)
    response = client.post(f"{API}/opportunities/{opportunity_id}/deep-parse")
    assert response.status_code == 200, response.text
    payload = response.json()
    db.expire_all()
    opportunity = db.get(Opportunity, opportunity_id)
    assert str(opportunity.id) == opportunity_id
    assert opportunity.visibility_status == "visible" and opportunity.hidden_by_rule is None
    assert payload["visibility_status"] == opportunity.visibility_status
    assert opportunity.breakdown_classification == "Acting Role"
    assert opportunity.extracted_facts["stale_fact"] is True
    assert opportunity.extracted_facts["controlled_fact"] == "new-deep-parse-value"
    assert opportunity.ai_inference["controlled_inference"]["value"] == "authority"
    assert opportunity.source_metadata["breakdown_parser_version"] == "breakdown-intelligence-v1"
    assert opportunity.source_metadata["actor_facing_parse_summary"] == "Controlled deep-parse actor summary."
    assert opportunity.source_metadata["trust_verification"]["status"] != "Stale"
    assert opportunity.demographic_match_status != "Needs Review"
    assert opportunity.urgency_score != 1 and opportunity.quality_score != 2
    assert opportunity.priority != "Low" and opportunity.risk_explanation != "Stale risk"
    assert opportunity.watchlist_match_count >= 1

    runs = list(db.scalars(select(BreakdownParseRun).where(BreakdownParseRun.breakdown_id == opportunity_id).order_by(BreakdownParseRun.started_at)))
    assert len(runs) == parse_runs_before + 1
    assert runs[-1].status == "succeeded" and runs[-1].parse_mode == "Deep Parse"
    sections = list(db.scalars(select(BreakdownSection).where(BreakdownSection.breakdown_id == opportunity_id).order_by(BreakdownSection.display_order)))
    assert [section.section_type for section in sections] == ["Roles", "Dates"]
    assert not obsolete_section_ids.intersection({section.id for section in sections})
    roles = list(db.scalars(select(BreakdownRole).where(BreakdownRole.breakdown_id == opportunity_id).order_by(BreakdownRole.created_at)))
    assert [role.role_name for role in roles] == ["New Detective", "New Captain"]
    assert not obsolete_role_ids.intersection({role.id for role in roles})
    profiles = list(
        db.scalars(select(CharacterProfile).where(CharacterProfile.breakdown_id == opportunity_id))
    )
    assert len(profiles) == 2
    assert {profile.breakdown_role_id for profile in profiles} == {role.id for role in roles}
    first_profile_ids = {profile.id for profile in profiles}

    after_readiness = client.get(f"{API}/intelligence/readiness/opportunities").json()
    after_materials = client.get(f"{API}/opportunities/material-matches").json()
    after_industry = client.get(f"{API}/intelligence/casting-patterns").json()
    after_command = client.get(f"{API}/command-center").json()
    after_operations = client.get(f"{API}/operations/dashboard").json()
    after_intelligence = client.get(f"{API}/intelligence/dashboard").json()
    after_material_performance = client.get(f"{API}/intelligence/materials/performance").json()
    assert before_readiness != after_readiness and any(row["opportunity_id"] == opportunity_id for row in after_readiness)
    assert before_materials != after_materials and any(row["opportunity"]["id"] == opportunity_id for row in after_materials)
    assert before_industry != after_industry
    assert before_command != after_command and any(row["id"] == opportunity_id for row in after_command["today_opportunities"])
    assert before_operations != after_operations
    assert before_intelligence == after_intelligence
    assert before_material_performance == after_material_performance
    assert {
        model.__tablename__: set(db.scalars(select(model.id)).all()) for model in tracked_models
    } == before_ids
    assert {
        model.__tablename__: {row.id: row.updated_at for row in db.scalars(select(model)).all()}
        for model in tracked_models
    } == before_versions
    assert set(db.scalars(select(BreakdownRole.id).where(BreakdownRole.breakdown_id == unrelated_id))) == unrelated_role_ids

    first_section_ids = {section.id for section in sections}
    first_role_ids = {role.id for role in roles}
    retry = client.post(f"{API}/opportunities/{opportunity_id}/deep-parse")
    assert retry.status_code == 200, retry.text
    db.expire_all()
    retry_sections = list(db.scalars(select(BreakdownSection).where(BreakdownSection.breakdown_id == opportunity_id)))
    retry_roles = list(db.scalars(select(BreakdownRole).where(BreakdownRole.breakdown_id == opportunity_id)))
    assert db.scalar(select(func.count()).select_from(BreakdownParseRun).where(BreakdownParseRun.breakdown_id == opportunity_id)) == parse_runs_before + 2
    assert len(retry_sections) == 2 and not first_section_ids.intersection({row.id for row in retry_sections})
    assert len(retry_roles) == 2 and not first_role_ids.intersection({row.id for row in retry_roles})
    retry_profiles = list(
        db.scalars(select(CharacterProfile).where(CharacterProfile.breakdown_id == opportunity_id))
    )
    assert len(retry_profiles) == 2
    assert not first_profile_ids.intersection({profile.id for profile in retry_profiles})
    assert {profile.breakdown_role_id for profile in retry_profiles} == {role.id for role in retry_roles}
    assert db.get(Opportunity, opportunity_id).visibility_status == "visible"
    assert {
        model.__tablename__: set(db.scalars(select(model.id)).all()) for model in tracked_models
    } == before_ids
    assert {
        model.__tablename__: {row.id: row.updated_at for row in db.scalars(select(model)).all()}
        for model in tracked_models
    } == before_versions


def test_deep_parse_atomic_rollback_and_pre_persistence_failure(client, db, monkeypatch):
    from sqlalchemy.orm import Session
    from app.db.models import BreakdownParseRun, BreakdownRole, BreakdownSection, CharacterProfile, Opportunity
    from app.services.breakdown_intelligence_engine import BreakdownIntelligenceEngine

    create_actor(client)
    created = create_opportunity(client)
    opportunity_id = created["id"]
    baseline = db.get(Opportunity, opportunity_id)
    baseline_role = BreakdownRole(
        breakdown=baseline, role_name="Rollback Role", fit_status="Possible Fit",
        extracted_facts={}, ai_inference={},
    )
    db.add(baseline_role)
    db.flush()
    baseline_profile = CharacterProfile(
        breakdown=baseline, breakdown_role=baseline_role, role_name="Rollback Role",
        primary_archetypes=["Rollback Archetype"],
    )
    db.add(baseline_profile)
    db.commit()
    before = {
        "description": baseline.description,
        "source_metadata": baseline.source_metadata,
        "extracted_facts": baseline.extracted_facts,
        "ai_inference": baseline.ai_inference,
        "classification": baseline.breakdown_classification,
        "visibility": baseline.visibility_status,
        "runs": set(db.scalars(select(BreakdownParseRun.id).where(BreakdownParseRun.breakdown_id == opportunity_id))),
        "sections": set(db.scalars(select(BreakdownSection.id).where(BreakdownSection.breakdown_id == opportunity_id))),
        "roles": set(db.scalars(select(BreakdownRole.id).where(BreakdownRole.breakdown_id == opportunity_id))),
        "profiles": set(db.scalars(select(CharacterProfile.id).where(CharacterProfile.breakdown_id == opportunity_id))),
    }
    monkeypatch.setattr(BreakdownIntelligenceEngine, "parse", controlled_deep_parse_result)
    original_commit = Session.commit

    def fail_deep_parse_commit(session):
        raise RuntimeError("forced deep-parse pre-commit failure")

    monkeypatch.setattr(Session, "commit", fail_deep_parse_commit)
    with pytest.raises(RuntimeError, match="forced deep-parse pre-commit failure"):
        client.post(f"{API}/opportunities/{opportunity_id}/deep-parse")
    monkeypatch.setattr(Session, "commit", original_commit)
    db.expire_all()
    rolled_back = db.get(Opportunity, opportunity_id)
    assert rolled_back.description == before["description"]
    assert rolled_back.source_metadata == before["source_metadata"]
    assert rolled_back.extracted_facts == before["extracted_facts"]
    assert rolled_back.ai_inference == before["ai_inference"]
    assert rolled_back.breakdown_classification == before["classification"]
    assert rolled_back.visibility_status == before["visibility"]
    assert set(db.scalars(select(BreakdownParseRun.id).where(BreakdownParseRun.breakdown_id == opportunity_id))) == before["runs"]
    assert set(db.scalars(select(BreakdownSection.id).where(BreakdownSection.breakdown_id == opportunity_id))) == before["sections"]
    assert set(db.scalars(select(BreakdownRole.id).where(BreakdownRole.breakdown_id == opportunity_id))) == before["roles"]
    assert set(db.scalars(select(CharacterProfile.id).where(CharacterProfile.breakdown_id == opportunity_id))) == before["profiles"]

    def fail_before_persistence(*_args, **_kwargs):
        raise RuntimeError("forced parser boundary failure")

    monkeypatch.setattr(BreakdownIntelligenceEngine, "run_for_opportunity", fail_before_persistence)
    with pytest.raises(RuntimeError, match="forced parser boundary failure"):
        client.post(f"{API}/opportunities/{opportunity_id}/deep-parse")
    db.expire_all()
    assert set(db.scalars(select(BreakdownParseRun.id).where(BreakdownParseRun.breakdown_id == opportunity_id))) == before["runs"]
    assert set(db.scalars(select(BreakdownSection.id).where(BreakdownSection.breakdown_id == opportunity_id))) == before["sections"]
    assert set(db.scalars(select(BreakdownRole.id).where(BreakdownRole.breakdown_id == opportunity_id))) == before["roles"]
    assert set(db.scalars(select(CharacterProfile.id).where(CharacterProfile.breakdown_id == opportunity_id))) == before["profiles"]


def test_deep_parse_visible_to_review_and_discarded_ownership(client, db, monkeypatch):
    from app.db.models import Opportunity
    from app.services.breakdown_intelligence_engine import BreakdownIntelligenceEngine

    create_actor(client)
    review = create_opportunity(client)
    review_id = review["id"]
    review_row = db.get(Opportunity, review_id)
    review_row.visibility_status = "visible"
    review_row.hidden_by_rule = None
    review_row.hidden_reason = None
    review_row.manual_review_required = False
    review_row.submission_deadline = None
    review_row.audition_deadline = None
    review_row.callback_date = None
    db.commit()

    def needs_date_review(engine, text, parse_mode="Deep Parse"):
        result = controlled_deep_parse_result(engine, text, parse_mode)
        result["details"]["role_details"]["submission_deadline"] = "deadline unknown"
        return result

    monkeypatch.setattr(BreakdownIntelligenceEngine, "parse", needs_date_review)
    response = client.post(f"{API}/opportunities/{review_id}/deep-parse")
    assert response.status_code == 200, response.text
    db.expire_all()
    review_row = db.get(Opportunity, review_id)
    assert review_row.visibility_status == "hidden"
    assert review_row.hidden_by_rule == "needs_date_review"
    assert all(item["id"] != review_id for item in client.get(f"{API}/opportunities").json())
    assert any(item["id"] == review_id for item in client.get(f"{API}/opportunities", params={"include_hidden": True}).json())

    discarded = create_opportunity(client)
    discarded_id = discarded["id"]
    discarded_row = db.get(Opportunity, discarded_id)
    discarded_row.visibility_status = "visible"
    discarded_row.hidden_by_rule = None
    discarded_row.hidden_reason = None
    discarded_row.submission_deadline = datetime(2026, 8, 20, 18, tzinfo=timezone(timedelta(hours=-4)))
    db.commit()

    def rejected_listing(engine, text, parse_mode="Deep Parse"):
        result = controlled_deep_parse_result(engine, text, parse_mode)
        result["details"]["breakdown_classification"] = "Crew Job"
        result["details"]["rejection_reason"] = "Controlled crew classification."
        return result

    monkeypatch.setattr(BreakdownIntelligenceEngine, "parse", rejected_listing)
    response = client.post(f"{API}/opportunities/{discarded_id}/deep-parse")
    assert response.status_code == 200, response.text
    db.expire_all()
    discarded_row = db.get(Opportunity, discarded_id)
    # The row retains a visible status, but the standard owner excludes it through the
    # main-classification filter; include_hidden remains the authoritative review owner.
    assert discarded_row.breakdown_classification == "Crew Job"
    assert discarded_row.rejection_reason == "Controlled crew classification."
    assert discarded_row.visibility_status == "visible"
    assert discarded_row.hidden_by_rule is None
    assert all(item["id"] != discarded_id for item in client.get(f"{API}/opportunities").json())
    assert any(
        item["id"] == discarded_id
        for item in client.get(f"{API}/opportunities", params={"include_hidden": True}).json()
    )


def test_deep_parse_preserves_an_explicitly_rejected_manual_entry(client, db, monkeypatch):
    from app.db.models import Opportunity
    from app.services.breakdown_intelligence_engine import BreakdownIntelligenceEngine

    actor = create_actor(client)
    asset = client.post(
        f"{API}/assets",
        data={
            "actor_profile_id": actor["id"],
            "asset_name": "Rejected-state Headshot",
            "asset_type": "Headshot",
            "tags": '["detective"]',
            "archetype_names": '["Authority"]',
        },
        files={"file": ("rejected-state.txt", b"contract", "text/plain")},
    )
    assert asset.status_code == 201, asset.text
    opportunity = create_opportunity(client)
    opportunity_id = opportunity["id"]

    rejected = client.post(
        f"{API}/opportunities/{opportunity_id}/reject",
        json={"rejection_reason": "Actor archived this opportunity."},
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["visibility_status"] == "discarded"
    assert rejected.json()["hidden_by_rule"] == "user_rejected"
    assert rejected.json()["status"] == "archived"

    def acting_listing(engine, text, parse_mode="Deep Parse"):
        result = controlled_deep_parse_result(engine, text, parse_mode)
        result["details"]["breakdown_classification"] = "Acting Role"
        result["details"]["rejection_reason"] = None
        return result

    monkeypatch.setattr(BreakdownIntelligenceEngine, "parse", acting_listing)
    for _attempt in range(2):
        reparsed = client.post(f"{API}/opportunities/{opportunity_id}/deep-parse")
        assert reparsed.status_code == 200, reparsed.text
        assert reparsed.json()["visibility_status"] == "discarded"
        assert reparsed.json()["hidden_by_rule"] == "user_rejected"
        assert reparsed.json()["rejection_reason"] == "Actor archived this opportunity."
        assert reparsed.json()["status"] == "archived"

        db.expire_all()
        row = db.get(Opportunity, opportunity_id)
        assert row.visibility_status == "discarded"
        assert row.hidden_by_rule == "user_rejected"
        assert row.hidden_reason == "Actor archived this opportunity."
        assert row.rejection_reason == "Actor archived this opportunity."
        assert row.status == "archived"
        assert row.source_metadata["user_rejected"] is True

        visible_ids = {item["id"] for item in client.get(f"{API}/opportunities").json()}
        hidden_ids = {
            item["id"] for item in client.get(f"{API}/automation/opportunities/hidden").json()
        }
        diagnostic_ids = {
            item["id"]
            for item in client.get(f"{API}/opportunities", params={"include_hidden": True}).json()
        }
        readiness_ids = {
            item["opportunity_id"] for item in client.get(f"{API}/intelligence/readiness/opportunities").json()
        }
        material_ids = {
            item["opportunity"]["id"]
            for item in client.get(
                f"{API}/opportunities/material-matches",
                params={"include_hidden": False, "min_score": 0},
            ).json()
        }
        command_center_ids = {
            item["id"] for item in client.get(f"{API}/command-center").json()["today_opportunities"]
        }
        assert opportunity_id not in visible_ids
        assert opportunity_id not in hidden_ids
        assert opportunity_id in diagnostic_ids
        assert opportunity_id not in readiness_ids
        assert opportunity_id not in material_ids
        assert opportunity_id not in command_center_ids
        assert client.get(f"{API}/opportunities/{opportunity_id}").json()["visibility_status"] == "discarded"


def test_rejected_deep_parse_rolls_back_without_partial_visibility_change(client, db, monkeypatch):
    from sqlalchemy.orm import Session
    from app.db.models import BreakdownParseRun, Opportunity
    from app.services.breakdown_intelligence_engine import BreakdownIntelligenceEngine

    create_actor(client)
    opportunity_id = create_opportunity(client)["id"]
    client.post(
        f"{API}/opportunities/{opportunity_id}/reject",
        json={"rejection_reason": "Keep this archived."},
    )
    before_runs = set(
        db.scalars(select(BreakdownParseRun.id).where(BreakdownParseRun.breakdown_id == opportunity_id))
    )
    monkeypatch.setattr(BreakdownIntelligenceEngine, "parse", controlled_deep_parse_result)
    original_commit = Session.commit

    def fail_commit(session):
        raise RuntimeError("forced rejected deep-parse failure")

    monkeypatch.setattr(Session, "commit", fail_commit)
    with pytest.raises(RuntimeError, match="forced rejected deep-parse failure"):
        client.post(f"{API}/opportunities/{opportunity_id}/deep-parse")
    monkeypatch.setattr(Session, "commit", original_commit)
    db.expire_all()

    row = db.get(Opportunity, opportunity_id)
    assert row.visibility_status == "discarded"
    assert row.status == "archived"
    assert row.hidden_by_rule == "user_rejected"
    assert row.rejection_reason == "Keep this archived."
    assert set(
        db.scalars(select(BreakdownParseRun.id).where(BreakdownParseRun.breakdown_id == opportunity_id))
    ) == before_runs


def test_reject_archive_visible_persistence_repeat_and_response_owners(client, db):
    from app.db.models import ManualOverrideLog, Opportunity

    actor = create_actor(client)
    opportunity = create_opportunity(client)
    opportunity_id = opportunity["id"]
    asset = client.post(
        f"{API}/assets",
        data={
            "actor_profile_id": actor["id"],
            "asset_name": "Reject Contract Headshot",
            "asset_type": "Headshot",
            "tags": '["detective"]',
            "archetype_names": '["Authority"]',
        },
        files={"file": ("reject-contract.txt", b"contract", "text/plain")},
    )
    assert asset.status_code == 201, asset.text

    unchanged_before = {
        "recommendations": client.get(f"{API}/agents/recommendations").json(),
        "journal": client.get(f"{API}/journal").json(),
        "calendar": client.get(f"{API}/operations/calendar/events").json(),
        "workflows": client.get(f"{API}/command-center/self-tapes").json(),
        "queue": client.get(f"{API}/automation/submission-queue").json(),
        "operations": client.get(f"{API}/operations/dashboard").json(),
        "intelligence": client.get(f"{API}/intelligence/dashboard").json(),
        "industry": client.get(f"{API}/intelligence/casting-patterns").json(),
        "material_performance": client.get(f"{API}/intelligence/materials/performance").json(),
        "system_capabilities": client.get(f"{API}/system/capabilities").json(),
    }
    assert opportunity_id in {
        item["id"] for item in client.get(f"{API}/command-center").json()["today_opportunities"]
    }

    first = client.post(
        f"{API}/opportunities/{opportunity_id}/reject",
        json={
            "highlighted_text_as_rejection_reason": "Not for this actor",
            "rejection_reason": "Actor archived this opportunity.",
        },
    )
    assert first.status_code == 200, first.text
    assert first.json()["visibility_status"] == "discarded"
    assert first.json()["status"] == "archived"
    assert first.json()["hidden_by_rule"] == "user_rejected"
    assert first.json()["rejection_reason"] == "Actor archived this opportunity."
    assert first.json()["highlighted_text_as_rejection_reason"] == "Not for this actor"

    db.expire_all()
    row = db.get(Opportunity, opportunity_id)
    assert row.source_metadata["user_rejected"] is True
    logs = list(
        db.scalars(
            select(ManualOverrideLog)
            .where(ManualOverrideLog.entity_type == "Opportunity")
            .where(ManualOverrideLog.entity_id == opportunity_id)
            .order_by(ManualOverrideLog.created_at)
        )
    )
    assert [log.field_name for log in logs] == [
        "visibility_status", "hidden_by_rule", "rejection_reason"
    ]

    same = client.post(
        f"{API}/opportunities/{opportunity_id}/reject",
        json={
            "highlighted_text_as_rejection_reason": "Not for this actor",
            "rejection_reason": "Actor archived this opportunity.",
        },
    )
    assert same.status_code == 200
    db.expire_all()
    assert db.scalar(
        select(func.count()).select_from(ManualOverrideLog)
        .where(ManualOverrideLog.entity_type == "Opportunity")
        .where(ManualOverrideLog.entity_id == opportunity_id)
    ) == 3

    replaced = client.post(
        f"{API}/opportunities/{opportunity_id}/reject",
        json={"rejection_reason": "Actor replaced the archive reason."},
    )
    assert replaced.status_code == 200
    assert replaced.json()["rejection_reason"] == "Actor replaced the archive reason."
    db.expire_all()
    assert db.scalar(
        select(func.count()).select_from(ManualOverrideLog)
        .where(ManualOverrideLog.entity_type == "Opportunity")
        .where(ManualOverrideLog.entity_id == opportunity_id)
    ) == 4

    assert opportunity_id not in {item["id"] for item in client.get(f"{API}/opportunities").json()}
    assert opportunity_id not in {
        item["id"] for item in client.get(f"{API}/automation/opportunities/hidden").json()
    }
    assert opportunity_id in {
        item["id"] for item in client.get(f"{API}/opportunities", params={"include_hidden": True}).json()
    }
    assert opportunity_id not in {
        item["opportunity_id"] for item in client.get(f"{API}/intelligence/readiness/opportunities").json()
    }
    assert opportunity_id not in {
        item["opportunity"]["id"]
        for item in client.get(
            f"{API}/opportunities/material-matches", params={"include_hidden": False, "min_score": 0}
        ).json()
    }
    assert opportunity_id not in {
        item["id"] for item in client.get(f"{API}/command-center").json()["today_opportunities"]
    }
    assert client.get(f"{API}/opportunities/{opportunity_id}").json()["visibility_status"] == "discarded"
    assert {
        "recommendations": client.get(f"{API}/agents/recommendations").json(),
        "journal": client.get(f"{API}/journal").json(),
        "calendar": client.get(f"{API}/operations/calendar/events").json(),
        "workflows": client.get(f"{API}/command-center/self-tapes").json(),
        "queue": client.get(f"{API}/automation/submission-queue").json(),
        "operations": client.get(f"{API}/operations/dashboard").json(),
        "intelligence": client.get(f"{API}/intelligence/dashboard").json(),
        "industry": client.get(f"{API}/intelligence/casting-patterns").json(),
        "material_performance": client.get(f"{API}/intelligence/materials/performance").json(),
        "system_capabilities": client.get(f"{API}/system/capabilities").json(),
    } == unchanged_before


def test_reject_archive_hidden_and_rollback_are_atomic(client, db, monkeypatch):
    from sqlalchemy.orm import Session
    from app.db.models import ManualOverrideLog, Opportunity

    create_actor(client)
    hidden = create_opportunity(client)
    hidden_id = hidden["id"]
    hidden_row = db.get(Opportunity, hidden_id)
    hidden_row.visibility_status = "hidden"
    hidden_row.hidden_by_rule = "needs_date_review"
    hidden_row.hidden_reason = "Confirm the deadline."
    hidden_row.manual_review_required = True
    db.commit()
    assert hidden_id in {
        item["id"] for item in client.get(f"{API}/automation/opportunities/hidden").json()
    }

    rejected = client.post(
        f"{API}/opportunities/{hidden_id}/reject",
        json={"rejection_reason": "Actor rejected the review item."},
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["visibility_status"] == "discarded"
    assert rejected.json()["hidden_by_rule"] == "user_rejected"
    assert hidden_id not in {
        item["id"] for item in client.get(f"{API}/automation/opportunities/hidden").json()
    }
    assert hidden_id not in {item["id"] for item in client.get(f"{API}/opportunities").json()}
    assert hidden_id in {
        item["id"] for item in client.get(f"{API}/opportunities", params={"include_hidden": True}).json()
    }
    assert db.scalar(
        select(func.count()).select_from(ManualOverrideLog)
        .where(ManualOverrideLog.entity_type == "Opportunity")
        .where(ManualOverrideLog.entity_id == hidden_id)
    ) == 3

    rollback = create_opportunity(client)
    rollback_id = rollback["id"]
    original_commit = Session.commit

    def fail_commit(session):
        raise RuntimeError("forced reject pre-commit failure")

    monkeypatch.setattr(Session, "commit", fail_commit)
    with pytest.raises(RuntimeError, match="forced reject pre-commit failure"):
        client.post(
            f"{API}/opportunities/{rollback_id}/reject",
            json={"rejection_reason": "This must roll back."},
        )
    monkeypatch.setattr(Session, "commit", original_commit)
    db.expire_all()
    rollback_row = db.get(Opportunity, rollback_id)
    assert rollback_row.visibility_status == "visible"
    assert rollback_row.status == "open"
    assert rollback_row.hidden_by_rule is None
    assert rollback_row.rejection_reason is None
    assert db.scalar(
        select(func.count()).select_from(ManualOverrideLog)
        .where(ManualOverrideLog.entity_type == "Opportunity")
        .where(ManualOverrideLog.entity_id == rollback_id)
    ) == 0


def test_deep_parse_preserves_duplicate_controlled_roles(client, db, monkeypatch):
    from app.db.models import BreakdownRole, CharacterProfile
    from app.services.breakdown_intelligence_engine import BreakdownIntelligenceEngine

    create_actor(client)
    opportunity_id = create_opportunity(client)["id"]

    def duplicate_roles(engine, text, parse_mode="Deep Parse"):
        result = controlled_deep_parse_result(engine, text, parse_mode)
        result["details"]["role_details"]["available_roles"].append(
            dict(result["details"]["role_details"]["available_roles"][0])
        )
        return result

    monkeypatch.setattr(BreakdownIntelligenceEngine, "parse", duplicate_roles)
    previous_profile_ids = set()
    for _attempt in range(2):
        response = client.post(f"{API}/opportunities/{opportunity_id}/deep-parse")
        assert response.status_code == 200, response.text
        db.expire_all()
        roles = list(
            db.scalars(
                select(BreakdownRole)
                .where(BreakdownRole.breakdown_id == opportunity_id)
                .order_by(BreakdownRole.created_at)
            )
        )
        assert [role.role_name for role in roles] == ["New Detective", "New Captain", "New Detective"]
        profiles = list(
            db.scalars(select(CharacterProfile).where(CharacterProfile.breakdown_id == opportunity_id))
        )
        assert len(profiles) == 3
        assert len({profile.breakdown_role_id for profile in profiles}) == 3
        assert len({profile.id for profile in profiles}) == 3
        assert not previous_profile_ids.intersection({profile.id for profile in profiles})
        previous_profile_ids = {profile.id for profile in profiles}


def test_character_profile_persists_and_matches_fresh_authoritative_reads(client, db, monkeypatch):
    from sqlalchemy.orm import selectinload
    from app.core.database import SessionLocal
    from app.db.models import BreakdownRole, CharacterProfile, Opportunity
    from app.services.breakdown_intelligence_engine import BreakdownIntelligenceEngine

    create_actor(client)
    opportunity_id = create_opportunity(client)["id"]
    baseline_opportunity = db.get(Opportunity, opportunity_id)
    baseline_role = BreakdownRole(
        breakdown=baseline_opportunity,
        role_name="Obsolete Profile Role",
        fit_status="Possible Fit",
        extracted_facts={},
        ai_inference={},
    )
    db.add(baseline_role)
    db.flush()
    baseline_profile = CharacterProfile(
        breakdown_id=baseline_role.breakdown_id,
        breakdown_role_id=baseline_role.id,
        role_name=baseline_role.role_name,
        primary_archetypes=["Obsolete Archetype"],
    )
    db.add(baseline_profile)
    db.commit()
    baseline_profile_id = baseline_profile.id

    monkeypatch.setattr(BreakdownIntelligenceEngine, "parse", controlled_deep_parse_result)
    response = client.post(f"{API}/opportunities/{opportunity_id}/deep-parse")
    assert response.status_code == 200, response.text

    immediate_roles = response.json()["breakdown_roles"]
    assert [role["role_name"] for role in immediate_roles] == ["New Detective", "New Captain"]
    assert all(role["character_profile"] is not None for role in immediate_roles)
    assert immediate_roles[0]["character_description"] == "A precise authority figure with teleprompter skills."
    assert immediate_roles[0]["ai_inference"]["compatibility"]["value"]
    detective_profile = immediate_roles[0]["character_profile"]
    assert "Authority Figure" in detective_profile["primary_archetypes"]
    assert detective_profile["archetype_confidence_scores"]
    assert detective_profile["ai_summary"]

    with SessionLocal() as fresh_db:
        fresh = fresh_db.scalar(
            select(Opportunity)
            .where(Opportunity.id == opportunity_id)
            .options(selectinload(Opportunity.breakdown_roles).selectinload(BreakdownRole.character_profile))
        )
        assert fresh is not None
        assert [role.role_name for role in fresh.breakdown_roles] == ["New Detective", "New Captain"]
        assert all(role.character_profile is not None for role in fresh.breakdown_roles)
        assert fresh_db.get(CharacterProfile, baseline_profile_id) is None
        assert fresh_db.scalar(
            select(func.count()).select_from(CharacterProfile).where(CharacterProfile.breakdown_id == opportunity_id)
        ) == 2

    fresh_response = client.get(f"{API}/opportunities/{opportunity_id}")
    assert fresh_response.status_code == 200, fresh_response.text
    fresh_roles = fresh_response.json()["breakdown_roles"]
    assert [role["role_name"] for role in fresh_roles] == ["New Detective", "New Captain"]
    assert [role["character_profile"] for role in fresh_roles] == [role["character_profile"] for role in immediate_roles]

    readiness = client.get(f"{API}/intelligence/readiness/opportunities").json()
    readiness_row = next(row for row in readiness if row["opportunity_id"] == opportunity_id)
    assert "Authority Figure" in readiness_row["character_archetypes"]
    assert readiness_row["character_parsing_status"] == "Ready"
    recommendation = client.post(f"{API}/opportunities/{opportunity_id}/recommend")
    assert recommendation.status_code == 200, recommendation.text
    assert "Authority Figure" in recommendation.json()["archetype_explanation"]

    first_profile_ids = {role["character_profile"]["id"] for role in immediate_roles}
    retry = client.post(f"{API}/opportunities/{opportunity_id}/deep-parse")
    assert retry.status_code == 200, retry.text
    retry_profiles = [role["character_profile"] for role in retry.json()["breakdown_roles"]]
    assert all(profile is not None for profile in retry_profiles)
    assert not first_profile_ids.intersection({profile["id"] for profile in retry_profiles})
    assert db.scalar(
        select(func.count()).select_from(CharacterProfile).where(CharacterProfile.breakdown_id == opportunity_id)
    ) == 2

def test_profile_representation_and_material_contracts(client):
    actor = create_actor(client)
    assert client.get(f"{API}/actor-profile").json()["id"] == actor["id"]
    invalid = client.put(f"{API}/actor-profile", json={"name": "Incomplete"})
    assert invalid.status_code == 422

    representation = client.post(
        f"{API}/representation",
        json={
            "actor_profile_id": actor["id"],
            "agency_name": "Contract Artists",
            "agent_name": None,
            "representation_type": "Theatrical",
            "market": ["New York"],
            "start_date": "2026-01-15",
        },
    )
    assert representation.status_code == 201, representation.text
    rep = representation.json()
    assert rep["start_date"] == "2026-01-15" and rep["agent_name"] is None
    updated = client.patch(
        f"{API}/representation/{rep['id']}", json={"agent_name": "Jordan Agent"}
    )
    assert updated.json()["agent_name"] == "Jordan Agent"
    assert client.get(f"{API}/representation").json()[0]["agency_name"] == "Contract Artists"

    asset_response = client.post(
        f"{API}/assets",
        data={
            "actor_profile_id": actor["id"],
            "asset_name": "Contract Headshot",
            "asset_type": "Headshot",
            "tags": '["theatrical"]',
            "archetype_names": '["Authority"]',
        },
        files={"file": ("pixel.txt", b"contract", "text/plain")},
    )
    assert asset_response.status_code == 201, asset_response.text
    asset = asset_response.json()
    assert {"id", "asset_name", "asset_type", "tags", "archetype_names", "local_file_path"} <= asset.keys()
    assert client.patch(f"{API}/assets/{asset['id']}", json={"asset_name": "Updated Headshot"}).json()["asset_name"] == "Updated Headshot"
    assert client.delete(f"{API}/assets/{asset['id']}").status_code == 204
    assert client.get(f"{API}/assets").json() == []
    assert client.delete(f"{API}/representation/{rep['id']}").status_code == 204


def test_audition_calendar_and_journal_contracts(client):
    actor = create_actor(client)
    opportunity = create_opportunity(client)
    visible = client.get(f"{API}/opportunities").json()
    assert any(item["id"] == opportunity["id"] for item in visible)
    submission_response = client.post(
        f"{API}/submissions",
        json={
            "actor_profile_id": actor["id"],
            "opportunity_id": opportunity["id"],
            "current_status": "Submitted",
            "submitted_at": "2026-03-07T18:00:00-05:00",
        },
    )
    assert submission_response.status_code == 201, submission_response.text
    submission = submission_response.json()
    assert submission["opportunity_id"] == opportunity["id"]
    assert submission["opportunity"]["project"] == "Spring Forward"

    workflow = client.post(
        f"{API}/command-center/self-tapes",
        json={
            "opportunity_id": opportunity["id"],
            "submission_id": submission["id"],
            "status": "Not Started",
            "tape_due_at": "2026-03-08T01:30:00-05:00",
        },
    )
    assert workflow.status_code == 201, workflow.text
    assert workflow.json()["submission_id"] == submission["id"]

    callback = client.post(
        f"{API}/intelligence/callback-events",
        json={
            "submission_id": submission["id"],
            "opportunity_id": opportunity["id"],
            "event_name": "Producer Callback",
            "event_datetime": "2026-03-09",
            "is_virtual": True,
        },
    )
    assert callback.status_code == 201, callback.text
    assert callback.json()["event_datetime"] == "2026-03-09"

    performance = client.post(
        f"{API}/intelligence/audition-journal",
        json={
            "submission_id": submission["id"],
            "opportunity_id": opportunity["id"],
            "date": "2026-03-08",
            "performance_notes": "Kept the choices specific.",
        },
    )
    assert performance.status_code == 201, performance.text
    performance_entries = client.get(f"{API}/intelligence/audition-journal").json()
    assert any(item["id"] == performance.json()["id"] for item in performance_entries)
    actor_journal = client.get(f"{API}/journal").json()
    assert all(item.get("performance_notes") is None for item in actor_journal)

    outcome = client.post(
        f"{API}/submissions/{submission['id']}/status-history",
        json={"status": "Booked", "occurred_at": "2026-03-10T12:00:00-04:00"},
    )
    assert outcome.status_code == 200, outcome.text
    assert outcome.json()["current_status"] == "Booked"
    actor_journal = client.get(f"{API}/journal").json()
    assert any(item["event_type"] == "Booking Recorded" and item["linked_audition_id"] == submission["id"] for item in actor_journal)
    intelligence = client.get(f"{API}/intelligence/dashboard")
    assert intelligence.status_code == 200

    calendar = client.get(f"{API}/operations/calendar/events")
    assert calendar.status_code == 200
    events = calendar.json()
    assert events
    deadline = next(item for item in events if item["opportunity_id"] == opportunity["id"])
    assert datetime.fromisoformat(
        deadline["start_datetime"].replace("Z", "+00:00")
    ) == datetime.fromisoformat("2026-03-08T01:30:00-05:00")

    changed = client.patch(
        f"{API}/operations/calendar/events/{deadline['id']}",
        json={"start_datetime": "2026-03-08T03:30:00-04:00"},
    )
    assert changed.status_code == 200
    assert datetime.fromisoformat(
        changed.json()["start_datetime"].replace("Z", "+00:00")
    ) == datetime.fromisoformat("2026-03-08T03:30:00-04:00")

def test_opportunity_delete_protects_linked_submission_history(client):
    actor = create_actor(client)
    opportunity = create_opportunity(client)
    submissions = []
    for submitted_at in ("2026-03-07T18:00:00-05:00", "2026-03-07T19:00:00-05:00"):
        response = client.post(
            f"{API}/submissions",
            json={
                "actor_profile_id": actor["id"],
                "opportunity_id": opportunity["id"],
                "current_status": "Submitted",
                "submitted_at": submitted_at,
            },
        )
        assert response.status_code == 201, response.text
        submissions.append(response.json())

    workflow = client.post(
        f"{API}/command-center/self-tapes",
        json={
            "opportunity_id": opportunity["id"],
            "submission_id": submissions[0]["id"],
            "status": "Not Started",
        },
    )
    assert workflow.status_code == 201, workflow.text
    recommendation = client.post(f"{API}/agents/opportunities/{opportunity['id']}/recommend")
    assert recommendation.status_code == 200, recommendation.text
    queue = client.post(f"{API}/automation/submission-queue/from-recommendation/{recommendation.json()['id']}")
    assert queue.status_code == 200, queue.text

    before = {
        "submissions": [
            (item["id"], item["opportunity_id"], item["current_status"], item["submitted_at"])
            for item in client.get(f"{API}/submissions").json()
        ],
        "workflows": client.get(f"{API}/command-center/self-tapes").json(),
        "recommendations": client.get(f"{API}/agents/recommendations").json(),
        "queue": client.get(f"{API}/automation/submission-queue").json(),
        "journal": client.get(f"{API}/journal").json(),
        "calendar": client.get(f"{API}/operations/calendar/events").json(),
    }
    expected_detail = {
        "code": "opportunity_has_submissions",
        "message": "This opportunity cannot be permanently deleted because it has linked submissions. Reject or archive it instead.",
    }

    for _ in range(2):
        deleted = client.delete(f"{API}/opportunities/{opportunity['id']}")
        assert deleted.status_code == 409, deleted.text
        assert deleted.json() == {"detail": expected_detail}

    assert any(item["id"] == opportunity["id"] for item in client.get(f"{API}/opportunities").json())
    retained_submissions = [
        (item["id"], item["opportunity_id"], item["current_status"], item["submitted_at"])
        for item in client.get(f"{API}/submissions").json()
    ]
    assert retained_submissions == before["submissions"]
    assert client.get(f"{API}/command-center/self-tapes").json() == before["workflows"]
    assert client.get(f"{API}/agents/recommendations").json() == before["recommendations"]
    assert client.get(f"{API}/automation/submission-queue").json() == before["queue"]
    assert client.get(f"{API}/journal").json() == before["journal"]
    assert client.get(f"{API}/operations/calendar/events").json() == before["calendar"]

    rejected = client.post(
        f"{API}/opportunities/{opportunity['id']}/reject",
        json={"rejection_reason": "Archived without deleting audition history"},
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "archived"


def test_opportunity_delete_protects_one_linked_submission(client):
    actor = create_actor(client)
    opportunity = create_opportunity(client)
    submission = client.post(
        f"{API}/submissions",
        json={
            "actor_profile_id": actor["id"],
            "opportunity_id": opportunity["id"],
            "current_status": "Submitted",
        },
    )
    assert submission.status_code == 201, submission.text

    deleted = client.delete(f"{API}/opportunities/{opportunity['id']}")
    assert deleted.status_code == 409
    assert deleted.json()["detail"]["code"] == "opportunity_has_submissions"
    assert [item["id"] for item in client.get(f"{API}/submissions").json()] == [submission.json()["id"]]


def test_reusable_tapes_analytics_and_aggregate_contracts(client):
    create_actor(client)
    tape = client.post(
        f"{API}/intelligence/self-tapes",
        json={
            "title": "Reusable Authority Tape",
            "role_type": "Guest Star",
            "archetypes": ["Authority"],
            "file_path": "/contract-fixtures/reusable.mp4",
            "date_created": "2026-03-01",
        },
    )
    assert tape.status_code == 201, tape.text
    tape_id = tape.json()["id"]
    before = client.get(f"{API}/intelligence/self-tapes/analytics").json()
    assert {"by_archetype", "by_outcome", "best_performing_tapes", "underused_tapes"} <= before.keys()
    updated = client.patch(f"{API}/intelligence/self-tapes/{tape_id}", json={"outcome": "Callback"})
    assert updated.status_code == 200
    after = client.get(f"{API}/intelligence/self-tapes/analytics").json()
    assert after["by_outcome"] != before["by_outcome"]
    assert client.get(f"{API}/command-center/self-tapes").json() == []
    assert client.delete(f"{API}/intelligence/self-tapes/{tape_id}").status_code == 204
    assert client.get(f"{API}/intelligence/self-tapes").json() == []

    capabilities = client.get(f"{API}/system/capabilities").json()
    assert {"flags", "states", "integrations", "labels"} <= capabilities.keys()
    command = client.get(f"{API}/command-center").json()
    assert {"today_opportunities", "queued_submissions", "upcoming_deadlines", "career_tasks"} <= command.keys()
    intelligence = client.get(f"{API}/intelligence/dashboard").json()
    assert {"archetype_performance", "casting_office_analytics", "role_similarity"} <= intelligence.keys()
    operations = client.get(f"{API}/operations/dashboard").json()
    assert {"alerts", "upcoming_events", "cost_dashboard", "freshness_warnings"} <= operations.keys()


def test_breakdown_mutation_side_effect_contracts(client):
    create_actor(client)
    opportunity = create_opportunity(client)
    opportunity_id = opportunity["id"]

    initial_workflows = client.get(f"{API}/command-center/self-tapes").json()
    assert initial_workflows == []
    initial_journal = client.get(f"{API}/journal").json()
    initial_calendar = client.get(f"{API}/operations/calendar/events").json()

    updated = client.patch(
        f"{API}/opportunities/{opportunity_id}",
        json={"audition_type": "Self-Tape", "audition_deadline": "2026-03-12T18:00:00-04:00"},
    )
    assert updated.status_code == 200, updated.text
    workflows = client.get(f"{API}/command-center/self-tapes").json()
    assert len(workflows) == 1
    workflow_id = workflows[0]["id"]

    assert datetime.fromisoformat(
        workflows[0]["tape_due_at"].replace("Z", "+00:00")
    ) == datetime.fromisoformat("2026-03-12T18:00:00-04:00")
    assert client.get(f"{API}/journal").json() == initial_journal
    assert client.get(f"{API}/operations/calendar/events").json() == initial_calendar

    harmless = client.patch(f"{API}/opportunities/{opportunity_id}", json={"priority": "High"})
    assert harmless.status_code == 200
    parsed_workflows = client.get(f"{API}/command-center/self-tapes").json()
    assert len(parsed_workflows) == 1 and parsed_workflows[0]["id"] == workflow_id

    parsed = client.post(
        f"{API}/opportunities/{opportunity_id}/parse-breakdown-text",
        json={"raw_text": "PROJECT: Spring Forward\nROLE: Detective\nSelf-tape due March 15, 2026 at 6:00 PM ET."},
    )
    assert parsed.status_code == 200, parsed.text
    assert parsed.json()["description"].startswith("PROJECT: Spring Forward")
    assert parsed.json()["breakdown_parse_runs"]
    assert all(role["character_profile"] is not None for role in parsed.json()["breakdown_roles"])
    assert len(client.get(f"{API}/command-center/self-tapes").json()) == 1
    assert client.get(f"{API}/journal").json() == initial_journal
    assert client.get(f"{API}/operations/calendar/events").json() == initial_calendar

    recommendation = client.post(f"{API}/agents/opportunities/{opportunity_id}/recommend")
    assert recommendation.status_code == 200, recommendation.text
    queued = client.post(f"{API}/automation/submission-queue/from-recommendation/{recommendation.json()['id']}")
    assert queued.status_code == 200, queued.text
    note = client.post(
        f"{API}/intelligence/audition-journal",
        json={"opportunity_id": opportunity_id, "date": "2026-03-08", "performance_notes": "Historical note"},
    )
    assert note.status_code == 201, note.text
    callback = client.post(
        f"{API}/intelligence/callback-events",
        json={"opportunity_id": opportunity_id, "event_name": "Linked callback", "event_datetime": "2026-03-09"},
    )
    assert callback.status_code == 201, callback.text
    reusable = client.post(
        f"{API}/intelligence/self-tapes",
        json={"title": "Linked reusable tape", "archetypes": [], "file_path": "/contract/linked.mp4", "linked_opportunity_id": opportunity_id, "date_created": "2026-03-08"},
    )
    assert reusable.status_code == 201, reusable.text

    assert client.delete(f"{API}/opportunities/{opportunity_id}").status_code == 204
    assert client.get(f"{API}/submissions").json() == []
    assert client.get(f"{API}/command-center/self-tapes").json() == []
    assert client.get(f"{API}/automation/submission-queue").json() == []
    assert client.get(f"{API}/agents/recommendations").json() == []
    assert client.get(f"{API}/intelligence/callback-events").json() == []
    retained_note = client.get(f"{API}/intelligence/audition-journal").json()
    assert len(retained_note) == 1
    assert retained_note[0]["opportunity_id"] is None and retained_note[0]["submission_id"] is None
    retained_journal = client.get(f"{API}/journal").json()
    assert retained_journal and all(item["linked_breakdown_id"] is None for item in retained_journal)
    retained_calendar = client.get(f"{API}/operations/calendar/events").json()
    assert retained_calendar and all(item["opportunity_id"] is None for item in retained_calendar)
    retained_reusable = client.get(f"{API}/intelligence/self-tapes").json()
    assert len(retained_reusable) == 1
    assert retained_reusable[0]["linked_opportunity_id"] is None and retained_reusable[0]["linked_submission_id"] is None


def test_normalized_openapi_contract(client):
    document = client.get("/openapi.json").json()
    required = {
        "/api/v1/actor-profile": {"get", "put", "patch"},
        "/api/v1/representation": {"get", "post"},
        "/api/v1/assets": {"get", "post"},
        "/api/v1/opportunities": {"get", "post"},
        "/api/v1/submissions": {"get", "post"},
        "/api/v1/command-center/self-tapes": {"get", "post"},
        "/api/v1/intelligence/callback-events": {"get", "post"},
        "/api/v1/intelligence/audition-journal": {"get", "post"},
        "/api/v1/intelligence/self-tapes": {"get", "post"},
        "/api/v1/operations/calendar/events": {"get", "post"},
        "/api/v1/system/capabilities": {"get"},
    }
    for path, methods in required.items():
        assert path in document["paths"]
        assert methods <= document["paths"][path].keys()
    actor_required = document["components"]["schemas"]["ActorProfileCreate"]["required"]
    assert {"name", "sag_status", "union_status", "current_location", "playable_age_min", "playable_age_max"} <= set(actor_required)


def test_destructive_guard_and_external_network_guard():
    with pytest.raises(RuntimeError, match="must contain 'test'"):
        assert_safe_test_database("postgresql+psycopg://localhost/casting_intelligence", "true")
    with pytest.raises(RuntimeError, match="ALLOW_TEST_DATABASE_RESET"):
        assert_safe_test_database("postgresql+psycopg://localhost/contract_test", None)
    with pytest.raises(RuntimeError, match="external network disabled"):
        socket.create_connection(("203.0.113.1", 443), timeout=0.01)
