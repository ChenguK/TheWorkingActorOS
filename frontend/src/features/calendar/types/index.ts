import type { EventInput } from "@fullcalendar/core";
import type {
  ActorCommandCenter,
  ActorProfile,
  AuditionCalendarEvent,
  AuditionCalendarEventType,
  CallbackEvent,
  Opportunity,
  SelfTapeWorkflow,
  Submission
} from "../../../types/domain";

export type CalendarEvent = AuditionCalendarEvent;
export type CalendarEventType = AuditionCalendarEventType;
export type FullCalendarActorEvent = EventInput;

export type CalendarEventOwner = "Calendar" | "Auditions" | "Breakdowns" | "Chief of Staff";

export type CalendarEventOwnership = {
  owner: CalendarEventOwner;
  sourceKind: "calendar" | "linked-calendar" | "workflow-self-tape" | "opportunity" | "callback" | "chief-reminder";
  canonicalId: string;
  formEditable: boolean;
  dragEditable: false;
  resizeEditable: false;
  allDayConversion: false;
  description: string;
};

export type CalendarCreatePayload = {
  title: string;
  event_type: string;
  opportunity_id?: string | null;
  submission_id?: string | null;
  start_datetime: string;
  end_datetime?: string | null;
  location?: string | null;
  is_virtual: boolean;
  notes?: string | null;
};

export type CalendarFormState = {
  title: string;
  event_type: AuditionCalendarEventType;
  opportunity_id: string;
  submission_id: string;
  start_datetime: string;
  end_datetime: string;
  location: string;
  is_virtual: boolean;
  notes: string;
};

export type AvailabilityCreatePayload = {
  actor_profile_id: string;
  title: string;
  block_type: string;
  start_date: string;
  end_date: string;
  notes?: string | null;
};

export type ActorCalendarData = {
  actor: ActorProfile | null;
  selfTapes: SelfTapeWorkflow[];
  opportunities: Opportunity[];
  callbackEvents: CallbackEvent[];
  submissions: Submission[];
  commandCenter: ActorCommandCenter | null;
};
