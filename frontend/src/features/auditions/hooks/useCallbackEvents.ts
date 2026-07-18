import { useState, type FormEvent } from "react";
import type { CallbackEventFormState } from "../types";
import { useCreateCallbackEvent, useDeleteCallbackEvent } from "./useAuditionQueries";

function initialCallbackForm(): CallbackEventFormState {
  return {
    submission_id: "",
    opportunity_id: "",
    event_name: "First Callback",
    event_type: "First Callback",
    event_datetime: "",
    location: "",
    is_virtual: false,
    preparation_notes: "",
    outcome: "",
    notes: ""
  };
}

export function useCallbackEventActions() {
  const [form, setForm] = useState<CallbackEventFormState>(initialCallbackForm);
  const createEvent = useCreateCallbackEvent();
  const deleteEvent = useDeleteCallbackEvent();

  async function submit(event: FormEvent) {
    event.preventDefault();
    await createEvent.mutateAsync({
      ...form,
      submission_id: form.submission_id || null,
      opportunity_id: form.opportunity_id || null,
      event_datetime: form.event_datetime || null,
      location: form.location || null,
      preparation_notes: form.preparation_notes || null,
      outcome: form.outcome || null,
      notes: form.notes || null
    });
    setForm(initialCallbackForm());
  }

  async function remove(eventId: string) {
    await deleteEvent.mutateAsync(eventId);
  }

  return { form, setForm, submit, remove };
}
