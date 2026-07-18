from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.errors import ConflictError
from app.services.opportunity_service import OpportunityService


def build_service(linked_submission_id=None):
    db = Mock()
    db.scalar.return_value = linked_submission_id
    service = OpportunityService(db)
    service.repo = Mock()
    opportunity = SimpleNamespace(id=uuid4())
    service.repo.get.return_value = opportunity
    return service, db, opportunity


def test_delete_rejects_linked_submission_before_any_mutation():
    service, db, opportunity = build_service(uuid4())

    with pytest.raises(ConflictError) as caught:
        service.delete(opportunity.id)

    assert caught.value.status_code == 409
    assert caught.value.detail["code"] == "opportunity_has_submissions"
    service.repo.delete.assert_not_called()
    db.commit.assert_not_called()


def test_delete_commits_an_unlinked_opportunity():
    service, db, opportunity = build_service()

    service.delete(opportunity.id)

    service.repo.delete.assert_called_once_with(opportunity)
    db.commit.assert_called_once_with()


def test_delete_translates_a_concurrent_submission_constraint_race():
    service, db, opportunity = build_service()
    db.scalar.side_effect = [None, uuid4()]
    db.commit.side_effect = IntegrityError("delete", {}, Exception("restricted"))

    with pytest.raises(ConflictError) as caught:
        service.delete(opportunity.id)

    assert caught.value.detail["code"] == "opportunity_has_submissions"
    db.rollback.assert_called_once_with()
