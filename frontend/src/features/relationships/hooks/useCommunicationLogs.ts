import { useState, type FormEvent } from "react";
import { errorMessage } from "../../../services/api/errors";
import type { CommunicationLogFormState } from "../types";
import {
  useAddRelationshipInteraction,
  useDeleteRelationshipInteraction,
  useRelationshipInteractions
} from "./useRelationshipQueries";

function initialCommunicationForm(): CommunicationLogFormState {
  return {
    representation_id: "",
    opportunity_id: "",
    submission_id: "",
    date: new Date().toISOString().slice(0, 10),
    topic: "",
    notes: "",
    follow_up_needed: false,
    follow_up_date: ""
  };
}

export function useCommunicationLogs() {
  const logsQuery = useRelationshipInteractions();
  const createMutation = useAddRelationshipInteraction();
  const deleteMutation = useDeleteRelationshipInteraction();
  const [form, setForm] = useState<CommunicationLogFormState>(initialCommunicationForm);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await createMutation.mutateAsync({
        representation_id: form.representation_id || null,
        opportunity_id: form.opportunity_id || null,
        submission_id: form.submission_id || null,
        date: form.date,
        topic: form.topic,
        notes: form.notes || null,
        follow_up_needed: form.follow_up_needed,
        follow_up_date: form.follow_up_date || null
      });
      setForm(initialCommunicationForm());
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "Could not save this communication.");
    } finally {
      setSaving(false);
    }
  }

  async function remove(logId: string) {
    try {
      await deleteMutation.mutateAsync(logId);
    } catch {
      // The mutation retains the standardized ApiError for presentation.
    }
  }

  return {
    logs: logsQuery.data ?? [],
    isLoading: logsQuery.isLoading,
    isRefetching: logsQuery.isRefetching,
    queryError: logsQuery.error && !logsQuery.data ? errorMessage(logsQuery.error, "Could not load communication history.") : null,
    form,
    setForm,
    saving: saving || createMutation.isPending,
    deletePending: deleteMutation.isPending,
    error: error ?? (deleteMutation.error ? errorMessage(deleteMutation.error, "Could not delete this communication.") : null),
    submit,
    remove
  };
}
