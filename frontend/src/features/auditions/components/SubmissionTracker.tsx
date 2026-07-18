import { ActionCard, Badge, Button, DetailDisclosure, EmptyState, Field, Section, inputClass } from "../../../components/ui";
import { selfTapeStatuses, submissionStatuses } from "../constants";
import { useSubmissionTracker } from "../hooks/useSubmissionTracker";
import type { ActorProfile, Opportunity, SelfTapeWorkflow, Submission, SubmissionStatus } from "../types";
import type { MaterialOption } from "../../materials";
import { formatDateTime } from "../utils";
import { OpportunityLink } from "./LinkedBreakdownSummary";

const callbackStatuses = new Set(["Requested", "Self-Tape Callback", "In-Person Callback", "Pinned"]);

export function SubmissionTracker({
  actor,
  opportunities,
  assets,
  submissions,
  selfTapes
}: {
  actor: ActorProfile | null;
  opportunities: Opportunity[];
  assets: MaterialOption[];
  submissions: Submission[];
  selfTapes: SelfTapeWorkflow[];
}) {
  const tracker = useSubmissionTracker({ actor, opportunities, submissions, selfTapes });

  function renderSelfTapeCard(workflow: SelfTapeWorkflow) {
    const opportunity = opportunities.find((item) => item.id === workflow.opportunity_id);
    const isEditing = tracker.editingTapeId === workflow.id;
    return (
      <article key={workflow.id} className="rounded-md border border-slate-200 bg-white p-3 text-sm">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="font-semibold">{opportunity ? <OpportunityLink opportunity={opportunity} /> : "Self-Tape"}</h3>
            <p className="text-xs text-slate-600">{opportunity?.project ?? "Linked breakdown"} · Due {formatDateTime(workflow.tape_due_at)}</p>
          </div>
          <Badge>{workflow.status}</Badge>
        </div>
        {isEditing ? (
          <div className="mt-3 grid gap-2 md:grid-cols-2">
            <Field label="Status">
              <select className={inputClass} value={tracker.tapeEditForm.status} onChange={(event) => tracker.setTapeEditForm({ ...tracker.tapeEditForm, status: event.target.value })}>
                {selfTapeStatuses.map((status) => <option key={status}>{status}</option>)}
              </select>
            </Field>
            <Field label="Audition/Tape Due">
              <input className={inputClass} type="datetime-local" value={tracker.tapeEditForm.tape_due_at} onChange={(event) => tracker.setTapeEditForm({ ...tracker.tapeEditForm, tape_due_at: event.target.value })} />
            </Field>
            <Field label="Upload Link">
              <input className={inputClass} value={tracker.tapeEditForm.upload_link} onChange={(event) => tracker.setTapeEditForm({ ...tracker.tapeEditForm, upload_link: event.target.value })} />
            </Field>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input type="checkbox" checked={tracker.tapeEditForm.reader_needed} onChange={(event) => tracker.setTapeEditForm({ ...tracker.tapeEditForm, reader_needed: event.target.checked })} />
              Reader needed
            </label>
            <div className="md:col-span-2"><Field label="Preparation / Slate"><input className={inputClass} value={tracker.tapeEditForm.slate_requirements} onChange={(event) => tracker.setTapeEditForm({ ...tracker.tapeEditForm, slate_requirements: event.target.value })} /></Field></div>
            <div className="md:col-span-2"><Field label="Wardrobe"><input className={inputClass} value={tracker.tapeEditForm.wardrobe_notes} onChange={(event) => tracker.setTapeEditForm({ ...tracker.tapeEditForm, wardrobe_notes: event.target.value })} /></Field></div>
            <div className="flex gap-2 md:col-span-2">
              <Button type="button" onClick={() => void tracker.saveTapeEdit(workflow)}>Save</Button>
              <Button type="button" variant="secondary" onClick={() => tracker.setEditingTapeId(null)}>Cancel</Button>
            </div>
          </div>
        ) : (
          <>
            <div className="mt-2 grid gap-1 text-xs text-slate-600">
              <p>Reader: {workflow.reader_needed ? "Needed" : "Not needed"}</p>
              {workflow.slate_requirements && <p>Prep: {workflow.slate_requirements}</p>}
              {workflow.wardrobe_notes && <p>Wardrobe: {workflow.wardrobe_notes}</p>}
              {workflow.upload_link && <a className="font-semibold text-accent hover:underline" href={workflow.upload_link} target="_blank" rel="noreferrer">Upload destination</a>}
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {selfTapeStatuses.map((status) => (
                <button key={status} type="button" className="text-xs font-semibold text-accent hover:underline" onClick={() => void tracker.quickUpdateTapeStatus(workflow.id, status)}>
                  {status}
                </button>
              ))}
              <button type="button" className="text-xs font-semibold text-slate-700 hover:underline" onClick={() => tracker.startTapeEdit(workflow)}>Edit</button>
            </div>
          </>
        )}
      </article>
    );
  }

  function renderSubmissionCard(submission: Submission) {
    return (
      <ActionCard
        key={submission.id}
        title={submission.opportunity ? <OpportunityLink opportunity={submission.opportunity} /> : "Audition"}
        status={<Badge>{submission.current_status}</Badge>}
        meta={`Total cost: $${Number(submission.total_cost).toFixed(2)}`}
        primaryAction={<Button variant="secondary" onClick={() => void tracker.markSubmissionStatus(submission.id, "Submitted")}>Mark Submitted</Button>}
        secondaryAction={<Button variant="danger" onClick={() => void tracker.removeSubmission(submission.id)}>Delete</Button>}
        details={(
          <div className="grid gap-2">
            <DetailDisclosure label="Materials Used">
              <div className="flex flex-wrap gap-1">{submission.assets.length === 0 ? "No materials linked." : submission.assets.map((asset) => <Badge key={asset.id}>{asset.asset_name}</Badge>)}</div>
            </DetailDisclosure>
            <DetailDisclosure label="Update Status">
              <div className="flex flex-wrap gap-2">{submissionStatuses.map((status) => <button key={status} className="rounded border border-slate-300 px-2 py-1 text-xs hover:bg-slate-50" onClick={() => void tracker.markSubmissionStatus(submission.id, status as SubmissionStatus)}>{status}</button>)}</div>
            </DetailDisclosure>
            <DetailDisclosure label="History">
              <ol className="grid gap-1 text-xs text-slate-600">{submission.status_history.map((history) => <li key={history.id}>{new Date(history.occurred_at).toLocaleString()} · {history.status}</li>)}</ol>
            </DetailDisclosure>
          </div>
        )}
      />
    );
  }

  function AuditionGroup({ title, items }: { title: string; items: Submission[] }) {
    return (
      <div className="grid gap-2">
        <h3 className="text-sm font-semibold text-ink">{title}</h3>
        {items.length === 0 ? <p className="text-xs text-slate-500">No {title.toLowerCase()} yet.</p> : items.map(renderSubmissionCard)}
      </div>
    );
  }

  const selfTapeSubmissions = submissions.filter((submission) => submission.opportunity?.audition_type === "Self-Tape" && !callbackStatuses.has(submission.current_status) && !["Booked", "Passed", "No Response"].includes(submission.current_status));
  const inPersonSubmissions = submissions.filter((submission) => submission.opportunity?.audition_type === "In-Person" && !callbackStatuses.has(submission.current_status) && !["Booked", "Passed", "No Response"].includes(submission.current_status));
  const virtualSubmissions = submissions.filter((submission) => submission.opportunity?.audition_type === "Virtual" && !callbackStatuses.has(submission.current_status) && !["Booked", "Passed", "No Response"].includes(submission.current_status));
  const callbacks = submissions.filter((submission) => callbackStatuses.has(submission.current_status));
  const booked = submissions.filter((submission) => submission.current_status === "Booked");
  const closed = submissions.filter((submission) => ["Passed", "No Response"].includes(submission.current_status));

  return (
    <Section title="Auditions" actions={<Button onClick={() => tracker.setFormOpen((current) => !current)}>{tracker.formOpen ? "Hide Form" : "Add Audition"}</Button>}>
      {!actor ? <EmptyState>Create an actor profile before tracking submissions.</EmptyState> : (
        tracker.formOpen && <form className="mb-4 grid gap-3 rounded-md border border-slate-200 bg-slate-50 p-3 lg:grid-cols-4" onSubmit={tracker.submit}>
          <Field label="Breakdown"><select className={inputClass} value={tracker.form.opportunity_id} onChange={(e) => tracker.selectBreakdown(e.target.value)} required><option value="">Select breakdown</option>{opportunities.map((opportunity) => <option value={opportunity.id} key={opportunity.id}>{opportunity.role} · {opportunity.project}</option>)}</select></Field>
          <Field label="Status"><select className={inputClass} value={tracker.form.current_status} onChange={(e) => tracker.setForm({ ...tracker.form, current_status: e.target.value as SubmissionStatus })}>{submissionStatuses.map((status) => <option key={status}>{status}</option>)}</select></Field>
          <Field label="Audition/Tape Due Date"><input className={inputClass} type="datetime-local" value={tracker.form.tape_due_at} onChange={(e) => tracker.setForm({ ...tracker.form, tape_due_at: e.target.value })} /></Field>
          <Field label="Audition Date"><input className={inputClass} type="datetime-local" value={tracker.form.audition_date} onChange={(e) => tracker.setForm({ ...tracker.form, audition_date: e.target.value })} /></Field>
          <Field label="Audition Location"><input className={inputClass} value={tracker.form.audition_location} onChange={(e) => tracker.setForm({ ...tracker.form, audition_location: e.target.value })} /></Field>
          <Field label="Virtual Audition Link"><input className={inputClass} type="url" value={tracker.form.virtual_audition_link} onChange={(e) => tracker.setForm({ ...tracker.form, virtual_audition_link: e.target.value })} /></Field>
          <Field label="Self-Tape Submission Link"><input className={inputClass} type="url" value={tracker.form.self_tape_submission_link} onChange={(e) => tracker.setForm({ ...tracker.form, self_tape_submission_link: e.target.value })} /></Field>
          <div className="flex items-end"><Button type="submit">Submitted/Auditioned for this role</Button></div>
          <div className="lg:col-span-4 grid gap-2 rounded-md border border-slate-200 bg-white p-3">
            <Field label="Paste Audition Text">
              <textarea className={inputClass} rows={5} value={tracker.form.audition_text} onChange={(e) => tracker.setForm({ ...tracker.form, audition_text: e.target.value })} placeholder="Paste an agent email, casting message, or platform text here." />
            </Field>
            <div><Button variant="secondary" onClick={tracker.parseAuditionDetails}>Parse Audition Details</Button></div>
          </div>
          <div className="lg:col-span-2"><Field label="Preparation Instructions"><textarea className={inputClass} value={tracker.form.preparation_instructions} onChange={(e) => tracker.setForm({ ...tracker.form, preparation_instructions: e.target.value })} /></Field></div>
          <div className="lg:col-span-2"><Field label="Submission Instructions"><textarea className={inputClass} value={tracker.form.submission_instructions} onChange={(e) => tracker.setForm({ ...tracker.form, submission_instructions: e.target.value })} /></Field></div>
          <div className="lg:col-span-4"><Field label="Notes"><textarea className={inputClass} value={tracker.form.notes} onChange={(e) => tracker.setForm({ ...tracker.form, notes: e.target.value })} /></Field></div>
          <label className="flex items-center gap-2 text-sm text-slate-700"><input name="create_self_tape" type="checkbox" checked={tracker.form.create_self_tape} onChange={(e) => tracker.setForm({ ...tracker.form, create_self_tape: e.target.checked })} />Create self-tape task if due date exists</label>
          <label className="flex items-center gap-2 text-sm text-slate-700"><input name="create_calendar" type="checkbox" checked={tracker.form.create_calendar} onChange={(e) => tracker.setForm({ ...tracker.form, create_calendar: e.target.checked })} />Add to calendar</label>
          <label className="flex items-center gap-2 text-sm text-slate-700"><input name="create_journal" type="checkbox" checked={tracker.form.create_journal} onChange={(e) => tracker.setForm({ ...tracker.form, create_journal: e.target.checked })} />Create journal entry</label>
          <Field label="Submission Fee"><input className={inputClass} type="number" step="0.01" value={tracker.form.submission_fee} onChange={(e) => tracker.setForm({ ...tracker.form, submission_fee: e.target.value })} /></Field>
          <Field label="Media Fee"><input className={inputClass} type="number" step="0.01" value={tracker.form.media_fee} onChange={(e) => tracker.setForm({ ...tracker.form, media_fee: e.target.value })} /></Field>
          <Field label="Travel Cost"><input className={inputClass} type="number" step="0.01" value={tracker.form.travel_cost} onChange={(e) => tracker.setForm({ ...tracker.form, travel_cost: e.target.value })} /></Field>
          <Field label="Housing Cost"><input className={inputClass} type="number" step="0.01" value={tracker.form.housing_cost} onChange={(e) => tracker.setForm({ ...tracker.form, housing_cost: e.target.value })} /></Field>
          <Field label="Parking Cost"><input className={inputClass} type="number" step="0.01" value={tracker.form.parking_cost} onChange={(e) => tracker.setForm({ ...tracker.form, parking_cost: e.target.value })} /></Field>
          <Field label="Other Cost"><input className={inputClass} type="number" step="0.01" value={tracker.form.other_cost} onChange={(e) => tracker.setForm({ ...tracker.form, other_cost: e.target.value })} /></Field>
          <div className="lg:col-span-4">
            <p className="mb-2 text-sm font-medium text-slate-700">Linked Assets</p>
            <div className="flex flex-wrap gap-2">
              {assets.map((asset) => <label key={asset.id} className="flex items-center gap-2 rounded-md border border-slate-200 px-3 py-2 text-sm"><input type="checkbox" checked={tracker.form.asset_ids.includes(asset.id)} onChange={() => tracker.toggleAsset(asset.id)} />{asset.asset_name}</label>)}
            </div>
          </div>
        </form>
      )}
      {tracker.submissionMessage && <p className="mb-3 rounded-md bg-green-50 px-3 py-2 text-xs font-medium text-green-800">{tracker.submissionMessage}</p>}
      <div className="grid gap-3">
        {selfTapes.length === 0 && submissions.length === 0 ? <EmptyState>Add an audition manually or track one from a breakdown.</EmptyState> : (
          <>
            <div className="grid gap-2">
              <h3 className="text-sm font-semibold text-ink">Self-Tapes</h3>
              {selfTapes.length === 0 ? <p className="text-xs text-slate-500">No self-tape tasks yet.</p> : <div className="grid gap-3 lg:grid-cols-2">{selfTapes.map(renderSelfTapeCard)}</div>}
            </div>
            <AuditionGroup title="In-Person Auditions" items={inPersonSubmissions} />
            <AuditionGroup title="Virtual Auditions" items={virtualSubmissions} />
            <AuditionGroup title="Callbacks" items={callbacks} />
            <AuditionGroup title="Booked" items={booked} />
            <AuditionGroup title="Passed / No Response" items={closed} />
            {selfTapeSubmissions.length > 0 && <AuditionGroup title="Submitted Self-Tapes" items={selfTapeSubmissions} />}
          </>
        )}
      </div>
    </Section>
  );
}
