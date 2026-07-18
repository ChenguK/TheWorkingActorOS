import { useState, type FormEvent } from "react";
import FullCalendar from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";
import timeGridPlugin from "@fullcalendar/timegrid";
import { Badge, Button, EmptyState, Field, Section, inputClass } from "../../../components/ui";
import { calendarEventTypes } from "../../../constants/workflowOptions";
import { errorMessage } from "../../../services/api/errors";
import type { AvailabilityBlock, AuditionCalendarEvent, AuditionCalendarEventType } from "../../../types/domain";
import { useActorCalendar } from "../hooks/useActorCalendar";
import {
  useAvailabilityBlocks,
  useCreateAvailabilityBlock,
  useDeleteAvailabilityBlock,
  useUpdateAvailabilityBlock
} from "../hooks/useCalendarQueries";
import type { ActorCalendarData } from "../types";
import { calendarRecordOwnership, formatCalendarDateTime } from "../utils";

export function ActorCalendar(props: ActorCalendarData) {
  const calendar = useActorCalendar(props);
  const availability = useAvailabilityBlocks();
  const hasPlatformCheckIns = (props.commandCenter?.platform_check_ins ?? []).some((item) => item.active && item.has_subscription);

  if (calendar.isLoading || availability.isLoading) {
    return <div role="status" className="rounded-md border border-slate-200 bg-white p-4 text-sm text-slate-600">Loading Calendar...</div>;
  }

  const loadError = calendar.error ?? (availability.error && !availability.data ? errorMessage(availability.error, "Could not load availability.") : null);
  if (loadError) {
    return <div role="alert" className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">{loadError}</div>;
  }

  return (
    <div className="grid gap-4">
      <Section title="Calendar">
        <div className="grid gap-4">
          {(calendar.isRefetching || availability.isRefetching) && <p role="status" className="text-xs text-slate-500">Refreshing Calendar...</p>}
          <div className="overflow-hidden rounded-md border border-slate-200 bg-white p-2 text-xs">
            <FullCalendar
              plugins={[dayGridPlugin, timeGridPlugin]}
              initialView="dayGridMonth"
              headerToolbar={{
                left: "prev,next today",
                center: "title",
                right: "dayGridMonth,timeGridWeek,timeGridDay"
              }}
              buttonText={{ month: "Month", week: "Week", day: "Day", today: "Today" }}
              events={calendar.fullCalendarEvents}
              eventClick={calendar.openRelated}
              eventDidMount={({ event, el }) => {
                const ownership = event.extendedProps.ownership as { description?: string } | undefined;
                const description = ownership?.description ?? "Read-only Calendar projection.";
                el.setAttribute("aria-label", `${event.title}. ${description}`);
                el.setAttribute("title", description);
                el.setAttribute("data-calendar-interaction", "form-only");
              }}
              height="auto"
              nowIndicator
              eventDisplay="block"
            />
          </div>
          <p className="text-xs text-slate-600">
            Calendar editing is form-based. Calendar-owned items can be edited below. Audition, Breakdown, callback, self-tape, and Chief of Staff dates are read-only here and must be changed in their owning feature.
          </p>
          <div className="flex flex-wrap gap-2 text-xs">
            <Badge>Self-tapes</Badge>
            <Badge>Auditions</Badge>
            <Badge>Callbacks</Badge>
            <Badge>Fittings</Badge>
            <Badge>Shoots / performances</Badge>
            {hasPlatformCheckIns && <Badge>Platform check-ins</Badge>}
          </div>
        </div>
      </Section>

      <CalendarEventForm calendar={calendar} opportunities={props.opportunities} submissions={props.submissions} />
      {calendar.mutationError && <p role="alert" className="text-sm text-red-700">{errorMessage(calendar.mutationError, "Could not save the Calendar event.")}</p>}
      <AvailabilityCalendarSection actor={props.actor} availability={availability.data ?? []} />

      <UpcomingCalendarList
        events={calendar.calendarEvents}
        onRename={calendar.renameEvent}
        onDelete={calendar.removeEvent}
        pending={calendar.mutationPending}
      />
    </div>
  );
}

function AvailabilityCalendarSection({
  actor,
  availability,
}: {
  actor: ActorCalendarData["actor"];
  availability: AvailabilityBlock[];
}) {
  const createMutation = useCreateAvailabilityBlock();
  const updateMutation = useUpdateAvailabilityBlock();
  const deleteMutation = useDeleteAvailabilityBlock();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState("");
  const [form, setForm] = useState({
    title: "",
    block_type: "Personal Commitment",
    start_date: "",
    end_date: "",
    notes: ""
  });

  async function saveAvailability(event: FormEvent) {
    event.preventDefault();
    if (!actor) return;
    try {
      await createMutation.mutateAsync({
        actor_profile_id: actor.id,
        ...form,
        notes: form.notes || null
      });
      setForm({ title: "", block_type: "Personal Commitment", start_date: "", end_date: "", notes: "" });
    } catch {
      // The mutation retains the standardized ApiError for presentation.
    }
  }

  async function saveAvailabilityTitle(blockId: string) {
    if (!editingTitle.trim()) return;
    try {
      await updateMutation.mutateAsync({ blockId, patch: { title: editingTitle.trim() } });
      setEditingId(null);
    } catch {
      // The mutation retains the standardized ApiError for presentation.
    }
  }

  async function removeAvailability(blockId: string) {
    try {
      await deleteMutation.mutateAsync(blockId);
    } catch {
      // The mutation retains the standardized ApiError for presentation.
    }
  }

  const mutationError = createMutation.error ?? updateMutation.error ?? deleteMutation.error;
  const mutationPending = createMutation.isPending || updateMutation.isPending || deleteMutation.isPending;

  return (
    <Section title="Availability">
      <div className="grid gap-4 xl:grid-cols-2">
        <form className="grid gap-3 rounded-md border border-slate-200 bg-slate-50 p-3" onSubmit={saveAvailability}>
          <h3 className="font-semibold">Add Availability Block</h3>
          <Field label="Title"><input className={inputClass} value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} required /></Field>
          <Field label="Type"><select className={inputClass} value={form.block_type} onChange={(event) => setForm({ ...form, block_type: event.target.value })}><option>Unavailable</option><option>Travel Blackout</option><option>Already Booked</option><option>Vacation</option><option>Training</option><option>Personal Commitment</option></select></Field>
          <Field label="Start"><input className={inputClass} type="datetime-local" value={form.start_date} onChange={(event) => setForm({ ...form, start_date: event.target.value })} required /></Field>
          <Field label="End"><input className={inputClass} type="datetime-local" value={form.end_date} onChange={(event) => setForm({ ...form, end_date: event.target.value })} required /></Field>
          <Field label="Notes"><textarea className={inputClass} value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} /></Field>
          <Button type="submit" disabled={!actor || mutationPending}>{createMutation.isPending ? "Adding..." : "Add Availability Block"}</Button>
          {mutationError && <p role="alert" className="text-sm text-red-700">{errorMessage(mutationError, "Could not save availability.")}</p>}
        </form>
        <div className="grid gap-2 rounded-md border border-slate-200 bg-slate-50 p-3 text-sm">
          <h3 className="font-semibold">Saved Availability</h3>
          {availability.length === 0 ? <p className="text-slate-500">No blackout dates saved.</p> : availability.slice(0, 8).map((block) => (
            <div key={block.id} className="rounded bg-white p-2">
              <p className="font-semibold">{block.title}</p>
              <p>{block.block_type} · {formatCalendarDateTime(block.start_date)} to {formatCalendarDateTime(block.end_date)}</p>
              {block.notes && <p className="text-slate-600">{block.notes}</p>}
              {editingId === block.id ? (
                <div className="mt-2 grid gap-2">
                  <Field label="Availability Title"><input className={inputClass} value={editingTitle} onChange={(event) => setEditingTitle(event.target.value)} /></Field>
                  <div className="flex gap-2"><Button variant="secondary" disabled={mutationPending} onClick={() => void saveAvailabilityTitle(block.id)}>Save</Button><Button variant="secondary" onClick={() => setEditingId(null)}>Cancel</Button></div>
                </div>
              ) : (
                <div className="mt-2 flex gap-2">
                  <Button variant="secondary" disabled={mutationPending} onClick={() => { setEditingId(block.id); setEditingTitle(block.title); }}>Edit</Button>
                  <Button variant="danger" disabled={mutationPending} onClick={() => void removeAvailability(block.id)}>Delete</Button>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </Section>
  );
}

function CalendarEventForm({
  calendar,
  opportunities,
  submissions
}: {
  calendar: ReturnType<typeof useActorCalendar>;
  opportunities: ActorCalendarData["opportunities"];
  submissions: ActorCalendarData["submissions"];
}) {
  return (
    <Section title="Add Calendar Event">
      <form className="grid gap-3 lg:grid-cols-4" onSubmit={calendar.createEvent}>
        <Field label="Event Title">
          <input className={inputClass} value={calendar.form.title} onChange={(event) => calendar.setForm({ ...calendar.form, title: event.target.value })} required />
        </Field>
        <Field label="Event Type">
          <select className={inputClass} value={calendar.form.event_type} onChange={(event) => calendar.setForm({ ...calendar.form, event_type: event.target.value as AuditionCalendarEventType })}>
            {calendarEventTypes.map((type) => <option key={type}>{type}</option>)}
          </select>
        </Field>
        <Field label="Starts">
          <input className={inputClass} type="datetime-local" value={calendar.form.start_datetime} onChange={(event) => calendar.setForm({ ...calendar.form, start_datetime: event.target.value })} required />
        </Field>
        <Field label="Ends">
          <input className={inputClass} type="datetime-local" value={calendar.form.end_datetime} onChange={(event) => calendar.setForm({ ...calendar.form, end_datetime: event.target.value })} />
        </Field>
        <Field label="Breakdown">
          <select className={inputClass} value={calendar.form.opportunity_id} onChange={(event) => calendar.setForm({ ...calendar.form, opportunity_id: event.target.value })}>
            <option value="">None</option>
            {opportunities.map((opportunity) => <option key={opportunity.id} value={opportunity.id}>{opportunity.role} · {opportunity.project}</option>)}
          </select>
        </Field>
        <Field label="Submission">
          <select className={inputClass} value={calendar.form.submission_id} onChange={(event) => calendar.setForm({ ...calendar.form, submission_id: event.target.value })}>
            <option value="">None</option>
            {submissions.map((submission) => <option key={submission.id} value={submission.id}>{submission.opportunity?.role ?? "Submission"} · {submission.current_status}</option>)}
          </select>
        </Field>
        <Field label="Location">
          <input className={inputClass} value={calendar.form.location} onChange={(event) => calendar.setForm({ ...calendar.form, location: event.target.value })} />
        </Field>
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input type="checkbox" checked={calendar.form.is_virtual} onChange={(event) => calendar.setForm({ ...calendar.form, is_virtual: event.target.checked })} />
          Virtual
        </label>
        <div className="lg:col-span-3">
          <Field label="Notes">
            <input className={inputClass} value={calendar.form.notes} onChange={(event) => calendar.setForm({ ...calendar.form, notes: event.target.value })} />
          </Field>
        </div>
        <div className="flex items-end"><Button type="submit" disabled={calendar.mutationPending}>{calendar.mutationPending ? "Saving..." : "Create Calendar Event"}</Button></div>
      </form>
    </Section>
  );
}

function UpcomingCalendarList({
  events,
  onRename,
  onDelete,
  pending
}: {
  events: AuditionCalendarEvent[];
  onRename: (eventId: string, title: string) => Promise<boolean>;
  onDelete: (eventId: string) => Promise<void>;
  pending: boolean;
}) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [title, setTitle] = useState("");

  function startEdit(event: AuditionCalendarEvent) {
    setEditingId(event.id);
    setTitle(event.title);
  }

  async function saveEdit(eventId: string) {
    if (!title.trim()) return;
    const saved = await onRename(eventId, title.trim());
    if (!saved) return;
    setEditingId(null);
    setTitle("");
  }

  return (
    <Section title="Upcoming Calendar Items">
      {events.length === 0 ? <EmptyState>No calendar events yet.</EmptyState> : (
        <div className="grid gap-3 lg:grid-cols-3">
          {events.slice(0, 9).map((event) => (
            <article id={`calendar-event-${event.id}`} key={event.id} className="rounded-md border border-slate-200 p-3 text-sm">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="font-semibold">{event.title}</h3>
                  <p className="text-slate-600">{event.event_type}</p>
                </div>
                <Badge>{event.is_virtual ? "Virtual" : "In Person"}</Badge>
              </div>
              <p className="mt-2">{formatCalendarDateTime(event.start_datetime)} {event.end_datetime ? `to ${formatCalendarDateTime(event.end_datetime)}` : ""}</p>
              {event.location && <p>{event.location}</p>}
              {event.notes && <p className="mt-2 text-slate-600">{event.notes}</p>}
              {calendarRecordOwnership(event).formEditable ? <p className="mt-2 text-xs text-slate-500">Calendar-owned · edit with form controls</p> : <p className="mt-2 text-xs text-slate-500">Read-only linked workflow event · edit in {calendarRecordOwnership(event).owner}</p>}
              {calendarRecordOwnership(event).formEditable && editingId === event.id && (
                <div className="mt-3 grid gap-2">
                  <Field label="Event Title">
                    <input className={inputClass} value={title} onChange={(inputEvent) => setTitle(inputEvent.target.value)} />
                  </Field>
                  <div className="flex gap-2">
                    <Button variant="secondary" disabled={pending} onClick={() => void saveEdit(event.id)}>Save</Button>
                    <Button variant="secondary" onClick={() => setEditingId(null)}>Cancel</Button>
                  </div>
                </div>
              )}
              {calendarRecordOwnership(event).formEditable && <div className="mt-3 flex gap-2">
                <Button variant="secondary" disabled={pending} onClick={() => startEdit(event)}>Edit Calendar Event</Button>
                <Button variant="danger" disabled={pending} onClick={() => void onDelete(event.id)}>Delete Calendar Event</Button>
              </div>}
            </article>
          ))}
        </div>
      )}
    </Section>
  );
}
