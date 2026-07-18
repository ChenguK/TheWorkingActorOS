import { EmptyState, Section } from "../../../components/ui";
import type { OperationsDashboard } from "../types";
import { formatCurrency } from "../utils";

export function CostAnalyticsPanel({ dashboard }: { dashboard: OperationsDashboard | null }) {
  const costDashboard = dashboard?.cost_dashboard;
  if (!costDashboard) {
    return (
      <Section title="Cost Analytics">
        <EmptyState>Cost analytics will appear after costs or platform subscriptions are tracked.</EmptyState>
      </Section>
    );
  }
  return (
    <Section title="Cost Analytics">
      <div className="grid gap-4">
        <div className="grid gap-3 md:grid-cols-4">
          <CostMetric title="Total Spent" value={formatCurrency(costDashboard.total_spent)} />
          <CostMetric title="Cost Per Callback" value={formatCurrency(costDashboard.cost_per_callback)} />
          <CostMetric title="Cost Per Booking" value={formatCurrency(costDashboard.cost_per_booking)} />
          <CostMetric title="Monthly Subscriptions" value={formatCurrency(costDashboard.estimated_monthly_subscription_spend)} />
        </div>
        <div className="grid gap-3 lg:grid-cols-3">
          <CostList title="Subscriptions" rows={costDashboard.subscriptions} suffix="/mo estimated" />
          <div className="rounded-md border border-slate-200 p-3 text-sm">
            <h3 className="font-semibold">Spend Categories</h3>
            <p className="mt-2">Submission fees: {formatCurrency(costDashboard.submission_fees_total)}</p>
            <p>Media fees: {formatCurrency(costDashboard.media_fees_total)}</p>
            <p>Travel / housing: {formatCurrency(costDashboard.travel_housing_total)}</p>
            <p>Other: {formatCurrency(costDashboard.other_costs_total)}</p>
          </div>
          <CostList title="By Platform" rows={costDashboard.costs_by_platform} />
          <CostList title="By Archetype" rows={costDashboard.costs_by_archetype} />
        </div>
      </div>
    </Section>
  );
}

function CostMetric({ title, value }: { title: string; value: string }) {
  return (
    <div className="rounded-md border border-slate-200 bg-white p-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</p>
      <p className="mt-1 text-2xl font-semibold text-ink">{value}</p>
    </div>
  );
}

function CostList({ title, rows, suffix = "" }: { title: string; rows: Record<string, number>; suffix?: string }) {
  const entries = Object.entries(rows);
  return (
    <div className="rounded-md border border-slate-200 p-3 text-sm">
      <h3 className="font-semibold">{title}</h3>
      {entries.length === 0 ? <p className="mt-2 text-slate-500">No tracked costs yet.</p> : entries.slice(0, 8).map(([key, value]) => (
        <p key={key} className="mt-2">{key}: {formatCurrency(value)}{suffix}</p>
      ))}
    </div>
  );
}

