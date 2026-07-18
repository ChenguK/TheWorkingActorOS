from __future__ import annotations

import re
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ActorProfile, Opportunity, WatchList
from app.schemas.agent import WatchListCreate, WatchListUpdate


PRIORITY_WEIGHT = {"High": 3, "Medium": 2, "Low": 1}


class WatchListService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self) -> list[WatchList]:
        return list(
            self.db.scalars(
                select(WatchList).order_by(WatchList.enabled.desc(), WatchList.priority.desc(), WatchList.updated_at.desc())
            )
        )

    def create(self, payload: WatchListCreate) -> WatchList:
        actor = self.db.scalars(select(ActorProfile).limit(1)).first()
        data = payload.model_dump()
        if actor and not data.get("actor_profile_id"):
            data["actor_profile_id"] = actor.id
        record = WatchList(**data)
        self.db.add(record)
        self.db.flush()
        self.refresh_all()
        self.db.commit()
        self.db.refresh(record)
        return record

    def update(self, watch_list_id: UUID, payload: WatchListUpdate) -> WatchList:
        record = self.db.get(WatchList, watch_list_id)
        if not record:
            raise ValueError("Watch List not found")
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(record, key, value)
        self.refresh_all()
        self.db.commit()
        self.db.refresh(record)
        return record

    def delete(self, watch_list_id: UUID) -> None:
        record = self.db.get(WatchList, watch_list_id)
        if not record:
            raise ValueError("Watch List not found")
        self.db.delete(record)
        self.db.flush()
        self.refresh_all()
        self.db.commit()

    def apply_to_opportunity(self, opportunity: Opportunity) -> Opportunity:
        watch_lists = list(
            self.db.scalars(select(WatchList).where(WatchList.enabled.is_(True)))
        )
        text = self._opportunity_text(opportunity)
        matches = []
        for watch_list in watch_lists:
            matched_terms = [term for term in watch_list.terms if self._contains(text, str(term))]
            if not matched_terms:
                continue
            matches.append(
                {
                    "id": str(watch_list.id),
                    "title": watch_list.title,
                    "category": watch_list.category,
                    "priority": watch_list.priority,
                    "matched_terms": matched_terms,
                    "weight": PRIORITY_WEIGHT.get(watch_list.priority, 2),
                }
            )
            watch_list.match_count += 1
            watch_list.last_matched_at = datetime.now(timezone.utc)

        matches.sort(key=lambda item: (-item["weight"], item["title"]))
        opportunity.watchlist_match_names = matches
        opportunity.watchlist_match_count = len(matches)
        if matches:
            labels = ", ".join(item["title"] for item in matches[:3])
            opportunity.watchlist_notification = f"This breakdown matches one of your Watch Lists: {labels}."
        else:
            opportunity.watchlist_notification = None
        return opportunity

    def refresh_all(self) -> None:
        for opportunity in self.db.scalars(select(Opportunity).where(Opportunity.is_demo_data.is_(False))).all():
            self.apply_to_opportunity(opportunity)

    def _opportunity_text(self, opportunity: Opportunity) -> str:
        values = [
            opportunity.role,
            opportunity.project,
            opportunity.project_type,
            opportunity.role_type,
            opportunity.union,
            opportunity.rate,
            opportunity.location,
            opportunity.shoot_location,
            opportunity.audition_location,
            opportunity.description,
            opportunity.category,
            opportunity.source_type,
            opportunity.platform,
            " ".join(opportunity.archetypes or []),
        ]
        return " ".join(value for value in values if value).lower()

    def _contains(self, text: str, term: str) -> bool:
        cleaned = term.strip().lower()
        if not cleaned:
            return False
        return bool(re.search(r"(?<![a-z0-9])" + re.escape(cleaned) + r"(?![a-z0-9])", text))
