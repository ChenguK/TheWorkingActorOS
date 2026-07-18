from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Asset
from app.repositories.base import BaseRepository


class AssetRepository(BaseRepository[Asset]):
    model = Asset

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def list_by_actor(self, actor_profile_id, *, offset: int = 0, limit: int = 100) -> list[Asset]:
        statement = (
            select(Asset)
            .where(Asset.actor_profile_id == actor_profile_id)
            .order_by(Asset.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.scalars(statement))

