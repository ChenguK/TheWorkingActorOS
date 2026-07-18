import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "../../../services/api/queryKeys";
import { queryStaleTimes } from "../../../services/api/queryPolicy";
import { generateWeeklyBrief, listExecutiveBriefs } from "../api";

export const executiveBriefKeys = { list: queryKeys.chiefOfStaff.list({ resource: "briefs" }) } as const;
export const useExecutiveBriefs = () => useQuery({ queryKey: executiveBriefKeys.list, queryFn: listExecutiveBriefs, staleTime: queryStaleTimes.workflow, refetchOnMount: "always" });
export function useGenerateWeeklyBrief() {
  const client = useQueryClient();
  return useMutation({ mutationFn: generateWeeklyBrief, onSuccess: () => client.invalidateQueries({ queryKey: executiveBriefKeys.list }) });
}
