import { Gauge } from "lucide-react";
import { EmptyState, Section } from "../../../components/ui";
import type { CastingPatternDashboard, CastingPatternInsight, SystemCapabilities } from "../types";
import { DataSufficiencyNotice } from "./DataSufficiencyNotice";

export function CastingPatternsPanel({
  trends,
  capabilities
}: {
  trends: CastingPatternDashboard | null;
  capabilities?: SystemCapabilities | null;
}) {
  const trendState = capabilities?.states.industry_trend_analysis;
  return (
    <Section title="Your Casting Patterns" actions={<Gauge className="h-5 w-5 text-slate-500" />}>
      {trendState && trendState.state !== "Configured" ? (
        <DataSufficiencyNotice state={trendState.state} message={trendState.explanation} />
      ) : !trends ? (
        <EmptyState>Your tracked breakdowns, auditions, submissions, callbacks, bookings, and materials will generate casting pattern insights.</EmptyState>
      ) : (
        <div className="grid gap-3 lg:grid-cols-3">
          <div className="rounded-md border border-slate-200 p-3 text-sm">
            <h3 className="font-semibold">{trends.pattern_stage || "Early Signals"}</h3>
            <p className="mt-2 text-slate-600">{trends.unlock_message}</p>
            {(trends.insights ?? []).slice(0, 4).map((insight) => (
              <p key={insight} className="mt-2 rounded bg-slate-50 p-2">{insight}</p>
            ))}
          </div>
          <TrendList title="Archetypes" items={trends.archetype ?? []} />
          <TrendList title="Role Types" items={trends.role_type ?? []} />
          <TrendList title="Project Types" items={trends.project_type ?? []} />
          <TrendList title="Audition Types" items={trends.audition_type ?? []} />
          <TrendList title="Sources" items={trends.submission_source ?? []} />
          <TrendList title="Callback Signals" items={trends.callback_archetype ?? []} />
        </div>
      )}
    </Section>
  );
}

function TrendList({ title, items }: { title: string; items: CastingPatternInsight[] }) {
  return (
    <div>
      <p className="font-semibold">{title}</p>
      <div className="mt-1 grid gap-1">
        {items.slice(0, 4).map((item) => (
          <p key={`${item.trend_type}-${item.label}`} className="rounded bg-slate-50 p-2">
            {item.label}: {item.count}
            {item.recommended_action ? <span className="block text-slate-600">{item.recommended_action}</span> : null}
          </p>
        ))}
        {items.length === 0 && <p className="rounded bg-slate-50 p-2 text-slate-500">No signal yet.</p>}
      </div>
    </div>
  );
}

