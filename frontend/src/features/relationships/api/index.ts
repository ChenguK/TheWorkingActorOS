import { api } from "../../../services/api";
import type { ActorRelationship, CommunicationLog, RelationshipAnalytics } from "../../../types/domain";

export function listRelationships() {
  return api.get<ActorRelationship[]>("/intelligence/relationships");
}

export function createRelationship(payload: unknown) {
  return api.post<ActorRelationship>("/intelligence/relationships", payload);
}

export function updateRelationship(relationshipId: string, patch: unknown) {
  return api.patch(`/intelligence/relationships/${relationshipId}`, patch);
}

export function deleteRelationship(relationshipId: string) {
  return api.delete(`/intelligence/relationships/${relationshipId}`);
}

export function getRelationshipAnalytics() {
  return api.get<RelationshipAnalytics>("/intelligence/relationships/analytics");
}

export function listCommunicationLogs() {
  return api.get<CommunicationLog[]>("/intelligence/communication-logs");
}

export function createCommunicationLog(payload: unknown) {
  return api.post<CommunicationLog>("/intelligence/communication-logs", payload);
}

export function updateCommunicationLog(logId: string, patch: unknown) {
  return api.patch<CommunicationLog>(`/intelligence/communication-logs/${logId}`, patch);
}

export function deleteCommunicationLog(logId: string) {
  return api.delete(`/intelligence/communication-logs/${logId}`);
}
