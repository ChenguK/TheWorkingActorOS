import { api } from "../../../services/api";
import type { AvailabilityBlock, AuditionCalendarEvent } from "../../../types/domain";
import type { AvailabilityCreatePayload, CalendarCreatePayload } from "../types";

export function listCalendarEvents() {
  return api.get<AuditionCalendarEvent[]>("/operations/calendar/events");
}

export function createCalendarEvent(payload: CalendarCreatePayload) {
  return api.post<AuditionCalendarEvent>("/operations/calendar/events", payload);
}

export function updateCalendarEvent(eventId: string, patch: Partial<CalendarCreatePayload>) {
  return api.patch<AuditionCalendarEvent>(`/operations/calendar/events/${eventId}`, patch);
}

export function deleteCalendarEvent(eventId: string) {
  return api.delete(`/operations/calendar/events/${eventId}`);
}

export function listAvailabilityBlocks() {
  return api.get<AvailabilityBlock[]>("/operations/availability");
}

export function createAvailabilityBlock(payload: AvailabilityCreatePayload) {
  return api.post<AvailabilityBlock>("/operations/availability", payload);
}

export function updateAvailabilityBlock(blockId: string, patch: Partial<AvailabilityCreatePayload>) {
  return api.patch<AvailabilityBlock>(`/operations/availability/${blockId}`, patch);
}

export function deleteAvailabilityBlock(blockId: string) {
  return api.delete(`/operations/availability/${blockId}`);
}
