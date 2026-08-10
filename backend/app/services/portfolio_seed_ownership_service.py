from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Literal, Mapping
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ActorProfile, Opportunity, TravelPreference


PORTFOLIO_SEED_NAMESPACE = "sanitized-portfolio-v1"
PORTFOLIO_SEED_METADATA_KEY = "portfolio_seed"
PORTFOLIO_DATASET_VERSION = 1
PORTFOLIO_PROFILE_ID = UUID("c83b75d4-5585-5b5c-9a99-63363f5bc14d")
PORTFOLIO_TRAVEL_PREFERENCE_ID = UUID("9be1c450-e20c-59f8-b91b-5cf9593f89f5")
PORTFOLIO_PROFILE_NAME = "Mara Ellison — Fictional Portfolio Performer"

PORTFOLIO_PROFILE_FIELDS: dict[str, Any] = {
    "name": PORTFOLIO_PROFILE_NAME,
    "sag_status": "SAG-AFTRA",
    "union_status": "Union and Non-Union",
    "current_location": "Atlanta, GA",
    "playable_age_min": 28,
    "playable_age_max": 38,
    "secondary_playable_age_min": None,
    "secondary_playable_age_max": None,
    "skills": ["Improvisation", "Teleprompter", "Stage Combat"],
    "gender_identities": ["Woman"],
    "gender_expression": "Feminine and androgynous presentations",
    "pronouns": "she/they",
    "ethnicities": ["Latina / Hispanic"],
    "racial_identities": ["Multiracial"],
    "nationalities": ["American"],
    "languages": ["English", "Spanish"],
    "accents": ["General American", "Southern US"],
    "disability_identities": [],
    "included_role_types": ["Lead", "Supporting", "Guest Star", "Co-Star", "Recurring"],
    "excluded_role_types": ["Crew", "Staff", "Production Assistant", "Casting Assistant"],
    "accessibility_notes": None,
    "demographic_notes": None,
    "notes": None,
}

PORTFOLIO_TRAVEL_PREFERENCE_FIELDS: dict[str, Any] = {
    "max_local_drive_time": 180,
    "extended_drive_time": 480,
    "flight_allowed": True,
    "housing_required": True,
    "international_allowed": False,
    "audition_max_drive_time": 120,
    "audition_virtual_allowed": True,
    "audition_self_tape_allowed": True,
    "working_as_local_drive_time": 240,
    "working_as_local_housing_self_provided": True,
    "require_travel_housing_over_local_drive": True,
    "audition_notes": None,
    "working_notes": None,
}

SeedAction = Literal["create", "update", "unchanged", "remove"]


@dataclass(frozen=True)
class PortfolioSeedPlan:
    profile_action: SeedAction = "unchanged"
    travel_preference_action: SeedAction = "unchanged"
    remove_opportunity_ids: tuple[UUID, ...] = ()

    @property
    def create_count(self) -> int:
        return sum(
            action == "create" for action in (self.profile_action, self.travel_preference_action)
        )

    @property
    def update_count(self) -> int:
        return sum(
            action == "update" for action in (self.profile_action, self.travel_preference_action)
        )

    @property
    def remove_count(self) -> int:
        return len(self.remove_opportunity_ids) + sum(
            action == "remove" for action in (self.profile_action, self.travel_preference_action)
        )


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
        profile = self.db.get(ActorProfile, PORTFOLIO_PROFILE_ID)
        self._validate_profile_identity(profile)
        travel = self.db.get(TravelPreference, PORTFOLIO_TRAVEL_PREFERENCE_ID)
        self._validate_travel_identity(travel)
        if reset:
            return PortfolioSeedPlan(
                profile_action="remove" if profile else "unchanged",
                travel_preference_action="remove" if travel else "unchanged",
                remove_opportunity_ids=tuple(opportunity.id for opportunity in owned),
            )
        return PortfolioSeedPlan(
            profile_action=self._action(profile, PORTFOLIO_PROFILE_FIELDS),
            travel_preference_action=self._action(
                travel,
                {
                    "actor_profile_id": PORTFOLIO_PROFILE_ID,
                    **PORTFOLIO_TRAVEL_PREFERENCE_FIELDS,
                },
            ),
        )

    def apply(self, plan: PortfolioSeedPlan) -> None:
        profile = self.db.get(ActorProfile, PORTFOLIO_PROFILE_ID)
        self._validate_profile_identity(profile)
        if plan.profile_action == "create":
            profile = ActorProfile(
                id=PORTFOLIO_PROFILE_ID,
                **deepcopy(PORTFOLIO_PROFILE_FIELDS),
            )
            self.db.add(profile)
        elif plan.profile_action == "update" and profile:
            self._update(profile, PORTFOLIO_PROFILE_FIELDS)

        travel = self.db.get(TravelPreference, PORTFOLIO_TRAVEL_PREFERENCE_ID)
        self._validate_travel_identity(travel)
        travel_fields = {
            "actor_profile_id": PORTFOLIO_PROFILE_ID,
            **PORTFOLIO_TRAVEL_PREFERENCE_FIELDS,
        }
        if plan.travel_preference_action == "create":
            self.db.add(
                TravelPreference(
                    id=PORTFOLIO_TRAVEL_PREFERENCE_ID,
                    **deepcopy(travel_fields),
                )
            )
        elif plan.travel_preference_action == "update" and travel:
            self._update(travel, travel_fields)

    def apply_reset(self, plan: PortfolioSeedPlan) -> None:
        if plan.remove_opportunity_ids:
            statement = select(Opportunity).where(Opportunity.id.in_(plan.remove_opportunity_ids))
            for opportunity in self.db.scalars(statement).all():
                if self.is_portfolio_owned(opportunity):
                    self.db.delete(opportunity)

        travel = self.db.get(TravelPreference, PORTFOLIO_TRAVEL_PREFERENCE_ID)
        self._validate_travel_identity(travel)
        if plan.travel_preference_action == "remove" and travel:
            self.db.delete(travel)

        profile = self.db.get(ActorProfile, PORTFOLIO_PROFILE_ID)
        self._validate_profile_identity(profile)
        if plan.profile_action == "remove" and profile:
            self.db.delete(profile)

    @staticmethod
    def _action(record: object | None, fields: Mapping[str, Any]) -> SeedAction:
        if record is None:
            return "create"
        return (
            "unchanged"
            if all(getattr(record, key) == value for key, value in fields.items())
            else "update"
        )

    @staticmethod
    def _update(record: object, fields: Mapping[str, Any]) -> None:
        for key, value in fields.items():
            setattr(record, key, deepcopy(value))

    @staticmethod
    def _validate_profile_identity(profile: ActorProfile | None) -> None:
        if profile is not None and profile.name != PORTFOLIO_PROFILE_NAME:
            raise ValueError("reserved sanitized portfolio profile identity is already in use")

    @staticmethod
    def _validate_travel_identity(travel: TravelPreference | None) -> None:
        if travel is not None and travel.actor_profile_id != PORTFOLIO_PROFILE_ID:
            raise ValueError(
                "reserved sanitized portfolio travel preference identity is already in use"
            )
