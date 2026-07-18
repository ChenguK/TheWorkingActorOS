import { ActorCalendar } from "@/features/calendar";
import { useActorProfile } from "@/features/profile";
import { useBreakdowns } from "@/features/breakdowns";
import { useCallbackEvents, useSubmissions, useWorkflowSelfTapes } from "@/features/auditions";
import { useCommandCenter } from "@/features/chief-of-staff";

export function CalendarPage() {
  const actor = useActorProfile();
  const opportunities = useBreakdowns();
  const submissions = useSubmissions();
  const selfTapes = useWorkflowSelfTapes();
  const callbacks = useCallbackEvents();
  const commandCenter = useCommandCenter();
  return (
    <>
      {commandCenter.isLoading && <p className="mb-2 text-sm text-slate-600" role="status">Loading operational reminders...</p>}
      {commandCenter.isError && <p className="mb-2 rounded bg-red-50 p-2 text-sm text-red-700" role="alert">Operational reminders could not load. Calendar events remain available.</p>}
      <ActorCalendar
        actor={actor.data ?? null}
        selfTapes={selfTapes.data ?? []}
        opportunities={opportunities.data ?? []}
        callbackEvents={callbacks.data ?? []}
        submissions={submissions.data ?? []}
        commandCenter={commandCenter.data ?? null}
      />
    </>
  );
}
