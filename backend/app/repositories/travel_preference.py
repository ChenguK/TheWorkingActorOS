from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import TravelPreference
from app.repositories.base import BaseRepository


class TravelPreferenceRepository(BaseRepository[TravelPreference]):
    model = TravelPreference

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def get_for_actor(self, actor_profile_id) -> TravelPreference | None:
        return self.db.scalars(
            select(TravelPreference).where(TravelPreference.actor_profile_id == actor_profile_id)
        ).first()

