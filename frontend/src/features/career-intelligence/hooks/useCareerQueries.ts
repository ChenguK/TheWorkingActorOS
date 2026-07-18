import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { invalidateInBackground, publicInvalidationKeys } from "../../../services/api/invalidationContracts";
import { queryKeys } from "../../../services/api/queryKeys";
import { queryStaleTimes } from "../../../services/api/queryPolicy";
import type { CareerDevelopmentTask, CareerMemory, CastingGoal } from "../../../types/domain";
import {
  completeCareerTask, createCareerTask, createCastingGoal, createCastingOffice, createWatchList,
  deleteCareerTask, deleteCastingGoal, deleteWatchList, generateCareerSwot, generateQuarterlyReview,
  getCareerMemory, getCareerSwot, listCareerTasks, listCastingGoals, listCastingOffices,
  listDreamReadiness, listQuarterlyReviews, listWatchLists, updateCareerMemory, updateCareerTask,
  updateCastingGoal, updateWatchList
} from "../api";

export const careerKeys = {
  tasks: queryKeys.career.list({ resource: "tasks" }),
  swot: queryKeys.career.list({ resource: "swot" }),
  castingOffices: queryKeys.career.list({ resource: "castingOffices" }),
  quarterlyReviews: queryKeys.career.list({ resource: "quarterlyReviews" }),
  dreamReadiness: queryKeys.career.list({ resource: "dreamReadiness" }),
  castingGoals: queryKeys.career.list({ resource: "castingGoals" }),
  watchLists: queryKeys.career.list({ resource: "watchLists" }),
  memory: queryKeys.career.list({ resource: "memory" })
} as const;

const options = { staleTime: queryStaleTimes.workflow, refetchOnMount: "always" as const };
export const useCareerTasks = () => useQuery({ queryKey: careerKeys.tasks, queryFn: listCareerTasks, ...options });
export const useCareerSwot = () => useQuery({ queryKey: careerKeys.swot, queryFn: getCareerSwot, ...options });
export const useCastingOffices = () => useQuery({ queryKey: careerKeys.castingOffices, queryFn: listCastingOffices, ...options });
export const useQuarterlyReviews = () => useQuery({ queryKey: careerKeys.quarterlyReviews, queryFn: listQuarterlyReviews, ...options });
export const useDreamReadiness = () => useQuery({ queryKey: careerKeys.dreamReadiness, queryFn: listDreamReadiness, ...options });
export const useCastingGoals = () => useQuery({ queryKey: careerKeys.castingGoals, queryFn: listCastingGoals, ...options });
export const useWatchLists = () => useQuery({ queryKey: careerKeys.watchLists, queryFn: listWatchLists, ...options });
export const useCareerMemory = () => useQuery({ queryKey: careerKeys.memory, queryFn: getCareerMemory, ...options });

export type CareerTaskOption = Pick<CareerDevelopmentTask, "id" | "title" | "status">;
export const selectCareerTaskOptions = (tasks: CareerDevelopmentTask[]): CareerTaskOption[] => tasks.map(({ id, title, status }) => ({ id, title, status }));
export const useCareerTaskOptions = () => useQuery({ queryKey: careerKeys.tasks, queryFn: listCareerTasks, select: selectCareerTaskOptions, ...options });

function useInvalidate(...keys: readonly (readonly unknown[])[]) { const client = useQueryClient(); return () => invalidateInBackground(client, keys); }
export function useCreateCareerTask() { const invalidate = useInvalidate(careerKeys.tasks, publicInvalidationKeys.commandCenter); return useMutation({ mutationFn: createCareerTask, onSuccess: invalidate }); }
export function useUpdateCareerTask() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: unknown }) => updateCareerTask(id, patch),
    onSuccess: (_result, { patch }) => {
      const keys: (readonly unknown[])[] = [careerKeys.tasks, publicInvalidationKeys.commandCenter];
      if (((patch ?? {}) as Record<string, unknown>).status === "Completed") keys.push(publicInvalidationKeys.journalEntries);
      invalidateInBackground(client, keys);
    }
  });
}
export function useCompleteCareerTask() { const invalidate = useInvalidate(careerKeys.tasks, publicInvalidationKeys.journalEntries, publicInvalidationKeys.commandCenter); return useMutation({ mutationFn: completeCareerTask, onSuccess: invalidate }); }
export function useDeleteCareerTask() { const invalidate = useInvalidate(careerKeys.tasks, publicInvalidationKeys.commandCenter); return useMutation({ mutationFn: deleteCareerTask, onSuccess: invalidate }); }
export function useCreateCastingOffice() { const invalidate = useInvalidate(careerKeys.castingOffices); return useMutation({ mutationFn: createCastingOffice, onSuccess: invalidate }); }
export function useCreateWatchList() { const invalidate = useInvalidate(careerKeys.watchLists); return useMutation({ mutationFn: createWatchList, onSuccess: invalidate }); }
export function useUpdateWatchList() { const invalidate = useInvalidate(careerKeys.watchLists); return useMutation({ mutationFn: ({ id, patch }: { id: string; patch: unknown }) => updateWatchList(id, patch), onSuccess: invalidate }); }
export function useDeleteWatchList() { const invalidate = useInvalidate(careerKeys.watchLists); return useMutation({ mutationFn: deleteWatchList, onSuccess: invalidate }); }
export function useGenerateQuarterlyReview() { const invalidate = useInvalidate(careerKeys.quarterlyReviews); return useMutation({ mutationFn: ({ year, quarter }: { year: number; quarter: number }) => generateQuarterlyReview(year, quarter), onSuccess: invalidate }); }
export function useCreateCastingGoal() { const invalidate = useInvalidate(careerKeys.castingGoals, careerKeys.watchLists); return useMutation({ mutationFn: createCastingGoal, onSuccess: invalidate }); }
export function useUpdateCastingGoal() { const invalidate = useInvalidate(careerKeys.castingGoals, careerKeys.watchLists); return useMutation({ mutationFn: ({ id, patch }: { id: string; patch: Partial<CastingGoal> }) => updateCastingGoal(id, patch), onSuccess: invalidate }); }
export function useDeleteCastingGoal() { const invalidate = useInvalidate(careerKeys.castingGoals); return useMutation({ mutationFn: deleteCastingGoal, onSuccess: invalidate }); }
export function useGenerateCareerSwot() { const invalidate = useInvalidate(careerKeys.swot); return useMutation({ mutationFn: generateCareerSwot, onSuccess: invalidate }); }
export function useUpdateCareerMemory() { const invalidate = useInvalidate(careerKeys.memory); return useMutation({ mutationFn: (patch: Partial<CareerMemory>) => updateCareerMemory(patch), onSuccess: invalidate }); }
