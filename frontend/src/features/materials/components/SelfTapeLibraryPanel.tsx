import { useRef, useState } from "react";
import { Badge, Button, ConfirmAction, EmptyState, Field, Section, inputClass } from "../../../components/ui";
import { submissionStatuses } from "../constants";
import { useSelfTapeLibrary } from "../hooks/useSelfTapeLibrary";
import { useReusableSelfTapeAnalytics, useReusableSelfTapes } from "../hooks/useReusableSelfTapes";
import type { Opportunity, Submission } from "../types";
import { SelfTapeOutcomeForm } from "./SelfTapeOutcomeForm";

export function SelfTapeLibraryPanel({
  opportunities,
  submissions
}: {
  opportunities: Opportunity[];
  submissions: Submission[];
}) {
  const tapes = useReusableSelfTapes();
  const analytics = useReusableSelfTapeAnalytics();
  const selfTapes = tapes.data ?? [];
  const selfTapeAnalytics = analytics.data ?? null;
  const library = useSelfTapeLibrary({ opportunities, submissions });
  const [editingTapeId, setEditingTapeId] = useState<string | null>(null);
  const lastEditButtonRef = useRef<HTMLButtonElement | null>(null);

  function closeEditForm() {
    setEditingTapeId(null);
    window.setTimeout(() => lastEditButtonRef.current?.focus(), 0);
  }

  return (
    <Section title="Self-Tape Library">
      <div className="grid gap-4">
        {tapes.isLoading && <p role="status" className="text-sm text-slate-600">Loading reusable self-tapes...</p>}
        {tapes.isError && <p role="alert" className="rounded bg-red-50 p-2 text-sm text-red-700">Could not load the reusable self-tape library.</p>}
        {analytics.isLoading && <p role="status" className="text-sm text-slate-600">Loading reusable self-tape analytics...</p>}
        {analytics.isError && <p role="alert" className="rounded bg-red-50 p-2 text-sm text-red-700">Could not load self-tape analytics. Library records remain available.</p>}
        {library.mutationError && <p role="alert" className="rounded bg-red-50 p-2 text-sm text-red-700">Could not save the reusable self-tape change.</p>}
        {(tapes.isRefetching || analytics.isRefetching) && <p role="status" className="text-xs text-slate-500">Refreshing reusable self-tapes...</p>}
        <div className="rounded-md border border-slate-200 p-3">
          <h3 className="font-semibold">Self-Tape Library Analytics</h3>
          <div className="mt-3 grid gap-2 text-sm">
            <p className="font-semibold">By Archetype</p>
            <p>{(selfTapeAnalytics?.by_archetype ?? []).map((item) => `${String(item.archetype)} (${String(item.count)})`).join(", ") || "Not enough data"}</p>
            <p className="font-semibold">By Outcome</p>
            <p>{(selfTapeAnalytics?.by_outcome ?? []).map((item) => `${String(item.outcome)} (${String(item.count)})`).join(", ") || "Not enough data"}</p>
            <p className="font-semibold">Best Performing</p>
            <p>{(selfTapeAnalytics?.best_performing_tapes ?? []).map((tape) => tape.title).join(", ") || "No positive outcome tapes yet"}</p>
          </div>
        </div>

        <form className="grid gap-3 rounded-md border border-slate-200 p-3 lg:grid-cols-4" onSubmit={(event) => void library.submit(event).catch(() => undefined)}>
          <div>
            <h3 className="font-semibold">Add Self-Tape</h3>
            <p className="mt-1 text-sm text-slate-600">{selfTapes.length} reusable tapes tracked</p>
          </div>
          <Field label="Title">
            <input className={inputClass} value={library.form.title} onChange={(e) => library.setForm({ ...library.form, title: e.target.value })} required />
          </Field>
          <Field label="Role Type">
            <input className={inputClass} value={library.form.role_type} onChange={(e) => library.setForm({ ...library.form, role_type: e.target.value })} />
          </Field>
          <Field label="Archetypes">
            <input className={inputClass} value={library.form.archetypes} onChange={(e) => library.setForm({ ...library.form, archetypes: e.target.value })} placeholder="Attorney, Authority Figure" />
          </Field>
          <Field label="File Path">
            <input className={inputClass} value={library.form.file_path} onChange={(e) => library.setForm({ ...library.form, file_path: e.target.value })} required />
          </Field>
          <Field label="Outcome">
            <select className={inputClass} value={library.form.outcome} onChange={(e) => library.setForm({ ...library.form, outcome: e.target.value })}>
              <option value="">Untracked</option>
              {submissionStatuses.map((status) => <option key={status}>{status}</option>)}
            </select>
          </Field>
          <Field label="Date Created">
            <input className={inputClass} type="date" value={library.form.date_created} onChange={(e) => library.setForm({ ...library.form, date_created: e.target.value })} required />
          </Field>
          <Field label="Linked Breakdown">
            <select className={inputClass} value={library.form.linked_opportunity_id} onChange={(e) => library.setForm({ ...library.form, linked_opportunity_id: e.target.value })}>
              <option value="">None</option>
              {opportunities.map((opportunity) => <option key={opportunity.id} value={opportunity.id}>{opportunity.role} · {opportunity.project}</option>)}
            </select>
          </Field>
          {submissions.length > 0 ? (
            <Field label="Linked Submission">
              <select className={inputClass} value={library.form.linked_submission_id} onChange={(e) => library.setForm({ ...library.form, linked_submission_id: e.target.value })}>
                <option value="">None</option>
                {submissions.map((submission) => <option key={submission.id} value={submission.id}>{submission.opportunity?.role ?? "Submission"} · {submission.current_status}</option>)}
              </select>
            </Field>
          ) : (
            <p className="self-end rounded bg-slate-100 p-2 text-xs text-slate-600">No existing submissions yet. This self-tape can still be saved.</p>
          )}
          <div className="lg:col-span-3">
            <Field label="Notes">
              <textarea className={inputClass} value={library.form.notes} onChange={(e) => library.setForm({ ...library.form, notes: e.target.value })} />
            </Field>
          </div>
          <div className="flex items-end"><Button type="submit" disabled={library.mutationPending}>Add Self-Tape</Button></div>
        </form>

        <div className="grid gap-3 lg:grid-cols-3">
          {selfTapes.length === 0 ? <EmptyState>No self-tapes in the library yet.</EmptyState> : selfTapes.map((tape) => (
            <article key={tape.id} className="rounded-md border border-slate-200 p-3 text-sm">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="font-semibold">{tape.title}</h3>
                  <p className="text-slate-600">{tape.role_type || "General"} · {tape.date_created}</p>
                </div>
                {tape.outcome && <Badge>{tape.outcome}</Badge>}
              </div>
              <p className="mt-2">Archetypes: {tape.archetypes.join(", ") || "None"}</p>
              <p className="break-all">File: {tape.file_path}</p>
              {tape.linked_opportunity_id && <p>Breakdown: {library.opportunityById[tape.linked_opportunity_id]?.role ?? "Linked"}</p>}
              {tape.notes && <p className="mt-2 text-slate-600">{tape.notes}</p>}
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  className="inline-flex min-w-0 max-w-full items-center justify-center whitespace-normal break-words rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-ink transition hover:bg-slate-50"
                  ref={(element) => {
                    if (editingTapeId === tape.id && element) lastEditButtonRef.current = element;
                  }}
                  onClick={(event) => {
                    lastEditButtonRef.current = event.currentTarget;
                    setEditingTapeId((current) => current === tape.id ? null : tape.id);
                  }}
                >
                  Update Outcome
                </button>
                <ConfirmAction
                  label="Delete"
                  confirmLabel="Delete"
                  message={`Delete ${tape.title}?`}
                  onConfirm={() => library.remove(tape.id)}
                />
              </div>
              {editingTapeId === tape.id && (
                <SelfTapeOutcomeForm
                  tape={tape}
                  opportunities={opportunities}
                  submissions={submissions}
                  onSave={library.saveTapeUpdate}
                  onCancel={closeEditForm}
                />
              )}
            </article>
          ))}
        </div>
      </div>
    </Section>
  );
}
