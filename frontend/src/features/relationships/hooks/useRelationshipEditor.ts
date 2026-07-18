import { useState, type FormEvent } from "react";
import { errorMessage } from "../../../services/api/errors";
import { splitList } from "../../../utils/tags";
import type { ActorRelationship, RelationshipFormState } from "../types";
import { useCreateRelationship, useDeleteRelationship, useUpdateRelationship } from "./useRelationshipQueries";

export function relationshipToForm(relationship?: ActorRelationship): RelationshipFormState {
  return {
    name: relationship?.name ?? "",
    role_title: relationship?.role_title ?? "Casting Director",
    company_office: relationship?.company_office ?? "",
    projects: relationship?.projects.join(", ") ?? "",
    notes: relationship?.notes ?? "",
    last_contact_date: relationship?.last_contact_date ?? "",
    relationship_strength: relationship?.relationship_strength ?? "Warm",
    linked_outcomes: relationship?.linked_outcomes.join(", ") ?? "",
    linked_opportunity_ids: relationship?.linked_opportunity_ids ?? [],
    linked_submission_ids: relationship?.linked_submission_ids ?? []
  };
}

function relationshipPayload(form: RelationshipFormState) {
  return {
    ...form,
    company_office: form.company_office || null,
    projects: splitList(form.projects),
    notes: form.notes || null,
    last_contact_date: form.last_contact_date || null,
    linked_outcomes: splitList(form.linked_outcomes)
  };
}

export function useRelationshipEditor() {
  const createMutation = useCreateRelationship();
  const updateMutation = useUpdateRelationship();
  const deleteMutation = useDeleteRelationship();
  const [form, setForm] = useState<RelationshipFormState>(relationshipToForm());
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function create(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await createMutation.mutateAsync(relationshipPayload(form));
      setForm(relationshipToForm());
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "Could not save this relationship.");
    } finally {
      setSaving(false);
    }
  }

  async function save(relationshipId: string, editForm: RelationshipFormState) {
    await updateMutation.mutateAsync({ relationshipId, patch: relationshipPayload(editForm) });
  }

  async function remove(relationshipId: string) {
    try {
      await deleteMutation.mutateAsync(relationshipId);
    } catch {
      // The mutation retains the standardized ApiError for presentation.
    }
  }

  function toggleSelected(values: string[], value: string) {
    return values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
  }

  return {
    form,
    setForm,
    saving: saving || createMutation.isPending,
    error: error ?? (deleteMutation.error ? errorMessage(deleteMutation.error, "Could not delete this relationship.") : null),
    deletePending: deleteMutation.isPending,
    create,
    save,
    remove,
    toggleSelected
  };
}
