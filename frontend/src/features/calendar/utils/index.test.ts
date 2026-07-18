import { describe, expect, it } from "vitest";
import { buildFullCalendarEvents, calendarRecordOwnership } from ".";
import type { AuditionCalendarEvent } from "../../../types/domain";

describe("Calendar timezone adapters", () => {
  it("preserves server offsets, DST boundaries, and all-day dates without conversion", () => {
    const event: AuditionCalendarEvent = {
      id: "dst-event",
      title: "DST callback",
      event_type: "Virtual Callback",
      start_datetime: "2026-11-01T01:30:00-04:00",
      end_datetime: "2026-11-01T02:30:00-05:00",
      is_virtual: true,
      created_at: "2026-07-16T00:00:00Z",
      updated_at: "2026-07-16T00:00:00Z"
    };
    const [adapted] = buildFullCalendarEvents({ calendarEvents: [event], selfTapes: [], opportunities: [], callbackEvents: [], commandCenter: null });
    expect(adapted.start).toBe(event.start_datetime);
    expect(adapted.end).toBe(event.end_datetime);
    expect(adapted.editable).toBe(false);
    expect(adapted.startEditable).toBe(false);
    expect(adapted.durationEditable).toBe(false);
  });

  it("preserves spring-forward, fall-back, local, and all-day source values", () => {
    const opportunity = {
      id: "opportunity-1", role: "Detective", project: "DST", audition_type: "Self-Tape",
      audition_deadline: "2026-03-08T01:30", callback_date: "2026-11-01T01:30:00-04:00",
      shoot_start_date: "2026-11-01", shoot_end_date: "2026-11-02"
    } as never;
    const events = buildFullCalendarEvents({ calendarEvents: [], selfTapes: [], opportunities: [opportunity], callbackEvents: [], commandCenter: null });
    expect(events.find((item) => item.id === "audition-due-opportunity-1")?.start).toBe("2026-03-08T01:30");
    expect(events.find((item) => item.id === "callback-opportunity-1")?.start).toBe("2026-11-01T01:30:00-04:00");
    expect(events.find((item) => item.id === "shoot-opportunity-1")).toMatchObject({ start: "2026-11-01", end: "2026-11-02", allDay: true });
  });

  it("classifies Calendar-owned and linked records conservatively", () => {
    expect(calendarRecordOwnership({ ...({} as AuditionCalendarEvent), id: "calendar-1" })).toMatchObject({ owner: "Calendar", canonicalId: "calendar-1", formEditable: true, dragEditable: false, resizeEditable: false, allDayConversion: false });
    expect(calendarRecordOwnership({ ...({} as AuditionCalendarEvent), id: "calendar-2", opportunity_id: "opportunity-1" })).toMatchObject({ owner: "Breakdowns", canonicalId: "opportunity-1", formEditable: false });
    expect(calendarRecordOwnership({ ...({} as AuditionCalendarEvent), id: "calendar-3", submission_id: "submission-1" })).toMatchObject({ owner: "Auditions", canonicalId: "submission-1", formEditable: false });
  });

  it("classifies every derived projection as read-only under its canonical owner", () => {
    const events = buildFullCalendarEvents({
      calendarEvents: [],
      selfTapes: [{ id: "tape-1", opportunity_id: "opportunity-1", tape_due_at: "2026-03-08T01:30" } as never],
      opportunities: [{ id: "opportunity-1", role: "Detective", project: "DST", audition_type: "Self-Tape", audition_deadline: "2026-03-08T01:30" } as never],
      callbackEvents: [{ id: "callback-1", event_name: "Producer", event_type: "Callback", event_datetime: "2026-11-01T01:30", opportunity_id: "opportunity-1" } as never],
      commandCenter: { platform_check_ins: [{ platform_subscription_id: "platform-1", check_date: "2026-11-01", platform_name: "Casting", checked_today: false, active: true, has_subscription: true }] } as never
    });
    const ownership = Object.fromEntries(events.map((event) => [event.id, event.extendedProps?.ownership]));
    expect(ownership["self-tape-tape-1"]).toMatchObject({ owner: "Auditions", sourceKind: "workflow-self-tape", formEditable: false });
    expect(ownership["audition-due-opportunity-1"]).toMatchObject({ owner: "Breakdowns", sourceKind: "opportunity", formEditable: false });
    expect(ownership["callback-event-callback-1"]).toMatchObject({ owner: "Auditions", sourceKind: "callback", formEditable: false });
    expect(ownership["platform-check-in-platform-1-2026-11-01"]).toMatchObject({ owner: "Chief of Staff", sourceKind: "chief-reminder", formEditable: false });
  });
});
