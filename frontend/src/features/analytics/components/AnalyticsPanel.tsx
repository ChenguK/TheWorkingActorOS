import type { ReactNode } from "react";
import { errorMessage } from "../../../services/api/errors";
import type { Submission, SystemCapabilities } from "../../../types/domain";
import { useIndustryTrends, useIntelligenceDashboard, useMaterialPerformance, useOperationsDashboard } from "../hooks/useAnalyticsQueries";
import { ArchetypePerformancePanel } from "./ArchetypePerformancePanel";
import { CallbackBookingMetrics } from "./CallbackBookingMetrics";
import { CastingOfficePerformancePanel } from "./CastingOfficePerformancePanel";
import { CastingPatternsPanel } from "./CastingPatternsPanel";
import { CostAnalyticsPanel } from "./CostAnalyticsPanel";
import { MaterialPerformancePanel } from "./MaterialPerformancePanel";

export function AnalyticsPanel({ submissions, capabilities }: { submissions: Submission[]; capabilities: SystemCapabilities | null }) {
  const operations = useOperationsDashboard();
  const intelligence = useIntelligenceDashboard();
  const trends = useIndustryTrends();
  const materials = useMaterialPerformance();
  const refreshing = [operations, intelligence, trends, materials].some((query) => query.isRefetching && !query.isLoading);

  return (
    <div className="grid gap-4">
      {refreshing && <p className="text-xs text-slate-500">Refreshing analytics…</p>}
      <AnalyticsSection label="cost analytics" query={operations}><CostAnalyticsPanel dashboard={operations.data ?? null} /></AnalyticsSection>
      <CallbackBookingMetrics submissions={submissions} />
      <AnalyticsSection label="casting patterns" query={trends}><CastingPatternsPanel trends={trends.data ?? null} capabilities={capabilities} /></AnalyticsSection>
      <AnalyticsSection label="material performance" query={materials}><MaterialPerformancePanel rows={materials.data ?? []} capabilities={capabilities} /></AnalyticsSection>
      <AnalyticsSection label="archetype performance" query={intelligence}><ArchetypePerformancePanel dashboard={intelligence.data ?? null} capabilities={capabilities} /></AnalyticsSection>
      <AnalyticsSection label="casting office performance" query={intelligence}><CastingOfficePerformancePanel dashboard={intelligence.data ?? null} capabilities={capabilities} /></AnalyticsSection>
    </div>
  );
}

function AnalyticsSection({ label, query, children }: { label: string; query: { isLoading: boolean; error: unknown; data?: unknown }; children: ReactNode }) {
  if (query.isLoading) return <section className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-600 shadow-sm">Loading {label}…</section>;
  if (query.error && !query.data) return <section className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">{errorMessage(query.error, `Could not load ${label}.`)}</section>;
  return children;
}
