import { api } from "../../../services/api";
import type { AuditionJournalEntry, CallbackEvent, SelfTapeWorkflow, Submission } from "../../../types/domain";

export function listAuditions() {
  return api.get<SelfTapeWorkflow[]>("/command-center/self-tapes");
}

export function listSubmissions() {
  return api.get<Submission[]>("/submissions");
}

export function getSubmission(submissionId: string) {
  return api.get<Submission>(`/submissions/${submissionId}`);
}

export function updateSubmission(submissionId: string, patch: unknown) {
  return api.patch<Submission>(`/submissions/${submissionId}`, patch);
}

export function createAudition(payload: unknown) {
  return api.post("/command-center/self-tapes", payload);
}

export function updateAudition(auditionId: string, patch: unknown) {
  return api.patch(`/command-center/self-tapes/${auditionId}`, patch);
}

export function createSelfTapeTask(payload: unknown) {
  return api.post<SelfTapeWorkflow>("/command-center/self-tapes", payload);
}

export function updateSelfTapeTask(workflowId: string, patch: unknown) {
  return api.patch<SelfTapeWorkflow>(`/command-center/self-tapes/${workflowId}`, patch);
}

export function recordSubmission(payload: unknown) {
  return api.post<Submission>("/submissions", payload);
}

export function deleteSubmission(submissionId: string) {
  return api.delete(`/submissions/${submissionId}`);
}

export function addSubmissionStatus(submissionId: string, status: string) {
  return api.post(`/submissions/${submissionId}/status-history`, { status });
}

export function createCallbackEvent(payload: unknown) {
  return api.post<CallbackEvent>("/intelligence/callback-events", payload);
}

export function listCallbackEvents() {
  return api.get<CallbackEvent[]>("/intelligence/callback-events");
}

export function updateCallbackEvent(eventId: string, patch: unknown) {
  return api.patch<CallbackEvent>(`/intelligence/callback-events/${eventId}`, patch);
}

export function deleteCallbackEvent(eventId: string) {
  return api.delete(`/intelligence/callback-events/${eventId}`);
}

export function createAuditionCalendarEvent(payload: unknown) {
  return api.post("/operations/calendar/events", payload);
}

export function createAuditionNote(payload: unknown) {
  return api.post<AuditionJournalEntry>("/intelligence/audition-journal", payload);
}

export function listAuditionNotes() {
  return api.get<AuditionJournalEntry[]>("/intelligence/audition-journal");
}

export function updateAuditionNote(noteId: string, patch: unknown) {
  return api.patch<AuditionJournalEntry>(`/intelligence/audition-journal/${noteId}`, patch);
}

export function deleteAuditionNote(noteId: string) {
  return api.delete(`/intelligence/audition-journal/${noteId}`);
}
