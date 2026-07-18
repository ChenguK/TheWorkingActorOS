from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ActorProfile
from app.repositories.base import BaseRepository


class ActorProfileRepository(BaseRepository[ActorProfile]):
    model = ActorProfile

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def get_single(self) -> ActorProfile | None:
        return self.db.scalars(select(ActorProfile).limit(1)).first()

