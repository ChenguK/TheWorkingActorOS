import { Badge, EmptyState } from "../../../components/ui";
import type { RelationshipAnalytics } from "../types";

export function RelationshipInsights({ relationshipAnalytics }: { relationshipAnalytics: RelationshipAnalytics | null }) {
  return (
    <div className="rounded-md border border-slate-200 p-3">
      <h3 className="font-semibold">Relationship Insights</h3>
      <p className="mt-2 text-sm text-slate-600">{relationshipAnalytics?.relationship_agent_explanation ?? "Track relationships to unlock outcome correlation signals."}</p>
      <div className="mt-3 grid gap-2 text-sm">
        {(relationshipAnalytics?.rows ?? []).slice(0, 5).map((row) => (
          <div key={row.relationship_id} className="rounded bg-slate-50 p-2">
            <p className="font-semibold">{row.name}</p>
            <p>{row.role_title}{row.company_office ? ` · ${row.company_office}` : ""}</p>
            <p>{row.submissions} linked submissions · {Math.round(row.callback_rate * 100)}% callback · {row.bookings} bookings</p>
            <Badge>{row.correlation_signal}</Badge>
          </div>
        ))}
        {(relationshipAnalytics?.rows.length ?? 0) === 0 && <EmptyState>No relationship analytics yet.</EmptyState>}
      </div>
    </div>
  );
}
