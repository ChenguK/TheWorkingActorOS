import { Badge, EmptyState, Section } from "../../../components/ui";
import type { MaterialPerformance, SystemCapabilities } from "../types";
import { formatRate } from "../utils";
import { DataSufficiencyNotice } from "./DataSufficiencyNotice";

export function MaterialPerformancePanel({ rows, capabilities }: { rows: MaterialPerformance[]; capabilities?: SystemCapabilities | null }) {
  const state = capabilities?.states.material_performance_analytics;
  return (
    <Section title="Material Performance">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {state && state.state !== "Configured" ? (
          <div className="md:col-span-2 xl:col-span-4">
            <DataSufficiencyNotice state={state.state} message={state.explanation} />
          </div>
        ) : rows.length === 0 ? <EmptyState>Insufficient Data. Track more submissions to unlock this insight.</EmptyState> : rows.map((row) => (
          <article key={row.asset_id} className="rounded-md border border-slate-200 p-3 text-sm">
            <div className="flex items-start justify-between gap-2">
              <div>
                <h3 className="font-semibold">{row.asset_name}</h3>
                <p className="text-slate-600">{row.asset_type}</p>
              </div>
              <Badge>{formatRate(row.callback_rate)} callback</Badge>
            </div>
            <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
              <div><dt className="text-slate-500">Recommended</dt><dd className="font-semibold">{row.times_recommended}</dd></div>
              <div><dt className="text-slate-500">Selected</dt><dd className="font-semibold">{row.times_selected}</dd></div>
              <div><dt className="text-slate-500">Submissions</dt><dd className="font-semibold">{row.submissions}</dd></div>
              <div><dt className="text-slate-500">Bookings</dt><dd className="font-semibold">{row.bookings} · {formatRate(row.booking_rate)}</dd></div>
            </dl>
          </article>
        ))}
      </div>
    </Section>
  );
}

