import type { ActorJournalEntry } from "../../../types/domain";
import { Badge, Button, EmptyState, Field, Section, inputClass } from "../../../components/ui";
import { journalEventTypes } from "../constants";
import { useJournalEntries } from "../hooks/useJournalEntries";
import type { JournalLinkedEntity, JournalPanelData } from "../types";
import { formatJournalDate, journalEntryLinks } from "../utils";

export function JournalPanel({ opportunities, submissions, assets, careerTasks }: JournalPanelData) {
  const journal = useJournalEntries();

  return (
    <div className="grid gap-4">
      <Section
        title="Journal"
        actions={(
          <div className="flex gap-2">
            <Button variant="secondary" disabled={journal.isRefetching} onClick={() => void journal.refetch()}>
              {journal.isRefetching ? "Refreshing..." : "Refresh"}
            </Button>
            <Button onClick={() => journal.setFormOpen((current) => !current)}>{journal.formOpen ? "Hide Entry Form" : "Add Journal Entry"}</Button>
          </div>
        )}
      >
        <div className="grid gap-4">
          <p className="text-sm text-slate-600">
            A record of meaningful actor work: platform check-ins, accepted breakdowns, submissions, completed auditions, callbacks, bookings, materials, and career progress.
          </p>
          {journal.formOpen && (
            <JournalEntryForm
              form={journal.form}
              opportunities={opportunities}
              submissions={submissions}
              assets={assets}
              careerTasks={careerTasks}
              onChange={journal.setForm}
              onSubmit={journal.createEntry}
              saving={journal.createPending}
            />
          )}
          {journal.successMessage && <p className="rounded bg-emerald-50 p-2 text-sm text-emerald-800">{journal.successMessage}</p>}
          {journal.mutationError && <p className="rounded bg-red-50 p-2 text-sm text-red-700" role="alert">{journal.mutationError}</p>}
        </div>
      </Section>

      {journal.isLoading ? (
        <Section title="Daily View"><p className="text-sm text-slate-600" role="status">Loading Journal entries...</p></Section>
      ) : journal.error ? (
        <Section title="Daily View"><p className="rounded bg-red-50 p-2 text-sm text-red-700" role="alert">{journal.error}</p></Section>
      ) : journal.groupedEntries.length === 0 ? (
        <Section title="Daily View">
          <EmptyState>Your meaningful actor work will collect here automatically. You can also add a manual entry.</EmptyState>
        </Section>
      ) : journal.groupedEntries.map(([date, dateEntries]) => (
        <JournalDayGroup
          key={date}
          date={date}
          entries={dateEntries}
          opportunities={opportunities}
          assets={assets}
          careerTasks={careerTasks}
          editingNotesId={journal.editingNotesId}
          notesDraft={journal.notesDraft}
          onStartNotesEdit={journal.startNotesEdit}
          onNotesDraftChange={journal.setNotesDraft}
          onSaveNotes={journal.saveNotes}
          updatePending={journal.updatePending}
          onCancelNotesEdit={() => journal.setEditingNotesId(null)}
        />
      ))}
    </div>
  );
}

function JournalEntryForm({
  form,
  opportunities,
  submissions,
  assets,
  careerTasks,
  onChange,
  onSubmit,
  saving
}: {
  form: ReturnType<typeof useJournalEntries>["form"];
  opportunities: JournalPanelData["opportunities"];
  submissions: JournalPanelData["submissions"];
  assets: JournalPanelData["assets"];
  careerTasks: JournalPanelData["careerTasks"];
  onChange: ReturnType<typeof useJournalEntries>["setForm"];
  onSubmit: ReturnType<typeof useJournalEntries>["createEntry"];
  saving: boolean;
}) {
  return (
    <form className="grid gap-3 rounded-md border border-slate-200 bg-slate-50 p-3 lg:grid-cols-4" onSubmit={onSubmit}>
      <Field label="Date"><input className={inputClass} type="date" value={form.date} onChange={(event) => onChange({ ...form, date: event.target.value })} required /></Field>
      <Field label="Event Type">
        <select className={inputClass} value={form.event_type} onChange={(event) => onChange({ ...form, event_type: event.target.value })}>
          {journalEventTypes.map((type) => <option key={type}>{type}</option>)}
        </select>
      </Field>
      <Field label="Title"><input className={inputClass} value={form.title} onChange={(event) => onChange({ ...form, title: event.target.value })} required /></Field>
      <Field label="Breakdown">
        <select className={inputClass} value={form.linked_breakdown_id} onChange={(event) => onChange({ ...form, linked_breakdown_id: event.target.value })}>
          <option value="">None</option>
          {opportunities.map((opportunity) => <option key={opportunity.id} value={opportunity.id}>{opportunity.role} · {opportunity.project}</option>)}
        </select>
      </Field>
      <Field label="Audition / Submission">
        <select className={inputClass} value={form.linked_audition_id} onChange={(event) => onChange({ ...form, linked_audition_id: event.target.value })}>
          <option value="">None</option>
          {submissions.map((submission) => <option key={submission.id} value={submission.id}>{submission.opportunity?.role ?? "Submission"} · {submission.current_status}</option>)}
        </select>
      </Field>
      <Field label="Material">
        <select className={inputClass} value={form.linked_material_id} onChange={(event) => onChange({ ...form, linked_material_id: event.target.value })}>
          <option value="">None</option>
          {assets.map((asset) => <option key={asset.id} value={asset.id}>{asset.asset_name} · {asset.asset_type}</option>)}
        </select>
      </Field>
      <Field label="Career Task">
        <select className={inputClass} value={form.linked_career_task_id} onChange={(event) => onChange({ ...form, linked_career_task_id: event.target.value })}>
          <option value="">None</option>
          {careerTasks.map((task) => <option key={task.id} value={task.id}>{task.title}</option>)}
        </select>
      </Field>
      <div className="lg:col-span-2"><Field label="Description"><textarea className={inputClass} value={form.description} onChange={(event) => onChange({ ...form, description: event.target.value })} /></Field></div>
      <div className="lg:col-span-2"><Field label="Notes"><textarea className={inputClass} value={form.notes} onChange={(event) => onChange({ ...form, notes: event.target.value })} /></Field></div>
      <div className="flex items-end"><Button type="submit" disabled={saving}>{saving ? "Saving..." : "Save Entry"}</Button></div>
    </form>
  );
}

function JournalDayGroup({
  date,
  entries,
  opportunities,
  assets,
  careerTasks,
  editingNotesId,
  notesDraft,
  onStartNotesEdit,
  onNotesDraftChange,
  onSaveNotes,
  updatePending,
  onCancelNotesEdit
}: {
  date: string;
  entries: ActorJournalEntry[];
  opportunities: JournalPanelData["opportunities"];
  assets: JournalPanelData["assets"];
  careerTasks: JournalPanelData["careerTasks"];
  editingNotesId: string | null;
  notesDraft: string;
  onStartNotesEdit: (entry: ActorJournalEntry) => void;
  onNotesDraftChange: (value: string) => void;
  onSaveNotes: (entry: ActorJournalEntry) => Promise<void>;
  updatePending: boolean;
  onCancelNotesEdit: () => void;
}) {
  return (
    <Section title={formatJournalDate(date)}>
      <div className="grid gap-3">
        {entries.map((entry) => (
          <JournalEntryCard
            key={entry.id}
            entry={entry}
            links={journalEntryLinks({ entry, opportunities, assets, careerTasks })}
            editingNotesId={editingNotesId}
            notesDraft={notesDraft}
            onStartNotesEdit={onStartNotesEdit}
            onNotesDraftChange={onNotesDraftChange}
            onSaveNotes={onSaveNotes}
            updatePending={updatePending}
            onCancelNotesEdit={onCancelNotesEdit}
          />
        ))}
      </div>
    </Section>
  );
}

function JournalEntryCard({
  entry,
  links,
  editingNotesId,
  notesDraft,
  onStartNotesEdit,
  onNotesDraftChange,
  onSaveNotes,
  updatePending,
  onCancelNotesEdit
}: {
  entry: ActorJournalEntry;
  links: JournalLinkedEntity[];
  editingNotesId: string | null;
  notesDraft: string;
  onStartNotesEdit: (entry: ActorJournalEntry) => void;
  onNotesDraftChange: (value: string) => void;
  onSaveNotes: (entry: ActorJournalEntry) => Promise<void>;
  updatePending: boolean;
  onCancelNotesEdit: () => void;
}) {
  return (
    <article className="rounded-md border border-slate-200 bg-white p-3 text-sm">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Badge>{entry.event_type}</Badge>
            <h3 className="font-semibold text-ink">{entry.title}</h3>
          </div>
          {entry.description && <p className="mt-2 text-slate-700">{entry.description}</p>}
          <JournalLinkedEntities links={links} />
        </div>
        <button type="button" className="text-xs font-semibold text-accent hover:underline" onClick={() => onStartNotesEdit(entry)}>Edit notes</button>
      </div>
      {editingNotesId === entry.id ? (
        <div className="mt-3 grid gap-2">
          <textarea className={inputClass} value={notesDraft} onChange={(event) => onNotesDraftChange(event.target.value)} />
          <div className="flex gap-2">
            <Button type="button" disabled={updatePending} onClick={() => void onSaveNotes(entry)}>{updatePending ? "Saving..." : "Save Notes"}</Button>
            <Button type="button" variant="secondary" onClick={onCancelNotesEdit}>Cancel</Button>
          </div>
        </div>
      ) : entry.notes ? (
        <p className="mt-3 rounded bg-slate-50 p-2 text-slate-700">{entry.notes}</p>
      ) : null}
    </article>
  );
}

function JournalLinkedEntities({ links }: { links: JournalLinkedEntity[] }) {
  if (links.length === 0) return null;
  return (
    <div className="mt-2 flex flex-wrap gap-2 text-xs">
      {links.map((link) => <a key={link.key} className="text-accent hover:underline" href={link.href}>{link.label}</a>)}
    </div>
  );
}
