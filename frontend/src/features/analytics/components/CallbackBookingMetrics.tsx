import { EmptyState, Section } from "../../../components/ui";
import type { Submission } from "../../../types/domain";
import { calculateCallbackBookingMetrics, formatRate } from "../utils";

export function CallbackBookingMetrics({ submissions }: { submissions: Submission[] }) {
  const metrics = calculateCallbackBookingMetrics(submissions);
  return (
    <Section title="Callback and Booking Rates">
      {submissions.length === 0 ? (
        <EmptyState>Callback and booking rates will appear after submissions are tracked.</EmptyState>
      ) : (
        <div className="grid gap-3 md:grid-cols-4">
          <MetricCard title="Submissions" value={String(metrics.submissions)} />
          <MetricCard title="Callbacks or Better" value={String(metrics.callbacks)} />
          <MetricCard title="Callback Rate" value={formatRate(metrics.callbackRate)} />
          <MetricCard title="Booking Rate" value={formatRate(metrics.bookingRate)} />
        </div>
      )}
    </Section>
  );
}

function MetricCard({ title, value }: { title: string; value: string }) {
  return (
    <div className="rounded-md border border-slate-200 bg-white p-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</p>
      <p className="mt-1 text-2xl font-semibold text-ink">{value}</p>
    </div>
  );
}
