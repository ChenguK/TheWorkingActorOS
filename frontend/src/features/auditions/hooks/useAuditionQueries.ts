import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  invalidateInBackground,
  invalidationContracts,
  keysForContract,
  publicInvalidationKeys
} from "../../../services/api/invalidationContracts";
import { queryKeys } from "../../../services/api/queryKeys";
import { queryStaleTimes } from "../../../services/api/queryPolicy";
import type { Submission } from "../../../types/domain";
import {
  addSubmissionStatus, createAuditionNote, createCallbackEvent, createSelfTapeTask, deleteAuditionNote,
  deleteCallbackEvent, deleteSubmission, getSubmission, listAuditionNotes, listAuditions,
  listCallbackEvents, listSubmissions, recordSubmission, updateAuditionNote, updateCallbackEvent,
  updateSelfTapeTask, updateSubmission
} from "../api";

export const auditionKeys = {
  submissions: queryKeys.auditions.list({ resource: "submissions" }),
  submission: (id: string) => queryKeys.auditions.detail(id),
  statusHistory: (id: string) => queryKeys.auditions.list({ resource: "statusHistory", submissionId: id }),
  selfTapes: queryKeys.auditions.list({ resource: "selfTapes" }),
  callbacks: queryKeys.auditions.list({ resource: "callbacks" }),
  performanceNotes: queryKeys.auditions.list({ resource: "auditionJournal" })
} as const;

const workflow = { staleTime: queryStaleTimes.workflow, refetchOnMount: "always" as const };
export const useSubmissions = () => useQuery({ queryKey: auditionKeys.submissions, queryFn: listSubmissions, ...workflow });
export const useSubmission = (id?: string) => useQuery({ queryKey: auditionKeys.submission(id ?? ""), queryFn: () => getSubmission(id!), enabled: Boolean(id), ...workflow });
export const useSubmissionStatusHistory = (id?: string) => useQuery({ queryKey: auditionKeys.submissions, queryFn: listSubmissions, enabled: Boolean(id), select: (items) => items.find((item) => item.id === id)?.status_history ?? [], ...workflow });
export const useWorkflowSelfTapes = () => useQuery({ queryKey: auditionKeys.selfTapes, queryFn: listAuditions, ...workflow });
export const useCallbackEvents = () => useQuery({ queryKey: auditionKeys.callbacks, queryFn: listCallbackEvents, ...workflow });
export const useAuditionPerformanceNotes = () => useQuery({ queryKey: auditionKeys.performanceNotes, queryFn: listAuditionNotes, ...workflow });

export type SubmissionOption = Pick<Submission, "id" | "current_status" | "opportunity_id" | "opportunity">;
export const selectSubmissionOptions = (items: Submission[]): SubmissionOption[] => items.map(({ id, current_status, opportunity_id, opportunity }) => ({ id, current_status, opportunity_id, opportunity }));
export const useSubmissionOptions = () => useQuery({ queryKey: auditionKeys.submissions, queryFn: listSubmissions, select: selectSubmissionOptions, ...workflow });

function useInvalidate() {
  const client = useQueryClient();
  return (...keys: readonly (readonly unknown[])[]) => invalidateInBackground(client, keys);
}

export function useCreateSubmission() { const invalidate = useInvalidate(); return useMutation({ mutationFn: recordSubmission, onSuccess: () => invalidate(...keysForContract(invalidationContracts.submissionCreate)) }); }
export function useUpdateSubmission() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: unknown }) => updateSubmission(id, patch),
    onSuccess: (_result, { patch }) => invalidate(...submissionUpdateKeys(patch))
  });
}
export function useDeleteSubmission() { const invalidate = useInvalidate(); return useMutation({ mutationFn: deleteSubmission, onSuccess: () => invalidate(...keysForContract(invalidationContracts.submissionDelete)) }); }
export function useUpdateSubmissionStatus() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => addSubmissionStatus(id, status),
    onSuccess: (_result, { status }) => invalidate(...submissionStatusKeys(status))
  });
}
export function useCreateWorkflowSelfTape() { const invalidate = useInvalidate(); return useMutation({ mutationFn: createSelfTapeTask, onSuccess: () => invalidate(auditionKeys.selfTapes, publicInvalidationKeys.commandCenter) }); }
export function useUpdateWorkflowSelfTape() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: unknown }) => updateSelfTapeTask(id, patch),
    onSuccess: (_result, { patch }) => invalidate(...workflowSelfTapeUpdateKeys(patch))
  });
}
export function useCreateCallbackEvent() { const invalidate = useInvalidate(); return useMutation({ mutationFn: createCallbackEvent, onSuccess: () => invalidate(...keysForContract(invalidationContracts.callbackChange)) }); }
export function useUpdateCallbackEvent() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: unknown }) => updateCallbackEvent(id, patch),
    onSuccess: (_result, { patch }) => invalidate(...callbackUpdateKeys(patch))
  });
}
export function useDeleteCallbackEvent() { const invalidate = useInvalidate(); return useMutation({ mutationFn: deleteCallbackEvent, onSuccess: () => invalidate(auditionKeys.callbacks, publicInvalidationKeys.analyticsIntelligence) }); }
export function useCreateAuditionPerformanceNote() { const invalidate = useInvalidate(); return useMutation({ mutationFn: createAuditionNote, onSuccess: () => invalidate(auditionKeys.performanceNotes) }); }
export function useUpdateAuditionPerformanceNote() { const invalidate = useInvalidate(); return useMutation({ mutationFn: ({ id, patch }: { id: string; patch: unknown }) => updateAuditionNote(id, patch), onSuccess: () => invalidate(auditionKeys.performanceNotes) }); }
export function useDeleteAuditionPerformanceNote() { const invalidate = useInvalidate(); return useMutation({ mutationFn: deleteAuditionNote, onSuccess: () => invalidate(auditionKeys.performanceNotes) }); }

const outcomeJournalStatuses = new Set(["Self-Tape Callback", "In-Person Callback", "Pinned", "Booked", "Passed", "No Response"]);
const costFields = new Set(["submission_fee", "media_fee", "travel_cost", "housing_cost", "parking_cost", "other_cost"]);

function submissionUpdateKeys(patch: unknown): readonly (readonly unknown[])[] {
  const fields = Object.keys((patch ?? {}) as Record<string, unknown>);
  const keys: (readonly unknown[])[] = [auditionKeys.submissions];
  if (fields.some((field) => costFields.has(field))) keys.push(publicInvalidationKeys.analyticsOperations);
  if (fields.some((field) => ["asset_ids", "current_status", "opportunity_id", "submitted_at"].includes(field))) {
    keys.push(publicInvalidationKeys.analyticsIntelligence, publicInvalidationKeys.analyticsIndustryTrends, publicInvalidationKeys.analyticsMaterialPerformance, publicInvalidationKeys.breakdownReadiness, publicInvalidationKeys.commandCenter);
  }
  return keys;
}

function submissionStatusKeys(status: string): readonly (readonly unknown[])[] {
  const keys = keysForContract(invalidationContracts.submissionStatus).filter((key) => key !== publicInvalidationKeys.journalEntries);
  return outcomeJournalStatuses.has(status) ? [...keys, publicInvalidationKeys.journalEntries] : keys;
}

function workflowSelfTapeUpdateKeys(patch: unknown): readonly (readonly unknown[])[] {
  const status = ((patch ?? {}) as Record<string, unknown>).status;
  return status === "Completed"
    ? keysForContract(invalidationContracts.workflowSelfTapeUpdate)
    : [auditionKeys.selfTapes, publicInvalidationKeys.commandCenter];
}

function callbackUpdateKeys(patch: unknown): readonly (readonly unknown[])[] {
  const outcome = ((patch ?? {}) as Record<string, unknown>).outcome;
  const keys: (readonly unknown[])[] = [auditionKeys.callbacks, publicInvalidationKeys.analyticsIntelligence];
  if (outcome) keys.push(publicInvalidationKeys.journalEntries, publicInvalidationKeys.analyticsMaterialPerformance, publicInvalidationKeys.commandCenter);
  return keys;
}
