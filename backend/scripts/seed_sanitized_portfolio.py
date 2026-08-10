from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from app.core.config import Settings, get_settings  # noqa: E402
from app.services.portfolio_seed_ownership_service import (  # noqa: E402
    PORTFOLIO_SEED_NAMESPACE,
    PortfolioSeedOwnershipService,
)
from app.services.sanitized_portfolio_opportunity_service import (  # noqa: E402
    SanitizedPortfolioOpportunityService,
)


ALLOWED_SEED_ENVIRONMENTS = frozenset({"development", "portfolio_demo"})


class PortfolioSeedSafetyError(RuntimeError):
    pass


class SessionFactory(Protocol):
    def __call__(self): ...


def validate_seed_safety(settings: Settings) -> None:
    if settings.sanitized_portfolio_seed_enabled is not True:
        raise PortfolioSeedSafetyError(
            "sanitized portfolio seed is not enabled; "
            "set SANITIZED_PORTFOLIO_SEED_ENABLED=true only for a dedicated sanitized database"
        )
    environment = settings.environment.strip().lower()
    if environment not in ALLOWED_SEED_ENVIRONMENTS:
        raise PortfolioSeedSafetyError(
            "sanitized portfolio seed is allowed only in development or portfolio_demo"
        )


def load_authorized_settings() -> Settings:
    try:
        settings = get_settings()
    except (ValidationError, ValueError) as exc:
        raise PortfolioSeedSafetyError(
            "sanitized portfolio seed configuration is malformed"
        ) from exc
    validate_seed_safety(settings)
    return settings


def database_session_factory() -> SessionFactory:
    # Importing the database module is intentionally deferred until after the safety gate.
    from app.core.database import SessionLocal

    return SessionLocal


def print_plan(
    *,
    execute: bool,
    reset: bool,
    profile_action: str,
    travel_preference_action: str,
    create_count: int,
    update_count: int,
    remove_count: int,
    opportunity_actions: tuple[tuple[str, str], ...] = (),
    opportunity_create_count: int = 0,
    opportunity_update_count: int = 0,
    opportunity_unchanged_count: int = 0,
) -> None:
    mode = "EXECUTE" if execute else "DRY RUN"
    operation = "RESET" if reset else "SEED"
    print(f"Sanitized portfolio {operation} {mode}")
    print(f"Ownership namespace: {PORTFOLIO_SEED_NAMESPACE}")
    print(f"ActorProfile: {profile_action}")
    print(f"TravelPreference: {travel_preference_action}")
    print(f"Records to create: {create_count}")
    print(f"Records to update: {update_count}")
    print(f"Opportunities to remove: {remove_count}")
    for scenario, action in opportunity_actions:
        print(f"Opportunity {scenario}: {action}")
    if opportunity_actions:
        print("Opportunities:")
        print(f"  create: {opportunity_create_count}")
        print(f"  update: {opportunity_update_count}")
        print(f"  unchanged: {opportunity_unchanged_count}")
    if not execute:
        print("No changes written. Run with --execute to apply this plan.")


def run(
    *,
    execute: bool,
    reset: bool,
    settings: Settings | None = None,
    session_factory: Callable[[], object] | None = None,
    as_of: datetime | None = None,
) -> None:
    authorized_settings = settings or load_authorized_settings()
    validate_seed_safety(authorized_settings)
    factory = session_factory or database_session_factory()
    db = factory()
    try:
        service = PortfolioSeedOwnershipService(db)
        plan = service.plan(reset=reset)
        opportunity_service = SanitizedPortfolioOpportunityService(db)
        opportunity_plan = None
        if not reset:
            effective_as_of = as_of or datetime.now(timezone.utc)
            opportunity_plan = opportunity_service.plan(
                as_of=effective_as_of,
                allow_planned_profile_create=plan.profile_action == "create",
            )
        print_plan(
            execute=execute,
            reset=reset,
            profile_action=plan.profile_action,
            travel_preference_action=plan.travel_preference_action,
            create_count=plan.create_count,
            update_count=plan.update_count,
            remove_count=plan.remove_count,
            opportunity_actions=(
                tuple((item.scenario, item.action) for item in opportunity_plan.items)
                if opportunity_plan
                else ()
            ),
            opportunity_create_count=opportunity_plan.create_count if opportunity_plan else 0,
            opportunity_update_count=opportunity_plan.update_count if opportunity_plan else 0,
            opportunity_unchanged_count=opportunity_plan.unchanged_count if opportunity_plan else 0,
        )
        if not execute:
            return
        if reset:
            opportunity_service.reset_owned_opportunities()
            plan = service.plan(reset=True)
            service.apply_reset(plan)
        else:
            service.apply(plan)
            if opportunity_plan is None:
                raise RuntimeError("sanitized portfolio Opportunity plan is unavailable")
            opportunity_service.apply(
                opportunity_plan,
                profile_created_in_transaction=plan.profile_action == "create",
            )
        db.commit()
        print("Sanitized portfolio transaction committed.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plan or reset the sanitized portfolio seed dataset."
    )
    parser.add_argument("--execute", action="store_true", help="Commit the displayed plan.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Remove records owned by the sanitized portfolio namespace.",
    )
    args = parser.parse_args()
    try:
        run(execute=args.execute, reset=args.reset)
    except PortfolioSeedSafetyError as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    main()
