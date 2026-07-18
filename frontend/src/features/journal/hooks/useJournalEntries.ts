import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { errorMessage } from "../../../services/api/errors";
import { queryKeys } from "../../../services/api/queryKeys";
import { queryStaleTimes } from "../../../services/api/queryPolicy";
import type { ActorJournalEntry } from "../../../types/domain";
import {
  createJournalEntry,
  deleteJournalEntry,
  listJournalEntries,
  updateJournalEntryNotes
} from "../api";
import type { JournalCreatePayload } from "../types";
import { createBlankJournalForm, groupJournalEntriesByDate } from "../utils";

const journalListKey = queryKeys.journal.list();

export function useCreateJournalEntry() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: JournalCreatePayload) => createJournalEntry(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.journal.lists() })
  });
}

export function useUpdateJournalEntry() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ entryId, notes }: { entryId: string; notes: string | null }) => updateJournalEntryNotes(entryId, notes),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.journal.lists() })
  });
}

export function useDeleteJournalEntry() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (entryId: string) => deleteJournalEntry(entryId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.journal.lists() })
  });
}

export function useJournalEntries() {
  const [formOpen, setFormOpen] = useState(false);
  const emptyStateInitialized = useRef(false);
  const [editingNotesId, setEditingNotesId] = useState<string | null>(null);
  const [notesDraft, setNotesDraft] = useState("");
  const [form, setForm] = useState(createBlankJournalForm);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const entriesQuery = useQuery({
    queryKey: journalListKey,
    queryFn: listJournalEntries,
    staleTime: queryStaleTimes.workflow
  });
  const createMutation = useCreateJournalEntry();
  const updateMutation = useUpdateJournalEntry();
  const deleteMutation = useDeleteJournalEntry();
  const entries = useMemo(() => entriesQuery.data ?? [], [entriesQuery.data]);

  useEffect(() => {
    if (entriesQuery.isSuccess && !emptyStateInitialized.current) {
      emptyStateInitialized.current = true;
      if (entries.length === 0) setFormOpen(true);
    }
  }, [entries.length, entriesQuery.isSuccess]);

  const groupedEntries = useMemo(() => groupJournalEntriesByDate(entries), [entries]);

  async function createEntry(event: FormEvent) {
    event.preventDefault();
    setSuccessMessage(null);
    try {
      await createMutation.mutateAsync({
        date: form.date,
        event_type: form.event_type,
        title: form.title,
        description: form.description || null,
        linked_breakdown_id: form.linked_breakdown_id || null,
        linked_audition_id: form.linked_audition_id || null,
        linked_material_id: form.linked_material_id || null,
        linked_career_task_id: form.linked_career_task_id || null,
        notes: form.notes || null
      });
      setForm(createBlankJournalForm());
      setFormOpen(false);
      setSuccessMessage("Journal entry saved.");
    } catch {
      // The mutation retains the standardized ApiError for presentation below.
    }
  }

  async function saveNotes(entry: ActorJournalEntry) {
    setSuccessMessage(null);
    try {
      await updateMutation.mutateAsync({ entryId: entry.id, notes: notesDraft || null });
      setEditingNotesId(null);
      setSuccessMessage("Journal notes saved.");
    } catch {
      // The mutation retains the standardized ApiError for presentation below.
    }
  }

  function startNotesEdit(entry: ActorJournalEntry) {
    setEditingNotesId(entry.id);
    setNotesDraft(entry.notes ?? "");
  }

  const mutationError = createMutation.error ?? updateMutation.error ?? deleteMutation.error;

  return {
    entries,
    isLoading: entriesQuery.isLoading,
    isRefetching: entriesQuery.isRefetching,
    error: entriesQuery.error ? errorMessage(entriesQuery.error, "Could not load Journal entries.") : null,
    mutationError: mutationError ? errorMessage(mutationError, "Could not save the Journal entry.") : null,
    successMessage,
    refetch: entriesQuery.refetch,
    formOpen,
    setFormOpen,
    editingNotesId,
    setEditingNotesId,
    notesDraft,
    setNotesDraft,
    form,
    setForm,
    groupedEntries,
    createEntry,
    saveNotes,
    startNotesEdit,
    createPending: createMutation.isPending,
    updatePending: updateMutation.isPending
  };
}
