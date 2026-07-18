from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, *, offset: int = 0, limit: int = 100) -> list[ModelT]:
        statement = select(self.model).offset(offset).limit(limit)
        return list(self.db.scalars(statement))

    def get(self, item_id: UUID) -> ModelT:
        item = self.db.get(self.model, item_id)
        if item is None:
            raise NotFoundError(f"{self.model.__name__} not found")
        return item

    def add(self, item: ModelT) -> ModelT:
        self.db.add(item)
        self.db.flush()
        self.db.refresh(item)
        return item

    def delete(self, item: ModelT) -> None:
        self.db.delete(item)
        self.db.flush()

    def apply_updates(self, item: ModelT, data: dict[str, Any]) -> ModelT:
        for key, value in data.items():
            setattr(item, key, value)
        self.db.flush()
        self.db.refresh(item)
        return item

