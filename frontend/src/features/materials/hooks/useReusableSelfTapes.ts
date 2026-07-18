import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "../../../services/api/queryKeys";
import { queryStaleTimes } from "../../../services/api/queryPolicy";
import { createSelfTape, deleteSelfTape, getReusableSelfTapeAnalytics, listReusableSelfTapes, updateSelfTape } from "../api";
import type { ReusableSelfTapeUpdate } from "../api";

export const reusableSelfTapeKeys = {
  library: queryKeys.materials.list({ resource: "reusableSelfTapes" }),
  analytics: queryKeys.materials.list({ resource: "reusableSelfTapeAnalytics" })
} as const;

export const useReusableSelfTapes = () => useQuery({ queryKey: reusableSelfTapeKeys.library, queryFn: listReusableSelfTapes, staleTime: queryStaleTimes.workflow });
export const useReusableSelfTapeAnalytics = () => useQuery({ queryKey: reusableSelfTapeKeys.analytics, queryFn: getReusableSelfTapeAnalytics, staleTime: queryStaleTimes.reference });

function useInvalidateReusableTapes() {
  const client = useQueryClient();
  return () => Promise.all([
    client.invalidateQueries({ queryKey: reusableSelfTapeKeys.library }),
    client.invalidateQueries({ queryKey: reusableSelfTapeKeys.analytics })
  ]);
}

export function useCreateReusableSelfTape() { const invalidate = useInvalidateReusableTapes(); return useMutation({ mutationFn: createSelfTape, onSuccess: invalidate }); }
export function useUpdateReusableSelfTape() { const invalidate = useInvalidateReusableTapes(); return useMutation({ mutationFn: ({ id, patch }: { id: string; patch: ReusableSelfTapeUpdate }) => updateSelfTape(id, patch), onSuccess: invalidate }); }
export function useDeleteReusableSelfTape() { const invalidate = useInvalidateReusableTapes(); return useMutation({ mutationFn: deleteSelfTape, onSuccess: invalidate }); }
