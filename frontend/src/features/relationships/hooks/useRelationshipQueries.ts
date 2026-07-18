import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "../../../services/api/queryKeys";
import { queryStaleTimes } from "../../../services/api/queryPolicy";
import type { ActorRelationship, CommunicationLog } from "../../../types/domain";
import {
  createCommunicationLog,
  createRelationship,
  deleteCommunicationLog,
  deleteRelationship,
  getRelationshipAnalytics,
  listCommunicationLogs,
  listRelationships,
  updateCommunicationLog,
  updateRelationship
} from "../api";

export const relationshipsListKey = queryKeys.relationships.list({ resource: "relationships" });
export const relationshipAnalyticsKey = queryKeys.relationships.list({ resource: "analytics" });
export const communicationLogsKey = queryKeys.relationships.list({ resource: "communicationLogs" });

export function useRelationships() {
  return useQuery({ queryKey: relationshipsListKey, queryFn: listRelationships, staleTime: queryStaleTimes.workflow });
}

export function useRelationshipAnalytics() {
  return useQuery({ queryKey: relationshipAnalyticsKey, queryFn: getRelationshipAnalytics, staleTime: queryStaleTimes.workflow });
}

export function useRelationshipInteractions() {
  return useQuery({ queryKey: communicationLogsKey, queryFn: listCommunicationLogs, staleTime: queryStaleTimes.workflow });
}

function useInvalidate(queryKey: readonly unknown[]) {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey });
}

function useInvalidateRelationshipRecords() {
  const queryClient = useQueryClient();
  return () => Promise.all([
    queryClient.invalidateQueries({ queryKey: relationshipsListKey }),
    queryClient.invalidateQueries({ queryKey: relationshipAnalyticsKey })
  ]);
}

export function useCreateRelationship() {
  const invalidate = useInvalidateRelationshipRecords();
  return useMutation({ mutationFn: (payload: unknown) => createRelationship(payload), onSuccess: invalidate });
}

export function useUpdateRelationship() {
  const invalidate = useInvalidateRelationshipRecords();
  return useMutation({
    mutationFn: ({ relationshipId, patch }: { relationshipId: string; patch: Partial<ActorRelationship> }) => updateRelationship(relationshipId, patch),
    onSuccess: invalidate
  });
}

export function useDeleteRelationship() {
  const invalidate = useInvalidateRelationshipRecords();
  return useMutation({ mutationFn: (relationshipId: string) => deleteRelationship(relationshipId), onSuccess: invalidate });
}

export function useAddRelationshipInteraction() {
  const invalidate = useInvalidate(communicationLogsKey);
  return useMutation({ mutationFn: (payload: unknown) => createCommunicationLog(payload), onSuccess: invalidate });
}

export function useUpdateRelationshipInteraction() {
  const invalidate = useInvalidate(communicationLogsKey);
  return useMutation({
    mutationFn: ({ logId, patch }: { logId: string; patch: Partial<CommunicationLog> }) => updateCommunicationLog(logId, patch),
    onSuccess: invalidate
  });
}

export function useDeleteRelationshipInteraction() {
  const invalidate = useInvalidate(communicationLogsKey);
  return useMutation({ mutationFn: (logId: string) => deleteCommunicationLog(logId), onSuccess: invalidate });
}
