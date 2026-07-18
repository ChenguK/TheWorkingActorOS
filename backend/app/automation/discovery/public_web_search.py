from __future__ import annotations

import html
import logging
import re
import urllib.request
from dataclasses import dataclass, field
from datetime import date
from typing import Any
from urllib.parse import urlparse

from app.automation.discovery.classification import classify_breakdown_text
from app.automation.discovery.contracts import NormalizedOpportunity
from app.core.config import get_settings
from app.db.models import ActorProfile
from app.services.breakdown_details_service import BreakdownDetailsService


logger = logging.getLogger(__name__)

PARALLEL_BREAKDOWN_OBJECTIVE = (
    "Find current public acting breakdowns for film or television roles. "
    "Focus on active lead, supporting, principal, co-star, guest star, recurring, or series regular roles. "
    "Exclude background, extras, crew, classes, workshops, brand ambassadors, staff jobs, and expired listings. "
    "Prefer self-tape opportunities or in-person auditions within the actor's travel rules."
)
PARALLEL_ADVANCED_SETTINGS = {"max_results": 10}


@dataclass
class PublicWebSearchResult:
    configured: bool
    run: bool
    provider: str = "parallel"
    reason: str | None = None
    search_queries: list[str] = field(default_factory=list)
    candidate_urls: list[str] = field(default_factory=list)
    candidate_pages_found: int = 0
    candidates_rejected: int = 0
    candidate_reports: list[dict] = field(default_factory=list)
    normalized: list[NormalizedOpportunity] = field(default_factory=list)


class PublicWebBreakdownSearch:
    def __init__(self, actor: ActorProfile | None = None, parallel_client: Any | None = None) -> None:
        self.actor = actor
        self.settings = get_settings()
        self._parallel_client = parallel_client

    def configured(self) -> bool:
        return (
            str(self.settings.web_search_provider or "").lower() == "parallel"
            and bool(self.settings.parallel_api_key)
        )

    def search(self, discovery_mode: str) -> PublicWebSearchResult:
        if discovery_mode != "FilmTV":
            return PublicWebSearchResult(
                configured=self.configured(),
                run=False,
                reason="Public web search currently runs for Film/TV breakdown discovery only.",
            )
        if not self.configured():
            return PublicWebSearchResult(
                configured=False,
                run=False,
                reason="Public web search is not configured. Only approved active sources were searched.",
            )

        queries = self.search_queries()
        client = self._client()
        response = client.search(
            search_queries=queries,
            mode="advanced",
            advanced_settings=PARALLEL_ADVANCED_SETTINGS,
            objective=PARALLEL_BREAKDOWN_OBJECTIVE,
        )
        self._debug_log(
            "Parallel public web search response summary",
            {
                "queries": queries,
                "objective": PARALLEL_BREAKDOWN_OBJECTIVE,
                "response_summary": self._response_summary(response),
            },
        )
        candidates = self._extract_candidate_records(response)
        urls = [candidate["url"] for candidate in candidates]
        self._debug_log("Parallel candidate URL extraction", {"candidate_url_count": len(urls), "candidate_urls": urls})
        normalized: list[NormalizedOpportunity] = []
        candidate_reports: list[dict] = []
        rejected = 0
        rejection_reasons = {"fetch_failed": 0, "not_actor_facing_breakdown": 0}
        for candidate in candidates:
            url = candidate["url"]
            report = {
                "page_title": candidate.get("page_title") or self._title_from_url(url),
                "url": url,
                "source": "Parallel Public Web Search",
                "decision": "Rejected",
                "rejection_reason": "Unknown",
            }
            page_text = self._fetch_visible_text(url)
            if not page_text:
                rejected += 1
                rejection_reasons["fetch_failed"] += 1
                report["rejection_reason"] = "Fetch failed"
                candidate_reports.append(report)
                continue
            item = self._normalize_candidate(url, page_text)
            if item:
                normalized.append(item)
                report["decision"] = "Parsed"
                report["rejection_reason"] = None
            else:
                rejected += 1
                rejection_reasons["not_actor_facing_breakdown"] += 1
                report["rejection_reason"] = "Not an acting role"
            candidate_reports.append(report)
        self._debug_log(
            "Parallel public web search filtering summary",
            {
                "candidate_url_count": len(urls),
                "normalized_count": len(normalized),
                "rejected_count": rejected,
                "rejection_reason_counts": rejection_reasons,
            },
        )
        return PublicWebSearchResult(
            configured=True,
            run=True,
            search_queries=queries,
            candidate_urls=urls,
            candidate_pages_found=len(urls),
            candidates_rejected=rejected,
            candidate_reports=candidate_reports,
            normalized=normalized,
        )

    def search_queries(self) -> list[str]:
        actor = self.actor
        languages = [language.lower() for language in (actor.languages if actor else [])]
        language_note = "English-language " if not languages or "english" in languages else ""
        age_min = actor.playable_age_min if actor else 25
        age_max = actor.secondary_playable_age_max or actor.playable_age_max if actor else 40
        gender = "woman"
        ethnicity_terms = self._ethnicity_terms(actor)
        current_archetypes = self._current_archetype_terms(actor)
        queries = [
            f"{language_note}current SAG-AFTRA film casting {ethnicity_terms} {gender} {age_min}-{age_max} self tape",
            f"{language_note}current independent feature casting {ethnicity_terms} female supporting role self tape",
            f"{language_note}current union short film casting {ethnicity_terms} woman {age_min}-{age_max}",
            f"{language_note}current TV co-star casting {ethnicity_terms} woman self tape",
            f"{language_note}current film casting call {ethnicity_terms} woman 30s open ethnicity",
            f"{language_note}current feature film casting female {ethnicity_terms} any ethnicity SAG-AFTRA",
            f"{language_note}current principal role casting {ethnicity_terms} woman film self tape",
            f"{language_note}current guest star casting {ethnicity_terms} woman TV self tape",
            f"{language_note}current streaming series casting {ethnicity_terms} woman co-star self tape",
            f"{language_note}current non-union feature film casting {ethnicity_terms} woman principal role",
            f"{language_note}current New York film casting {ethnicity_terms} woman self tape",
            f"{language_note}current Philadelphia film casting {ethnicity_terms} woman self tape",
            f"{language_note}current regional film casting {ethnicity_terms} female actor",
            f"{language_note}current student film casting {ethnicity_terms} woman 25-40",
            f"{language_note}current MFA film casting {ethnicity_terms} woman actor",
            f"{language_note}current emerging filmmaker casting {ethnicity_terms} woman",
            f"{language_note}current open ethnicity principal role casting woman film",
            f"{language_note}current TV pilot casting {ethnicity_terms} woman self tape",
            f"{language_note}current web series casting {ethnicity_terms} woman principal",
            f"{language_note}current short film casting call {ethnicity_terms} female lead",
        ]
        for archetype in current_archetypes[:3]:
            queries.append(
                f"{language_note}current film television casting call {ethnicity_terms} woman {age_min}-{age_max} {archetype} self tape"
            )
        return [re.sub(r"\s+", " ", query).strip() for query in queries]

    def _client(self):
        if self._parallel_client:
            return self._parallel_client
        try:
            from parallel import Parallel
        except ImportError as exc:
            raise RuntimeError(
                "parallel-web is not installed. Run `pip install parallel-web` in the backend virtual environment."
            ) from exc
        return Parallel(api_key=self.settings.parallel_api_key)

    def _normalize_candidate(self, url: str, page_text: str) -> NormalizedOpportunity | None:
        classification = classify_breakdown_text(page_text)
        if classification.classification in {"Non-Acting Job", "Crew Job", "Unknown"}:
            return None
        details = BreakdownDetailsService().from_fields(
            role=self._role(page_text),
            project=self._project(page_text, url),
            union=self._union(page_text),
            location=self._location(page_text),
            description=page_text,
            source_name="Parallel Public Web Search",
            source_url=url,
            source_type="public_web_search",
            import_method="Parallel public web search",
            discovered_at=date.today().isoformat(),
            category="Film/TV Public Web Breakdown",
            audition_type=self._audition_type(page_text),
            raw_visible_text=page_text,
        )
        return NormalizedOpportunity(
            role=details["role_details"].get("role_name") or self._role(page_text),
            project=details["production_details"].get("project_title") or self._project(page_text, url),
            union=details["production_details"].get("union_status") or self._union(page_text),
            location=details["production_details"].get("shoot_location") or self._location(page_text),
            description=page_text,
            original_post_url=url,
            audition_type=details["role_details"].get("audition_type") or self._audition_type(page_text),
            audition_travel_hours=0 if self._audition_type(page_text) in {"Self-Tape", "Virtual"} else None,
            travel_covered=None,
            housing_covered=None,
            source_name="Parallel Public Web Search",
            category="Film/TV Public Web Breakdown",
            source_reliability_score=0.68,
            breakdown_classification=classification.classification,
            rejection_reason=classification.rejection_reason,
            source_metadata={
                **details["source_metadata"],
                "provider": "parallel",
                "source_type": "public_web_search",
                "source_url": url,
                "discovery_note": "Candidate found by configured Parallel public web search and then verified as a public actor-facing breakdown.",
            },
            production_details=details["production_details"],
            role_details=details["role_details"],
            ai_summary=details["ai_summary"],
        )

    def _extract_urls(self, response: Any) -> list[str]:
        urls: list[str] = []

        def visit(value: Any) -> None:
            if value is None:
                return
            if isinstance(value, str):
                if value.startswith(("http://", "https://")):
                    urls.append(value)
                return
            if hasattr(value, "model_dump"):
                try:
                    visit(value.model_dump())
                    return
                except Exception:
                    pass
            if isinstance(value, dict):
                for key, item in value.items():
                    if str(key).lower() in {"url", "link", "source_url", "href"}:
                        visit(item)
                    elif isinstance(item, (dict, list, tuple)):
                        visit(item)
                return
            if isinstance(value, (list, tuple)):
                for item in value:
                    visit(item)
                return
            for attr in ("url", "link", "source_url", "href"):
                if hasattr(value, attr):
                    visit(getattr(value, attr))
            for attr in ("results", "data", "items", "search_results"):
                if hasattr(value, attr):
                    visit(getattr(value, attr))

        visit(response)
        unique: list[str] = []
        seen: set[str] = set()
        for url in urls:
            normalized = self._normalize_url(url)
            if normalized and normalized not in seen:
                seen.add(normalized)
                unique.append(normalized)
        return unique[:30]

    def _extract_candidate_records(self, response: Any) -> list[dict]:
        records: list[dict] = []

        def add(url: Any, title: Any = None) -> None:
            if not isinstance(url, str):
                return
            normalized = self._normalize_url(url)
            if normalized:
                records.append({"url": normalized, "page_title": str(title or "").strip() or None})

        def visit(value: Any) -> None:
            if value is None:
                return
            if hasattr(value, "model_dump"):
                try:
                    visit(value.model_dump())
                    return
                except Exception:
                    pass
            if isinstance(value, dict):
                url = value.get("url") or value.get("link") or value.get("source_url") or value.get("href")
                if url:
                    add(url, value.get("title") or value.get("page_title"))
                for item in value.values():
                    if isinstance(item, (dict, list, tuple)):
                        visit(item)
                return
            if isinstance(value, (list, tuple)):
                for item in value:
                    visit(item)
                return
            url = getattr(value, "url", None) or getattr(value, "link", None) or getattr(value, "source_url", None) or getattr(value, "href", None)
            if url:
                add(url, getattr(value, "title", None) or getattr(value, "page_title", None))
            for attr in ("results", "data", "items", "search_results"):
                if hasattr(value, attr):
                    visit(getattr(value, attr))

        visit(response)
        unique: list[dict] = []
        seen: set[str] = set()
        for record in records:
            url = record["url"]
            if url not in seen:
                seen.add(url)
                unique.append(record)
        return unique[:30]

    def _title_from_url(self, url: str) -> str:
        parsed = urlparse(url)
        path = parsed.path.strip("/").split("/")[-1].replace("-", " ").replace("_", " ")
        return path.title() if path else parsed.netloc.removeprefix("www.")

    def _response_summary(self, response: Any) -> dict:
        if hasattr(response, "model_dump"):
            try:
                data = response.model_dump()
                results = data.get("results") or []
                return {
                    "response_type": type(response).__name__,
                    "response_keys": sorted(data.keys()),
                    "result_count": len(results),
                    "first_result_keys": sorted(results[0].keys()) if results else [],
                }
            except Exception:
                pass
        if isinstance(response, dict):
            results = response.get("results") or response.get("data") or response.get("items") or []
            return {
                "response_type": "dict",
                "response_keys": sorted(response.keys()),
                "result_count": len(results) if isinstance(results, list) else None,
            }
        return {"response_type": type(response).__name__}

    def _debug_log(self, message: str, payload: dict) -> None:
        if str(self.settings.environment or "").lower() in {"development", "dev", "local"}:
            logger.info("%s: %s", message, payload)

    def _fetch_visible_text(self, url: str) -> str | None:
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "WorkingActorOS/0.1 user-triggered public breakdown discovery",
                    "Accept": "text/html,application/xhtml+xml,text/plain",
                },
            )
            with urllib.request.urlopen(request, timeout=12) as response:
                content_type = response.headers.get("content-type", "")
                if content_type and "text/html" not in content_type and "text/plain" not in content_type:
                    return None
                body = response.read(500_000).decode("utf-8", errors="ignore")
        except Exception:
            return None
        text = self._clean_visible_page(body)
        return text[:12000] if len(text.split()) >= 25 else None

    def _clean_visible_page(self, html_text: str) -> str:
        text = re.sub(r"(?is)<(script|style|noscript|svg).*?</\1>", " ", html_text)
        text = re.sub(r"(?i)<br\s*/?>", "\n", text)
        text = re.sub(r"(?i)</(p|div|li|h1|h2|h3|h4|section|article)>", "\n", text)
        text = re.sub(r"<[^>]+>", " ", text)
        text = html.unescape(text)
        lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
        useful_lines = [
            line
            for line in lines
            if line
            and not re.search(
                r"^(menu|search|advertisement|privacy policy|terms of use|sign up|log in|subscribe)$",
                line,
                flags=re.I,
            )
        ]
        return "\n".join(useful_lines)

    def _project(self, text: str, url: str) -> str:
        for pattern in [
            r"(?:project|production|title)\s*[:\-]\s*([^\n]+)",
            r"casting\s+(?:for\s+)?['\"]?([^'\"\n]{3,80})",
        ]:
            match = re.search(pattern, text, flags=re.I)
            if match:
                return match.group(1).strip()[:255]
        path = urlparse(url).path.strip("/").split("/")[-1].replace("-", " ").replace("_", " ")
        return path.title()[:255] if path else "Public Web Breakdown"

    def _role(self, text: str) -> str:
        for pattern in [
            r"(?:role|character)\s*[:\-]\s*([^\n]+)",
            r"seeking\s+(?:a|an)?\s*([^\n,.;]{3,80})",
        ]:
            match = re.search(pattern, text, flags=re.I)
            if match:
                return match.group(1).strip(" '\"")[:255]
        return "Performer"

    def _union(self, text: str) -> str:
        lowered = text.lower()
        if "non-union" in lowered:
            return "Non-Union"
        if "sag-aftra" in lowered:
            return "SAG-AFTRA"
        if "union" in lowered:
            return "Union"
        return "Unknown"

    def _location(self, text: str) -> str:
        match = re.search(r"([A-Z][A-Za-z .'-]+,\s[A-Z]{2})(?:\s|$)", text)
        return match.group(1) if match else "See source"

    def _audition_type(self, text: str) -> str:
        lowered = text.lower()
        if "self-tape" in lowered or "self tape" in lowered:
            return "Self-Tape"
        if "zoom" in lowered or "virtual" in lowered:
            return "Virtual"
        if "in-person" in lowered or "in person" in lowered or "open call" in lowered:
            return "In-Person"
        return "Unknown"

    def _ethnicity_terms(self, actor: ActorProfile | None) -> str:
        values = [*(actor.racial_identities if actor else []), *(actor.ethnicities if actor else [])]
        lowered = " ".join(values).lower()
        if any(term in lowered for term in ["black", "african", "african american"]):
            return "Black African American"
        return "open ethnicity"

    def _current_archetype_terms(self, actor: ActorProfile | None) -> list[str]:
        if not actor:
            return ["mom", "authority", "professional"]
        terms = [skill for skill in actor.skills if skill]
        defaults = ["mom", "authority", "professional", "warm", "comedy"]
        return list(dict.fromkeys([*terms, *defaults]))

    def _normalize_url(self, url: str) -> str | None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return None
        return parsed._replace(fragment="").geturl()
