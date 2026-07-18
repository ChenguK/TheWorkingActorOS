import { useMemo } from "react";
import { Badge, Button, EmptyState } from "../../../components/ui";
import { useSubmissionQueueActions } from "../hooks/useBreakdownDiscovery";
import type { AgentRecommendation, Opportunity, SubmissionAutomationQueueItem } from "../types";
import { OpportunityLink } from "./BreakdownDetails";

type SubmissionQueuePanelProps = {
  recommendations: AgentRecommendation[];
  queueItems: SubmissionAutomationQueueItem[];
  opportunities: Opportunity[];
  hiddenOpportunities: Opportunity[];
};

export function SubmissionQueuePanel({
  recommendations,
  queueItems,
  opportunities,
  hiddenOpportunities
}: SubmissionQueuePanelProps) {
  const submissionQueue = useSubmissionQueueActions();
  const opportunityById = useMemo(
    () => Object.fromEntries([...opportunities, ...hiddenOpportunities].map((item) => [item.id, item])),
    [opportunities, hiddenOpportunities]
  );

  return (
    <>
      <div className="rounded-md border border-slate-200 p-3">
        <h3 className="font-semibold">Queue From Recommendation</h3>
        <p className="mt-1 text-sm text-slate-600">Prepare submissions. Nothing executes until approved.</p>
        <div className="mt-3 grid gap-2">
          {recommendations.length === 0 ? (
            <p className="text-sm text-slate-500">No recommendations to queue.</p>
          ) : (
            recommendations.slice(0, 6).map((recommendation) => {
              const opportunity = opportunityById[recommendation.opportunity_id];
              return (
                <div key={recommendation.id} className="rounded border border-slate-200 p-2 text-sm">
                  <p className="font-semibold">
                    {opportunity ? <OpportunityLink opportunity={opportunity} /> : "Breakdown"} · {recommendation.match_type}
                  </p>
                  <Button
                    variant="secondary"
                    disabled={submissionQueue.pendingAction === `queue:${recommendation.id}`}
                    onClick={() => void submissionQueue.queueRecommendation(recommendation.id)}
                  >
                    Queue
                  </Button>
                </div>
              );
            })
          )}
        </div>
      </div>

      {submissionQueue.error && <p role="alert" className="col-span-full mt-4 rounded bg-red-50 p-2 text-sm text-red-700">{submissionQueue.error}</p>}
      <div className="col-span-full mt-4 grid gap-3 lg:grid-cols-3">
        {queueItems.length === 0 ? (
          <EmptyState>No queued submission automation items.</EmptyState>
        ) : (
          queueItems.map((item) => {
            const opportunity = opportunityById[item.opportunity_id];
            return (
              <article key={item.id} className="rounded-md border border-slate-200 p-3 text-sm">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="font-semibold">{opportunity ? <OpportunityLink opportunity={opportunity} /> : "Queued Submission"}</h3>
                    <p className="text-slate-600">{item.submission_mode} · {item.adapter_key}</p>
                  </div>
                  <Badge>{item.approval_status}</Badge>
                </div>
                <p className="mt-2">Automation: {item.automation_status}</p>
                <p>Retries: {item.retry_count}/{item.max_retries}</p>
                {item.error_message && <p className="mt-2 text-red-700">{item.error_message}</p>}
                <div className="mt-3 flex flex-wrap gap-2">
                  {item.approval_status === "Pending Approval" && (
                    <>
                      <Button disabled={submissionQueue.pendingAction === `approve:${item.id}`} onClick={() => void submissionQueue.approve(item.id)}>Approve</Button>
                      <Button variant="danger" disabled={submissionQueue.pendingAction === `reject:${item.id}`} onClick={() => void submissionQueue.reject(item.id)}>Reject</Button>
                    </>
                  )}
                  {item.approval_status === "Approved" && item.automation_status !== "Completed" && (
                    <Button disabled={submissionQueue.pendingAction === `execute:${item.id}`} onClick={() => void submissionQueue.execute(item.id)}>Execute Mock</Button>
                  )}
                </div>
                {item.execution_log.length > 0 && (
                  <ol className="mt-3 grid gap-1 text-xs text-slate-600">
                    {item.execution_log.map((step, index) => (
                      <li key={index}>{String(step.step)} · {String(step.status)}</li>
                    ))}
                  </ol>
                )}
              </article>
            );
          })
        )}
      </div>
    </>
  );
}
