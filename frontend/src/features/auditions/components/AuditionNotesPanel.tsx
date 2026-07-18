import { useRef, useState } from "react";
import { Badge, Button, ConfirmAction, EmptyState, Field, Section, inputClass } from "../../../components/ui";
import { useAuditionNotes } from "../hooks/useAuditionNotes";
import type { AuditionJournalEntry, Opportunity, Submission } from "../types";
import { AuditionPerformanceNoteForm } from "./AuditionPerformanceNoteForm";

export function AuditionNotesPanel({
  journalEntries,
  opportunities,
  submissions
}: {
  journalEntries: AuditionJournalEntry[];
  opportunities: Opportunity[];
  submissions: Submission[];
}) {
  const notes = useAuditionNotes({ journalEntries, opportunities, submissions });
  const [editingEntryId, setEditingEntryId] = useState<string | null>(null);
  const editButtonRefs = useRef<Record<string, HTMLButtonElement | null>>({});

  function closeEditor(entryId: string) {
    setEditingEntryId(null);
    window.requestAnimationFrame(() => editButtonRefs.current[entryId]?.focus());
  }

  return (
    <Section title="Audition Notes">
      <div className="grid gap-4">
        <div className="grid gap-3 xl:grid-cols-3">
          <div className="rounded-md border border-slate-200 p-3">
            <h3 className="font-semibold">Private Audition Journal</h3>
            <p className="mt-2 text-sm text-slate-600">Use this for your own preparation, performance, wardrobe, emotional, and follow-up notes. Do not use it to ask casting why you did not book.</p>
            <p className="mt-3 text-sm">{journalEntries.length} journal entries tracked</p>
          </div>
        </div>

        <form className="grid gap-3 rounded-md border border-slate-200 p-3 lg:grid-cols-4" onSubmit={notes.submit}>
          <div>
            <h3 className="font-semibold">Add Journal Entry</h3>
            <p className="mt-1 text-sm text-slate-600">Private actor notes only.</p>
          </div>
          <Field label="Date">
            <input className={inputClass} type="date" value={notes.form.date} onChange={(e) => notes.setForm({ ...notes.form, date: e.target.value })} required />
          </Field>
          <Field label="Breakdown">
            <select className={inputClass} value={notes.form.opportunity_id} onChange={(e) => notes.setForm({ ...notes.form, opportunity_id: e.target.value })}>
              <option value="">None</option>
              {opportunities.map((opportunity) => <option key={opportunity.id} value={opportunity.id}>{opportunity.role} · {opportunity.project}</option>)}
            </select>
          </Field>
          {submissions.length > 0 ? (
            <Field label="Linked Submission">
              <select className={inputClass} value={notes.form.submission_id} onChange={(e) => notes.setForm({ ...notes.form, submission_id: e.target.value })}>
                <option value="">None</option>
                {submissions.map((submission) => <option key={submission.id} value={submission.id}>{submission.opportunity?.role ?? "Submission"} · {submission.current_status}</option>)}
              </select>
            </Field>
          ) : (
            <p className="self-end rounded bg-slate-100 p-2 text-xs text-slate-600">No existing submissions yet. This journal entry can still be saved.</p>
          )}
          <Field label="Preparation">
            <textarea className={inputClass} value={notes.form.preparation_notes} onChange={(e) => notes.setForm({ ...notes.form, preparation_notes: e.target.value })} />
          </Field>
          <Field label="Performance">
            <textarea className={inputClass} value={notes.form.performance_notes} onChange={(e) => notes.setForm({ ...notes.form, performance_notes: e.target.value })} />
          </Field>
          <Field label="Casting Notes">
            <textarea className={inputClass} value={notes.form.casting_notes} onChange={(e) => notes.setForm({ ...notes.form, casting_notes: e.target.value })} />
          </Field>
          <Field label="Wardrobe">
            <textarea className={inputClass} value={notes.form.wardrobe_notes} onChange={(e) => notes.setForm({ ...notes.form, wardrobe_notes: e.target.value })} />
          </Field>
          <Field label="Emotional Notes">
            <textarea className={inputClass} value={notes.form.emotional_notes} onChange={(e) => notes.setForm({ ...notes.form, emotional_notes: e.target.value })} />
          </Field>
          <div className="lg:col-span-2">
            <Field label="Follow-Up Notes">
              <textarea className={inputClass} value={notes.form.follow_up_notes} onChange={(e) => notes.setForm({ ...notes.form, follow_up_notes: e.target.value })} />
            </Field>
          </div>
          <div className="flex items-end"><Button type="submit">Add Journal Entry</Button></div>
        </form>

        <div className="grid gap-3 lg:grid-cols-3">
          {journalEntries.length === 0 ? <EmptyState>No audition journal entries yet.</EmptyState> : journalEntries.map((entry) => (
            <article key={entry.id} className="rounded-md border border-slate-200 p-3 text-sm">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="font-semibold">{entry.opportunity_id ? notes.opportunityById[entry.opportunity_id]?.role ?? "Audition" : "Audition Journal"}</h3>
                  <p className="text-slate-600">{entry.date}{entry.submission_id ? ` · ${notes.submissionById[entry.submission_id]?.current_status ?? "Submission"}` : ""}</p>
                </div>
                <Badge>Private</Badge>
              </div>
              {entry.preparation_notes && <p className="mt-2"><strong>Prep:</strong> {entry.preparation_notes}</p>}
              {entry.performance_notes && <p><strong>Performance:</strong> {entry.performance_notes}</p>}
              {entry.casting_notes && <p><strong>Casting:</strong> {entry.casting_notes}</p>}
              {entry.wardrobe_notes && <p><strong>Wardrobe:</strong> {entry.wardrobe_notes}</p>}
              {entry.emotional_notes && <p><strong>Emotional:</strong> {entry.emotional_notes}</p>}
              {entry.follow_up_notes && <p><strong>Follow-up:</strong> {entry.follow_up_notes}</p>}
              {editingEntryId === entry.id && (
                <AuditionPerformanceNoteForm
                  entry={entry}
                  onSave={notes.updateEntry}
                  onCancel={() => closeEditor(entry.id)}
                />
              )}
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  ref={(element) => { editButtonRefs.current[entry.id] = element; }}
                  type="button"
                  className="rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-ink transition hover:bg-slate-50"
                  onClick={() => setEditingEntryId(entry.id)}
                >
                  Edit Performance
                </button>
                <ConfirmAction
                  label="Delete"
                  message="Delete this private audition note?"
                  confirmLabel="Delete"
                  onConfirm={() => notes.remove(entry.id)}
                />
              </div>
            </article>
          ))}
        </div>
      </div>
    </Section>
  );
}
