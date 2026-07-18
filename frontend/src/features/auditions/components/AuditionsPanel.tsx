import type { ActorProfile, Opportunity } from "../types";
import type { MaterialOption } from "../../materials";
import { useAuditionPerformanceNotes, useCallbackEvents, useSubmissions, useWorkflowSelfTapes } from "../hooks/useAuditionQueries";
import { AuditionNotesPanel } from "./AuditionNotesPanel";
import { CallbackEventsPanel } from "./CallbackEventsPanel";
import { SubmissionTracker } from "./SubmissionTracker";

export function AuditionsPanel({
  actor,
  opportunities,
  assets
}: {
  actor: ActorProfile | null;
  opportunities: Opportunity[];
  assets: MaterialOption[];
}) {
  const submissions = useSubmissions();
  const selfTapes = useWorkflowSelfTapes();
  const callbackEvents = useCallbackEvents();
  const journalEntries = useAuditionPerformanceNotes();
  const queries = [["submissions", submissions], ["self-tapes", selfTapes], ["callbacks", callbackEvents], ["audition notes", journalEntries]] as const;
  return (
    <div className="grid gap-4">
      {queries.some(([, query]) => query.isLoading) && <p className="text-sm text-slate-600" role="status">Loading auditions...</p>}
      {queries.filter(([, query]) => query.isError).map(([label]) => <p key={label} className="rounded bg-red-50 p-2 text-sm text-red-700" role="alert">Audition {label} could not load. Other sections remain usable.</p>)}
      <SubmissionTracker
        actor={actor}
        opportunities={opportunities}
        assets={assets}
        submissions={submissions.data ?? []}
        selfTapes={selfTapes.data ?? []}
      />
      <CallbackEventsPanel
        callbackEvents={callbackEvents.data ?? []}
        opportunities={opportunities}
        submissions={submissions.data ?? []}
      />
      <AuditionNotesPanel
        journalEntries={journalEntries.data ?? []}
        opportunities={opportunities}
        submissions={submissions.data ?? []}
      />
    </div>
  );
}
