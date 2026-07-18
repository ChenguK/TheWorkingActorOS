import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../../../services/api/queryKeys";
import { queryStaleTimes } from "../../../services/api/queryPolicy";
import { getCastingPatterns, getIntelligenceDashboard, getMaterialPerformance, getOperationsDashboard } from "../api";

export const analyticsKeys = {
  operations: queryKeys.analytics.list({ resource: "operationsDashboard" }),
  intelligence: queryKeys.analytics.list({ resource: "intelligenceDashboard" }),
  industryTrends: queryKeys.analytics.list({ resource: "industryTrends" }),
  materialPerformance: queryKeys.analytics.list({ resource: "materialPerformance" })
} as const;

export function useOperationsDashboard() {
  return useQuery({ queryKey: analyticsKeys.operations, queryFn: getOperationsDashboard, staleTime: queryStaleTimes.live, refetchOnMount: "always" });
}

export function useIntelligenceDashboard() {
  return useQuery({ queryKey: analyticsKeys.intelligence, queryFn: getIntelligenceDashboard, staleTime: queryStaleTimes.workflow });
}

export function useIndustryTrends() {
  return useQuery({ queryKey: analyticsKeys.industryTrends, queryFn: getCastingPatterns, staleTime: queryStaleTimes.reference });
}

export function useMaterialPerformance() {
  return useQuery({ queryKey: analyticsKeys.materialPerformance, queryFn: getMaterialPerformance, staleTime: queryStaleTimes.workflow });
}
