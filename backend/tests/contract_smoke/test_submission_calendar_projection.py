"""Characterize the current Auditions submission-to-Calendar contract.

Observed frontend request graphs:

* unchecked "Add to calendar": POST submission, PATCH/POST self-tape when enabled,
  then POST audition journal; no Calendar POST.
* checked (the default): the same graph plus POST Calendar before POST audition
  journal.

WorkflowConnectorService is the sole automatic submission Calendar projector;
ActorWorkEventService still records the actor-work journal entry. The legacy
checked frontend Calendar POST bypasses the connector guard and creates a second
row until the frontend half of the correction removes that request. Repeating
POST /submissions remains intentionally non-idempotent and is outside this fix.
Strict Playwright records frontend requests, while PostgreSQL row assertions
live here.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

import pytest
from sqlalchemy import select


pytestmark = pytest.mark.contract_smoke
API = "/api/v1"


def create_actor(client) -> dict:
    response = client.put(
        f"{API}/actor-profile",
        json={
            "name": "Calendar Contract Actor",
            "sag_status": "SAG-AFTRA",
            "union_status": "Union",
            "current_location": "New York, NY",
            "playable_age_min": 28,
            "playable_age_max": 38,
            "skills": [],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def create_opportunity(client, **date_fields) -> dict:
    response = client.post(
        f"{API}/opportunities",
        json={
            "role": "Calendar Detective",
            "project": "Ownership Contract",
            "union": "SAG-AFTRA",
            "location": "New York, NY",
            "description": "Self-tape contract characterization.",
            "project_type": "Television",
            "role_type": "Guest Star",
            "audition_type": "Self-Tape",
            "audition_location": "Remote",
            "role_details": {
                "preparation_instructions": "Prepare scene two.",
                "submission_instructions": "Upload through the casting portal.",
                "self_tape_submission_link": "https://casting.example.invalid/upload",
            },
            **date_fields,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def submit_like_frontend(client, actor: dict, opportunity: dict) -> dict:
    response = client.post(
        f"{API}/submissions",
        json={
            "actor_profile_id": actor["id"],
            "opportunity_id": opportunity["id"],
            "asset_ids": [],
            "current_status": "Requested",
            "notes": "Prepare scene two.",
            "submission_fee": 0,
            "media_fee": 0,
            "travel_cost": 0,
            "housing_cost": 0,
            "parking_cost": 0,
            "other_cost": 0,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def finish_frontend_linked_records(
    client,
    submission: dict,
    opportunity: dict,
    *,
    create_calendar: bool,
) -> None:
    workflows = [
        item
        for item in client.get(f"{API}/command-center/self-tapes").json()
        if item["opportunity_id"] == opportunity["id"] and item["submission_id"] is None
    ]
    assert len(workflows) == 1
    tape_due_at = "2026-08-10T18:00:00"
    workflow = client.patch(
        f"{API}/command-center/self-tapes/{workflows[0]['id']}",
        json={
            "opportunity_id": opportunity["id"],
            "submission_id": submission["id"],
            "status": workflows[0]["status"],
            "tape_due_at": tape_due_at,
            "upload_link": "https://casting.example.invalid/upload",
            "slate_requirements": "Prepare scene two.",
            "wardrobe_notes": None,
        },
    )
    assert workflow.status_code == 200, workflow.text

    if create_calendar:
        calendar = client.post(
            f"{API}/operations/calendar/events",
            json={
                "title": "Calendar Detective · Ownership Contract",
                "event_type": "Self-Tape Due",
                "opportunity_id": opportunity["id"],
                "submission_id": submission["id"],
                "start_datetime": tape_due_at,
                "location": "Remote",
                "is_virtual": False,
                "notes": "Prepare scene two.",
            },
        )
        assert calendar.status_code == 201, calendar.text

    journal = client.post(
        f"{API}/intelligence/audition-journal",
        json={
            "submission_id": submission["id"],
            "opportunity_id": opportunity["id"],
            "date": date.today().isoformat(),
            "preparation_notes": "Prepare scene two.",
            "casting_notes": "Upload through the casting portal.",
            "follow_up_notes": "https://casting.example.invalid/upload",
        },
    )
    assert journal.status_code == 201, journal.text


def calendar_rows(db, opportunity_id, submission_id=None):
    from app.db.models import AuditionCalendarEvent

    statement = (
        select(AuditionCalendarEvent)
        .where(AuditionCalendarEvent.opportunity_id == opportunity_id)
        .order_by(AuditionCalendarEvent.start_datetime, AuditionCalendarEvent.created_at)
    )
    if submission_id is not None:
        statement = statement.where(AuditionCalendarEvent.submission_id == submission_id)
    return list(db.scalars(statement))


def journal_rows(db, submission_id):
    from app.db.models import AuditionJournalEntry

    return list(
        db.scalars(
            select(AuditionJournalEntry)
            .where(AuditionJournalEntry.submission_id == submission_id)
            .order_by(AuditionJournalEntry.created_at)
        )
    )


def wall_time(value: datetime) -> datetime:
    return value.replace(tzinfo=None)


def test_unchecked_frontend_flow_gets_one_backend_projection_per_semantic_milestone(client, db):
    from app.db.models import ActorJournalEntry

    actor = create_actor(client)
    opportunity = create_opportunity(
        client,
        submission_deadline="2026-08-09T18:00:00",
        audition_deadline="2026-08-10T18:00:00",
        callback_date="2026-08-12T14:00:00",
    )
    submission = submit_like_frontend(client, actor, opportunity)
    finish_frontend_linked_records(
        client,
        submission,
        opportunity,
        create_calendar=False,
    )

    linked_calendar = calendar_rows(db, opportunity["id"], submission["id"])
    assert [
        (row.event_type, row.title, wall_time(row.start_datetime), row.submission_id)
        for row in linked_calendar
    ] == [
        (
            "Submission Due",
            "Submission Due: Calendar Detective · Ownership Contract",
            datetime.fromisoformat("2026-08-09T18:00:00"),
            UUID(submission["id"]),
        ),
        (
            "Self-Tape Due",
            "Self-Tape Due: Calendar Detective · Ownership Contract",
            datetime.fromisoformat("2026-08-10T18:00:00"),
            UUID(submission["id"]),
        ),
        (
            "In-Person Callback",
            "In-Person Callback: Calendar Detective · Ownership Contract",
            datetime.fromisoformat("2026-08-12T14:00:00"),
            UUID(submission["id"]),
        ),
    ]
    assert all(row.opportunity_id == UUID(opportunity["id"]) for row in linked_calendar)

    # Opportunity creation projected its audition and callback dates without a
    # submission link; those rows intentionally coexist with three
    # submission-linked connector projections.
    opportunity_calendar = calendar_rows(db, opportunity["id"])
    assert len(opportunity_calendar) == 5
    assert sum(row.submission_id is None for row in opportunity_calendar) == 2

    # The connector creates one audition journal row; the default frontend POST
    # creates a second row with the same links but user-entered notes.
    linked_journal = journal_rows(db, submission["id"])
    assert len(linked_journal) == 2
    assert all(row.opportunity_id == UUID(opportunity["id"]) for row in linked_journal)
    assert linked_journal[0].preparation_notes == (
        "Prepare scene two.\nUpload through the casting portal."
    )
    assert linked_journal[1].casting_notes == "Upload through the casting portal."

    actor_work = list(
        db.scalars(
            select(ActorJournalEntry).where(
                ActorJournalEntry.linked_audition_id == submission["id"]
            )
        )
    )
    assert [(row.event_type, row.linked_breakdown_id) for row in actor_work] == [
        ("Submitted to Role", UUID(opportunity["id"]))
    ]


def test_legacy_checked_frontend_flow_adds_one_row_beyond_backend_projection(client, db):
    actor = create_actor(client)
    opportunity = create_opportunity(
        client,
        audition_deadline="2026-08-10T18:00:00",
    )
    submission = submit_like_frontend(client, actor, opportunity)
    finish_frontend_linked_records(
        client,
        submission,
        opportunity,
        create_calendar=True,
    )

    linked_calendar = calendar_rows(db, opportunity["id"], submission["id"])
    assert len(linked_calendar) == 2
    assert {
        (
            row.event_type,
            wall_time(row.start_datetime),
            row.opportunity_id,
            row.submission_id,
        )
        for row in linked_calendar
    } == {
        (
            "Self-Tape Due",
            datetime.fromisoformat("2026-08-10T18:00:00"),
            UUID(opportunity["id"]),
            UUID(submission["id"]),
        )
    }
    assert {row.title for row in linked_calendar} == {
        "Self-Tape Due: Calendar Detective · Ownership Contract",
        "Calendar Detective · Ownership Contract",
    }
    assert {row.location for row in linked_calendar} == {"Remote"}
    assert {row.is_virtual for row in linked_calendar} == {False}

    # No database uniqueness or OperationsService guard prevents the direct POST.
    assert len(journal_rows(db, submission["id"])) == 2


def test_retried_submission_and_direct_calendar_posts_are_not_idempotent(client, db):
    from app.db.models import ActorJournalEntry, Submission

    actor = create_actor(client)
    opportunity = create_opportunity(
        client,
        audition_deadline="2026-08-10T18:00:00",
    )
    first = submit_like_frontend(client, actor, opportunity)
    second = submit_like_frontend(client, actor, opportunity)

    assert first["id"] != second["id"]
    submissions = list(
        db.scalars(select(Submission).where(Submission.opportunity_id == opportunity["id"]))
    )
    assert {row.id for row in submissions} == {UUID(first["id"]), UUID(second["id"])}
    assert len(calendar_rows(db, opportunity["id"], first["id"])) == 1
    assert len(calendar_rows(db, opportunity["id"], second["id"])) == 1
    assert len(journal_rows(db, first["id"])) == 1
    assert len(journal_rows(db, second["id"])) == 1
    assert (
        len(
            list(
                db.scalars(
                    select(ActorJournalEntry).where(
                        ActorJournalEntry.linked_breakdown_id == opportunity["id"],
                        ActorJournalEntry.event_type == "Submitted to Role",
                    )
                )
            )
        )
        == 2
    )

    payload = {
        "title": "Calendar Detective · Ownership Contract",
        "event_type": "Self-Tape Due",
        "opportunity_id": opportunity["id"],
        "submission_id": first["id"],
        "start_datetime": "2026-08-10T18:00:00",
        "location": "Remote",
        "is_virtual": False,
        "notes": "Prepare scene two.",
    }
    for _ in range(2):
        response = client.post(f"{API}/operations/calendar/events", json=payload)
        assert response.status_code == 201, response.text

    first_calendar = calendar_rows(db, opportunity["id"], first["id"])
    assert len(first_calendar) == 3
    assert sum(row.title == payload["title"] for row in first_calendar) == 2
    assert len({row.id for row in first_calendar}) == 3


@pytest.mark.parametrize(
    ("date_fields", "expected"),
    [
        (
            {
                "audition_type": "In-Person",
                "audition_deadline": "2026-08-11T15:00:00",
            },
            [
                ("In-Person Callback", datetime.fromisoformat("2026-08-11T15:00:00")),
            ],
        ),
        (
            {"audition_deadline": "2026-08-10T18:00:00"},
            [
                ("Self-Tape Due", datetime.fromisoformat("2026-08-10T18:00:00")),
            ],
        ),
        ({}, []),
    ],
)
def test_submission_projection_date_variations(client, db, date_fields, expected):
    actor = create_actor(client)
    date_fields = dict(date_fields)
    audition_type = date_fields.pop("audition_type", None)
    opportunity = create_opportunity(client, **date_fields)
    if audition_type:
        response = client.patch(
            f"{API}/opportunities/{opportunity['id']}",
            json={"audition_type": audition_type},
        )
        assert response.status_code == 200, response.text
        opportunity = response.json()

    submission = submit_like_frontend(client, actor, opportunity)
    rows = calendar_rows(db, opportunity["id"], submission["id"])
    assert [(row.event_type, wall_time(row.start_datetime)) for row in rows] == expected
    assert all(row.submission_id == UUID(submission["id"]) for row in rows)
