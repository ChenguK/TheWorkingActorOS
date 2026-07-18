import { AsyncButton, Badge, ConfirmAction, EmptyState, Field, Section, inputClass } from "../../../components/ui";
import { useCommunicationLogs } from "../hooks/useCommunicationLogs";
import type { Opportunity, Representation, Submission } from "../types";

export function CommunicationLogPanel({
  representations,
  opportunities,
  submissions
}: {
  representations: Representation[];
  opportunities: Opportunity[];
  submissions: Submission[];
}) {
  const communication = useCommunicationLogs();

  return (
    <Section title="Agent Communication Log">
      {communication.isLoading && <p role="status" className="mb-3 text-sm text-slate-600">Loading interaction history...</p>}
      {communication.queryError && <p role="alert" className="mb-3 rounded bg-red-50 p-2 text-sm text-red-800">{communication.queryError}</p>}
      {communication.isRefetching && !communication.isLoading && <p role="status" className="mb-3 text-xs text-slate-500">Refreshing interaction history...</p>}
      <form className="mb-4 grid gap-3 rounded-md border border-slate-200 bg-slate-50 p-3 lg:grid-cols-4" onSubmit={communication.submit}>
        <Field label="Representative">
          <select className={inputClass} value={communication.form.representation_id} onChange={(event) => communication.setForm({ ...communication.form, representation_id: event.target.value })}>
            <option value="">None</option>
            {representations.map((rep) => <option key={rep.id} value={rep.id}>{rep.agent_name || rep.agency_name}</option>)}
          </select>
        </Field>
        <Field label="Date"><input className={inputClass} type="date" value={communication.form.date} onChange={(event) => communication.setForm({ ...communication.form, date: event.target.value })} required /></Field>
        <Field label="Topic"><input className={inputClass} value={communication.form.topic} onChange={(event) => communication.setForm({ ...communication.form, topic: event.target.value })} required /></Field>
        <Field label="Breakdown">
          <select className={inputClass} value={communication.form.opportunity_id} onChange={(event) => communication.setForm({ ...communication.form, opportunity_id: event.target.value })}>
            <option value="">None</option>
            {opportunities.map((opportunity) => <option key={opportunity.id} value={opportunity.id}>{opportunity.role} · {opportunity.project}</option>)}
          </select>
        </Field>
        <Field label="Linked Submission">
          <select className={inputClass} value={communication.form.submission_id} onChange={(event) => communication.setForm({ ...communication.form, submission_id: event.target.value })}>
            <option value="">None</option>
            {submissions.map((submission) => <option key={submission.id} value={submission.id}>{submission.opportunity?.role ?? "Submission"} · {submission.current_status}</option>)}
          </select>
        </Field>
        <label className="flex items-center gap-2 text-sm"><input name="follow_up_needed" type="checkbox" checked={communication.form.follow_up_needed} onChange={(event) => communication.setForm({ ...communication.form, follow_up_needed: event.target.checked })} />Follow-up needed</label>
        <Field label="Follow-Up Date"><input className={inputClass} type="date" value={communication.form.follow_up_date} onChange={(event) => communication.setForm({ ...communication.form, follow_up_date: event.target.value })} /></Field>
        <div className="lg:col-span-4"><Field label="Notes"><textarea className={inputClass} value={communication.form.notes} onChange={(event) => communication.setForm({ ...communication.form, notes: event.target.value })} /></Field></div>
        {communication.error && <p className="rounded bg-red-50 p-2 text-sm font-medium text-red-800 lg:col-span-4">{communication.error}</p>}
        <AsyncButton type="submit" loading={communication.saving}>Add Communication</AsyncButton>
      </form>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {!communication.isLoading && !communication.queryError && communication.logs.length === 0 ? <EmptyState>Log agent or manager conversations that affect auditions, submissions, or follow-ups.</EmptyState> : communication.logs.map((log) => (
          <article key={log.id} className="rounded-md border border-slate-200 p-3 text-sm">
            <div className="flex items-start justify-between gap-2">
              <div>
                <h3 className="font-semibold">{log.topic}</h3>
                <p className="text-slate-600">{log.date}</p>
              </div>
              {log.follow_up_needed && <Badge>Follow up</Badge>}
            </div>
            {log.notes && <p className="mt-2">{log.notes}</p>}
            <div className="mt-3">
              <ConfirmAction
                label="Delete"
                confirmLabel="Delete"
                message={`Delete communication about ${log.topic}?`}
                onConfirm={() => communication.remove(log.id)}
              />
            </div>
          </article>
        ))}
      </div>
    </Section>
  );
}
