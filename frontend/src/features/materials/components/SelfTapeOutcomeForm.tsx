import { useEffect, useRef, useState, type FormEvent } from "react";
import { AsyncButton, Button, Field, inputClass } from "../../../components/ui";
import { joinList, splitList } from "../../../utils/tags";
import { submissionStatuses } from "../constants";
import type { Opportunity, SelfTape, Submission } from "../types";

export function SelfTapeOutcomeForm({
  tape,
  opportunities,
  submissions,
  onSave,
  onCancel
}: {
  tape: SelfTape;
  opportunities: Opportunity[];
  submissions: Submission[];
  onSave: (tapeId: string, payload: {
    outcome: string | null;
    archetypes: string[];
    linked_opportunity_id: string | null;
    linked_submission_id: string | null;
    notes: string | null;
  }) => Promise<void>;
  onCancel: () => void;
}) {
  const firstFieldRef = useRef<HTMLSelectElement>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    outcome: tape.outcome ?? "",
    archetypes: joinList(tape.archetypes),
    linked_opportunity_id: tape.linked_opportunity_id ?? "",
    linked_submission_id: tape.linked_submission_id ?? "",
    notes: tape.notes ?? ""
  });

  useEffect(() => {
    firstFieldRef.current?.focus();
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await onSave(tape.id, {
        outcome: form.outcome || null,
        archetypes: splitList(form.archetypes),
        linked_opportunity_id: form.linked_opportunity_id || null,
        linked_submission_id: form.linked_submission_id || null,
        notes: form.notes || null
      });
      onCancel();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Could not save this self-tape.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="mt-3 grid gap-3 rounded-md border border-slate-200 bg-slate-50 p-3" onSubmit={(event) => void submit(event)}>
      <div className="grid gap-3 md:grid-cols-2">
        <Field label="Outcome">
          <select ref={firstFieldRef} name="edit_self_tape_outcome" className={inputClass} value={form.outcome} onChange={(event) => setForm({ ...form, outcome: event.target.value })}>
            <option value="">Untracked</option>
            {submissionStatuses.map((status) => <option key={status}>{status}</option>)}
          </select>
        </Field>
        <Field label="Archetypes">
          <input name="edit_self_tape_archetypes" className={inputClass} value={form.archetypes} onChange={(event) => setForm({ ...form, archetypes: event.target.value })} />
        </Field>
        <Field label="Linked Breakdown">
          <select name="edit_self_tape_breakdown" className={inputClass} value={form.linked_opportunity_id} onChange={(event) => setForm({ ...form, linked_opportunity_id: event.target.value })}>
            <option value="">None</option>
            {opportunities.map((opportunity) => <option key={opportunity.id} value={opportunity.id}>{opportunity.role} · {opportunity.project}</option>)}
          </select>
        </Field>
        {submissions.length > 0 && (
          <Field label="Linked Submission">
            <select name="edit_self_tape_submission" className={inputClass} value={form.linked_submission_id} onChange={(event) => setForm({ ...form, linked_submission_id: event.target.value })}>
              <option value="">None</option>
              {submissions.map((submission) => <option key={submission.id} value={submission.id}>{submission.opportunity?.role ?? "Submission"} · {submission.current_status}</option>)}
            </select>
          </Field>
        )}
        <div className="md:col-span-2">
          <Field label="Notes">
            <textarea name="edit_self_tape_notes" className={inputClass} value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} />
          </Field>
        </div>
      </div>
      {error && <p className="rounded bg-red-50 p-2 text-sm font-medium text-red-800">{error}</p>}
      <div className="flex flex-wrap gap-2">
        <AsyncButton type="submit" loading={saving}>Save Self-Tape</AsyncButton>
        <Button type="button" variant="secondary" onClick={onCancel}>Cancel</Button>
      </div>
    </form>
  );
}
