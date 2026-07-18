import { Link } from "react-router-dom";
import { Badge } from "../../../components/ui";
import type { ChiefOfStaffPriority, SinceLastVisitSummary } from "../types";
import { getPlatformCheckInRecommendationText } from "../utils";
import type { ChiefOfStaffCompactInput } from "../types";

export function TopPrioritiesWidget({ priorities }: { priorities: ChiefOfStaffPriority[] }) {
  if (priorities.length === 0) {
    return <ChiefOfStaffWidgetBody metric={0} items={[]} empty="The Chief of Staff will surface today’s top priorities after more career signals are available." />;
  }
  return (
    <div className="grid gap-3">
      {priorities.slice(0, 3).map((priority) => (
        <Link key={`${priority.rank}-${priority.title}`} to={priority.target_path} className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm transition hover:border-accent">
          <div className="flex items-start justify-between gap-2">
            <p className="font-semibold text-ink">{priority.rank}. {priority.title}</p>
            <Badge>{priority.category}</Badge>
          </div>
          <p className="mt-1 text-slate-600">{priority.reason}</p>
          <p className="mt-2 text-xs font-semibold text-accent">{priority.action_label}</p>
        </Link>
      ))}
    </div>
  );
}

export function SinceLastVisitWidget({ changes }: { changes: SinceLastVisitSummary[] }) {
  return (
    <ChiefOfStaffWidgetBody
      metric={changes.length}
      items={changes.slice(0, 4).map((item) => String(item.message ?? "Meaningful update"))}
      empty="No meaningful changes since your last dashboard visit."
    />
  );
}

export function ChiefOfStaffDashboardSummary({ data }: { data: ChiefOfStaffCompactInput }) {
  const checkInRecommendation = getPlatformCheckInRecommendationText(data);
  return (
    <div className="grid gap-3">
      <TopPrioritiesWidget priorities={data.commandCenter?.chief_of_staff_priorities ?? data.commandCenter?.executive_priorities ?? []} />
      <SinceLastVisitWidget changes={data.commandCenter?.since_last_visit ?? []} />
      {checkInRecommendation && (
        <p className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
          {checkInRecommendation} Manual check-in only; this app does not log in, scrape, or submit.
        </p>
      )}
    </div>
  );
}

function ChiefOfStaffWidgetBody({ metric, items, empty }: { metric: number; items: string[]; empty: string }) {
  return (
    <div className="flex flex-1 flex-col">
      <div className="flex items-center justify-between gap-2">
        <p className="text-3xl font-bold text-ink">{metric}</p>
        {metric > 0 && <Badge>Active</Badge>}
      </div>
      <div className="mt-3 grid gap-2 text-sm text-slate-700">
        {items.length === 0 ? (
          <p className="text-slate-500">{empty}</p>
        ) : (
          items.map((item, index) => (
            <p key={`${item}-${index}`} className="rounded bg-slate-50 px-2 py-1">{item}</p>
          ))
        )}
      </div>
    </div>
  );
}
