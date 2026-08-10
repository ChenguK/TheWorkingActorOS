from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from app.core.database import SessionLocal  # noqa: E402
from app.services.portfolio_seed_ownership_service import (  # noqa: E402
    PORTFOLIO_SEED_NAMESPACE,
    PortfolioSeedOwnershipService,
)


def print_plan(
    *, execute: bool, reset: bool, create_count: int, update_count: int, remove_count: int
) -> None:
    mode = "EXECUTE" if execute else "DRY RUN"
    operation = "RESET" if reset else "SEED"
    print(f"Sanitized portfolio {operation} {mode}")
    print(f"Ownership namespace: {PORTFOLIO_SEED_NAMESPACE}")
    print(f"Records to create: {create_count}")
    print(f"Records to update: {update_count}")
    print(f"Opportunities to remove: {remove_count}")
    if not execute:
        print("No changes written. Run with --execute to apply this plan.")


def run(*, execute: bool, reset: bool) -> None:
    db = SessionLocal()
    try:
        service = PortfolioSeedOwnershipService(db)
        plan = service.plan(reset=reset)
        print_plan(
            execute=execute,
            reset=reset,
            create_count=plan.create_count,
            update_count=plan.update_count,
            remove_count=plan.remove_count,
        )
        if not execute:
            return
        if reset:
            service.apply_reset(plan)
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
    run(execute=args.execute, reset=args.reset)


if __name__ == "__main__":
    main()
