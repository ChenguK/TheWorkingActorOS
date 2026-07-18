import type { SourceResearchItem } from "../../../types/domain";
import { badSourceHealth } from "../constants";

export function isVisibleSource(source: SourceResearchItem, hiddenSourceIds: Set<string>) {
  return (
    !source.deleted &&
    !source.rejected_by_user &&
    !hiddenSourceIds.has(source.id) &&
    source.source_usefulness !== "Not Useful" &&
    !["Not Useful", "Rejected"].includes(source.source_classification) &&
    !badSourceHealth.includes(source.source_health) &&
    !badSourceHealth.includes(source.url_health_status)
  );
}

export function isApprovedSource(source: SourceResearchItem) {
  return source.approved_by_user || ["Approved", "Active", "Paused"].includes(source.status);
}

export function sourceOpenUrl(source: SourceResearchItem) {
  return source.final_resolved_url || source.submitted_url || source.approved_discovery_url || source.suggested_specific_url || source.base_url || source.source_url;
}

export function formatSourceDateTime(value?: string | null): string {
  if (!value) return "Unknown";
  return new Date(value).toLocaleString();
}

