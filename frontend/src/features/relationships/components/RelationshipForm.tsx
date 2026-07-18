import type { FormEvent } from "react";
import { AsyncButton, Button, Field, inputClass } from "../../../components/ui";
import { relationshipRoles, relationshipStrengths } from "../constants";
import type { Opportunity, RelationshipFormState, RelationshipRole, RelationshipStrength, Submission } from "../types";

export function RelationshipForm({
  form,
  setForm,
  opportunities,
  submissions,
  onSubmit,
  saving = false,
  error,
  submitLabel,
  onCancel
}: {
  form: RelationshipFormState;
  setForm: (form: RelationshipFormState) => void;
  opportunities: Opportunity[];
  submissions: Submission[];
  onSubmit: (event: FormEvent) => void;
  saving?: boolean;
  error?: string | null;
  submitLabel: string;
  onCancel?: () => void;
}) {
  function toggleSelected(values: string[], value: string) {
    return values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
  }

  return (
    <form className="grid gap-3 rounded-md border border-slate-200 p-3 lg:grid-cols-4" onSubmit={onSubmit}>
      <div>
        <h3 className="font-semibold">{submitLabel}</h3>
      </div>
      <Field label="Name">
        <input className={inputClass} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required />
      </Field>
      <Field label="Role">
        <select className={inputClass} value={form.role_title} onChange={(event) => setForm({ ...form, role_title: event.target.value as RelationshipRole })}>
          {relationshipRoles.map((role) => <option key={role}>{role}</option>)}
        </select>
      </Field>
      <Field label="Company / Office">
        <input className={inputClass} value={form.company_office} onChange={(event) => setForm({ ...form, company_office: event.target.value })} />
      </Field>
      <Field label="Strength">
        <select className={inputClass} value={form.relationship_strength} onChange={(event) => setForm({ ...form, relationship_strength: event.target.value as RelationshipStrength })}>
          {relationshipStrengths.map((strength) => <option key={strength}>{strength}</option>)}
        </select>
      </Field>
      <Field label="Last Contact">
        <input className={inputClass} type="date" value={form.last_contact_date} onChange={(event) => setForm({ ...form, last_contact_date: event.target.value })} />
      </Field>
      <Field label="Projects">
        <input className={inputClass} value={form.projects} onChange={(event) => setForm({ ...form, projects: event.target.value })} placeholder="Project A, Project B" />
      </Field>
      <Field label="Linked Outcomes">
        <input className={inputClass} value={form.linked_outcomes} onChange={(event) => setForm({ ...form, linked_outcomes: event.target.value })} placeholder="Callback, Booked" />
      </Field>
      <div className="lg:col-span-2">
        <Field label="Linked Breakdowns">
          <div className="grid max-h-32 gap-1 overflow-auto rounded border border-slate-200 p-2 text-sm">
            {opportunities.slice(0, 12).map((opportunity) => (
              <label key={opportunity.id} className="flex items-center gap-2">
                <input type="checkbox" checked={form.linked_opportunity_ids.includes(opportunity.id)} onChange={() => setForm({ ...form, linked_opportunity_ids: toggleSelected(form.linked_opportunity_ids, opportunity.id) })} />
                {opportunity.role} · {opportunity.project}
              </label>
            ))}
          </div>
        </Field>
      </div>
      <div className="lg:col-span-2">
        <Field label="Linked Submissions">
          <div className="grid max-h-32 gap-1 overflow-auto rounded border border-slate-200 p-2 text-sm">
            {submissions.slice(0, 12).map((submission) => (
              <label key={submission.id} className="flex items-center gap-2">
                <input type="checkbox" checked={form.linked_submission_ids.includes(submission.id)} onChange={() => setForm({ ...form, linked_submission_ids: toggleSelected(form.linked_submission_ids, submission.id) })} />
                {submission.opportunity?.role ?? "Submission"} · {submission.current_status}
              </label>
            ))}
          </div>
        </Field>
      </div>
      <div className="lg:col-span-3">
        <Field label="Notes">
          <textarea className={inputClass} value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} />
        </Field>
      </div>
      {error && <p className="rounded bg-red-50 p-2 text-sm font-medium text-red-800 lg:col-span-4">{error}</p>}
      <div className="flex items-end gap-2">
        <AsyncButton type="submit" loading={saving}>{submitLabel}</AsyncButton>
        {onCancel && <Button type="button" variant="secondary" onClick={onCancel}>Cancel</Button>}
      </div>
    </form>
  );
}
