from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.db.models import ActorProfile, CastingGoal, Opportunity, WatchList
from app.services.watch_list_service import WatchListService
from app.services.workflow_connector_service import WorkflowConnectorService


pytestmark = pytest.mark.contract_smoke


def actor(name: str) -> ActorProfile:
    return ActorProfile(
        name=name,
        sag_status="Unknown",
        union_status="Unknown",
        current_location="Atlanta, GA",
        playable_age_min=25,
        playable_age_max=45,
    )


def goal(owner: ActorProfile) -> CastingGoal:
    return CastingGoal(
        actor_profile_id=owner.id,
        title="Shared Goal Title",
        goal_type="Career Growth",
        target_archetypes=["Investigator"],
        target_role_types=["Guest Star"],
        target_project_types=["Television"],
        target_markets=["Atlanta"],
        target_casting_offices=[],
        priority="High",
        status="Active",
    )


def test_goal_watch_lists_are_actor_scoped_idempotent_and_refresh_compatible(db) -> None:
    actor_a = actor("Fictional Actor A")
    actor_b = actor("Fictional Actor B")
    db.add_all([actor_a, actor_b])
    db.flush()
    goal_a = goal(actor_a)
    goal_b = goal(actor_b)
    null_owner = WatchList(
        actor_profile_id=None,
        title="Casting Goal: Shared Goal Title",
        category="Unowned",
        terms=["untouched"],
        priority="Low",
        enabled=True,
        notes="Do not adopt",
    )
    opportunity = Opportunity(
        role="Investigator",
        project="Fictional Series",
        union="SAG-AFTRA",
        location="Atlanta, GA",
        description="A fictional television Guest Star casting notice.",
        is_demo_data=False,
    )
    db.add_all([goal_a, goal_b, null_owner, opportunity])
    db.flush()
    connector = WorkflowConnectorService(db)

    connector.after_casting_goal_saved(goal_a)
    db.flush()
    connector.after_casting_goal_saved(goal_a)
    db.flush()
    connector.after_casting_goal_saved(goal_b)
    db.flush()
    WatchListService(db).refresh_all()

    rows = list(
        db.scalars(
            select(WatchList)
            .where(WatchList.title == "Casting Goal: Shared Goal Title")
            .order_by(WatchList.actor_profile_id.nulls_first())
        )
    )
    assert len(rows) == 3
    assert {row.actor_profile_id for row in rows} == {None, actor_a.id, actor_b.id}
    assert null_owner.actor_profile_id is None
    assert null_owner.category == "Unowned"
    assert null_owner.terms == ["untouched"]
    assert (
        db.scalar(
            select(func.count())
            .select_from(WatchList)
            .where(WatchList.actor_profile_id == actor_a.id)
        )
        == 1
    )
    assert (
        db.scalar(
            select(func.count())
            .select_from(WatchList)
            .where(WatchList.actor_profile_id == actor_b.id)
        )
        == 1
    )
    assert opportunity.watchlist_match_count == 2
    assert len(opportunity.watchlist_match_names) == 2
    assert "Casting Goal: Shared Goal Title" in opportunity.watchlist_notification


def test_actor_save_never_mutates_other_actor_same_title(db) -> None:
    actor_a = actor("Fictional Actor A")
    actor_b = actor("Fictional Actor B")
    db.add_all([actor_a, actor_b])
    db.flush()
    other = WatchList(
        actor_profile_id=actor_b.id,
        title="Casting Goal: Shared Goal Title",
        category="Actor B category",
        terms=["Actor B term"],
        priority="Low",
        enabled=False,
        notes="Actor B notes",
    )
    db.add(other)
    db.flush()

    WorkflowConnectorService(db).after_casting_goal_saved(goal(actor_a))
    db.flush()

    assert other.actor_profile_id == actor_b.id
    assert other.category == "Actor B category"
    assert other.terms == ["Actor B term"]
    assert other.priority == "Low"
    assert other.enabled is False
    assert other.notes == "Actor B notes"
    assert db.scalar(select(func.count()).select_from(WatchList)) == 2
