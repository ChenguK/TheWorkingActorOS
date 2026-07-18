from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import MAIN_BREAKDOWN_CLASSIFICATIONS
from app.db.models import Opportunity
from app.repositories.base import BaseRepository


class OpportunityRepository(BaseRepository[Opportunity]):
    model = Opportunity

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def search(
        self, *, q: str | None, include_hidden: bool = False, offset: int = 0, limit: int = 100
    ) -> list[Opportunity]:
        statement = select(Opportunity).where(Opportunity.is_demo_data.is_(False)).order_by(Opportunity.created_at.desc())
        if not include_hidden:
            statement = statement.where(Opportunity.visibility_status == "visible")
            statement = statement.where(Opportunity.breakdown_classification.in_(MAIN_BREAKDOWN_CLASSIFICATIONS))
        if q:
            term = f"%{q}%"
            statement = statement.where(
                Opportunity.role.ilike(term)
                | Opportunity.project.ilike(term)
                | Opportunity.location.ilike(term)
            )
        return list(self.db.scalars(statement.offset(offset).limit(limit)))
