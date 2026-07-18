import { useMemo, useState, type FormEvent } from "react";
import type { EventClickArg } from "@fullcalendar/core";
import { errorMessage } from "../../../services/api/errors";
import type { ActorCalendarData } from "../types";
import { buildFullCalendarEvents, createBlankCalendarForm } from "../utils";
import {
  useCalendarEvents,
  useCreateCalendarEvent,
  useDeleteCalendarEvent,
  useUpdateCalendarEvent
} from "./useCalendarQueries";

const noCalendarEvents: NonNullable<ReturnType<typeof useCalendarEvents>["data"]> = [];

export function useActorCalendar({
  selfTapes,
  opportunities,
  callbackEvents,
  commandCenter
}: ActorCalendarData) {
  const [form, setForm] = useState(createBlankCalendarForm);
  const eventsQuery = useCalendarEvents();
  const createMutation = useCreateCalendarEvent();
  const updateMutation = useUpdateCalendarEvent();
  const deleteMutation = useDeleteCalendarEvent();
  const calendarEvents = eventsQuery.data ?? noCalendarEvents;

  const fullCalendarEvents = useMemo(
    () => buildFullCalendarEvents({ calendarEvents, selfTapes, opportunities, callbackEvents, commandCenter }),
    [calendarEvents, selfTapes, opportunities, callbackEvents, commandCenter]
  );

  async function createEvent(event: FormEvent) {
    event.preventDefault();
    try {
      await createMutation.mutateAsync({
        ...form,
        opportunity_id: form.opportunity_id || null,
        submission_id: form.submission_id || null,
        end_datetime: form.end_datetime || null,
        location: form.location || null,
        notes: form.notes || null
      });
      setForm(createBlankCalendarForm());
    } catch {
      // The mutation retains the standardized ApiError for presentation.
    }
  }

  function openRelated(eventClick: EventClickArg) {
    const ownership = eventClick.event.extendedProps.ownership as { sourceKind?: string; canonicalId?: string; formEditable?: boolean } | undefined;
    if (ownership?.sourceKind === "calendar" && ownership.formEditable && ownership.canonicalId) {
      document.getElementById(`calendar-event-${ownership.canonicalId}`)?.scrollIntoView({ block: "center" });
      return;
    }
    const opportunityId = eventClick.event.extendedProps.opportunityId as string | undefined;
    const submissionId = eventClick.event.extendedProps.submissionId as string | undefined;
    if (opportunityId) {
      window.open(`/auditions?breakdownId=${opportunityId}`, "_blank", "noopener,noreferrer");
      return;
    }
    if (submissionId) {
      window.open("/auditions", "_blank", "noopener,noreferrer");
    }
  }

  async function renameEvent(eventId: string, title: string) {
    try {
      await updateMutation.mutateAsync({ eventId, patch: { title } });
      return true;
    } catch {
      // The mutation retains the standardized ApiError for presentation.
      return false;
    }
  }

  async function removeEvent(eventId: string) {
    try {
      await deleteMutation.mutateAsync(eventId);
    } catch {
      // The mutation retains the standardized ApiError for presentation.
    }
  }

  return {
    form,
    setForm,
    calendarEvents,
    fullCalendarEvents,
    createEvent,
    openRelated,
    renameEvent,
    removeEvent,
    isLoading: eventsQuery.isLoading,
    isRefetching: eventsQuery.isRefetching,
    error: eventsQuery.error && !eventsQuery.data ? errorMessage(eventsQuery.error, "Could not load Calendar events.") : null,
    mutationError: createMutation.error ?? updateMutation.error ?? deleteMutation.error,
    mutationPending: createMutation.isPending || updateMutation.isPending || deleteMutation.isPending,
    refetch: eventsQuery.refetch
  };
}
