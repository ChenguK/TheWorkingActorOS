import { api } from "../../../services/api";
import type { SourceResearchItem } from "../../../types/domain";
import type { DiscoveryMode } from "../types";

export function listSources() {
  return api.get<SourceResearchItem[]>("/automation/source-research");
}

export function listArchivedSources() {
  return api.get<SourceResearchItem[]>("/automation/source-research/archive");
}

export function createSource(payload: unknown) {
  return api.post<SourceResearchItem>("/automation/source-research", payload);
}

export function findNewSources(modeOrParams?: DiscoveryMode | string) {
  const params = modeOrParams?.startsWith("?")
    ? modeOrParams
    : modeOrParams ? `?mode=${encodeURIComponent(modeOrParams)}` : "";
  return api.post<SourceResearchItem[]>(`/automation/source-research/find-new${params}`);
}

export function updateSource(sourceId: string, patch: Partial<SourceResearchItem>) {
  return api.patch<SourceResearchItem>(`/automation/source-research/${sourceId}`, patch);
}

export function approveSource(sourceId: string) {
  return api.post<SourceResearchItem>(`/automation/source-research/${sourceId}/add-to-discovery`);
}

export function rejectSource(sourceId: string, reason?: string | null) {
  return api.post<SourceResearchItem>(`/automation/source-research/${sourceId}/reject`, { rejection_reason: reason ?? null });
}

export function restoreSource(sourceId: string) {
  return api.post<SourceResearchItem>(`/automation/source-research/${sourceId}/restore`);
}

export function activateSource(sourceId: string) {
  return approveSource(sourceId);
}

export function disableSource(sourceId: string) {
  return updateSource(sourceId, { status: "Paused" });
}
