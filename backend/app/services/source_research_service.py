from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models import DiscoveryProviderSettings, SourceResearchItem
from app.schemas.discovery import SourceResearchItemCreate, SourceResearchItemUpdate
from app.services.manual_override_service import ManualOverrideService


COMMON_SOURCE_NAME_WORDS = {
    "casting",
    "calls",
    "jobs",
    "job",
    "office",
    "source",
    "agency",
    "company",
    "productions",
    "production",
    "the",
    "inc",
    "llc",
}

BAD_SOURCE_HEALTH_STATUSES = {"Placeholder Website", "Dead / Unavailable Domain", "No Meaningful Content"}

KNOWN_PROVIDER_KEYS = {
    "playbilljobs": "playbill_public_jobs",
    "playbill": "playbill_public_jobs",
    "backstagecastingcalls": "backstage",
    "backstage": "backstage",
    "grantwilfley": "grant_wilfley_casting",
    "grantwilfleycasting": "grant_wilfley_casting",
    "waldron": "waldron_casting",
    "waldroncasting": "waldron_casting",
    "pennsylvaniafilmoffice": "pennsylvania_film_commission",
    "newjerseymotionpicturetelevisioncommission": "new_jersey_film_commission",
}


SUGGESTED_SOURCES = [
    {
        "name": "Playbill Jobs",
        "source_url": "https://playbill.com/jobs",
        "base_url": "https://playbill.com/",
        "suggested_specific_url": "https://playbill.com/jobs",
        "category": "Public casting site",
        "reliability_notes": "Useful for public theater auditions, EPAs, ECCs, and open calls. Review carefully because the feed also contains non-acting jobs.",
    },
    {
        "name": "Backstage Casting Calls",
        "source_url": "https://www.backstage.com/casting/",
        "base_url": "https://www.backstage.com/",
        "suggested_specific_url": "https://www.backstage.com/casting/",
        "category": "Public casting site",
        "reliability_notes": "Large public casting marketplace. Best used with user-approved filters and manual review.",
    },
    {
        "name": "Grant Wilfley Casting",
        "source_url": "https://www.gwcnyc.com/",
        "base_url": "https://www.gwcnyc.com/",
        "category": "Casting office",
        "reliability_notes": "Known New York casting office. Public posts should be reviewed manually before adding as a monitored source.",
    },
    {
        "name": "Waldron Casting",
        "source_url": "https://waldroncasting.com/",
        "base_url": "https://waldroncasting.com/",
        "category": "Casting office",
        "reliability_notes": "Casting office source candidate. Confirm whether public breakdown posts are currently available.",
    },
    {
        "name": "Pennsylvania Film Office",
        "source_url": "https://filminpa.com/",
        "base_url": "https://filminpa.com/",
        "category": "Film commission",
        "reliability_notes": "Good for production awareness and regional leads; not every listing is an actor-facing breakdown.",
    },
    {
        "name": "New Jersey Motion Picture & Television Commission",
        "source_url": "https://www.nj.gov/state/njfilm/",
        "base_url": "https://www.nj.gov/state/njfilm/",
        "category": "Film commission",
        "reliability_notes": "Useful for regional production research and source discovery.",
    },
]

DISCOVERABLE_SOURCE_CANDIDATES = [
    {
        "name": "Theatre Puget Sound Auditions",
        "source_url": "https://theatrepugetsound.org/auditions",
        "base_url": "https://theatrepugetsound.org/",
        "suggested_specific_url": "https://theatrepugetsound.org/auditions",
        "category": "Theater company",
        "reliability_notes": "Public audition board that may surface theatre breakdowns; useful if theatre is in scope.",
        "user_rating": 3,
    },
    {
        "name": "BroadwayWorld Auditions",
        "source_url": "https://www.broadwayworld.com/equity-auditions/",
        "base_url": "https://www.broadwayworld.com/",
        "suggested_specific_url": "https://www.broadwayworld.com/equity-auditions/",
        "category": "Public casting site",
        "reliability_notes": "Public theatre audition listings; review for actor-facing breakdown relevance.",
        "user_rating": 4,
    },
    {
        "name": "Actors Theatre Workshop Casting Calls",
        "source_url": "https://www.actorsfund.org/",
        "base_url": "https://www.actorsfund.org/",
        "category": "Other",
        "reliability_notes": "Potential research lead. Confirm whether current public audition listings are available before approving.",
        "user_rating": 2,
    },
    {
        "name": "Telsey Office",
        "source_url": "https://www.telseyandco.com/",
        "base_url": "https://www.telseyandco.com/",
        "category": "Casting office",
        "reliability_notes": "Major casting office. Approve only if you identify a public page with useful breakdown or submission information.",
        "user_rating": 3,
    },
    {
        "name": "Central Casting",
        "source_url": "https://www.centralcasting.com/",
        "base_url": "https://www.centralcasting.com/",
        "suggested_specific_url": "https://www.centralcasting.com/jobs/",
        "category": "Public casting site",
        "reliability_notes": "Often background-focused; keep rejected or paused unless background work is enabled.",
        "user_rating": 2,
    },
    {
        "name": "Georgia Production Jobs Hotline",
        "source_url": "https://www.georgia.org/industries/film-entertainment/georgia-production-directory",
        "base_url": "https://www.georgia.org/",
        "category": "Film commission",
        "reliability_notes": "Film commission research source; may help find production companies and public casting leads.",
        "user_rating": 3,
    },
]

FILM_TV_SOURCE_CANDIDATES = [
    {
        "name": "NYU Tisch Casting Calls",
        "source_url": "https://tisch.nyu.edu/casting",
        "base_url": "https://tisch.nyu.edu/",
        "suggested_specific_url": "https://tisch.nyu.edu/casting",
        "category": "Public casting site",
        "reliability_notes": "University and emerging-filmmaker casting board. Review for current film/TV role listings before approving.",
        "user_rating": 3,
    },
    {
        "name": "Columbia University Film Casting",
        "source_url": "https://arts.columbia.edu/film/casting",
        "base_url": "https://arts.columbia.edu/",
        "suggested_specific_url": "https://arts.columbia.edu/film/casting",
        "category": "Public casting site",
        "reliability_notes": "University/MFA film casting source candidate. Useful only if it publishes current actor-facing role notices.",
        "user_rating": 3,
    },
    {
        "name": "New York Women in Film & Television Casting",
        "source_url": "https://www.nywift.org/jobs/",
        "base_url": "https://www.nywift.org/",
        "suggested_specific_url": "https://www.nywift.org/jobs/",
        "category": "Public casting site",
        "reliability_notes": "Film/TV community board candidate. Verify exact page usefulness; some posts may be crew or employment listings.",
        "user_rating": 3,
    },
    {
        "name": "Pennsylvania Film Office Casting Resources",
        "source_url": "https://filminpa.com/",
        "base_url": "https://filminpa.com/",
        "category": "Film commission",
        "reliability_notes": "Regional film resource. Useful for finding production and casting leads; approve only if a public acting-breakdown page is identified.",
        "user_rating": 3,
    },
    {
        "name": "Georgia Film Office Help Wanted Hotline",
        "source_url": "https://www.georgia.org/industries/film-entertainment/georgia-film-tv-production/help-wanted-hotline",
        "base_url": "https://www.georgia.org/",
        "suggested_specific_url": "https://www.georgia.org/industries/film-entertainment/georgia-film-tv-production/help-wanted-hotline",
        "category": "Film commission",
        "reliability_notes": "Regional film/TV page that may surface casting or production leads. Verify performer-role relevance before approval.",
        "user_rating": 3,
    },
    {
        "name": "British Film Institute Opportunities",
        "source_url": "https://www.bfi.org.uk/get-funding-support",
        "base_url": "https://www.bfi.org.uk/",
        "category": "Other",
        "reliability_notes": "English-language international film resource candidate. Treat as research until a role-specific casting page is found.",
        "user_rating": 2,
    },
]


PLACEHOLDER_PATTERNS = [
    r"domain isn'?t connected",
    r"looks like this domain",
    r"domain is for sale",
    r"buy this domain",
    r"parked free",
    r"godaddy",
    r"namecheap",
    r"wix.*domain",
    r"squarespace.*domain",
    r"coming soon",
    r"under construction",
    r"site unavailable",
    r"website coming soon",
    r"no website is currently configured",
]
BREAKDOWN_PATTERNS = [
    r"\bcasting call(s)?\b",
    r"\baudition(s)?\b",
    r"\bself[- ]tape\b",
    r"\bseeking (actors|performers|talent)\b",
    r"\bopen call\b",
    r"\bequity principal audition\b",
    r"\bepa\b",
    r"\becc\b",
    r"\bsubmission instructions\b",
    r"\brole(s)?\b",
]
CASTING_OFFICE_PATTERNS = [r"\bcasting director\b", r"\bcasting office\b", r"\bcast by\b", r"\bcasting for\b"]
PRODUCTION_COMPANY_PATTERNS = [r"\bproduction company\b", r"\bproductions\b", r"\bstudio\b", r"\bfilms?\b"]
REGIONAL_RESOURCE_PATTERNS = [r"\bfilm commission\b", r"\bproduction directory\b", r"\bshooting in\b", r"\bregional\b"]


@dataclass
class SourceHealthResult:
    source_health: str
    suggested_classification: str
    health_reason: str
    http_status: int | None = None
    page_title: str | None = None
    redirect_target: str | None = None
    visible_text_excerpt: str | None = None
    submitted_url: str | None = None
    final_resolved_url: str | None = None
    source_usefulness: str = "Needs Review"
    verification_notes: str | None = None


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self._in_title = False
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if not text:
            return
        if self._in_title:
            self.title_parts.append(text)
        elif not self._skip_depth:
            self.text_parts.append(text)

    @property
    def title(self) -> str | None:
        title = " ".join(self.title_parts).strip()
        return title[:300] if title else None

    @property
    def visible_text(self) -> str:
        return " ".join(self.text_parts)


class SourceResearchService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self) -> list[SourceResearchItem]:
        self.ensure_suggestions()
        return list(
            self.db.scalars(
                select(SourceResearchItem)
                .where(SourceResearchItem.deleted.is_(False))
                .where(SourceResearchItem.rejected_by_user.is_(False))
                .where(SourceResearchItem.source_usefulness != "Not Useful")
                .where(SourceResearchItem.source_classification != "Not Useful")
                .where(SourceResearchItem.source_health.notin_(BAD_SOURCE_HEALTH_STATUSES))
                .order_by(
                    SourceResearchItem.status.asc(),
                    SourceResearchItem.user_rating.desc().nullslast(),
                    SourceResearchItem.updated_at.desc(),
                )
            )
        )

    def archive(self) -> list[SourceResearchItem]:
        return list(
            self.db.scalars(
                select(SourceResearchItem)
                .where(SourceResearchItem.deleted.is_(True))
                .order_by(SourceResearchItem.deleted_at.desc().nullslast())
            )
        )

    def create(self, payload: SourceResearchItemCreate) -> SourceResearchItem:
        data = payload.model_dump()
        data["base_url"] = data.get("base_url") or data.get("source_url")
        data["source_url"] = data.get("base_url")
        if self._matches_deleted_source(data):
            raise ValueError("Source was previously rejected or deleted.")
        data["deleted"] = False
        data["deleted_at"] = None
        data["rejected_by_user"] = False
        data["previous_status"] = None
        item = SourceResearchItem(**data)
        item.provider_key = self._provider_key(item.name)
        self._apply_health_check(item)
        self._soft_delete_if_bad_source(item)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def find_new_sources(self, discovery_mode: str | None = None) -> list[SourceResearchItem]:
        candidates = self._source_candidates(discovery_mode)
        created = self._add_suggestions(candidates)
        self.db.commit()
        for item in created:
            self.db.refresh(item)
        return created

    def _source_candidates(self, discovery_mode: str | None) -> list[dict]:
        if discovery_mode == "FilmTV":
            return FILM_TV_SOURCE_CANDIDATES
        return DISCOVERABLE_SOURCE_CANDIDATES

    def update(self, item_id: UUID, payload: SourceResearchItemUpdate) -> SourceResearchItem:
        item = self._get(item_id)
        before = self._source_snapshot(item)
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, key, value)
        if payload.name:
            item.provider_key = self._provider_key(payload.name)
        if payload.base_url is not None:
            item.source_url = payload.base_url
        if payload.status == "Researching":
            item.last_researched_date = datetime.now(timezone.utc)
            self._apply_health_check(item)
        self._soft_delete_if_bad_source(item)
        if payload.status == "Approved":
            self._apply_health_check(item)
            self._soft_delete_if_bad_source(item)
            if item.deleted:
                self._set_provider_enabled(item, False)
                self._log_source_changes(item, before, item.rejection_reason or "Source was not useful and was removed from normal source queues.")
                self.db.commit()
                self.db.refresh(item)
                return item
            if not self._valid_breakdown_source(item):
                item.status = "Deleted" if item.deleted else "Researching"
                item.approved_by_user = False
                self._set_provider_enabled(item, False)
                self._log_source_changes(item, before, "Source approval blocked by exact URL verification.")
                self.db.commit()
                self.db.refresh(item)
                return item
            item.approved_by_user = True
            item.approved_discovery_url = item.approved_discovery_url or item.suggested_specific_url or item.base_url
            self._set_provider_enabled(item, False)
        if payload.status in {"Rejected", "Paused", "Suggested", "Researching", "Deleted"}:
            self._set_provider_enabled(item, False)
        if payload.status == "Deleted":
            item.deleted = True
            item.deleted_at = item.deleted_at or datetime.now(timezone.utc)
            item.rejected_by_user = True
        self._soft_delete_if_bad_source(item)
        if payload.status == "Active":
            self.add_to_discovery(item.id)
            self.db.refresh(item)
            return item
        self._log_source_changes(item, before, "User updated source research item.")
        self.db.commit()
        self.db.refresh(item)
        return item

    def reject(self, item_id: UUID, rejection_reason: str | None = None) -> SourceResearchItem:
        item = self._get(item_id)
        before = self._source_snapshot(item)
        if not item.deleted:
            item.previous_status = item.status
        item.status = "Deleted"
        item.deleted = True
        item.deleted_at = datetime.now(timezone.utc)
        item.rejected_by_user = True
        item.rejection_reason = rejection_reason or item.rejection_reason
        self._set_provider_enabled(item, False)
        self._log_source_changes(item, before, item.rejection_reason or "Source removed. It will no longer be suggested.")
        self.db.commit()
        self.db.refresh(item)
        return item

    def restore(self, item_id: UUID) -> SourceResearchItem:
        item = self._get(item_id, include_deleted=True)
        before = self._source_snapshot(item)
        item.deleted = False
        item.deleted_at = None
        item.rejected_by_user = False
        item.status = item.previous_status or "Researching"
        item.previous_status = None
        self._log_source_changes(item, before, "Developer/admin restored deleted source.")
        self.db.commit()
        self.db.refresh(item)
        return item

    def delete(self, item_id: UUID) -> None:
        self.reject(item_id)

    def add_to_discovery(self, item_id: UUID) -> SourceResearchItem:
        item = self._get(item_id)
        before = self._source_snapshot(item)
        if item.deleted:
            raise ValueError("Deleted sources must be restored before activation")
        self._apply_health_check(item)
        if not self._valid_breakdown_source(item):
            item.status = "Researching" if not item.deleted else "Deleted"
            item.approved_by_user = False
            self._set_provider_enabled(item, False)
            self._log_source_changes(item, before, "Source activation blocked by exact URL verification.")
            self.db.commit()
            self.db.refresh(item)
            return item
        provider_key = self._provider_key(item.name)
        item.provider_key = provider_key
        item.status = "Active"
        item.approved_by_user = True
        item.approved_discovery_url = item.approved_discovery_url or item.suggested_specific_url or item.base_url
        if not item.approved_discovery_url and not item.base_url:
            raise ValueError("Source needs an approved discovery URL or base URL before activation")
        item.added_to_discovery_at = datetime.now(timezone.utc)
        item.last_checked_date = item.last_checked_date or datetime.now(timezone.utc)
        discovery_url = item.approved_discovery_url or item.base_url
        provider = self.db.scalars(
            select(DiscoveryProviderSettings).where(DiscoveryProviderSettings.provider_key == provider_key)
        ).first()
        if not provider:
            provider = DiscoveryProviderSettings(
                provider_key=provider_key,
                display_name=item.name,
                tier=self._tier(item.category),
                category=item.category,
                source_type=self._source_type(item.category),
                enabled=True,
                poll_frequency_minutes=1440,
                priority=500,
                authentication_method="Public URL" if discovery_url else "Manual Entry",
                supported_authentication_methods=["Public URL", "Manual Entry"],
                reliability_score=self._reliability(item),
                notes=item.notes or item.reliability_notes,
                provider_metadata={
                    "provider_kind": "user_researched_source",
                    "source_url": discovery_url,
                    "base_url": item.base_url,
                    "suggested_specific_url": item.suggested_specific_url,
                    "approved_discovery_url": item.approved_discovery_url,
                    "source_research_item_id": str(item.id),
                },
                health_status="research_approved",
                health_message="User approved this source for discovery monitoring. Implementation remains safe and source-specific.",
            )
            self.db.add(provider)
        else:
            provider.enabled = True
            provider.display_name = item.name
            provider.category = item.category
            provider.source_type = self._source_type(item.category)
            provider.reliability_score = self._reliability(item)
            provider.notes = item.notes or item.reliability_notes
            provider.provider_metadata = {
                **(provider.provider_metadata or {}),
                "provider_kind": "user_researched_source",
                "source_url": discovery_url,
                "base_url": item.base_url,
                "suggested_specific_url": item.suggested_specific_url,
                "approved_discovery_url": item.approved_discovery_url,
                "source_research_item_id": str(item.id),
            }
        self._log_source_changes(item, before, "User approved source for active discovery monitoring.")
        self.db.commit()
        self.db.refresh(item)
        return item

    def _source_snapshot(self, item: SourceResearchItem) -> dict:
        fields = [
            "status",
            "approved_by_user",
            "deleted",
            "deleted_at",
            "rejection_reason",
            "approved_discovery_url",
            "url_health_status",
            "source_usefulness",
            "source_classification",
        ]
        return {field: getattr(item, field, None) for field in fields}

    def _log_source_changes(self, item: SourceResearchItem, before: dict, reason: str) -> None:
        ManualOverrideService(self.db).log_many(
            entity_type="SourceResearchItem",
            entity_id=item.id,
            before=before,
            after=self._source_snapshot(item),
            reason=reason,
        )

    def ensure_suggestions(self) -> None:
        self._add_suggestions(SUGGESTED_SOURCES)
        self._health_check_unchecked_sources()
        self._soft_delete_existing_bad_sources()
        self.db.commit()

    def _add_suggestions(self, sources: list[dict]) -> list[SourceResearchItem]:
        existing_items = list(self.db.scalars(select(SourceResearchItem)))
        existing_names = {self._name_signature(item.name) for item in existing_items}
        existing_domains = {domain for item in existing_items if not item.deleted for domain in self._item_domains(item)}
        existing_urls = {url for item in existing_items if not item.deleted for url in self._item_urls(item)}
        blocked_name_aliases = {
            alias
            for item in existing_items
            if item.deleted
            for alias in self._name_aliases(item.name)
        }
        blocked_domains = {
            domain
            for item in existing_items
            if item.deleted
            for domain in self._item_domains(item)
        }
        blocked_urls = {
            url
            for item in existing_items
            if item.deleted
            for url in self._item_urls(item)
        }
        created: list[SourceResearchItem] = []
        for source in sources:
            if self._looks_like_individual_breakdown(source):
                continue
            if self._matches_deleted_source(source, existing_items):
                continue
            source_name = self._name_signature(source["name"])
            source_name_aliases = self._name_aliases(source["name"])
            source_urls = self._source_urls(source)
            source_domains = {self._domain(url) for url in source_urls if url}
            if (
                source_name in existing_names
                or bool(source_domains & existing_domains)
                or bool(source_urls & existing_urls)
                or bool(source_name_aliases & blocked_name_aliases)
                or bool(source_domains & blocked_domains)
                or bool(source_urls & blocked_urls)
            ):
                continue
            payload = {**source}
            payload["source_url"] = payload.get("base_url") or payload.get("source_url")
            item = SourceResearchItem(
                **payload,
                status="Suggested",
                suggested_by_ai=True,
                approved_by_user=False,
                provider_key=self._provider_key(source["name"]),
            )
            self._apply_health_check(item)
            self._soft_delete_if_bad_source(item)
            if item.deleted:
                self.db.add(item)
                existing_names.add(source_name)
                existing_domains.update(source_domains)
                existing_urls.update(source_urls)
                continue
            self.db.add(item)
            created.append(item)
            existing_names.add(source_name)
            existing_domains.update(source_domains)
            existing_urls.update(source_urls)
        return created

    def _looks_like_individual_breakdown(self, source: dict) -> bool:
        url_values = [source.get("source_url"), source.get("suggested_specific_url"), source.get("base_url")]
        for value in url_values:
            path = urlparse(str(value or "")).path.lower()
            if re.search(r"/job/[^/]+", path) or re.search(r"/casting/[^/]+", path):
                return True
        return False

    def _apply_health_check(self, item: SourceResearchItem) -> None:
        submitted_url = item.approved_discovery_url or item.suggested_specific_url or item.base_url or item.source_url
        result = self._health_check(submitted_url)
        item.organization_name = item.organization_name or item.name
        item.organization_legitimacy = self._organization_legitimacy(item)
        item.submitted_url = result.submitted_url or submitted_url
        item.final_resolved_url = result.final_resolved_url
        item.url_health_status = result.source_health
        item.source_usefulness = result.source_usefulness
        item.source_classification = result.suggested_classification
        item.verification_notes = result.verification_notes or result.health_reason
        item.source_health = result.source_health
        item.suggested_classification = result.suggested_classification
        item.health_reason = result.health_reason
        item.http_status = result.http_status
        item.page_title = result.page_title
        item.redirect_target = result.redirect_target
        item.visible_text_excerpt = result.visible_text_excerpt
        item.last_checked_date = datetime.now(timezone.utc)
        if result.source_health in {"Placeholder Website", "Dead / Unavailable Domain", "No Meaningful Content"}:
            item.rejection_reason = result.health_reason
            item.suggested_classification = "Rejected"
            item.source_classification = "Rejected"
            item.source_usefulness = "Not Useful"
            item.verification_notes = self._guardrail_rejection_note(item, result)
            self._soft_delete_if_bad_source(item)
        self._soft_delete_if_bad_source(item)

    def _health_check(self, url: str | None) -> SourceHealthResult:
        if not url:
            return SourceHealthResult(
                source_health="Needs Review",
                suggested_classification="Needs Review",
                health_reason="No URL was provided for this source.",
                source_usefulness="Needs Review",
                verification_notes="Cannot approve a source until an exact URL is submitted and verified.",
            )
        requested_url = url if "://" in url else f"https://{url}"
        try:
            request = Request(
                requested_url,
                headers={"User-Agent": "WorkingActorOS/0.1 source-health-check"},
            )
            with urlopen(request, timeout=10) as response:
                status = getattr(response, "status", None)
                final_url = response.geturl()
                content_type = response.headers.get("content-type", "")
                body = response.read(500_000)
        except HTTPError as error:
            return SourceHealthResult(
                source_health="Dead / Unavailable Domain" if error.code >= 400 else "Needs Review",
                suggested_classification="Rejected" if error.code >= 400 else "Needs Review",
                health_reason=f"HTTP status {error.code}; source is not currently usable as a public breakdown source.",
                http_status=error.code,
                submitted_url=requested_url,
                redirect_target=getattr(error, "url", None),
                final_resolved_url=getattr(error, "url", None),
                source_usefulness="Not Useful" if error.code >= 400 else "Needs Review",
                verification_notes="Exact URL failed HTTP verification; organization recognition is not enough for approval.",
            )
        except (URLError, TimeoutError, ValueError):
            return SourceHealthResult(
                source_health="Dead / Unavailable Domain",
                suggested_classification="Rejected",
                health_reason="Domain unavailable or could not be reached during source health check.",
                submitted_url=requested_url,
                source_usefulness="Not Useful",
                verification_notes="Exact URL could not be reached; reject this URL or add a corrected URL manually.",
            )
        if "text/html" not in content_type and "text/plain" not in content_type and content_type:
            return SourceHealthResult(
                source_health="Needs Review",
                suggested_classification="Needs Review",
                health_reason=f"Unsupported content type for source classification: {content_type}.",
                http_status=status,
                submitted_url=requested_url,
                redirect_target=final_url,
                final_resolved_url=final_url,
                source_usefulness="Needs Review",
                verification_notes="Exact URL loaded, but the content type is not a normal readable page.",
            )
        parser = VisibleTextParser()
        html = body.decode("utf-8", errors="ignore")
        parser.feed(html)
        text = " ".join(parser.visible_text.split())
        combined = f"{parser.title or ''} {text}".lower()
        excerpt = text[:1000] if text else None
        if any(re.search(pattern, combined) for pattern in PLACEHOLDER_PATTERNS):
            return SourceHealthResult(
                source_health="Placeholder Website",
                suggested_classification="Rejected",
                health_reason="Placeholder domain / no active website.",
                http_status=status,
                page_title=parser.title,
                submitted_url=requested_url,
                redirect_target=final_url,
                final_resolved_url=final_url,
                visible_text_excerpt=excerpt,
                source_usefulness="Not Useful",
                verification_notes="Exact URL resolved to placeholder/domain parking content. Reject this URL unless a corrected official URL is provided.",
            )
        if len(text) < 120:
            return SourceHealthResult(
                source_health="No Meaningful Content",
                suggested_classification="Rejected",
                health_reason="No meaningful public content was found on this page.",
                http_status=status,
                page_title=parser.title,
                submitted_url=requested_url,
                redirect_target=final_url,
                final_resolved_url=final_url,
                visible_text_excerpt=excerpt,
                source_usefulness="Not Useful",
                verification_notes="Exact URL loaded but did not contain enough useful visible text for source approval.",
            )
        classification, reason, usefulness = self._classify_source_text(combined)
        return SourceHealthResult(
            source_health="Active",
            suggested_classification=classification,
            health_reason=reason,
            http_status=status,
            page_title=parser.title,
            submitted_url=requested_url,
            redirect_target=final_url,
            final_resolved_url=final_url,
            visible_text_excerpt=excerpt,
            source_usefulness=usefulness,
            verification_notes=reason,
        )

    def _classify_source_text(self, text: str) -> tuple[str, str, str]:
        if any(re.search(pattern, text) for pattern in BREAKDOWN_PATTERNS):
            return (
                "Valid Breakdown Source",
                "Publicly lists casting calls, auditions, roles, or performer submission information.",
                "Useful Breakdown Source",
            )
        if any(re.search(pattern, text) for pattern in CASTING_OFFICE_PATTERNS):
            return (
                "Casting Office",
                "Useful for relationship tracking, but no clear public breakdown feed was detected.",
                "Useful Non-Breakdown Source",
            )
        if any(re.search(pattern, text) for pattern in REGIONAL_RESOURCE_PATTERNS):
            return (
                "Regional Resource",
                "Useful for regional production research, but not a direct breakdown source.",
                "Useful Non-Breakdown Source",
            )
        if any(re.search(pattern, text) for pattern in PRODUCTION_COMPANY_PATTERNS):
            return (
                "Production Company",
                "Useful for watch lists or company research, but not a direct breakdown source.",
                "Useful Non-Breakdown Source",
            )
        return "Not Useful", "Active website found, but no actor-facing public breakdown signals were detected.", "Not Useful"

    def _valid_breakdown_source(self, item: SourceResearchItem) -> bool:
        return bool(
            item.url_health_status == "Active"
            and item.source_classification == "Valid Breakdown Source"
            and item.source_usefulness == "Useful Breakdown Source"
            and not item.deleted
        )

    def _organization_legitimacy(self, item: SourceResearchItem) -> str:
        if self._provider_key(item.name) in KNOWN_PROVIDER_KEYS.values() or item.category in {
            "Casting office",
            "Film commission",
            "Production company",
            "Public casting site",
            "Theater company",
        }:
            return "Recognized Organization"
        return "Unverified Organization"

    def _guardrail_rejection_note(self, item: SourceResearchItem, result: SourceHealthResult) -> str:
        if item.organization_legitimacy == "Recognized Organization":
            return (
                "Recognized organization, but this URL is not a usable source. "
                f"{result.health_reason} Add a corrected official URL manually or reject this source."
            )
        return result.verification_notes or result.health_reason

    def _health_check_unchecked_sources(self) -> None:
        items = list(
            self.db.scalars(
                select(SourceResearchItem)
                .where(SourceResearchItem.deleted.is_(False))
                .where(SourceResearchItem.source_health == "Unchecked")
            )
        )
        for item in items:
            self._apply_health_check(item)
            self._soft_delete_if_bad_source(item)
            if item.deleted:
                continue
            if item.status in {"Approved", "Active"} and not self._valid_breakdown_source(item):
                item.previous_status = item.status
                item.status = "Researching"
                item.approved_by_user = False
                self._set_provider_enabled(item, False)

    def _soft_delete_existing_bad_sources(self) -> None:
        items = list(
            self.db.scalars(
                select(SourceResearchItem)
                .where(SourceResearchItem.deleted.is_(False))
                .where(
                    or_(
                        SourceResearchItem.source_usefulness == "Not Useful",
                        SourceResearchItem.source_classification == "Not Useful",
                        SourceResearchItem.source_health.in_(BAD_SOURCE_HEALTH_STATUSES),
                        SourceResearchItem.url_health_status.in_(BAD_SOURCE_HEALTH_STATUSES),
                    )
                )
            )
        )
        for item in items:
            self._soft_delete_if_bad_source(item)

    def _get(self, item_id: UUID, include_deleted: bool = False) -> SourceResearchItem:
        item = self.db.get(SourceResearchItem, item_id)
        if not item or (item.deleted and not include_deleted):
            raise ValueError("Source research item not found")
        return item

    def _provider_key(self, name: str) -> str:
        signature = self._name_signature(name)
        return KNOWN_PROVIDER_KEYS.get(signature, re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:150])

    def _name_signature(self, name: str | None) -> str:
        return re.sub(r"[^a-z0-9]+", "", (name or "").lower())

    def _name_aliases(self, name: str | None) -> set[str]:
        text = (name or "").lower()
        words = re.findall(r"[a-z0-9]+", text)
        meaningful_words = [word for word in words if word not in COMMON_SOURCE_NAME_WORDS]
        aliases = {self._name_signature(name)}
        if meaningful_words:
            aliases.add("".join(meaningful_words))
        return {alias for alias in aliases if alias}

    def _normalize_url(self, url: str | None) -> str | None:
        if not url:
            return None
        parsed = urlparse(url if "://" in url else f"https://{url}")
        domain = self._domain(url)
        path = parsed.path.rstrip("/")
        return f"{domain}{path}".lower() if domain else None

    def _domain(self, url: str | None) -> str | None:
        if not url:
            return None
        parsed = urlparse(url if "://" in url else f"https://{url}")
        host = (parsed.hostname or "").lower()
        if host.startswith("www."):
            host = host[4:]
        return host or None

    def _source_urls(self, source: dict) -> set[str]:
        return {
            normalized
            for normalized in (
                self._normalize_url(source.get("source_url")),
                self._normalize_url(source.get("base_url")),
                self._normalize_url(source.get("suggested_specific_url")),
                self._normalize_url(source.get("approved_discovery_url")),
                self._normalize_url(source.get("submitted_url")),
                self._normalize_url(source.get("final_resolved_url")),
                self._normalize_url(source.get("redirect_target")),
            )
            if normalized
        }

    def _source_domains(self, source: dict) -> set[str]:
        return {
            domain
            for domain in (
                self._domain(source.get("source_url")),
                self._domain(source.get("base_url")),
                self._domain(source.get("suggested_specific_url")),
                self._domain(source.get("approved_discovery_url")),
                self._domain(source.get("submitted_url")),
                self._domain(source.get("final_resolved_url")),
                self._domain(source.get("redirect_target")),
            )
            if domain
        }

    def _is_bad_source(self, item: SourceResearchItem) -> bool:
        return bool(
            item.source_usefulness == "Not Useful"
            or item.source_classification == "Not Useful"
            or item.source_health in BAD_SOURCE_HEALTH_STATUSES
            or item.url_health_status in BAD_SOURCE_HEALTH_STATUSES
        )

    def _soft_delete_if_bad_source(self, item: SourceResearchItem) -> None:
        if not self._is_bad_source(item):
            return
        if not item.deleted:
            item.previous_status = item.status
        item.status = "Deleted"
        item.deleted = True
        item.deleted_at = item.deleted_at or datetime.now(timezone.utc)
        item.rejection_reason = item.rejection_reason or item.health_reason or "Source was not useful for actor-facing breakdown discovery."
        if item.source_classification == "Not Useful":
            item.suggested_classification = "Not Useful"
        elif item.source_health in BAD_SOURCE_HEALTH_STATUSES or item.url_health_status in BAD_SOURCE_HEALTH_STATUSES:
            item.suggested_classification = "Rejected"
            item.source_classification = "Rejected"
            item.source_usefulness = "Not Useful"
        self._set_provider_enabled(item, False)

    def _matches_deleted_source(self, source: dict, existing_items: list[SourceResearchItem] | None = None) -> bool:
        items = existing_items if existing_items is not None else list(self.db.scalars(select(SourceResearchItem)))
        source_name_aliases = self._name_aliases(source.get("name"))
        source_urls = self._source_urls(source)
        source_domains = self._source_domains(source)
        for item in items:
            if not (item.deleted or item.rejected_by_user or self._is_bad_source(item)):
                continue
            if source_name_aliases & self._name_aliases(item.name):
                return True
            if source_urls & self._item_urls(item):
                return True
            if source_domains & self._item_domains(item):
                return True
        return False

    def _item_urls(self, item: SourceResearchItem) -> set[str]:
        return {
            normalized
            for normalized in (
                self._normalize_url(item.source_url),
                self._normalize_url(item.base_url),
                self._normalize_url(item.suggested_specific_url),
                self._normalize_url(item.approved_discovery_url),
                self._normalize_url(item.submitted_url),
                self._normalize_url(item.final_resolved_url),
                self._normalize_url(item.redirect_target),
            )
            if normalized
        }

    def _item_domains(self, item: SourceResearchItem) -> set[str]:
        return {
            domain
            for domain in (
                self._domain(item.source_url),
                self._domain(item.base_url),
                self._domain(item.suggested_specific_url),
                self._domain(item.approved_discovery_url),
                self._domain(item.submitted_url),
                self._domain(item.final_resolved_url),
                self._domain(item.redirect_target),
            )
            if domain
        }

    def _source_type(self, category: str) -> str:
        return {
            "Public casting site": "public_breakdowns",
            "Casting office": "casting_office",
            "Film commission": "film_commission",
            "Social media account": "social",
            "Production company": "production_company",
            "Theater company": "theater_company",
            "Talent platform": "platform",
        }.get(category, "other")

    def _tier(self, category: str) -> int:
        return {
            "Talent platform": 1,
            "Public casting site": 2,
            "Casting office": 3,
            "Social media account": 4,
            "Film commission": 5,
        }.get(category, 5)

    def _reliability(self, item: SourceResearchItem) -> float:
        if item.user_rating:
            return min(1.0, max(0.2, item.user_rating / 5))
        return {
            "Public casting site": 0.72,
            "Casting office": 0.82,
            "Film commission": 0.68,
            "Social media account": 0.55,
            "Production company": 0.7,
            "Theater company": 0.74,
            "Talent platform": 0.9,
        }.get(item.category, 0.6)

    def _set_provider_enabled(self, item: SourceResearchItem, enabled: bool) -> None:
        if not item.provider_key:
            return
        provider = self.db.scalars(
            select(DiscoveryProviderSettings).where(DiscoveryProviderSettings.provider_key == item.provider_key)
        ).first()
        if provider:
            provider.enabled = enabled
