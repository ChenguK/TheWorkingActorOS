from __future__ import annotations

import re
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.automation.discovery.classification import classify_breakdown_text
from app.core.errors import NotFoundError
from app.db.models import ActorProfile, Opportunity, SupervisedBreakdownImport
from app.schemas.opportunity import OpportunityCreate
from app.schemas.supervised_breakdown import SupervisedBreakdownImportUpdate
from app.services.breakdown_details_service import BreakdownDetailsService
from app.services.opportunity_service import OpportunityService


PLATFORM_START_URLS = {
    "Actors Access": "https://actorsaccess.com/",
    "Casting Networks": "https://www.castingnetworks.com/",
    "Casting Frontier": "https://castingfrontier.com/",
}

BLOCKED_HINTS = {
    "captcha",
    "verify you are human",
    "access denied",
    "automated traffic",
    "blocked",
    "unusual activity",
    "enable cookies",
}


class SupervisedBrowserController:
    def __init__(self) -> None:
        self._playwright = None
        self._browser = None
        self._page = None
        self.platform_name: str | None = None

    def start(self, platform_name: str) -> dict:
        self.close()
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                "Playwright is not installed in the backend environment. Run `pip install -e .` "
                "after updating dependencies, then run `playwright install chromium` if prompted."
            ) from exc

        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=False)
        self._page = self._browser.new_page()
        self.platform_name = platform_name
        self._page.goto(PLATFORM_START_URLS[platform_name], wait_until="domcontentloaded", timeout=30000)
        return self.status("Supervised browser opened. Log in manually, navigate to one breakdown, then click Import This Breakdown.")

    def status(self, message: str = "Supervised browser status.") -> dict:
        return {
            "active": self._page is not None,
            "platform_name": self.platform_name,
            "current_url": self.current_url(),
            "message": message,
        }

    def current_url(self) -> str | None:
        if not self._page:
            return None
        try:
            return self._page.url
        except Exception:
            return None

    def capture_visible_page(self) -> dict:
        if not self._page or not self.platform_name:
            raise RuntimeError("Open the supervised browser before importing a breakdown.")
        try:
            self._page.wait_for_load_state("domcontentloaded", timeout=5000)
            visible_text = self._page.locator("body").inner_text(timeout=8000)
            title = self._page.title()
            url = self._page.url
        except Exception as exc:
            raise RuntimeError(
                "This platform blocked automated extraction. Use copy/paste, screenshot, PDF, or manual entry instead."
            ) from exc
        return {
            "platform_name": self.platform_name,
            "source_url": url,
            "page_title": title,
            "raw_visible_text": visible_text.strip(),
        }

    def close(self) -> None:
        for resource in (self._browser, self._playwright):
            if resource:
                try:
                    resource.close() if resource is self._browser else resource.stop()
                except Exception:
                    pass
        self._browser = None
        self._playwright = None
        self._page = None
        self.platform_name = None


supervised_browser = SupervisedBrowserController()


class SupervisedBreakdownImportService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_imports(self) -> list[SupervisedBreakdownImport]:
        return list(
            self.db.scalars(
                select(SupervisedBreakdownImport).order_by(SupervisedBreakdownImport.imported_at.desc())
            )
        )

    def start_browser(self, platform_name: str) -> dict:
        return supervised_browser.start(platform_name)

    def browser_status(self) -> dict:
        return supervised_browser.status()

    def close_browser(self) -> dict:
        supervised_browser.close()
        return supervised_browser.status("Supervised browser closed.")

    def import_current_page(self) -> SupervisedBreakdownImport:
        captured = supervised_browser.capture_visible_page()
        actor = self.db.scalars(select(ActorProfile).limit(1)).first()
        raw_text = captured["raw_visible_text"]
        status = "Draft"
        error_message = None
        parsed: dict = {}
        if not raw_text:
            status = "Blocked"
            error_message = "This platform blocked automated extraction. Use copy/paste, screenshot, PDF, or manual entry instead."
        elif self._looks_blocked(raw_text):
            status = "Blocked"
            error_message = "This platform blocked automated extraction. Use copy/paste, screenshot, PDF, or manual entry instead."
        else:
            parsed = self._parse_breakdown(raw_text, captured["source_url"], captured["platform_name"])
            status = "Draft" if parsed.get("confidence") != "Low" else "Needs Review"

        record = SupervisedBreakdownImport(
            actor_profile_id=actor.id if actor else None,
            platform_name=captured["platform_name"],
            source_url=captured["source_url"],
            imported_at=datetime.now(timezone.utc),
            raw_visible_text=raw_text,
            parsed_data_json=parsed,
            import_status=status,
            user_approved=False,
            error_message=error_message,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def update_import(
        self, import_id: UUID, payload: SupervisedBreakdownImportUpdate
    ) -> SupervisedBreakdownImport:
        record = self._get(import_id)
        data = payload.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(record, key, value)
        self.db.commit()
        self.db.refresh(record)
        return record

    def approve_import(self, import_id: UUID) -> tuple[SupervisedBreakdownImport, Opportunity]:
        record = self._get(import_id)
        if record.import_status == "Blocked":
            raise ValueError("Blocked imports cannot be approved. Use copy/paste, screenshot, PDF, or manual entry instead.")
        if record.import_status == "Rejected":
            raise ValueError("Rejected imports cannot be approved.")
        parsed = record.parsed_data_json or {}
        opportunity = OpportunityService(self.db).create(self._payload_from_parsed(record, parsed))
        record.approved_opportunity_id = opportunity.id
        record.import_status = "Approved"
        record.user_approved = True
        self.db.commit()
        self.db.refresh(record)
        self.db.refresh(opportunity)
        return record, opportunity

    def reject_import(self, import_id: UUID) -> SupervisedBreakdownImport:
        record = self._get(import_id)
        record.import_status = "Rejected"
        record.user_approved = False
        self.db.commit()
        self.db.refresh(record)
        return record

    def delete_import(self, import_id: UUID) -> None:
        record = self._get(import_id)
        self.db.delete(record)
        self.db.commit()

    def _get(self, import_id: UUID) -> SupervisedBreakdownImport:
        record = self.db.get(SupervisedBreakdownImport, import_id)
        if not record:
            raise NotFoundError("Supervised breakdown import not found")
        return record

    def _looks_blocked(self, text: str) -> bool:
        lower = text.lower()
        return any(hint in lower for hint in BLOCKED_HINTS)

    def _parse_breakdown(self, text: str, source_url: str | None, platform_name: str) -> dict:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        joined = "\n".join(lines)
        project = self._field(lines, ["project", "title", "production"]) or self._guess_project(lines)
        role = self._field(lines, ["role", "character"]) or self._guess_role(lines)
        role_type = self._find_known(joined, ["Guest Star", "Co-Star", "Recurring", "Series Regular", "Lead", "Supporting", "Principal", "Featured"])
        project_type = self._find_known(joined, ["Television", "TV", "Film", "Feature", "Short", "Commercial", "Theater", "Theatre", "New Media", "Voiceover"])
        union = self._find_known(joined, ["SAG-AFTRA", "SAG", "AFTRA", "Equity", "AEA", "Non-Union", "Union"]) or "Unknown"
        audition_type = self._audition_type(joined)
        return {
            "platform": platform_name,
            "project_title": project,
            "role_name": role,
            "role_type": role_type,
            "union_status": union,
            "project_type": project_type,
            "casting_office": self._field(lines, ["casting", "casting office", "casting director"]),
            "audition_type": audition_type,
            "self_tape_due_date": self._field(lines, ["self tape due", "self-tape due", "due date", "deadline"]),
            "audition_location": self._field(lines, ["audition location", "audition"]),
            "shoot_location": self._field(lines, ["shoot location", "location", "works"]),
            "travel_provided": self._bool_field(joined, "travel"),
            "housing_provided": self._bool_field(joined, "housing"),
            "rate": self._field(lines, ["rate", "pay", "salary", "compensation"]),
            "submission_instructions": self._section(lines, ["submission", "instructions", "submit"]),
            "visible_role_description": self._description(lines),
            "source_url": source_url,
            "import_timestamp": datetime.now(timezone.utc).isoformat(),
            "confidence": "Medium" if project and role else "Low",
            "compliance_note": "Imported only visible text from the single user-opened page. No login data was stored and no crawl was performed.",
        }

    def _payload_from_parsed(self, record: SupervisedBreakdownImport, parsed: dict) -> OpportunityCreate:
        classification = classify_breakdown_text(
            " ".join(
                str(value or "")
                for value in [
                    parsed.get("project_title"),
                    parsed.get("role_name"),
                    parsed.get("role_type"),
                    parsed.get("union_status"),
                    parsed.get("submission_instructions"),
                    parsed.get("visible_role_description"),
                    record.raw_visible_text,
                ]
            )
        )
        details = BreakdownDetailsService().from_fields(
            role=str(parsed.get("role_name") or "Role Needs Review")[:255],
            project=str(parsed.get("project_title") or "Project Needs Review")[:255],
            union=str(parsed.get("union_status") or "Unknown")[:80],
            location=str(parsed.get("shoot_location") or parsed.get("audition_location") or "See source")[:255],
            description=str(parsed.get("visible_role_description") or record.raw_visible_text[:1200] or "See source"),
            source_name=record.platform_name,
            source_url=record.source_url,
            source_type="Platform Discovery",
            platform=record.platform_name,
            import_method="Supervised visible-page import",
            discovered_at=record.imported_at.isoformat() if record.imported_at else None,
            project_type=parsed.get("project_type") or None,
            role_type=parsed.get("role_type") or None,
            audition_type=parsed.get("audition_type") or "Unknown",
            rate=parsed.get("rate") or None,
            shoot_location=parsed.get("shoot_location") or None,
            audition_location=parsed.get("audition_location") or None,
            travel_covered=parsed.get("travel_provided"),
            housing_covered=parsed.get("housing_provided"),
            raw_visible_text=record.raw_visible_text,
        )
        if parsed.get("submission_instructions"):
            details["role_details"]["submission_instructions"] = parsed.get("submission_instructions")
        return OpportunityCreate(
            source_type="Platform Discovery",
            platform=record.platform_name,
            role=str(parsed.get("role_name") or "Role Needs Review")[:255],
            project=str(parsed.get("project_title") or "Project Needs Review")[:255],
            project_type=parsed.get("project_type") or None,
            role_type=parsed.get("role_type") or None,
            archetypes=[],
            union=str(parsed.get("union_status") or "Unknown")[:80],
            rate=parsed.get("rate") or None,
            location=str(parsed.get("shoot_location") or parsed.get("audition_location") or "See source")[:255],
            shoot_location=parsed.get("shoot_location") or None,
            audition_location=parsed.get("audition_location") or None,
            travel_covered=parsed.get("travel_provided"),
            housing_covered=parsed.get("housing_provided"),
            description=str(parsed.get("visible_role_description") or record.raw_visible_text[:1200] or "See source"),
            original_post_url=record.source_url,
            status="open",
            breakdown_classification=classification.classification,
            rejection_reason=classification.rejection_reason,
            source_metadata=details["source_metadata"],
            production_details=details["production_details"],
            role_details=details["role_details"],
            ai_summary=details["ai_summary"],
            audition_type=parsed.get("audition_type") or "Unknown",
            priority="Medium",
        )

    def _field(self, lines: list[str], labels: list[str]) -> str | None:
        for index, line in enumerate(lines):
            lower = line.lower().strip(":")
            for label in labels:
                if lower.startswith(label.lower()):
                    value = re.sub(rf"^{re.escape(label)}\s*:?\s*", "", line, flags=re.I).strip()
                    if value:
                        return value[:500]
                    if index + 1 < len(lines):
                        return lines[index + 1][:500]
        return None

    def _find_known(self, text: str, values: list[str]) -> str | None:
        lower = text.lower()
        return next((value for value in values if value.lower() in lower), None)

    def _audition_type(self, text: str) -> str:
        lower = text.lower()
        if "self tape" in lower or "self-tape" in lower or "eco cast" in lower:
            return "Self-Tape"
        if "zoom" in lower or "virtual" in lower:
            return "Virtual"
        if "in-person" in lower or "in person" in lower or "callback location" in lower:
            return "In-Person"
        return "Unknown"

    def _bool_field(self, text: str, label: str) -> bool | None:
        lower = text.lower()
        if label not in lower:
            return None
        if re.search(rf"{label}.{{0,40}}(provided|covered|paid)", lower):
            return True
        if re.search(rf"{label}.{{0,40}}(not provided|not covered|unpaid)", lower):
            return False
        return None

    def _guess_project(self, lines: list[str]) -> str:
        return next((line for line in lines if len(line) <= 120), "Project Needs Review")[:255]

    def _guess_role(self, lines: list[str]) -> str:
        for line in lines:
            if any(term in line.lower() for term in ["role", "seeking", "character"]):
                return line[:255]
        return "Role Needs Review"

    def _section(self, lines: list[str], labels: list[str]) -> str | None:
        for index, line in enumerate(lines):
            if any(label in line.lower() for label in labels):
                return "\n".join(lines[index : index + 5])[:1200]
        return None

    def _description(self, lines: list[str]) -> str:
        description_lines = [
            line for line in lines if len(line) > 35 and not line.lower().startswith(("project", "role", "rate"))
        ]
        return "\n".join(description_lines[:8])[:2000] or "\n".join(lines[:12])[:2000]
