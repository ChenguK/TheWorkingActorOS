import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "../../../services/api/queryKeys";
import { queryStaleTimes } from "../../../services/api/queryPolicy";
import type { SourceResearchItem } from "../../../types/domain";
import {
  approveSource,
  createSource,
  findNewSources,
  listArchivedSources,
  listSources,
  rejectSource,
  restoreSource,
  updateSource
} from "../api";
import type { DiscoveryMode } from "../types";
import { isApprovedSource } from "../utils";

export const sourceListKey = queryKeys.sourceLibrary.list({ resource: "sources" });
export const sourceArchiveKey = queryKeys.sourceLibrary.list({ resource: "archive" });

export function useSourceResearchItems() {
  return useQuery({
    queryKey: sourceListKey,
    queryFn: listSources,
    staleTime: queryStaleTimes.workflow,
    refetchOnMount: "always"
  });
}

export function usePendingSourceApprovals() {
  return useQuery({
    queryKey: sourceListKey,
    queryFn: listSources,
    staleTime: queryStaleTimes.workflow,
    refetchOnMount: "always",
    select: (sources) => sources.filter(
      (source) => ["Suggested", "Researching"].includes(source.status)
        && source.url_health_status === "Active"
        && !isApprovedSource(source)
    )
  });
}

export function useRejectedSources() {
  return useQuery({
    queryKey: sourceArchiveKey,
    queryFn: listArchivedSources,
    staleTime: queryStaleTimes.workflow,
    enabled: false
  });
}

function useInvalidateSourceLists() {
  const queryClient = useQueryClient();
  return () => Promise.all([
    queryClient.invalidateQueries({ queryKey: sourceListKey }),
    queryClient.invalidateQueries({ queryKey: sourceArchiveKey })
  ]);
}

export function useCreateSourceResearchItem() {
  const invalidate = useInvalidateSourceLists();
  return useMutation({ mutationFn: (payload: unknown) => createSource(payload), onSuccess: invalidate });
}

export function useUpdateSourceResearchItem() {
  const invalidate = useInvalidateSourceLists();
  return useMutation({
    mutationFn: ({ sourceId, patch }: { sourceId: string; patch: Partial<SourceResearchItem> }) => updateSource(sourceId, patch),
    onSuccess: invalidate
  });
}

export function useActivateSourceResearchItem() {
  const invalidate = useInvalidateSourceLists();
  return useMutation({ mutationFn: (sourceId: string) => approveSource(sourceId), onSuccess: invalidate });
}

export const useApproveSourceResearchItem = useActivateSourceResearchItem;

export function useRejectSourceResearchItem() {
  const invalidate = useInvalidateSourceLists();
  return useMutation({
    mutationFn: ({ sourceId, reason }: { sourceId: string; reason?: string | null }) => rejectSource(sourceId, reason),
    onSuccess: invalidate
  });
}

export function useRestoreSourceResearchItem() {
  const invalidate = useInvalidateSourceLists();
  return useMutation({ mutationFn: (sourceId: string) => restoreSource(sourceId), onSuccess: invalidate });
}

export function useDiscoverNewSources() {
  const invalidate = useInvalidateSourceLists();
  return useMutation({ mutationFn: (mode?: DiscoveryMode) => findNewSources(mode), onSuccess: invalidate });
}
