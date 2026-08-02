from __future__ import annotations

import html
import re
import urllib.request
from datetime import date
from urllib.parse import urljoin

from app.automation.discovery.classification import classify_breakdown_text
from app.automation.discovery.contracts import DiscoverySourcePlugin, NormalizedOpportunity
from app.services.breakdown_details_service import BreakdownDetailsService


DISCOVERY_REVIEW_TERMS = ("actor", "audition", "casting", "performer", "talent", "epa", "ecc", "self-tape", "role")


class PublicPlaybillJobsSource(DiscoverySourcePlugin):
    name = "Playbill Public Jobs"
    priority_rank = 100
    source_type = "public_breakdowns"
    implementation_key = "playbill_public_jobs"
    reliability_score = 0.82
    category = "Public Casting Sites"
    tier = 2
    provider_kind = "public_casting_site"
    authentication_methods = ("None", "Public URL")
    default_poll_frequency_minutes = 720
    notes = "User-triggered public jobs page discovery."
    operational_adapter = True
    listing_url = "https://playbill.com/jobs"

    def discover(self) -> list[dict]:
        request = urllib.request.Request(
            self.listing_url,
            headers={
                "User-Agent": "CastingIntelligenceAgent/1.0 (+user-triggered public profile portability)",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            html_text = response.read().decode("utf-8", errors="ignore")

        items: list[dict] = []
        for href, label in re.findall(r'<a\s+[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html_text, flags=re.I | re.S):
            if "/job/" not in href:
                continue
            text = self._clean(label)
            lower = text.lower()
            classification = classify_breakdown_text(text)
            if classification.classification in {"Non-Acting Job", "Crew Job"}:
                continue
            if not text or (
                classification.classification == "Unknown"
                and not any(term in lower for term in DISCOVERY_REVIEW_TERMS)
            ):
                continue
            if "playbill" in lower and len(text.split()) < 4:
                continue
            items.append(
                {
                    "title": text,
                    "url": urljoin(self.listing_url, href),
                    "discovered_on": date.today().isoformat(),
                }
            )
            if len(items) >= 30:
                break
        return items

    def normalize(self, raw_items: list[dict]) -> list[NormalizedOpportunity]:
        return [self._normalize_item(item) for item in raw_items]

    def _normalize_item(self, item: dict) -> NormalizedOpportunity:
        title = item["title"]
        detail_text = self._detail_text(item["url"]) or title
        searchable_text = f"{title}\n{detail_text}"
        project = self._project(title)
        role = self._role(title)
        location = self._location(searchable_text)
        union = self._union(searchable_text)
        audition_type = "In-Person" if any(term in searchable_text.lower() for term in ["epa", "ecc", "open call"]) else "Unknown"
        classification = classify_breakdown_text(searchable_text)
        details = BreakdownDetailsService().from_fields(
            role=role,
            project=project,
            union=union,
            location=location,
            description=detail_text,
            source_name=self.name,
            source_url=item["url"],
            source_type=self.source_type,
            import_method="Public jobs page",
            discovered_at=item.get("discovered_on"),
            category="Theatre / Public Casting",
            audition_type=audition_type,
            raw_visible_text=detail_text,
        )
        return NormalizedOpportunity(
            role=role,
            project=project,
            union=union,
            location=location,
            description=detail_text,
            original_post_url=item["url"],
            audition_type=audition_type,
            audition_travel_hours=None,
            travel_covered=None,
            housing_covered=None,
            source_name=self.name,
            category="Theatre / Public Casting",
            source_reliability_score=self.reliability_score,
            breakdown_classification=classification.classification,
            rejection_reason=classification.rejection_reason,
            source_metadata={
                **details["source_metadata"],
                "discovery_note": "Public Playbill breakdown discovered from the jobs page. Open the original source link for complete submission instructions.",
            },
            production_details=details["production_details"],
            role_details=details["role_details"],
            ai_summary=details["ai_summary"],
        )

    def _clean(self, value: str) -> str:
        text = re.sub(r"<[^>]+>", " ", value)
        text = html.unescape(text)
        return re.sub(r"\s+", " ", text).strip()

    def _detail_text(self, url: str) -> str | None:
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "CastingIntelligenceAgent/1.0 (+user-triggered public breakdown discovery)",
                    "Accept": "text/html,application/xhtml+xml",
                },
            )
            with urllib.request.urlopen(request, timeout=12) as response:
                html_text = response.read().decode("utf-8", errors="ignore")
        except Exception:
            return None
        text = self._clean_visible_page(html_text)
        return text if len(text.split()) >= 20 else None

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
            and not re.search(r"^(menu|search|advertisement|privacy policy|terms of use|sign up|log in)$", line, flags=re.I)
        ]
        return "\n".join(useful_lines)[:12000]

    def _project(self, title: str) -> str:
        cleaned = re.sub(r"^(Performer|Other|Submissions|Festival/Competition|Non-Theatrical)\s+", "", title, flags=re.I)
        cleaned = re.sub(r"^(Paid|Unpaid)\s+", "", cleaned, flags=re.I)
        return cleaned[:255]

    def _role(self, title: str) -> str:
        lower = title.lower()
        for marker in ["seeking ", "casting ", "auditions for ", "open call audition for "]:
            if marker in lower:
                start = lower.index(marker) + len(marker)
                return title[start:].split(" - ")[0].split(" at ")[0][:120].strip(" '\"") or "Performer"
        if "epa" in lower:
            return "EPA Performer"
        if "ecc" in lower:
            return "ECC Performer"
        return "Performer"

    def _location(self, title: str) -> str:
        match = re.search(r"([A-Z][A-Za-z .'-]+,\s[A-Z]{2})(?:\s|$)", title)
        return match.group(1) if match else "See source"

    def _union(self, title: str) -> str:
        lower = title.lower()
        if "non-union" in lower:
            return "Non-Union"
        if "union" in lower or "epa" in lower or "ecc" in lower:
            return "Union"
        return "Unknown"


def build_public_sources() -> list[DiscoverySourcePlugin]:
    return [PublicPlaybillJobsSource()]
