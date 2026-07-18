import { api } from "../../../services/api";
import type {
  AuditionPreparationBrief,
  CareerDevelopmentTask,
  CareerMemory,
  CareerPathSimulation,
  CareerSwotAnalysis,
  CastingGoal,
  CastingOffice,
  DreamRoleReadiness,
  MaterialCreationPlan,
  QuarterlyCareerReview,
  WatchList
} from "../../../types/domain";

export const listCareerTasks = () => api.get<CareerDevelopmentTask[]>("/career-development/tasks");
export const getCareerSwot = () => api.get<CareerSwotAnalysis | null>("/agents/career/swot");
export const listCastingOffices = () => api.get<CastingOffice[]>("/intelligence/casting-offices");
export const listQuarterlyReviews = () => api.get<QuarterlyCareerReview[]>("/intelligence/career/quarterly-reviews");
export const listDreamReadiness = () => api.get<DreamRoleReadiness[]>("/intelligence/dream-targets/readiness");
export const listCastingGoals = () => api.get<CastingGoal[]>("/agents/casting-goals");
export const listWatchLists = () => api.get<WatchList[]>("/agents/watch-lists");
export const getCareerMemory = () => api.get<CareerMemory | null>("/agents/career-memory");
export const updateCareerMemory = (payload: Partial<CareerMemory>) => api.put<CareerMemory>("/agents/career-memory", payload);

export function createCareerTask(payload: unknown) {
  return api.post<CareerDevelopmentTask>("/career-development/tasks", payload);
}

export function updateCareerTask(taskId: string, patch: unknown) {
  return api.patch<CareerDevelopmentTask>(`/career-development/tasks/${taskId}`, patch);
}

export function completeCareerTask(taskId: string) {
  return api.post(`/career-development/tasks/${taskId}/complete`);
}

export function deleteCareerTask(taskId: string) {
  return api.delete(`/career-development/tasks/${taskId}`);
}

export function createCastingOffice(payload: unknown) {
  return api.post<CastingOffice>("/intelligence/casting-offices", payload);
}

export function prepareOpportunity(opportunityId: string) {
  return api.post<AuditionPreparationBrief>(`/intelligence/opportunities/${opportunityId}/prepare`);
}

export function createMaterialPlan(payload: unknown) {
  return api.post<MaterialCreationPlan>("/intelligence/materials/plan", payload);
}

export function createWatchList(payload: unknown) {
  return api.post<WatchList>("/agents/watch-lists", payload);
}

export function updateWatchList(watchListId: string, payload: unknown) {
  return api.patch<WatchList>(`/agents/watch-lists/${watchListId}`, payload);
}

export function deleteWatchList(watchListId: string) {
  return api.delete(`/agents/watch-lists/${watchListId}`);
}

export function generateQuarterlyReview(year: number, quarter: number) {
  return api.post<QuarterlyCareerReview>("/intelligence/career/quarterly-reviews", { year, quarter });
}

export function simulateCareerPath(goal: string) {
  return api.post<CareerPathSimulation>("/intelligence/career/simulate", { goal });
}

export function createCastingGoal(payload: unknown) {
  return api.post<CastingGoal>("/agents/casting-goals", payload);
}

export function updateCastingGoal(goalId: string, patch: Partial<CastingGoal>) {
  return api.patch<CastingGoal>(`/agents/casting-goals/${goalId}`, patch);
}

export function deleteCastingGoal(goalId: string) {
  return api.delete(`/agents/casting-goals/${goalId}`);
}

export function generateCareerSwot() {
  return api.post("/agents/career/swot");
}
