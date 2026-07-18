import { api } from "../../../services/api";
import type { MaterialCreationPlan, SceneCandidate, ScriptSource, SystemCapabilities } from "../../../types/domain";

export function listScriptSources() {
  return api.get<ScriptSource[]>("/intelligence/scripts/sources");
}

export function createScriptSource(payload: unknown) {
  return api.post<ScriptSource>("/intelligence/scripts/sources", payload);
}

export function createMaterialPlan(payload: unknown) {
  return api.post<MaterialCreationPlan>("/intelligence/materials/plan", payload);
}

export function approveMaterialPlan(planId: string) {
  return api.patch<MaterialCreationPlan>(`/intelligence/materials/plans/${planId}`, { plan_status: "Approved" });
}

export function denyMaterialPlan(planId: string) {
  return api.patch<MaterialCreationPlan>(`/intelligence/materials/plans/${planId}`, { plan_status: "Denied" });
}

export function findSceneOptions(payload: unknown) {
  return api.post<SceneCandidate[]>("/intelligence/scripts/find-scenes", payload);
}

export function saveSceneCandidate(candidateId: string, actionStatus = "Saved") {
  return api.patch<SceneCandidate>(`/intelligence/scripts/scene-candidates/${candidateId}`, { action_status: actionStatus });
}

export function requestScenePermission(candidateId: string) {
  return saveSceneCandidate(candidateId, "Permission Requested");
}

export function getScriptFinderCapabilities() {
  return api.get<SystemCapabilities>("/system/capabilities");
}

