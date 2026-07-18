import { EmptyState, Section } from "../../../components/ui";
import type { IntelligenceDashboard, SystemCapabilities } from "../types";
import { formatRate } from "../utils";
import { DataSufficiencyNotice } from "./DataSufficiencyNotice";

export function CastingOfficePerformancePanel({
  dashboard,
  capabilities
}: {
  dashboard: IntelligenceDashboard | null;
  capabilities?: SystemCapabilities | null;
}) {
  const state = capabilities?.states.casting_office_intelligence;
  const rows = dashboard?.casting_office_analytics ?? [];
  return (
    <Section title="Casting Office Performance">
      {state && state.state !== "Configured" ? (
        <DataSufficiencyNotice state={state.state} message={state.explanation} />
      ) : rows.length === 0 ? (
        <EmptyState>Add Data First. Link at least 3 submissions to a casting office to unlock this insight.</EmptyState>
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {rows.slice(0, 9).map((office) => (
            <article key={office.casting_office_id ?? office.casting_office} className="rounded-md border border-slate-200 p-3 text-sm">
              <h3 className="font-semibold">{office.casting_office}</h3>
              <p className="mt-2">{office.submissions} submissions · {formatRate(office.callback_rate)} callback · {formatRate(office.booking_rate)} booking</p>
              <p className="mt-1 text-slate-600">Best materials: {office.best_materials.join(", ") || "Not enough data"}</p>
              <p className="mt-1 text-slate-600">Stretch signal: {office.stretch_response_signal}</p>
            </article>
          ))}
        </div>
      )}
    </Section>
  );
}

