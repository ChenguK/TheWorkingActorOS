import type { EventInput } from "@fullcalendar/core";
import type { AuditionCalendarEvent } from "../../../types/domain";
import { colorForCalendarEvent } from "../constants";
import type { ActorCalendarData, CalendarEventOwnership, CalendarFormState } from "../types";

export function calendarRecordOwnership(event: AuditionCalendarEvent): CalendarEventOwnership {
  if (event.submission_id) {
    return { owner: "Auditions", sourceKind: "linked-calendar", canonicalId: event.submission_id, formEditable: false, dragEditable: false, resizeEditable: false, allDayConversion: false, description: "Read-only linked Auditions event. Edit its source in Auditions." };
  }
  if (event.opportunity_id) {
    return { owner: "Breakdowns", sourceKind: "linked-calendar", canonicalId: event.opportunity_id, formEditable: false, dragEditable: false, resizeEditable: false, allDayConversion: false, description: "Read-only linked Breakdown event. Edit its source in Breakdowns." };
  }
  return { owner: "Calendar", sourceKind: "calendar", canonicalId: event.id, formEditable: true, dragEditable: false, resizeEditable: false, allDayConversion: false, description: "Calendar-owned event. Edit with the form below; drag and resize are intentionally unavailable." };
}

function readOnlyOwnership(owner: CalendarEventOwnership["owner"], sourceKind: CalendarEventOwnership["sourceKind"], canonicalId: string, description: string): CalendarEventOwnership {
  return { owner, sourceKind, canonicalId, formEditable: false, dragEditable: false, resizeEditable: false, allDayConversion: false, description };
}

function eventWithOwnership(event: EventInput & { id: string }, ownership: CalendarEventOwnership): EventInput & { id: string } {
  return {
    ...event,
    editable: false,
    startEditable: false,
    durationEditable: false,
    classNames: [ownership.formEditable ? "calendar-event-form-editable" : "calendar-event-read-only"],
    extendedProps: { ...event.extendedProps, ownership }
  };
}

export function createBlankCalendarForm(): CalendarFormState {
  return {
    title: "",
    event_type: "Self-Tape Due",
    opportunity_id: "",
    submission_id: "",
    start_datetime: "",
    end_datetime: "",
    location: "",
    is_virtual: false,
    notes: ""
  };
}

export function formatCalendarDateTime(value?: string | null): string {
  if (!value) return "Not scheduled";
  return new Date(value).toLocaleString();
}

export function buildFullCalendarEvents({
  calendarEvents,
  selfTapes,
  opportunities,
  callbackEvents,
  commandCenter
}: Pick<ActorCalendarData, "selfTapes" | "opportunities" | "callbackEvents" | "commandCenter"> & {
  calendarEvents: AuditionCalendarEvent[];
}): EventInput[] {
  const events: EventInput[] = [];
  const seen = new Set<string>();

  function addEvent(event: EventInput & { id: string }) {
    const key = `${event.id}-${event.start ?? ""}`;
    if (seen.has(key) || !event.start) return;
    seen.add(key);
    events.push(event);
  }

  calendarEvents.forEach((event) => {
    addEvent(eventWithOwnership({
      id: `calendar-${event.id}`,
      title: event.title,
      start: event.start_datetime,
      end: event.end_datetime ?? undefined,
      backgroundColor: colorForCalendarEvent(event.event_type),
      borderColor: colorForCalendarEvent(event.event_type),
      extendedProps: {
        kind: event.event_type,
        opportunityId: event.opportunity_id,
        submissionId: event.submission_id,
        location: event.location,
        notes: event.notes
      }
    }, calendarRecordOwnership(event)));
  });

  selfTapes.forEach((workflow) => {
    const opportunity = opportunities.find((item) => item.id === workflow.opportunity_id);
    if (!workflow.tape_due_at) return;
    addEvent(eventWithOwnership({
      id: `self-tape-${workflow.id}`,
      title: `${opportunity?.role ?? "Self-tape"} due`,
      start: workflow.tape_due_at,
      backgroundColor: "#2563eb",
      borderColor: "#2563eb",
      extendedProps: {
        kind: "Self-Tape Due",
        opportunityId: workflow.opportunity_id,
        submissionId: workflow.submission_id,
        notes: workflow.slate_requirements
      }
    }, readOnlyOwnership("Auditions", "workflow-self-tape", workflow.id, "Read-only self-tape deadline. Edit it in Auditions.")));
  });

  opportunities.forEach((opportunity) => {
    const title = `${opportunity.role} · ${opportunity.project}`;
    if (opportunity.audition_deadline) {
      const eventType = opportunity.audition_type === "Virtual" ? "Virtual Callback" : opportunity.audition_type === "In-Person" ? "In-Person Callback" : "Self-Tape Due";
      addEvent(eventWithOwnership({
        id: `audition-due-${opportunity.id}`,
        title: `${opportunity.audition_type === "Self-Tape" ? "Tape" : "Audition"} due: ${title}`,
        start: opportunity.audition_deadline,
        backgroundColor: colorForCalendarEvent(eventType),
        borderColor: colorForCalendarEvent(eventType),
        extendedProps: { kind: opportunity.audition_type, opportunityId: opportunity.id }
      }, readOnlyOwnership("Breakdowns", "opportunity", opportunity.id, "Read-only audition deadline. Edit it in Breakdowns.")));
    }
    if (opportunity.callback_date) {
      addEvent(eventWithOwnership({
        id: `callback-${opportunity.id}`,
        title: `Callback: ${title}`,
        start: opportunity.callback_date,
        backgroundColor: "#7c3aed",
        borderColor: "#7c3aed",
        extendedProps: { kind: "Callback", opportunityId: opportunity.id }
      }, readOnlyOwnership("Breakdowns", "opportunity", opportunity.id, "Read-only callback date. Edit it in Breakdowns.")));
    }
    if (opportunity.shoot_start_date) {
      addEvent(eventWithOwnership({
        id: `shoot-${opportunity.id}`,
        title: `${opportunity.project_type === "Theater" ? "Performance" : "Shoot"}: ${title}`,
        start: opportunity.shoot_start_date,
        end: opportunity.shoot_end_date ?? undefined,
        allDay: true,
        backgroundColor: "#0f766e",
        borderColor: "#0f766e",
        extendedProps: { kind: "Shoot / Performance", opportunityId: opportunity.id }
      }, readOnlyOwnership("Breakdowns", "opportunity", opportunity.id, "Read-only shoot or performance dates. Edit them in Breakdowns.")));
    }
  });

  callbackEvents.forEach((callback) => {
    if (!callback.event_datetime) return;
    const opportunity = callback.opportunity_id ? opportunities.find((item) => item.id === callback.opportunity_id) : null;
    addEvent(eventWithOwnership({
      id: `callback-event-${callback.id}`,
      title: `${callback.event_name}: ${opportunity?.role ?? "Callback"}`,
      start: callback.event_datetime,
      backgroundColor: "#7c3aed",
      borderColor: "#7c3aed",
      extendedProps: {
        kind: callback.event_type,
        opportunityId: callback.opportunity_id,
        submissionId: callback.submission_id,
        location: callback.location,
        notes: callback.preparation_notes
      }
    }, readOnlyOwnership("Auditions", "callback", callback.id, "Read-only callback event. Edit it in Auditions.")));
  });

  const platformCheckIns = commandCenter?.platform_check_ins?.filter((item) => item.active && item.has_subscription) ?? [];
  platformCheckIns.forEach((checkIn) => {
    addEvent(eventWithOwnership({
      id: `platform-check-in-${checkIn.platform_subscription_id}-${checkIn.check_date}`,
      title: `${checkIn.checked_today ? "Checked" : "Check"} ${checkIn.platform_name}`,
      start: checkIn.check_date,
      allDay: true,
      backgroundColor: checkIn.checked_today ? "#64748b" : "#f59e0b",
      borderColor: checkIn.checked_today ? "#64748b" : "#f59e0b",
      extendedProps: { kind: "Platform Check-In" }
    }, readOnlyOwnership("Chief of Staff", "chief-reminder", `${checkIn.platform_subscription_id}-${checkIn.check_date}`, "Read-only platform reminder. Update it through Chief of Staff.")));
  });

  return events;
}
