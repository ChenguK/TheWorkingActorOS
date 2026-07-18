import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { invalidateInBackground, publicInvalidationKeys } from "../../../services/api/invalidationContracts";
import { queryKeys } from "../../../services/api/queryKeys";
import { queryStaleTimes } from "../../../services/api/queryPolicy";
import { getCommandCenter, refreshCommandCenter, resolveOutcomeNudge, updatePlatformCheckIn } from "../api";

export const commandCenterKey = queryKeys.chiefOfStaff.list({ resource: "commandCenter" });

export function useCommandCenter() {
  return useQuery({
    queryKey: commandCenterKey,
    queryFn: getCommandCenter,
    staleTime: queryStaleTimes.live,
    refetchOnMount: "always"
  });
}

function useCommandCenterInvalidation() {
  const client = useQueryClient();
  return () => client.invalidateQueries({ queryKey: commandCenterKey });
}

export function usePlatformCheckIn() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ subscriptionId, checkedToday }: { subscriptionId: string; checkedToday: boolean }) =>
      updatePlatformCheckIn(subscriptionId, checkedToday),
    onSuccess: (_result, { checkedToday }) => invalidateInBackground(
      client,
      checkedToday ? [commandCenterKey, publicInvalidationKeys.journalEntries] : [commandCenterKey]
    )
  });
}

export function useResolveOutcomeNudge() {
  const invalidate = useCommandCenterInvalidation();
  return useMutation({ mutationFn: resolveOutcomeNudge, onSuccess: invalidate });
}

export function useRefreshCommandCenter() {
  const invalidate = useCommandCenterInvalidation();
  return useMutation({ mutationFn: refreshCommandCenter, onSuccess: invalidate });
}
