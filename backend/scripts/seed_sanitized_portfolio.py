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
from app.services.sanitized_portfolio_career_targeting_service import (  # noqa: E402
    SanitizedPortfolioCareerTargetingService,
)
from app.services.sanitized_portfolio_manifest import (  # noqa: E402
    build_sanitized_portfolio_manifest,
)
from app.services.sanitized_portfolio_submission_service import (  # noqa: E402
    SanitizedPortfolioSubmissionService,
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
    casting_goal_action: str | None = None,
    watch_list_action: str | None = None,
    career_memory_action: str | None = None,
    submission_actions: tuple[tuple[str, str], ...] = (),
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
    if casting_goal_action:
        print(f"CastingGoal: {casting_goal_action}")
        print(f"WatchList: {watch_list_action}")
        print(f"CareerMemory: {career_memory_action}")
    for submission_id, action in submission_actions:
        print(f"Submission {submission_id}: {action}")
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
        career_service = SanitizedPortfolioCareerTargetingService(db)
        submission_service = SanitizedPortfolioSubmissionService(db)
        opportunity_plan = None
        career_plan = None
        submission_plan = None
        if not reset:
            effective_as_of = as_of or datetime.now(timezone.utc)
            opportunity_plan = opportunity_service.plan(
                as_of=effective_as_of,
                allow_planned_profile_create=plan.profile_action == "create",
            )
            career_plan = career_service.plan(
                opportunity_plan.manifest,
                allow_planned_actor_create=plan.profile_action == "create",
            )
            submission_plan = submission_service.plan(
                opportunity_plan.manifest,
                allow_planned_actor_create=plan.profile_action == "create",
                allow_planned_opportunity_create=opportunity_plan.create_count > 0,
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
            casting_goal_action=career_plan.casting_goal_action if career_plan else None,
            watch_list_action=career_plan.watch_list_action if career_plan else None,
            career_memory_action=career_plan.career_memory_action if career_plan else None,
            submission_actions=(
                tuple((str(item.id), item.action) for item in submission_plan.items)
                if submission_plan
                else ()
            ),
        )
        if not execute:
            return
        if reset:
            reset_manifest = build_sanitized_portfolio_manifest(
                as_of or datetime.now(timezone.utc)
            )
            submission_service.reset(reset_manifest)
            career_service.reset(reset_manifest)
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
            if career_plan is None:
                raise RuntimeError("sanitized portfolio career-targeting plan is unavailable")
            career_service.apply(
                career_plan,
                actor_created_in_transaction=plan.profile_action == "create",
            )
            if submission_plan is None:
                raise RuntimeError("sanitized portfolio Submission plan is unavailable")
            submission_service.apply(submission_plan)
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
