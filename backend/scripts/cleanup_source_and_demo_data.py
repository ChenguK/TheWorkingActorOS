from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from app.core.database import SessionLocal
from app.db.models import Opportunity, SourceResearchItem


BAD_SOURCE_HEALTH_STATUSES = {"Placeholder Website", "Dead / Unavailable Domain", "No Meaningful Content"}
DEMO_PATTERNS = [
    re.compile(pattern, re.I)
    for pattern in [
        r"\bdemo\b",
        r"\bexample\b",
        r"\bsample\b",
        r"\btest\b",
        r"Feature Demo",
        r"Production Websites Feature Demo",
        r"example\.com",
    ]
]


@dataclass
class CleanupReport:
    bad_sources: list[SourceResearchItem]
    demo_breakdowns: list[Opportunity]


def is_bad_source(item: SourceResearchItem) -> bool:
    return bool(
        item.source_usefulness == "Not Useful"
        or item.source_classification == "Not Useful"
        or item.source_health in BAD_SOURCE_HEALTH_STATUSES
        or item.url_health_status in BAD_SOURCE_HEALTH_STATUSES
    )


def is_demo_breakdown(opportunity: Opportunity) -> bool:
    text = " ".join(
        str(value or "")
        for value in [
            opportunity.role,
            opportunity.project,
            opportunity.description,
            opportunity.original_post_url,
            opportunity.platform,
            opportunity.source_type,
        ]
    )
    return bool(opportunity.is_demo_data or any(pattern.search(text) for pattern in DEMO_PATTERNS))


def collect_report(db) -> CleanupReport:
    sources = [item for item in db.query(SourceResearchItem).all() if not item.deleted and is_bad_source(item)]
    breakdowns = [item for item in db.query(Opportunity).all() if is_demo_breakdown(item)]
    return CleanupReport(bad_sources=sources, demo_breakdowns=breakdowns)


def apply_cleanup(report: CleanupReport) -> None:
    now = datetime.now(timezone.utc)
    for item in report.bad_sources:
        if not item.deleted:
            item.previous_status = item.status
        item.status = "Deleted"
        item.deleted = True
        item.deleted_at = item.deleted_at or now
        item.rejection_reason = item.rejection_reason or item.health_reason or "Source was not useful for actor-facing breakdown discovery."
        item.source_usefulness = "Not Useful"
        if item.source_classification == "Not Useful":
            item.suggested_classification = "Not Useful"
    for opportunity in report.demo_breakdowns:
        opportunity.is_demo_data = True
        opportunity.visibility_status = "discarded"
        opportunity.rejection_reason = opportunity.rejection_reason or "Demo/example data hidden from actor workflows."


def print_report(report: CleanupReport, execute: bool) -> None:
    mode = "EXECUTE" if execute else "DRY RUN"
    print(f"Source/demo cleanup {mode}")
    print(f"Bad sources to soft-delete: {len(report.bad_sources)}")
    for item in report.bad_sources[:10]:
        print(f"  - {item.name} [{item.source_health} / {item.source_usefulness} / {item.source_classification}]")
    print(f"Demo/example breakdowns to mark hidden: {len(report.demo_breakdowns)}")
    for item in report.demo_breakdowns[:10]:
        print(f"  - {item.project} · {item.role}")
    if not execute:
        print("No changes written. Run with --execute to mutate data.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Soft-delete bad sources and hide demo/example breakdowns.")
    parser.add_argument("--execute", action="store_true", help="Actually write cleanup changes.")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        report = collect_report(db)
        print_report(report, execute=args.execute)
        if args.execute:
            apply_cleanup(report)
            db.commit()
            print("Cleanup changes committed.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
