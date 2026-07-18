import { Badge, Button, EmptyState, Field, Section, inputClass } from "../../../components/ui";
import { callbackEventTypes } from "../constants";
import { useCallbackEventActions } from "../hooks/useCallbackEvents";
import type { CallbackEvent, Opportunity, Submission } from "../types";
import { formatDateTime } from "../utils";

export function CallbackEventsPanel({
  callbackEvents,
  opportunities,
  submissions
}: {
  callbackEvents: CallbackEvent[];
  opportunities: Opportunity[];
  submissions: Submission[];
}) {
  const callbacks = useCallbackEventActions();

  return (
    <Section title="Callback Events">
      <form className="mb-4 grid gap-3 rounded-md border border-slate-200 bg-slate-50 p-3 lg:grid-cols-4" onSubmit={callbacks.submit}>
        <Field label="Linked Submission">
          <select className={inputClass} value={callbacks.form.submission_id} onChange={(e) => callbacks.setForm({ ...callbacks.form, submission_id: e.target.value })}>
            <option value="">None</option>
            {submissions.map((submission) => <option key={submission.id} value={submission.id}>{submission.opportunity?.role ?? "Submission"} · {submission.current_status}</option>)}
          </select>
        </Field>
        <Field label="Linked Breakdown">
          <select className={inputClass} value={callbacks.form.opportunity_id} onChange={(e) => callbacks.setForm({ ...callbacks.form, opportunity_id: e.target.value })}>
            <option value="">None</option>
            {opportunities.map((opportunity) => <option key={opportunity.id} value={opportunity.id}>{opportunity.role} · {opportunity.project}</option>)}
          </select>
        </Field>
        <Field label="Callback Type">
          <select className={inputClass} value={callbacks.form.event_type} onChange={(e) => callbacks.setForm({ ...callbacks.form, event_type: e.target.value, event_name: e.target.value })}>
            {callbackEventTypes.map((type) => <option key={type}>{type}</option>)}
          </select>
        </Field>
        <Field label="Custom Name"><input className={inputClass} value={callbacks.form.event_name} onChange={(e) => callbacks.setForm({ ...callbacks.form, event_name: e.target.value })} /></Field>
        <Field label="Date"><input className={inputClass} type="date" value={callbacks.form.event_datetime} onChange={(e) => callbacks.setForm({ ...callbacks.form, event_datetime: e.target.value })} /></Field>
        <Field label="Location"><input className={inputClass} value={callbacks.form.location} onChange={(e) => callbacks.setForm({ ...callbacks.form, location: e.target.value })} /></Field>
        <label className="flex items-center gap-2 text-sm"><input name="is_virtual" type="checkbox" checked={callbacks.form.is_virtual} onChange={(e) => callbacks.setForm({ ...callbacks.form, is_virtual: e.target.checked })} />Virtual</label>
        <Field label="Outcome"><input className={inputClass} value={callbacks.form.outcome} onChange={(e) => callbacks.setForm({ ...callbacks.form, outcome: e.target.value })} /></Field>
        <div className="lg:col-span-2"><Field label="Preparation Notes"><textarea className={inputClass} value={callbacks.form.preparation_notes} onChange={(e) => callbacks.setForm({ ...callbacks.form, preparation_notes: e.target.value })} /></Field></div>
        <div className="lg:col-span-2"><Field label="Notes"><textarea className={inputClass} value={callbacks.form.notes} onChange={(e) => callbacks.setForm({ ...callbacks.form, notes: e.target.value })} /></Field></div>
        <Button type="submit">Add Callback Event</Button>
      </form>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {callbackEvents.length === 0 ? <EmptyState>Callback events will create a clearer audition progression timeline.</EmptyState> : callbackEvents.map((event) => (
          <article key={event.id} className="rounded-md border border-slate-200 p-3 text-sm">
            <div className="flex items-start justify-between gap-2">
              <div>
                <h3 className="font-semibold">{event.event_name}</h3>
                <p className="text-slate-600">{event.event_datetime ? formatDateTime(event.event_datetime) : "No date"} · {event.location || (event.is_virtual ? "Virtual" : "Location TBD")}</p>
              </div>
              <Badge>{event.event_type}</Badge>
            </div>
            {event.preparation_notes && <p className="mt-2">{event.preparation_notes}</p>}
            <div className="mt-3 flex gap-2">
              <button type="button" className="text-sm font-semibold text-red-700 underline-offset-2 hover:text-red-800 hover:underline" onClick={() => void callbacks.remove(event.id)}>Delete</button>
            </div>
          </article>
        ))}
      </div>
    </Section>
  );
}
