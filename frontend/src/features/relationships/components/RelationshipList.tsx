import { useState, type FormEvent } from "react";
import { ActionCard, Badge, ConfirmAction, DetailDisclosure, EmptyState } from "../../../components/ui";
import { relationshipToForm } from "../hooks/useRelationshipEditor";
import type { ActorRelationship, Opportunity, RelationshipFormState, Submission } from "../types";
import { RelationshipForm } from "./RelationshipForm";

export function RelationshipList({
  relationships,
  opportunities,
  submissions,
  onSave,
  onDelete
}: {
  relationships: ActorRelationship[];
  opportunities: Opportunity[];
  submissions: Submission[];
  onSave: (relationshipId: string, form: RelationshipFormState) => Promise<void>;
  onDelete: (relationshipId: string) => Promise<void>;
}) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<RelationshipFormState | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function startEdit(relationship: ActorRelationship) {
    setEditingId(relationship.id);
    setEditForm(relationshipToForm(relationship));
    setError(null);
  }

  async function saveEdit(relationship: ActorRelationship, event: FormEvent) {
    event.preventDefault();
    if (!editForm) return;
    setSavingId(relationship.id);
    setError(null);
    try {
      await onSave(relationship.id, editForm);
      setEditingId(null);
      setEditForm(null);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Could not save this relationship.");
    } finally {
      setSavingId(null);
    }
  }

  return (
    <div className="grid gap-3 lg:grid-cols-3">
      {relationships.length === 0 ? <EmptyState>No relationships tracked yet.</EmptyState> : relationships.map((relationship) => (
        <ActionCard
          key={relationship.id}
          title={relationship.name}
          status={<Badge>{relationship.relationship_strength}</Badge>}
          meta={`${relationship.role_title}${relationship.company_office ? ` · ${relationship.company_office}` : ""}`}
          primaryAction={<button type="button" className="text-xs font-semibold text-accent hover:underline" onClick={() => startEdit(relationship)}>Edit</button>}
          secondaryAction={(
            <ConfirmAction
              label="Delete"
              confirmLabel="Delete"
              message={`Delete ${relationship.name}?`}
              onConfirm={() => onDelete(relationship.id)}
            />
          )}
          details={(
            <div className="grid gap-3">
              {editingId === relationship.id && editForm ? (
                <RelationshipForm
                  form={editForm}
                  setForm={setEditForm}
                  opportunities={opportunities}
                  submissions={submissions}
                  onSubmit={(event) => void saveEdit(relationship, event)}
                  saving={savingId === relationship.id}
                  error={error}
                  submitLabel="Save Relationship"
                  onCancel={() => {
                    setEditingId(null);
                    setEditForm(null);
                    setError(null);
                  }}
                />
              ) : null}
              <DetailDisclosure label="Details">
                <p>Projects: {relationship.projects.join(", ") || "None"}</p>
                <p>Last contact: {relationship.last_contact_date || "None"}</p>
                <p>Linked outcomes: {relationship.linked_outcomes.join(", ") || "None"}</p>
                <p>Linked breakdowns: {relationship.linked_opportunity_ids.length}</p>
                <p>Linked submissions: {relationship.linked_submission_ids.length}</p>
                {relationship.notes && <p className="mt-2">{relationship.notes}</p>}
              </DetailDisclosure>
            </div>
          )}
        />
      ))}
    </div>
  );
}
