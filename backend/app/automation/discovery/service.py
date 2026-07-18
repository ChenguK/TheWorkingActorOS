from __future__ import annotations

import logging
import re
from dataclasses import replace
from datetime import datetime, timezone
from urllib.parse import urlparse
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.automation.discovery.classification import REJECTED_CLASSIFICATIONS
from app.automation.discovery.contracts import DiscoveryProvider, NormalizedOpportunity
from app.automation.discovery.registry import DiscoveryPluginRegistry
from app.db.models import (
    ActorProfile,
    Asset,
    CastingGoal,
    DiscoverySettings,
    DiscoveryProviderSettings,
    DiscoveryRun,
    DiscoverySourcePlugin,
    Opportunity,
    OpportunitySource,
    SourceResearchItem,
    WatchList,
)
from app.schemas.discovery import DiscoveryProviderSettingsUpdate
from app.services.watch_list_service import WatchListService
from app.services.breakdown_details_service import BreakdownDetailsService
from app.services.breakdown_intelligence_engine import BreakdownIntelligenceEngine
from app.services.breakdown_role_service import BreakdownRoleService
from app.services.breakdown_deadline_service import BreakdownDeadlineService
from app.automation.discovery.public_web_search import PublicWebBreakdownSearch, PublicWebSearchResult


logger = logging.getLogger(__name__)


DISCOVERY_MODES = {"Theater", "FilmTV", "All"}
DISCOVERY_SEARCH_MODES = {
    "Match My Profile",
    "Match My Archetypes",
    "Find Stretch Roles",
    "Search Specific Archetype",
}
DEFAULT_SEARCH_MODES = ["Match My Profile", "Match My Archetypes"]
BASE_PROFILE_ARCHETYPES = {
    "mom",
    "mother",
    "parent",
    "authority",
    "authority figure",
    "professional",
    "warm",
    "comedy",
    "dramatic guest star",
}
STRETCH_ARCHETYPES = {
    "attorney",
    "lawyer",
    "detective",
    "investigator",
    "executive",
    "principal",
    "journalist",
    "political staffer",
    "political leader",
    "judge",
    "university dean",
}
DEFAULT_REJECTION_SUMMARY = {
    "mode_mismatch": 0,
    "validation_failed": 0,
    "hidden": 0,
    "travel_exception": 0,
    "discarded": 0,
    "duplicate": 0,
    "demo_data": 0,
    "search_intent_mismatch": 0,
    "deadline_expired": 0,
    "needs_date_review": 0,
    "source_result_in_role_search": 0,
}


class DiscoveryAutomationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.registry = DiscoveryPluginRegistry()

    def list_plugins(self) -> list[dict]:
        self._sync_plugins()
        return [
            {
                "name": plugin.name,
                "priority_rank": self._provider_settings(plugin.implementation_key).priority,
                "source_type": plugin.source_type,
                "implementation_key": plugin.implementation_key,
                "reliability_score": plugin.reliability_score,
                "category": plugin.category,
                "tier": plugin.tier,
                "enabled": self._provider_settings(plugin.implementation_key).enabled,
            }
            for plugin in self.registry.list()
        ]

    def list_provider_settings(self) -> list[DiscoveryProviderSettings]:
        self._sync_plugins()
        return list(
            self.db.scalars(
                select(DiscoveryProviderSettings).order_by(
                    DiscoveryProviderSettings.tier,
                    DiscoveryProviderSettings.priority,
                    DiscoveryProviderSettings.display_name,
                )
            )
        )

    def get_settings(self) -> DiscoverySettings:
        settings = self.db.scalars(select(DiscoverySettings).limit(1)).first()
        if not settings:
            settings = DiscoverySettings()
            self.db.add(settings)
            self.db.commit()
            self.db.refresh(settings)
        return settings

    def update_settings(self, payload) -> DiscoverySettings:
        settings = self.get_settings()
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(settings, key, value)
        self.db.commit()
        self.db.refresh(settings)
        return settings

    def get_provider_settings(self, provider_key: str) -> DiscoveryProviderSettings:
        self._sync_plugins()
        settings = self._provider_settings(provider_key)
        if not settings:
            raise KeyError(provider_key)
        return settings

    def update_provider_settings(
        self, provider_key: str, payload: DiscoveryProviderSettingsUpdate
    ) -> DiscoveryProviderSettings:
        settings = self.get_provider_settings(provider_key)
        data = payload.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(settings, key, value)
        self.db.commit()
        self.db.refresh(settings)
        return settings

    def health_check(self, provider_key: str) -> DiscoveryProviderSettings:
        self._sync_plugins()
        provider = self.registry.get(provider_key)
        settings = self.get_provider_settings(provider_key)
        health = provider.health_check()
        settings.health_status = health.status
        settings.health_message = health.message
        settings.last_health_check_at = datetime.now(timezone.utc)
        settings.provider_metadata = {
            **(settings.provider_metadata or {}),
            "last_health_details": health.details or {},
        }
        self.db.commit()
        self.db.refresh(settings)
        return settings

    def run_all(
        self,
        discovery_mode: str = "All",
        search_modes: list[str] | str | None = None,
        specific_archetype: str | None = None,
    ) -> dict:
        discovery_mode = self._mode(discovery_mode)
        search_modes = self._search_modes(search_modes)
        self._sync_plugins()
        target_visible = self._target_visible_limit(discovery_mode)
        all_plugins = self.registry.list()
        enabled = [
            plugin
            for plugin in all_plugins
            if self._provider_settings(plugin.implementation_key).enabled
            and self._research_source_allowed(self._provider_settings(plugin.implementation_key))
            and self._source_supports_mode(self._provider_settings(plugin.implementation_key), discovery_mode)
        ]
        results = []
        visible_total = 0
        for plugin in enabled:
            remaining = None if target_visible is None else max(target_visible - visible_total, 0)
            if remaining == 0:
                break
            result = self.run_source(
                plugin.implementation_key,
                discovery_mode=discovery_mode,
                visible_limit=remaining,
                search_modes=search_modes,
                specific_archetype=specific_archetype,
            )
            results.append(result)
            visible_total += result.get("visible", 0)
        public_web_result = self._run_public_web_search(
            discovery_mode=discovery_mode,
            remaining_visible=None if target_visible is None else max(target_visible - visible_total, 0),
            search_modes=search_modes,
            specific_archetype=specific_archetype,
        )
        if public_web_result["result"]:
            results.append(public_web_result["result"])
            visible_total += public_web_result["result"].get("visible", 0)
        rejected_total = sum(item.get("rejected", 0) for item in results)
        hidden_total = sum(item.get("hidden", 0) for item in results)
        travel_exception_total = sum(item.get("travel_exceptions", 0) for item in results)
        rejection_summary = self._merge_rejection_summaries(results)
        coverage = self._coverage_report(discovery_mode, enabled)
        discovery_report = self._discovery_report(results, public_web_result["summary"])
        return {
            "discovery_mode": discovery_mode,
            "search_modes": search_modes,
            "specific_archetype": specific_archetype,
            "sources_run": len(results),
            "opportunities_created": sum(item["created"] for item in results),
            "opportunities_hidden": hidden_total,
            "travel_exceptions": travel_exception_total,
            "opportunities_rejected": rejected_total,
            "total_found": sum(item.get("total_found", 0) for item in results),
            "total_rejected": rejected_total,
            "total_hidden": hidden_total,
            "total_travel_exceptions": travel_exception_total,
            "total_visible": visible_total,
            "target_visible": target_visible,
            "limit_reached": target_visible is not None and visible_total >= target_visible,
            "rejection_reasons_summary": rejection_summary,
            "coverage": coverage,
            "public_web_search": public_web_result["summary"],
            "discovery_report": discovery_report,
            "results": results,
        }

    def run_source(
        self,
        implementation_key: str,
        discovery_mode: str = "All",
        visible_limit: int | None = None,
        search_modes: list[str] | str | None = None,
        specific_archetype: str | None = None,
    ) -> dict:
        discovery_mode = self._mode(discovery_mode)
        search_modes = self._search_modes(search_modes)
        plugin = self.registry.get(implementation_key)
        settings = self._provider_settings(plugin.implementation_key)
        if not settings.enabled:
            return self._empty_result(plugin.name, skipped=True, reason="Provider disabled")
        if not self._research_source_allowed(settings):
            return self._empty_result(plugin.name, skipped=True, reason="Source is not approved and active")
        plugin_record = self._plugin_record(plugin.implementation_key)
        run_id = uuid4()
        started_at = datetime.utcnow()
        run_payload = {
            "source": plugin.name,
            "provider_key": plugin.implementation_key,
            "discovery_mode": discovery_mode,
            "search_modes": search_modes,
            "specific_archetype": specific_archetype,
            "intent_priority": [
                "hard demographic fit",
                "user role preferences",
                "project type mode",
                "current archetypes",
                "stretch potential",
            ],
        }
        run = DiscoveryRun(
            id=run_id,
            source_plugin_id=plugin_record.id,
            discovery_mode=discovery_mode,
            status="running",
            started_at=started_at,
            run_payload=run_payload,
        )
        try:
            self.db.add(run)
            self.db.flush()
            raw_items = plugin.discover()
            if not raw_items:
                settings.health_status = "no_real_breakdowns_found"
                settings.health_message = "No real breakdowns found for this source."
                settings.last_health_check_at = datetime.now(timezone.utc)
            normalized_raw = plugin.deduplicate(plugin.normalize(raw_items))
            normalized = []
            rejection_summary = dict(DEFAULT_REJECTION_SUMMARY)
            for item in normalized_raw:
                if plugin.validate(item):
                    normalized.append(item)
                else:
                    if getattr(item, "result_type", "breakdown") != "breakdown":
                        rejection_summary["source_result_in_role_search"] += 1
                    rejection_summary["validation_failed"] += 1
            created = 0
            hidden = 0
            travel_exceptions = 0
            discarded = 0
            rejected = 0
            visible = 0
            for item in normalized:
                if visible_limit is not None and visible >= visible_limit:
                    break
                if item.is_demo_data:
                    rejected += 1
                    rejection_summary["demo_data"] += 1
                    continue
                if not self._matches_mode(item, discovery_mode):
                    rejected += 1
                    rejection_summary["mode_mismatch"] += 1
                    continue
                if not self._matches_search_intent(item, search_modes, specific_archetype):
                    rejected += 1
                    rejection_summary["search_intent_mismatch"] += 1
                    continue
                date_result = BreakdownDeadlineService().validate_normalized(item)
                if date_result.expired:
                    rejected += 1
                    rejection_summary["deadline_expired"] += 1
                    continue
                if date_result.needs_review:
                    rejection_summary["needs_date_review"] += 1
                item = replace(
                    item,
                    source_metadata={
                        **(item.source_metadata or {}),
                        "date_validation": date_result.as_metadata(),
                    },
                )
                opportunity, was_created = self._create_opportunity(item)
                opportunity.source_metadata = {
                    **(opportunity.source_metadata or {}),
                    "discovery_mode": discovery_mode,
                    "search_modes": search_modes,
                    "specific_archetype": specific_archetype,
                    "intent_priority": [
                        "hard demographic fit",
                        "user role preferences",
                        "project type mode",
                        "current archetypes",
                        "stretch potential",
                    ],
                }
                if was_created:
                    created += 1
                if opportunity.visibility_status == "visible":
                    visible += 1
                elif opportunity.visibility_status == "travel_exception":
                    travel_exceptions += 1
                    rejection_summary["travel_exception"] += 1
                elif opportunity.visibility_status == "discarded":
                    discarded += 1
                    rejected += 1
                    rejection_summary["discarded"] += 1
                    if opportunity.hidden_by_rule:
                        rejection_summary[opportunity.hidden_by_rule] = rejection_summary.get(opportunity.hidden_by_rule, 0) + 1
                else:
                    hidden += 1
                    rejected += 1
                    rejection_summary["hidden"] += 1
                    if opportunity.hidden_by_rule:
                        rejection_summary[opportunity.hidden_by_rule] = rejection_summary.get(opportunity.hidden_by_rule, 0) + 1
                if not was_created:
                    rejection_summary["duplicate"] += 1
            run.status = "succeeded"
            run.opportunities_found = len(raw_items)
            run.opportunities_created = created
            run.opportunities_hidden = hidden
            run.total_found = len(raw_items)
            run.total_saved = created
            run.total_rejected = rejected
            run.notes = self._mode_notes(discovery_mode, rejected)
            run.finished_at = datetime.utcnow()
            run.completed_at = run.finished_at
            self.db.commit()
            return {
                "source": plugin.name,
                "created": created,
                "hidden": hidden,
                "travel_exceptions": travel_exceptions,
                "discarded": discarded,
                "visible": visible,
                "rejected": rejected,
                "total_found": len(raw_items),
                "rejection_reasons_summary": rejection_summary,
                "skipped": False,
            }
        except Exception as exc:
            self.db.rollback()
            completed_at = datetime.utcnow()
            failed_run = DiscoveryRun(
                id=run_id,
                source_plugin_id=plugin_record.id,
                discovery_mode=discovery_mode,
                status="failed",
                opportunities_found=0,
                opportunities_created=0,
                opportunities_hidden=0,
                total_found=0,
                total_saved=0,
                total_rejected=0,
                error_message=str(exc),
                run_payload=run_payload,
                started_at=started_at,
                finished_at=completed_at,
                completed_at=completed_at,
            )
            try:
                self.db.add(failed_run)
                self.db.commit()
            except Exception:
                self.db.rollback()
                logger.exception("Failed to persist failed DiscoveryRun %s", run_id)
            raise

    def _create_opportunity(self, item: NormalizedOpportunity) -> tuple[Opportunity, bool]:
        source = self._opportunity_source(item.source_name)
        visibility, hidden_reason, hidden_by_rule, manual_review = self._visibility(item)
        normalized_key = self._key(item)
        existing = self.db.scalars(
            select(Opportunity)
            .where(Opportunity.normalized_key == normalized_key)
            .where(Opportunity.is_demo_data.is_(False))
            .limit(1)
        ).first()
        if existing:
            return existing, False
        opportunity = Opportunity(
            opportunity_source_id=source.id,
            role=item.role,
            project=item.project,
            union=item.union,
            location=item.location,
            travel_covered=item.travel_covered,
            housing_covered=item.housing_covered,
            description=item.description,
            original_post_url=item.original_post_url,
            normalized_key=normalized_key,
            category=item.category,
            source_reliability_score=item.source_reliability_score,
            is_duplicate=False,
            breakdown_classification=item.breakdown_classification,
            rejection_reason=item.rejection_reason,
            is_demo_data=item.is_demo_data,
            audition_type=item.audition_type,
            audition_travel_hours=item.audition_travel_hours,
            audition_drive_time=item.audition_travel_hours,
            visibility_status=visibility,
            hidden_reason=hidden_reason,
            hidden_by_rule=hidden_by_rule,
            manual_review_required=manual_review,
            source_metadata=item.source_metadata,
            production_details=item.production_details,
            role_details=item.role_details,
            ai_summary=item.ai_summary,
        )
        self._ensure_details(opportunity)
        self.db.add(opportunity)
        self.db.flush()
        engine_result = BreakdownIntelligenceEngine(self.db).run_for_opportunity(
            opportunity, opportunity.description, "Deep Parse"
        )
        parsed = engine_result["details"]
        opportunity.production_details = {**(opportunity.production_details or {}), **parsed["production_details"]}
        opportunity.role_details = {**(opportunity.role_details or {}), **parsed["role_details"]}
        opportunity.extracted_facts = {**(opportunity.extracted_facts or {}), **parsed.get("extracted_facts", {})}
        opportunity.ai_inference = {**(opportunity.ai_inference or {}), **parsed.get("ai_inference", {})}
        if parsed["production_details"].get("project_type"):
            opportunity.project_type = parsed["production_details"]["project_type"]
        if parsed["production_details"].get("union_status"):
            opportunity.union = parsed["production_details"]["union_status"]
        if parsed["role_details"].get("audition_type"):
            opportunity.audition_type = parsed["role_details"]["audition_type"]
        if parsed["role_details"].get("audition_location_name") and not opportunity.audition_location:
            opportunity.audition_location = parsed["role_details"]["audition_location_name"]
        opportunity.ai_summary = opportunity.ai_summary or parsed["ai_summary"]
        date_result = BreakdownDeadlineService().apply_to_opportunity(opportunity)
        if date_result.expired or date_result.needs_review:
            self.db.add(opportunity)
            self.db.flush()
            return opportunity, True
        BreakdownRoleService(self.db).sync_from_details(opportunity)
        WatchListService(self.db).apply_to_opportunity(opportunity)
        from app.services.opportunity_intelligence_service import OpportunityIntelligenceService
        from app.services.trust_verification_service import TrustVerificationService

        OpportunityIntelligenceService(self.db).enrich(opportunity)
        TrustVerificationService(self.db).verify(opportunity)
        return opportunity, True

    def _run_public_web_search(
        self,
        discovery_mode: str,
        remaining_visible: int | None,
        search_modes: list[str],
        specific_archetype: str | None,
    ) -> dict:
        actor = self.db.scalars(select(ActorProfile).limit(1)).first()
        search = PublicWebBreakdownSearch(actor)
        base_summary = {
            "provider": "parallel",
            "configured": search.configured(),
            "run": False,
            "reason": None,
            "search_queries": [],
            "candidate_pages_found": 0,
            "candidate_pages_fetched": 0,
            "candidate_pages_parsed": 0,
            "candidates_rejected": 0,
            "eligible_breakdowns_added": 0,
            "sources_suggested_for_approval": 0,
            "candidate_reports": [],
        }
        if remaining_visible == 0:
            base_summary["reason"] = "Visible breakdown limit was reached before public web search."
            return {"summary": base_summary, "result": None}
        try:
            search_result = search.search(discovery_mode)
        except Exception as exc:
            base_summary["configured"] = search.configured()
            base_summary["reason"] = str(exc)
            return {"summary": base_summary, "result": None}
        summary, result = self._process_public_web_search_result(
            search_result,
            discovery_mode,
            remaining_visible,
            search_modes,
            specific_archetype,
        )
        return {"summary": summary, "result": result}

    def _process_public_web_search_result(
        self,
        search_result: PublicWebSearchResult,
        discovery_mode: str,
        visible_limit: int | None,
        search_modes: list[str],
        specific_archetype: str | None,
    ) -> tuple[dict, dict | None]:
        summary = {
            "provider": search_result.provider,
            "configured": search_result.configured,
            "run": search_result.run,
            "reason": search_result.reason,
            "search_queries": search_result.search_queries,
            "candidate_pages_found": search_result.candidate_pages_found,
            "candidate_pages_fetched": len(search_result.candidate_reports),
            "candidate_pages_parsed": len(search_result.normalized),
            "candidates_rejected": search_result.candidates_rejected,
            "eligible_breakdowns_added": 0,
            "sources_suggested_for_approval": 0,
            "candidate_reports": [dict(report) for report in search_result.candidate_reports],
        }
        if not search_result.run:
            return summary, None

        rejection_summary = dict(DEFAULT_REJECTION_SUMMARY)
        created = 0
        hidden = 0
        travel_exceptions = 0
        discarded = 0
        rejected = search_result.candidates_rejected
        visible = 0
        eligible_added = 0
        suggested_sources = 0
        for item in search_result.normalized:
            candidate_report = self._candidate_report_for_url(summary["candidate_reports"], item.original_post_url)
            if visible_limit is not None and visible >= visible_limit:
                self._mark_candidate_report(candidate_report, "Rejected", "Visible result limit reached")
                break
            if not self._matches_mode(item, discovery_mode):
                rejected += 1
                rejection_summary["mode_mismatch"] += 1
                self._mark_candidate_report(candidate_report, "Rejected", "Project type mismatch")
                continue
            if not self._matches_search_intent(item, search_modes, specific_archetype):
                rejected += 1
                rejection_summary["search_intent_mismatch"] += 1
                self._mark_candidate_report(candidate_report, "Rejected", "Search intent mismatch")
                continue
            date_result = BreakdownDeadlineService().validate_normalized(item)
            if date_result.expired:
                rejected += 1
                rejection_summary["deadline_expired"] += 1
                self._mark_candidate_report(candidate_report, "Rejected", "Expired")
                continue
            if date_result.needs_review:
                rejection_summary["needs_date_review"] += 1
            item = replace(
                item,
                source_metadata={
                    **(item.source_metadata or {}),
                    "date_validation": date_result.as_metadata(),
                    "discovery_mode": discovery_mode,
                    "search_modes": search_modes,
                    "specific_archetype": specific_archetype,
                },
            )
            opportunity, was_created = self._create_opportunity(item)
            parse_confidence = (opportunity.source_metadata or {}).get("breakdown_parse_confidence")
            if candidate_report is not None and isinstance(parse_confidence, (int, float)):
                candidate_report["parser_confidence"] = parse_confidence
            if was_created:
                created += 1
            if opportunity.visibility_status == "visible":
                visible += 1
                self._mark_candidate_report(candidate_report, "Accepted", None)
                if was_created:
                    eligible_added += 1
                if was_created and self._suggest_source_from_public_breakdown(opportunity):
                    suggested_sources += 1
            elif opportunity.visibility_status == "travel_exception":
                travel_exceptions += 1
                rejection_summary["travel_exception"] += 1
                self._mark_candidate_report(candidate_report, "Rejected", "Travel restriction")
            elif opportunity.visibility_status == "discarded":
                discarded += 1
                rejected += 1
                rejection_summary["discarded"] += 1
                self._mark_candidate_report(candidate_report, "Rejected", self._plain_rejection_reason(opportunity.hidden_by_rule or opportunity.hidden_reason or "discarded"))
            else:
                hidden += 1
                rejected += 1
                rejection_summary["hidden"] += 1
                self._mark_candidate_report(candidate_report, "Rejected", self._plain_rejection_reason(opportunity.hidden_by_rule or opportunity.hidden_reason or "Unknown"))
            if not was_created:
                rejection_summary["duplicate"] += 1
                self._mark_candidate_report(candidate_report, "Rejected", "Duplicate")

        result = {
            "source": "Parallel Public Web Search",
            "created": created,
            "hidden": hidden,
            "travel_exceptions": travel_exceptions,
            "discarded": discarded,
            "visible": visible,
            "rejected": rejected,
            "total_found": search_result.candidate_pages_found,
            "rejection_reasons_summary": rejection_summary,
            "skipped": False,
            "public_web_search": True,
        }
        summary["eligible_breakdowns_added"] = eligible_added
        summary["candidates_rejected"] = rejected
        summary["sources_suggested_for_approval"] = suggested_sources
        return summary, result

    def _candidate_report_for_url(self, reports: list[dict], url: str | None) -> dict | None:
        if not url:
            return None
        for report in reports:
            if report.get("url") == url:
                return report
        return None

    def _mark_candidate_report(self, report: dict | None, decision: str, reason: str | None) -> None:
        if report is None:
            return
        report["decision"] = decision
        report["rejection_reason"] = reason

    def _plain_rejection_reason(self, reason: str | None) -> str:
        if not reason:
            return "Unknown"
        value = str(reason).lower()
        if "expired" in value or "deadline" in value:
            return "Expired"
        if "background" in value or "extra" in value:
            return "Background/Extra"
        if "crew" in value or "staff" in value or "job" in value:
            return "Crew/Staff"
        if "workshop" in value or "class" in value:
            return "Workshop/Class"
        if "gender" in value:
            return "Wrong gender"
        if "age" in value:
            return "Wrong age"
        if "ethnicity" in value or "race" in value:
            return "Wrong ethnicity"
        if "travel" in value:
            return "Travel restriction"
        if "acting" in value or "performer" in value:
            return "Not an acting role"
        if "role block" in value:
            return "No role blocks detected"
        if "confidence" in value:
            return "Low parser confidence"
        if "duplicate" in value:
            return "Duplicate"
        if "submitted" in value:
            return "Already submitted"
        return str(reason)

    def _discovery_report(self, results: list[dict], public_web_summary: dict) -> dict:
        candidates = list(public_web_summary.get("candidate_reports") or [])
        accepted = [item for item in candidates if item.get("decision") == "Accepted"]
        rejected = [item for item in candidates if item.get("decision") == "Rejected"]
        rejection_counts: dict[str, int] = {}
        for item in rejected:
            reason = item.get("rejection_reason") or "Unknown"
            rejection_counts[reason] = rejection_counts.get(reason, 0) + 1
        confidences = [
            item.get("parser_confidence")
            for item in candidates
            if isinstance(item.get("parser_confidence"), (int, float))
        ]
        return {
            "parallel_queries_run": len(public_web_summary.get("search_queries") or []),
            "candidate_pages_returned": public_web_summary.get("candidate_pages_found", 0),
            "candidate_pages_fetched": public_web_summary.get("candidate_pages_fetched", 0),
            "candidate_pages_parsed": public_web_summary.get("candidate_pages_parsed", 0),
            "accepted": len(accepted),
            "rejected": len(rejected),
            "top_rejection_reasons": rejection_counts,
            "average_parser_confidence": round(sum(confidences) / len(confidences), 1) if confidences else None,
            "approved_source_hits": sum(item.get("total_found", 0) for item in results if not item.get("public_web_search")),
            "public_web_hits": public_web_summary.get("candidate_pages_found", 0),
            "candidates": candidates,
        }

    def _suggest_source_from_public_breakdown(self, opportunity: Opportunity) -> bool:
        source_url = opportunity.original_post_url
        if not source_url:
            return False
        parsed = urlparse(source_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return False
        domain = parsed.netloc.lower().removeprefix("www.")
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        existing = list(
            self.db.scalars(
                select(SourceResearchItem)
                .where(SourceResearchItem.deleted.is_(False))
                .where(
                    (SourceResearchItem.base_url.ilike(f"%{domain}%"))
                    | (SourceResearchItem.source_url.ilike(f"%{domain}%"))
                    | (SourceResearchItem.approved_discovery_url.ilike(f"%{domain}%"))
                    | (SourceResearchItem.suggested_specific_url.ilike(f"%{domain}%"))
                )
            )
        )
        discovery_reason = self._matched_breakdown_discovery_reason(opportunity)
        if existing:
            source_item = existing[0]
            source_item.discovered_from_breakdown_id = source_item.discovered_from_breakdown_id or opportunity.id
            source_item.discovery_reason = discovery_reason
            source_item.source_role_match_count = (source_item.source_role_match_count or 0) + 1
            if source_item.source_usefulness == "Needs Review":
                source_item.source_usefulness = "Useful Breakdown Source"
            if source_item.source_classification == "Needs Review":
                source_item.source_classification = "Valid Breakdown Source"
            if source_item.suggested_classification == "Needs Review":
                source_item.suggested_classification = "Valid Breakdown Source"
            self.db.flush()
            return False
        item = SourceResearchItem(
            name=domain,
            source_url=base_url,
            base_url=base_url,
            suggested_specific_url=source_url,
            approved_discovery_url=None,
            category="Public casting site",
            status="Suggested",
            reliability_notes="Source produced at least one public Film/TV breakdown through Parallel public web search.",
            notes="Source of matched breakdown. Review and approve before allowing this source to be monitored directly.",
            suggested_by_ai=True,
            approved_by_user=False,
            source_health="Active",
            suggested_classification="Valid Breakdown Source",
            health_reason="Exact page produced a matched public actor-facing breakdown.",
            organization_name=domain,
            submitted_url=source_url,
            final_resolved_url=source_url,
            url_health_status="Active",
            organization_legitimacy="Unverified Organization",
            source_usefulness="Useful Breakdown Source",
            source_classification="Valid Breakdown Source",
            verification_notes="Suggested because a matched breakdown was found on this source.",
            discovered_from_breakdown_id=opportunity.id,
            discovery_reason=discovery_reason,
            source_role_match_count=1,
        )
        self.db.add(item)
        self.db.flush()
        return True

    def _matched_breakdown_discovery_reason(self, opportunity: Opportunity) -> str:
        role = opportunity.role or "a role"
        project = opportunity.project or "this project"
        return f'Matched breakdown found for "{role}" in "{project}."'

    def _ensure_details(self, opportunity: Opportunity) -> None:
        if opportunity.production_details and opportunity.role_details and opportunity.ai_summary:
            return
        details = BreakdownDetailsService().from_fields(
            role=opportunity.role,
            project=opportunity.project,
            union=opportunity.union,
            location=opportunity.location,
            description=opportunity.description,
            source_name=opportunity.source.name if opportunity.source else None,
            source_url=opportunity.original_post_url,
            source_type=opportunity.source_type,
            platform=opportunity.platform,
            category=opportunity.category,
            role_type=opportunity.role_type,
            project_type=opportunity.project_type,
            archetypes=opportunity.archetypes,
            audition_type=opportunity.audition_type,
            rate=opportunity.rate,
            shoot_location=opportunity.shoot_location,
            audition_location=opportunity.audition_location,
            travel_covered=opportunity.travel_covered,
            housing_covered=opportunity.housing_covered,
        )
        opportunity.source_metadata = details["source_metadata"]
        opportunity.production_details = details["production_details"]
        opportunity.role_details = details["role_details"]
        opportunity.extracted_facts = details.get("extracted_facts", {})
        opportunity.ai_inference = details.get("ai_inference", {})
        opportunity.ai_summary = details["ai_summary"]

    def _visibility(self, item: NormalizedOpportunity) -> tuple[str, str | None, str | None, bool]:
        date_validation = (item.source_metadata or {}).get("date_validation") or {}
        if date_validation.get("status") == "Needs Date Review":
            return (
                "hidden",
                date_validation.get("reason") or "Needs Date Review before recommendation.",
                "needs_date_review",
                True,
            )
        if item.breakdown_classification in REJECTED_CLASSIFICATIONS:
            return (
                "discarded",
                item.rejection_reason or "This listing is not an acting breakdown.",
                "breakdown_classification_rejected",
                False,
            )
        if item.breakdown_classification == "Unknown":
            return (
                "hidden",
                "Breakdown classification is unknown and requires manual review before scoring.",
                "breakdown_classification_needs_review",
                True,
            )
        if item.audition_type == "In-Person":
            if item.audition_travel_hours is not None and item.audition_travel_hours > 2:
                return (
                    "travel_exception",
                    "Audition exceeds maximum in-person audition travel threshold.",
                    "travel_exception",
                    False,
                )
            return "visible", None, None, False
        if item.audition_type == "Unknown":
            return "visible", "Audition type is unknown and requires manual review.", None, True
        return "visible", None, None, False

    def _mode(self, discovery_mode: str | None) -> str:
        if discovery_mode in DISCOVERY_MODES:
            return discovery_mode
        return "All"

    def _search_modes(self, search_modes: list[str] | str | None) -> list[str]:
        if search_modes is None:
            return list(DEFAULT_SEARCH_MODES)
        if isinstance(search_modes, str):
            raw_modes = [item.strip() for item in search_modes.split(",")]
        else:
            raw_modes = [str(item).strip() for item in search_modes]
        modes = [mode for mode in raw_modes if mode in DISCOVERY_SEARCH_MODES]
        return modes or list(DEFAULT_SEARCH_MODES)

    def _target_visible_limit(self, discovery_mode: str) -> int | None:
        settings = self.get_settings()
        if discovery_mode == "FilmTV":
            return settings.film_tv_breakdown_limit
        if discovery_mode == "Theater":
            return settings.theater_breakdown_limit
        if discovery_mode == "All":
            return None
        return None

    def _empty_result(self, source: str, skipped: bool = False, reason: str | None = None) -> dict:
        return {
            "source": source,
            "created": 0,
            "hidden": 0,
            "travel_exceptions": 0,
            "discarded": 0,
            "visible": 0,
            "rejected": 0,
            "total_found": 0,
            "rejection_reasons_summary": dict(DEFAULT_REJECTION_SUMMARY),
            "skipped": skipped,
            "reason": reason,
        }

    def _merge_rejection_summaries(self, results: list[dict]) -> dict:
        merged: dict[str, int] = {}
        for result in results:
            for reason, count in (result.get("rejection_reasons_summary") or {}).items():
                merged[reason] = merged.get(reason, 0) + int(count or 0)
        return {key: count for key, count in merged.items() if count}

    def _coverage_report(self, discovery_mode: str, checked_plugins: list[DiscoveryProvider]) -> dict:
        settings_rows = list(
            self.db.scalars(
                select(DiscoveryProviderSettings).order_by(
                    DiscoveryProviderSettings.priority,
                    DiscoveryProviderSettings.display_name,
                )
            )
        )
        checked_keys = {plugin.implementation_key for plugin in checked_plugins}
        mode_label = "Film/TV" if discovery_mode == "FilmTV" else discovery_mode
        mode_source_label = "approved active sources" if discovery_mode == "All" else f"approved active {mode_label} sources"
        active_mode_sources = [
            settings
            for settings in settings_rows
            if settings.enabled
            and self._research_source_allowed(settings)
            and self._source_supports_mode(settings, discovery_mode)
        ]
        skipped: list[dict] = []
        for settings in settings_rows:
            if settings.provider_key in checked_keys:
                continue
            reason = self._skip_reason(settings, discovery_mode)
            if reason:
                source_item = self._source_item_for_provider(settings)
                if source_item and self._source_item_hidden_from_workflow(source_item):
                    continue
                skipped.append(
                    {
                        "source": settings.display_name,
                        "provider_key": settings.provider_key,
                        "reason": reason,
                        "status": "Active" if settings.enabled else "Paused",
                        "source_research_item_id": str(source_item.id) if source_item else None,
                        "source_status": source_item.status if source_item else None,
                        "approved_by_user": source_item.approved_by_user if source_item else None,
                        "source_classification": source_item.source_classification if source_item else None,
                        "url_health_status": source_item.url_health_status if source_item else None,
                        "source_usefulness": source_item.source_usefulness if source_item else None,
                    }
                )
        suggested_count = self._suggested_sources_awaiting_approval(discovery_mode)
        active_count = len(active_mode_sources)
        return {
            "approved_active_sources_checked": len(checked_plugins),
            "approved_active_source_names_checked": [plugin.name for plugin in checked_plugins],
            "eligible_sources_skipped": len(skipped),
            "skipped_source_reasons": skipped,
            "approved_mode_sources_available": active_count,
            "approved_mode_sources_label": mode_source_label,
            "suggested_sources_awaiting_approval": suggested_count,
            "coverage_level": self._coverage_level(active_count),
            "scope_note": (
                "This search only checked active approved breakdown sources configured in The Working Actor OS. "
                "It did not search the full public web, all casting platforms, all regional productions, or all independent films."
            ),
        }

    def _source_item_hidden_from_workflow(self, item: SourceResearchItem) -> bool:
        bad_health = {"Placeholder Website", "Dead / Unavailable Domain", "No Meaningful Content"}
        return bool(
            item.deleted
            or item.rejected_by_user
            or item.source_usefulness == "Not Useful"
            or item.source_classification in {"Not Useful", "Rejected"}
            or item.source_health in bad_health
            or item.url_health_status in bad_health
        )

    def _source_item_for_provider(self, settings: DiscoveryProviderSettings) -> SourceResearchItem | None:
        metadata = settings.provider_metadata or {}
        source_id = metadata.get("source_research_item_id")
        if source_id:
            try:
                return self.db.get(SourceResearchItem, UUID(str(source_id)))
            except Exception:
                return None
        result = self.db.scalars(
            select(SourceResearchItem)
            .where(SourceResearchItem.deleted.is_(False))
            .where(SourceResearchItem.provider_key == settings.provider_key)
        )
        if hasattr(result, "first"):
            return result.first()
        return result[0] if result else None

    def _coverage_level(self, active_source_count: int) -> str:
        if active_source_count <= 2:
            return "Very Limited"
        if active_source_count <= 5:
            return "Limited"
        if active_source_count <= 10:
            return "Good"
        return "Broad"

    def _skip_reason(self, settings: DiscoveryProviderSettings, discovery_mode: str) -> str | None:
        if not settings.enabled:
            return "Disabled or paused."
        if not self._research_source_allowed(settings):
            return "Not approved, inactive, deleted, paused, or not verified as a valid breakdown source."
        if not self._source_supports_mode(settings, discovery_mode):
            mode_label = "Film/TV" if discovery_mode == "FilmTV" else discovery_mode
            family = self._source_family(settings)
            return f"Classified as {family}; skipped for {mode_label} discovery."
        return None

    def _source_supports_mode(self, settings: DiscoveryProviderSettings, discovery_mode: str) -> bool:
        if discovery_mode == "All":
            return True
        family = self._source_family(settings)
        return family in {discovery_mode, "All"}

    def _source_family(self, settings: DiscoveryProviderSettings) -> str:
        metadata = settings.provider_metadata or {}
        source_text = " ".join(
            str(value or "")
            for value in [
                settings.display_name,
                settings.category,
                settings.source_type,
                settings.notes,
                metadata.get("source_url"),
                metadata.get("base_url"),
                metadata.get("suggested_specific_url"),
                metadata.get("approved_discovery_url"),
            ]
        ).lower()
        theater_terms = [
            "playbill",
            "theater",
            "theatre",
            "broadway",
            "stage",
            "epa",
            "equity audition",
        ]
        film_tv_terms = [
            "film",
            "tv",
            "television",
            "streaming",
            "screen",
            "cinema",
            "movie",
            "production company",
            "film commission",
            "university",
            "mfa",
        ]
        has_theater = any(term in source_text for term in theater_terms)
        has_film_tv = any(term in source_text for term in film_tv_terms)
        if has_theater and not has_film_tv:
            return "Theater"
        if has_film_tv and not has_theater:
            return "FilmTV"
        return "All"

    def _suggested_sources_awaiting_approval(self, discovery_mode: str) -> int:
        items = list(
            self.db.scalars(
                select(SourceResearchItem)
                .where(SourceResearchItem.deleted.is_(False))
                .where(SourceResearchItem.status.in_(["Suggested", "Researching"]))
                .where(SourceResearchItem.url_health_status == "Active")
            )
        )
        return sum(1 for item in items if self._source_item_supports_mode(item, discovery_mode))

    def _source_item_supports_mode(self, item: SourceResearchItem, discovery_mode: str) -> bool:
        if discovery_mode == "All":
            return True
        text = " ".join(
            str(value or "")
            for value in [
                item.name,
                item.category,
                item.notes,
                item.reliability_notes,
                item.source_url,
                item.base_url,
                item.suggested_specific_url,
                item.approved_discovery_url,
                item.page_title,
            ]
        ).lower()
        theater_terms = ["playbill", "theater", "theatre", "broadway", "stage", "epa", "auditions"]
        film_tv_terms = [
            "film",
            "tv",
            "television",
            "streaming",
            "screen",
            "movie",
            "independent",
            "short film",
            "student film",
            "mfa",
            "film commission",
            "production company",
        ]
        has_theater = any(term in text for term in theater_terms)
        has_film_tv = any(term in text for term in film_tv_terms)
        if discovery_mode == "Theater":
            return has_theater or not has_film_tv
        if discovery_mode == "FilmTV":
            return has_film_tv or not has_theater
        return True

    def _matches_mode(self, item: NormalizedOpportunity, discovery_mode: str) -> bool:
        if discovery_mode == "All":
            return True
        family = self._project_family(item)
        if discovery_mode == "Theater":
            return family in {"Theater", "Unknown"}
        if discovery_mode == "FilmTV":
            return family in {"FilmTV", "Unknown"}
        return True

    def _matches_search_intent(
        self,
        item: NormalizedOpportunity,
        search_modes: list[str],
        specific_archetype: str | None = None,
    ) -> bool:
        text = self._item_text(item)
        if "Search Specific Archetype" in search_modes:
            target = (specific_archetype or "").strip().lower()
            if not target:
                return False
            return target in text
        if "Find Stretch Roles" in search_modes:
            stretch_terms = self._active_stretch_terms()
            return any(term in text for term in stretch_terms)
        if "Match My Profile" in search_modes:
            return True
        if "Match My Archetypes" in search_modes:
            archetypes = self._current_archetype_terms()
            if any(term in text for term in archetypes):
                return True
        return False

    def _item_text(self, item: NormalizedOpportunity) -> str:
        values = [
            item.role,
            item.project,
            item.category,
            item.description,
            item.production_details.get("project_type"),
            item.role_details.get("role_type"),
            item.role_details.get("character_description"),
            " ".join(str(value) for value in item.role_details.get("archetypes", []) if value)
            if isinstance(item.role_details.get("archetypes"), list)
            else item.role_details.get("archetypes"),
        ]
        return " ".join(str(value or "") for value in values).lower()

    def _current_archetype_terms(self) -> set[str]:
        actor = self.db.scalars(select(ActorProfile).limit(1)).first()
        terms = set(BASE_PROFILE_ARCHETYPES)
        if actor:
            terms.update(str(skill).lower() for skill in actor.skills)
        for asset in self.db.scalars(select(Asset)):
            terms.update(str(item).lower() for item in asset.archetype_names)
            terms.update(str(item).lower() for item in asset.tags)
        for watch in self.db.scalars(select(WatchList).where(WatchList.enabled.is_(True))):
            if watch.category in {"Archetypes", "Role Types", "Keywords", "Genres"}:
                terms.update(str(term).lower() for term in watch.terms)
        return {term for term in terms if term}

    def _active_stretch_terms(self) -> set[str]:
        terms = set(STRETCH_ARCHETYPES)
        for goal in self.db.scalars(select(CastingGoal).where(CastingGoal.status == "Active")):
            terms.update(str(term).lower() for term in goal.target_archetypes)
            terms.update(str(term).lower() for term in goal.target_role_types)
        for watch in self.db.scalars(select(WatchList).where(WatchList.enabled.is_(True))):
            if watch.category in {"Archetypes", "Role Types", "Keywords"}:
                terms.update(str(term).lower() for term in watch.terms)
        return {term for term in terms if term}

    def _project_family(self, item: NormalizedOpportunity) -> str:
        text = " ".join(
            str(value or "")
            for value in [
                item.project,
                item.role,
                item.category,
                item.description,
                item.production_details.get("project_type"),
                item.source_metadata.get("source_type"),
            ]
        ).lower()
        theater_terms = [
            "theater",
            "theatre",
            "musical theater",
            "musical theatre",
            "stage production",
            "stage",
            "play",
            "reading",
            "workshop",
            "regional theater",
            "regional theatre",
            "broadway",
            "off-broadway",
            "off-off-broadway",
            "epa",
            "ecc",
        ]
        film_tv_terms = [
            "film",
            "television",
            " tv ",
            "streaming",
            "episodic",
            "series",
            "feature film",
            "short film",
            "tv movie",
            "web series",
            "pilot",
        ]
        has_theater = any(term in text for term in theater_terms)
        has_film_tv = any(term in text for term in film_tv_terms)
        if has_theater and not has_film_tv:
            return "Theater"
        if has_film_tv and not has_theater:
            return "FilmTV"
        return "Unknown"

    def _mode_notes(self, discovery_mode: str, rejected: int) -> str | None:
        if discovery_mode == "All":
            return None
        if rejected:
            return f"Excluded {rejected} breakdown(s) that did not match {discovery_mode} discovery mode."
        return f"Discovery run prioritized {discovery_mode} breakdowns."

    def _sync_plugins(self) -> None:
        for plugin in self.registry.list():
            if not self._plugin_record(plugin.implementation_key):
                self.db.add(
                    DiscoverySourcePlugin(
                        name=plugin.name,
                        priority_rank=plugin.priority_rank,
                        source_type=plugin.source_type,
                        implementation_key=plugin.implementation_key,
                        reliability_score=plugin.reliability_score,
                    )
                )
            if not self._provider_settings(plugin.implementation_key):
                self.db.add(self._settings_from_provider(plugin))
        self.db.commit()

    def _settings_from_provider(self, plugin: DiscoveryProvider) -> DiscoveryProviderSettings:
        enabled_by_default = False
        supported_auth = list(plugin.authentication_methods)
        return DiscoveryProviderSettings(
            provider_key=plugin.implementation_key,
            display_name=plugin.name,
            tier=plugin.tier,
            category=plugin.category,
            source_type=plugin.source_type,
            enabled=enabled_by_default,
            poll_frequency_minutes=plugin.default_poll_frequency_minutes,
            priority=plugin.priority_rank,
            authentication_method=supported_auth[0] if supported_auth else "None",
            supported_authentication_methods=supported_auth,
            reliability_score=plugin.reliability_score,
            notes=plugin.notes,
            provider_metadata={"provider_kind": plugin.provider_kind},
            health_status="unknown",
        )

    def _provider_settings(self, provider_key: str) -> DiscoveryProviderSettings:
        return self.db.scalars(
            select(DiscoveryProviderSettings).where(
                DiscoveryProviderSettings.provider_key == provider_key
            )
        ).first()

    def _research_source_allowed(self, settings: DiscoveryProviderSettings) -> bool:
        metadata = settings.provider_metadata or {}
        if metadata.get("provider_kind") != "user_researched_source":
            return True
        item_id = metadata.get("source_research_item_id")
        try:
            source_id = UUID(str(item_id)) if item_id else None
        except ValueError:
            return False
        source = self.db.get(SourceResearchItem, source_id) if source_id else None
        if not source:
            return False
        return bool(
            source.status == "Active"
            and not source.deleted
            and source.approved_by_user
            and source.url_health_status == "Active"
            and source.source_usefulness == "Useful Breakdown Source"
            and source.source_classification == "Valid Breakdown Source"
            and (source.approved_discovery_url or source.base_url)
        )

    def _plugin_record(self, implementation_key: str):
        return self.db.scalars(
            select(DiscoverySourcePlugin).where(
                DiscoverySourcePlugin.implementation_key == implementation_key
            )
        ).first()

    def _opportunity_source(self, name: str) -> OpportunitySource:
        source = self.db.scalars(
            select(OpportunitySource).where(OpportunitySource.name == name)
        ).first()
        if source:
            return source
        source = OpportunitySource(name=name, source_type="public_breakdowns", priority_rank=99, is_enabled=True)
        self.db.add(source)
        self.db.flush()
        return source

    def _key(self, item: NormalizedOpportunity) -> str:
        metadata = item.source_metadata or {}
        details = {**(item.production_details or {}), **(item.role_details or {})}
        date_parts = [
            metadata.get("posted_date"),
            details.get("submission_deadline"),
            details.get("audition_date"),
            details.get("shoot_dates"),
        ]
        source_url = item.original_post_url or metadata.get("source_url") or ""
        source_host = ""
        if source_url:
            from urllib.parse import urlparse

            source_host = urlparse(str(source_url)).netloc.lower().removeprefix("www.")
        value = " ".join(
            str(part or "")
            for part in [
                item.project,
                item.role,
                item.location,
                source_host,
                " ".join(str(date or "") for date in date_parts if date),
            ]
        )
        return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
