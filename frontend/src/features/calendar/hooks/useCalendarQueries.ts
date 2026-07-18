import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { invalidateInBackground, publicInvalidationKeys } from "../../../services/api/invalidationContracts";
import { queryKeys } from "../../../services/api/queryKeys";
import { queryStaleTimes } from "../../../services/api/queryPolicy";
import {
  createAvailabilityBlock,
  createCalendarEvent,
  deleteAvailabilityBlock,
  deleteCalendarEvent,
  listAvailabilityBlocks,
  listCalendarEvents,
  updateAvailabilityBlock,
  updateCalendarEvent
} from "../api";
import type { AvailabilityCreatePayload, CalendarCreatePayload } from "../types";

export const calendarEventListKey = queryKeys.calendar.list({ resource: "events" });
export const availabilityListKey = queryKeys.calendar.list({ resource: "availability" });

export function useCalendarEvents() {
  return useQuery({
    queryKey: calendarEventListKey,
    queryFn: listCalendarEvents,
    staleTime: queryStaleTimes.live,
    refetchOnMount: "always"
  });
}

export function useAvailabilityBlocks() {
  return useQuery({
    queryKey: availabilityListKey,
    queryFn: listAvailabilityBlocks,
    staleTime: queryStaleTimes.workflow,
    refetchOnMount: "always"
  });
}

function useCalendarInvalidation(queryKey: readonly unknown[]) {
  const queryClient = useQueryClient();
  return () => invalidateInBackground(
    queryClient,
    queryKey === calendarEventListKey ? [queryKey, publicInvalidationKeys.analyticsOperations] : [queryKey]
  );
}

export function useCreateCalendarEvent() {
  const invalidate = useCalendarInvalidation(calendarEventListKey);
  return useMutation({ mutationFn: (payload: CalendarCreatePayload) => createCalendarEvent(payload), onSuccess: invalidate });
}

export function useUpdateCalendarEvent() {
  const invalidate = useCalendarInvalidation(calendarEventListKey);
  return useMutation({
    mutationFn: ({ eventId, patch }: { eventId: string; patch: Partial<CalendarCreatePayload> }) =>
      updateCalendarEvent(eventId, patch),
    onSuccess: invalidate
  });
}

export function useDeleteCalendarEvent() {
  const invalidate = useCalendarInvalidation(calendarEventListKey);
  return useMutation({ mutationFn: (eventId: string) => deleteCalendarEvent(eventId), onSuccess: invalidate });
}

export function useCreateAvailabilityBlock() {
  const invalidate = useCalendarInvalidation(availabilityListKey);
  return useMutation({ mutationFn: (payload: AvailabilityCreatePayload) => createAvailabilityBlock(payload), onSuccess: invalidate });
}

export function useUpdateAvailabilityBlock() {
  const invalidate = useCalendarInvalidation(availabilityListKey);
  return useMutation({
    mutationFn: ({ blockId, patch }: { blockId: string; patch: Partial<AvailabilityCreatePayload> }) =>
      updateAvailabilityBlock(blockId, patch),
    onSuccess: invalidate
  });
}

export function useDeleteAvailabilityBlock() {
  const invalidate = useCalendarInvalidation(availabilityListKey);
  return useMutation({ mutationFn: (blockId: string) => deleteAvailabilityBlock(blockId), onSuccess: invalidate });
}
