import { api } from "../../../services/api";
import type { ActorJournalEntry } from "../../../types/domain";
import type { JournalCreatePayload, JournalUpdatePayload } from "../types";

export function listJournalEntries() {
  return api.get<ActorJournalEntry[]>("/journal");
}

export function createJournalEntry(payload: JournalCreatePayload) {
  return api.post<ActorJournalEntry>("/journal", payload);
}

export function updateJournalEntryNotes(entryId: string, notes: string | null) {
  return api.patch<ActorJournalEntry>(`/journal/${entryId}`, { notes } satisfies JournalUpdatePayload);
}

export function deleteJournalEntry(entryId: string) {
  return api.delete(`/journal/${entryId}`);
}
