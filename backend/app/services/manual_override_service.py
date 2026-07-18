from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import ManualOverrideLog


class ManualOverrideService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def log(
        self,
        *,
        entity_type: str,
        entity_id: UUID,
        field_name: str,
        previous_value: Any,
        new_value: Any,
        reason: str | None = None,
        changed_by: str = "user",
    ) -> ManualOverrideLog | None:
        if previous_value == new_value:
            return None
        now = datetime.now(timezone.utc)
        record = ManualOverrideLog(
            entity_type=entity_type,
            entity_id=entity_id,
            field_name=field_name,
            previous_value=self._json_value(previous_value),
            new_value=self._json_value(new_value),
            reason=reason,
            changed_by=changed_by,
            created_at=now,
            updated_at=now,
        )
        self.db.add(record)
        return record

    def log_many(
        self,
        *,
        entity_type: str,
        entity_id: UUID,
        before: dict[str, Any],
        after: dict[str, Any],
        reason: str | None = None,
        changed_by: str = "user",
    ) -> None:
        for field_name, previous_value in before.items():
            self.log(
                entity_type=entity_type,
                entity_id=entity_id,
                field_name=field_name,
                previous_value=previous_value,
                new_value=after.get(field_name),
                reason=reason,
                changed_by=changed_by,
            )

    def _json_value(self, value: Any) -> dict | None:
        if value is None:
            return None
        if isinstance(value, dict):
            return value
        if isinstance(value, list):
            return {"value": value}
        return {"value": str(value)}
