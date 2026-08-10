from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Opportunity


PORTFOLIO_SEED_NAMESPACE = "sanitized-portfolio-v1"
PORTFOLIO_SEED_METADATA_KEY = "portfolio_seed"


@dataclass(frozen=True)
class PortfolioSeedPlan:
    create_count: int = 0
    update_count: int = 0
    remove_opportunity_ids: tuple[UUID, ...] = ()

    @property
    def remove_count(self) -> int:
        return len(self.remove_opportunity_ids)


class PortfolioSeedOwnershipService:
    """Owns portfolio-seed identification and reset planning, but not transactions."""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def ownership_metadata() -> dict[str, dict[str, str]]:
        return {
            PORTFOLIO_SEED_METADATA_KEY: {
                "namespace": PORTFOLIO_SEED_NAMESPACE,
            }
        }

    @staticmethod
    def is_portfolio_owned(opportunity: Opportunity) -> bool:
        metadata = opportunity.source_metadata
        if not isinstance(metadata, Mapping):
            return False
        ownership = metadata.get(PORTFOLIO_SEED_METADATA_KEY)
        return (
            isinstance(ownership, Mapping)
            and ownership.get("namespace") == PORTFOLIO_SEED_NAMESPACE
        )

    @classmethod
    def mark_portfolio_owned(cls, opportunity: Opportunity) -> None:
        metadata: dict[str, Any] = dict(opportunity.source_metadata or {})
        metadata.update(cls.ownership_metadata())
        opportunity.source_metadata = metadata
        opportunity.is_demo_data = False

    def find_owned_opportunities(self) -> list[Opportunity]:
        ownership = self.ownership_metadata()
        statement = (
            select(Opportunity)
            .where(Opportunity.source_metadata.contains(ownership))
            .order_by(Opportunity.id)
        )
        return [
            opportunity
            for opportunity in self.db.scalars(statement).all()
            if self.is_portfolio_owned(opportunity)
        ]

    def plan(self, *, reset: bool = False) -> PortfolioSeedPlan:
        owned = self.find_owned_opportunities()
        return PortfolioSeedPlan(
            remove_opportunity_ids=(tuple(opportunity.id for opportunity in owned) if reset else ())
        )

    def apply_reset(self, plan: PortfolioSeedPlan) -> None:
        if not plan.remove_opportunity_ids:
            return
        statement = select(Opportunity).where(Opportunity.id.in_(plan.remove_opportunity_ids))
        for opportunity in self.db.scalars(statement).all():
            if self.is_portfolio_owned(opportunity):
                self.db.delete(opportunity)
