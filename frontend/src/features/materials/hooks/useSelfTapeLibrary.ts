import { useMemo, useState, type FormEvent } from "react";
import { splitList } from "../../../utils/tags";
import type { Opportunity, SelfTapeFormState, Submission } from "../types";
import { useCreateReusableSelfTape, useDeleteReusableSelfTape, useUpdateReusableSelfTape } from "./useReusableSelfTapes";

export function useSelfTapeLibrary({
  opportunities,
  submissions
}: {
  opportunities: Opportunity[];
  submissions: Submission[];
}) {
  const createTape = useCreateReusableSelfTape();
  const updateTape = useUpdateReusableSelfTape();
  const deleteTape = useDeleteReusableSelfTape();
  const mutationError = createTape.error ?? updateTape.error ?? deleteTape.error;
  const today = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState<SelfTapeFormState>({
    title: "",
    role_type: "",
    archetypes: "",
    file_path: "",
    linked_opportunity_id: "",
    linked_submission_id: "",
    outcome: "",
    notes: "",
    date_created: today
  });

  const opportunityById = useMemo(() => Object.fromEntries(opportunities.map((item) => [item.id, item])), [opportunities]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    await createTape.mutateAsync({
      ...form,
      role_type: form.role_type || null,
      archetypes: splitList(form.archetypes),
      linked_opportunity_id: form.linked_opportunity_id || null,
      linked_submission_id: form.linked_submission_id || null,
      outcome: form.outcome || null,
      notes: form.notes || null
    });
    setForm({
      title: "",
      role_type: "",
      archetypes: "",
      file_path: "",
      linked_opportunity_id: "",
      linked_submission_id: "",
      outcome: "",
      notes: "",
      date_created: today
    });
  }

  async function saveTapeUpdate(tapeId: string, payload: {
    outcome: string | null;
    archetypes: string[];
    linked_opportunity_id: string | null;
    linked_submission_id: string | null;
    notes: string | null;
  }) {
    await updateTape.mutateAsync({ id: tapeId, patch: payload });
  }

  async function remove(tapeId: string) {
    await deleteTape.mutateAsync(tapeId);
  }

  return {
    form,
    setForm,
    opportunityById,
    submit,
    saveTapeUpdate,
    remove,
    mutationError,
    mutationPending: createTape.isPending || updateTape.isPending || deleteTape.isPending
  };
}
