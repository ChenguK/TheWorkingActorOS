from __future__ import annotations

from unittest.mock import MagicMock
from uuid import UUID

from app.db.models import CastingGoal, WatchList
from app.services.workflow_connector_service import WorkflowConnectorService


ACTOR_A = UUID("10000000-0000-0000-0000-00000000000a")


def goal(actor_id: UUID | None = ACTOR_A) -> CastingGoal:
    return CastingGoal(
        actor_profile_id=actor_id,
        title="Build Guest-Star Momentum",
        goal_type="Career Growth",
        target_archetypes=["Investigator"],
        target_role_types=["Guest Star"],
        target_project_types=["Television"],
        target_markets=["Atlanta"],
        target_casting_offices=[],
        priority="High",
        status="Active",
    )


def watch_list(actor_id: UUID | None = ACTOR_A) -> WatchList:
    return WatchList(
        actor_profile_id=actor_id,
        title="Casting Goal: Build Guest-Star Momentum",
        category="Old category",
        terms=["Old term"],
        priority="Low",
        enabled=False,
        notes="Old notes",
    )


def test_no_existing_same_title_creates_actor_owned_list_without_commit() -> None:
    db = MagicMock()
    db.scalars.return_value.first.return_value = None

    WorkflowConnectorService(db).after_casting_goal_saved(goal())

    created = db.add.call_args.args[0]
    assert created.actor_profile_id == ACTOR_A
    assert created.title == "Casting Goal: Build Guest-Star Momentum"
    assert created.category == "Casting Goals"
    assert created.terms == [
        "Build Guest-Star Momentum",
        "Career Growth",
        "Investigator",
        "Guest Star",
        "Television",
        "Atlanta",
    ]
    assert created.priority == "High"
    assert created.enabled is True
    assert created.notes == "Automatically suggested from an active Casting Goal."
    db.commit.assert_not_called()
    db.flush.assert_not_called()


def test_same_actor_same_title_reuses_and_updates_existing_list() -> None:
    existing = watch_list()
    db = MagicMock()
    db.scalars.return_value.first.return_value = existing

    connector = WorkflowConnectorService(db)
    connector.after_casting_goal_saved(goal())
    connector.after_casting_goal_saved(goal())

    assert existing.actor_profile_id == ACTOR_A
    assert existing.category == "Casting Goals"
    assert existing.terms[-1] == "Atlanta"
    assert existing.priority == "High"
    assert existing.enabled is True
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_null_owner_goal_preserves_legacy_null_to_null_derivation() -> None:
    existing = watch_list(None)
    db = MagicMock()
    db.scalars.return_value.first.return_value = existing

    WorkflowConnectorService(db).after_casting_goal_saved(goal(None))

    assert existing.actor_profile_id is None
    assert existing.category == "Casting Goals"
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_inactive_goal_creates_nothing() -> None:
    inactive = goal()
    inactive.status = "Completed"
    db = MagicMock()

    WorkflowConnectorService(db).after_casting_goal_saved(inactive)

    db.scalars.assert_not_called()
    db.add.assert_not_called()
