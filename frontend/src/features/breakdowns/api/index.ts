import { api } from "../../../services/api";
import type {
  AgentRecommendation,
  AuditionReadiness,
  DiscoveryPlugin,
  MaterialOpportunityMatch,
  Opportunity, SubmissionAutomationQueueItem,
  RecommendationFeedback
} from "../../../types/domain";
import type { DiscoveryReport, DiscoveryRunRequest, DiscoveryRunResult } from "../types";

export function listBreakdowns() {
  return api.get<Opportunity[]>("/opportunities");
}

export const listHiddenBreakdowns = () => api.get<Opportunity[]>("/automation/opportunities/hidden");
export const listBreakdownRecommendations = () => api.get<AgentRecommendation[]>("/agents/recommendations");
export const listDiscoveryPlugins = () => api.get<DiscoveryPlugin[]>("/automation/discovery/plugins");
export const listSubmissionQueue = () => api.get<SubmissionAutomationQueueItem[]>("/automation/submission-queue");
export const listAuditionReadiness = () => api.get<AuditionReadiness[]>("/intelligence/readiness/opportunities");

export function createBreakdown(payload: unknown) {
  return api.post<Opportunity>("/opportunities", payload);
}

export function updateBreakdown(opportunityId: string, patch: unknown) {
  return api.patch<Opportunity>(`/opportunities/${opportunityId}`, patch);
}

export function deleteBreakdown(opportunityId: string) {
  return api.delete(`/opportunities/${opportunityId}`);
}

export function approveActingBreakdown(opportunityId: string) {
  return api.post(`/opportunities/${opportunityId}/approve-acting-breakdown`);
}

export function rejectBreakdown(opportunityId: string, payload: unknown) {
  return api.post(`/opportunities/${opportunityId}/reject`, payload);
}

export function deepParseBreakdown(opportunityId: string) {
  return api.post(`/opportunities/${opportunityId}/deep-parse`);
}

export function parseBreakdownText(opportunityId: string, rawText: string) {
  return api.post(`/opportunities/${opportunityId}/parse-breakdown-text`, { raw_text: rawText });
}

export function refreshDemographicCheck(opportunityId: string) {
  return api.post(`/opportunities/${opportunityId}/demographic-check`);
}

export function generateBreakdownStrategy(opportunityId: string) {
  return api.post<AgentRecommendation>(`/opportunities/${opportunityId}/recommend`);
}

export function listMaterialMatches(query = "include_hidden=false&min_score=15") {
  return api.get<MaterialOpportunityMatch[]>(`/opportunities/material-matches?${query}`);
}

export function sendRecommendationFeedback(recommendationId: string, payload: unknown) {
  return api.post<RecommendationFeedback>(`/agents/recommendations/${recommendationId}/feedback`, payload);
}

export function getDiscoveryReport() {
  return api.get<DiscoveryReport>("/automation/discovery/report");
}

export function runBreakdownDiscovery({ mode, searchModes, specificArchetype }: DiscoveryRunRequest) {
  const params = new URLSearchParams({ mode });
  searchModes.forEach((searchMode) => params.append("search_modes", searchMode));
  if (specificArchetype?.trim()) params.set("specific_archetype", specificArchetype.trim());
  return api.post<DiscoveryRunResult>(`/automation/discovery/run?${params.toString()}`);
}

export function queueSubmissionFromRecommendation(recommendationId: string) {
  return api.post(`/automation/submission-queue/from-recommendation/${recommendationId}`);
}

export function approveSubmissionQueueItem(queueItemId: string) {
  return api.post(`/automation/submission-queue/${queueItemId}/approve`);
}

export function rejectSubmissionQueueItem(queueItemId: string) {
  return api.post(`/automation/submission-queue/${queueItemId}/reject`);
}

export function executeSubmissionQueueItem(queueItemId: string) {
  return api.post(`/automation/submission-queue/${queueItemId}/execute`);
}
