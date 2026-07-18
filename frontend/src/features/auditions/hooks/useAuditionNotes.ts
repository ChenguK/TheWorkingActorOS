import { useMemo, useState, type FormEvent } from "react";
import type { AuditionJournalEntry, AuditionNoteFormState, Opportunity, Submission } from "../types";
import { useCreateAuditionPerformanceNote, useDeleteAuditionPerformanceNote, useUpdateAuditionPerformanceNote } from "./useAuditionQueries";

export function useAuditionNotes({
  opportunities,
  submissions
}: {
  journalEntries: AuditionJournalEntry[];
  opportunities: Opportunity[];
  submissions: Submission[];
}) {
  const createNote = useCreateAuditionPerformanceNote();
  const updateNote = useUpdateAuditionPerformanceNote();
  const deleteNote = useDeleteAuditionPerformanceNote();
  const today = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState<AuditionNoteFormState>({
    submission_id: "",
    opportunity_id: "",
    date: today,
    preparation_notes: "",
    performance_notes: "",
    casting_notes: "",
    wardrobe_notes: "",
    emotional_notes: "",
    follow_up_notes: ""
  });

  const opportunityById = useMemo(() => Object.fromEntries(opportunities.map((item) => [item.id, item])), [opportunities]);
  const submissionById = useMemo(() => Object.fromEntries(submissions.map((item) => [item.id, item])), [submissions]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    await createNote.mutateAsync({
      ...form,
      submission_id: form.submission_id || null,
      opportunity_id: form.opportunity_id || null,
      preparation_notes: form.preparation_notes || null,
      performance_notes: form.performance_notes || null,
      casting_notes: form.casting_notes || null,
      wardrobe_notes: form.wardrobe_notes || null,
      emotional_notes: form.emotional_notes || null,
      follow_up_notes: form.follow_up_notes || null
    });
    setForm({
      submission_id: "",
      opportunity_id: "",
      date: today,
      preparation_notes: "",
      performance_notes: "",
      casting_notes: "",
      wardrobe_notes: "",
      emotional_notes: "",
      follow_up_notes: ""
    });
  }

  async function updateEntry(entryId: string, patch: Partial<AuditionNoteFormState>) {
    await updateNote.mutateAsync({ id: entryId, patch: {
      preparation_notes: patch.preparation_notes || null,
      performance_notes: patch.performance_notes || null,
      casting_notes: patch.casting_notes || null,
      wardrobe_notes: patch.wardrobe_notes || null,
      emotional_notes: patch.emotional_notes || null,
      follow_up_notes: patch.follow_up_notes || null
    }});
  }

  async function remove(entryId: string) {
    await deleteNote.mutateAsync(entryId);
  }

  return {
    form,
    setForm,
    opportunityById,
    submissionById,
    submit,
    updateEntry,
    remove
  };
}
