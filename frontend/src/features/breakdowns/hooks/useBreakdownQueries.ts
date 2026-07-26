import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { invalidateInBackground, invalidationContracts, keysForContract, publicInvalidationKeys } from "../../../services/api/invalidationContracts";
import { queryKeys } from "../../../services/api/queryKeys";
import { queryStaleTimes } from "../../../services/api/queryPolicy";
import type { Opportunity } from "../../../types/domain";
import { sourceArchiveKey, sourceListKey } from "../../source-library";
import {
  approveActingBreakdown, approveSubmissionQueueItem, createBreakdown, deepParseBreakdown, deleteBreakdown,
  executeSubmissionQueueItem, generateBreakdownStrategy, listAuditionReadiness,
  listBreakdownRecommendations, listBreakdowns, listDiscoveryPlugins, listHiddenBreakdowns, listMaterialMatches,
  listSubmissionQueue, parseBreakdownText, queueSubmissionFromRecommendation, refreshDemographicCheck,
  rejectBreakdown, rejectSubmissionQueueItem, runBreakdownDiscovery, sendRecommendationFeedback, updateBreakdown
} from "../api";
import type { DiscoveryRunRequest } from "../types";

export const breakdownKeys = {
  opportunities: queryKeys.breakdowns.list({ resource: "opportunities" }),
  hidden: queryKeys.breakdowns.list({ resource: "hiddenOpportunities" }),
  recommendations: queryKeys.breakdowns.list({ resource: "recommendations" }),
  plugins: queryKeys.breakdowns.list({ resource: "discoveryPlugins" }),
  queue: queryKeys.breakdowns.list({ resource: "submissionQueue" }),
  readiness: queryKeys.breakdowns.list({ resource: "readiness" }),
  materialMatches: queryKeys.breakdowns.list({ resource: "materialMatches" })
} as const;

const workflow = { staleTime: queryStaleTimes.workflow, refetchOnMount: "always" as const };
export const useBreakdowns = () => useQuery({ queryKey: breakdownKeys.opportunities, queryFn: listBreakdowns, ...workflow });
export const useHiddenBreakdowns = () => useQuery({ queryKey: breakdownKeys.hidden, queryFn: listHiddenBreakdowns, ...workflow });
export const useBreakdownRecommendations = () => useQuery({ queryKey: breakdownKeys.recommendations, queryFn: listBreakdownRecommendations, ...workflow });
export const useDiscoveryPlugins = () => useQuery({ queryKey: breakdownKeys.plugins, queryFn: listDiscoveryPlugins, ...workflow });
export const useSubmissionQueue = () => useQuery({ queryKey: breakdownKeys.queue, queryFn: listSubmissionQueue, ...workflow });
export const useAuditionReadiness = () => useQuery({ queryKey: breakdownKeys.readiness, queryFn: listAuditionReadiness, ...workflow });
export const useMaterialMatches = () => useQuery({ queryKey: breakdownKeys.materialMatches, queryFn: () => listMaterialMatches(), ...workflow });
export const useBreakdown = (id?: string) => useQuery({ queryKey: breakdownKeys.opportunities, queryFn: listBreakdowns, select: (items) => items.find((item) => item.id === id) ?? null, enabled: Boolean(id), ...workflow });

export type OpportunityOption = Pick<Opportunity, "id" | "project" | "role" | "project_type" | "status">;
export const selectOpportunityOptions = (items: Opportunity[]): OpportunityOption[] => items.map(({ id, project, role, project_type, status }) => ({ id, project, role, project_type, status }));
export const useOpportunityOptions = () => useQuery({ queryKey: breakdownKeys.opportunities, queryFn: listBreakdowns, select: selectOpportunityOptions, ...workflow });

function useInvalidator() {
  const client = useQueryClient();
  return (...keys: readonly (readonly unknown[])[]) => invalidateInBackground(client, keys);
}
const listKeys = [breakdownKeys.opportunities, breakdownKeys.hidden] as const;
const classificationKeys = [...listKeys, breakdownKeys.readiness, breakdownKeys.materialMatches] as const;
const opportunityAggregateKeys = [publicInvalidationKeys.analyticsIntelligence, publicInvalidationKeys.analyticsIndustryTrends] as const;

export function useCreateBreakdown() { const invalidate = useInvalidator(); return useMutation({ mutationFn: createBreakdown, onSuccess: () => invalidate(...keysForContract(invalidationContracts.opportunityCreate)) }); }
export function useUpdateBreakdown() { const invalidate = useInvalidator(); return useMutation({ mutationFn: ({ id, patch }: { id: string; patch: unknown }) => updateBreakdown(id, patch), onSuccess: () => invalidate(...keysForContract(invalidationContracts.opportunityUpdate)) }); }
export function useDeleteBreakdown() { const invalidate = useInvalidator(); return useMutation({ mutationFn: deleteBreakdown, onSuccess: () => invalidate(...keysForContract(invalidationContracts.opportunityDelete)) }); }
export function useApproveBreakdown() { const invalidate = useInvalidator(); return useMutation({ mutationFn: approveActingBreakdown, onSuccess: () => invalidate(...classificationKeys, ...opportunityAggregateKeys, publicInvalidationKeys.workflowSelfTapes, publicInvalidationKeys.calendarEvents, publicInvalidationKeys.journalEntries, publicInvalidationKeys.commandCenter, publicInvalidationKeys.analyticsOperations) }); }
export function useRejectBreakdown() { const invalidate = useInvalidator(); return useMutation({ mutationFn: ({ id, payload }: { id: string; payload: unknown }) => rejectBreakdown(id, payload), onSuccess: () => invalidate(...keysForContract(invalidationContracts.opportunityReject)) }); }
export function useDeepParseBreakdown() { const invalidate = useInvalidator(); return useMutation({ mutationFn: deepParseBreakdown, onSuccess: () => invalidate(...keysForContract(invalidationContracts.opportunityDeepParse)) }); }
export function useParseBreakdownText() { const invalidate = useInvalidator(); return useMutation({ mutationFn: ({ id, text }: { id: string; text: string }) => parseBreakdownText(id, text), onSuccess: () => invalidate(...keysForContract(invalidationContracts.opportunityManualParse)) }); }
export function useRefreshDemographicCheck() { const invalidate = useInvalidator(); return useMutation({ mutationFn: refreshDemographicCheck, onSuccess: () => invalidate(...classificationKeys, ...opportunityAggregateKeys) }); }
export function useGenerateBreakdownStrategy() { const invalidate = useInvalidator(); return useMutation({ mutationFn: generateBreakdownStrategy, onSuccess: () => invalidate(...keysForContract(invalidationContracts.opportunityStrategyGenerate)) }); }
export function useRecommendationFeedback() { const invalidate = useInvalidator(); return useMutation({ mutationFn: ({ id, payload }: { id: string; payload: unknown }) => sendRecommendationFeedback(id, payload), onSuccess: () => invalidate(...keysForContract(invalidationContracts.recommendationFeedbackCreate)) }); }
export function useRunBreakdownDiscovery() { const invalidate = useInvalidator(); return useMutation({ mutationFn: (request: DiscoveryRunRequest) => runBreakdownDiscovery(request), onSuccess: () => invalidate(...classificationKeys, ...opportunityAggregateKeys, breakdownKeys.recommendations, sourceListKey, sourceArchiveKey) }); }
export function useQueueRecommendation() { const invalidate = useInvalidator(); return useMutation({ mutationFn: queueSubmissionFromRecommendation, onSuccess: () => invalidate(breakdownKeys.queue, breakdownKeys.recommendations) }); }
export function useApproveQueueItem() { const invalidate = useInvalidator(); return useMutation({ mutationFn: approveSubmissionQueueItem, onSuccess: () => invalidate(breakdownKeys.queue) }); }
export function useRejectQueueItem() { const invalidate = useInvalidator(); return useMutation({ mutationFn: rejectSubmissionQueueItem, onSuccess: () => invalidate(breakdownKeys.queue) }); }
export function useExecuteQueueItem() { const invalidate = useInvalidator(); return useMutation({ mutationFn: executeSubmissionQueueItem, onSuccess: () => invalidate(breakdownKeys.queue) }); }
