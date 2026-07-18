import { EmptyState, Section } from "../../../components/ui";
import type { IntelligenceDashboard, SystemCapabilities } from "../types";
import { formatRate } from "../utils";
import { DataSufficiencyNotice } from "./DataSufficiencyNotice";

export function ArchetypePerformancePanel({
  dashboard,
  capabilities
}: {
  dashboard: IntelligenceDashboard | null;
  capabilities?: SystemCapabilities | null;
}) {
  const state = capabilities?.states.archetype_performance;
  const rows = dashboard?.archetype_performance.metrics ?? [];
  return (
    <Section title="Archetype Performance">
      {state && state.state !== "Configured" ? (
        <DataSufficiencyNotice state={state.state} message={state.explanation} />
      ) : rows.length === 0 ? (
        <EmptyState>Add Data First. Track more submissions to unlock this insight.</EmptyState>
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {rows.slice(0, 9).map((row) => (
            <article key={row.archetype} className="rounded-md border border-slate-200 p-3 text-sm">
              <h3 className="font-semibold">{row.archetype}</h3>
              <p className="mt-2">{row.submissions} submissions · {formatRate(row.callback_rate)} callback · {formatRate(row.booking_rate)} booking</p>
              <p className="mt-1 text-slate-600">Booked {row.booked} · Pinned {row.pinned} · Passed {row.passed} · No response {row.no_response}</p>
            </article>
          ))}
        </div>
      )}
    </Section>
  );
}

