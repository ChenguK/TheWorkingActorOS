from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Submission
from app.repositories.base import BaseRepository


class SubmissionRepository(BaseRepository[Submission]):
    model = Submission

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def list_full(self, *, offset: int = 0, limit: int = 100) -> list[Submission]:
        statement = (
            select(Submission)
            .options(
                selectinload(Submission.opportunity),
                selectinload(Submission.assets),
                selectinload(Submission.status_history),
            )
            .order_by(Submission.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.scalars(statement))

    def get_full(self, submission_id) -> Submission:
        statement = (
            select(Submission)
            .where(Submission.id == submission_id)
            .options(
                selectinload(Submission.opportunity),
                selectinload(Submission.assets),
                selectinload(Submission.status_history),
            )
        )
        item = self.db.scalars(statement).first()
        if item is None:
            return self.get(submission_id)
        return item

