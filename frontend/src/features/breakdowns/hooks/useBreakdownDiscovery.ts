import { useState } from "react";
import { errorMessage } from "../../../services/api/errors";
import { useApproveQueueItem, useExecuteQueueItem, useQueueRecommendation, useRejectQueueItem, useRunBreakdownDiscovery } from "./useBreakdownQueries";
import type { DiscoveryRunRequest, DiscoveryRunResult } from "../types";

export function useBreakdownDiscovery() {
  const [discovering, setDiscovering] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const discovery = useRunBreakdownDiscovery();

  async function run(request: DiscoveryRunRequest): Promise<DiscoveryRunResult | null> {
    setDiscovering(true);
    setError(null);
    try {
      return await discovery.mutateAsync(request);
    } catch (caught) {
      setError(errorMessage(caught, "Could not fetch public breakdowns right now."));
      return null;
    } finally {
      setDiscovering(false);
    }
  }

  return { discovering, error, clearError: () => setError(null), run };
}

export function useSubmissionQueueActions() {
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const queue = useQueueRecommendation(); const approve = useApproveQueueItem(); const reject = useRejectQueueItem(); const execute = useExecuteQueueItem();

  async function mutate(actionKey: string, request: () => Promise<unknown>) {
    setPendingAction(actionKey);
    setError(null);
    try {
      await request();
    } catch (caught) {
      setError(errorMessage(caught, "Could not update the submission queue."));
    } finally {
      setPendingAction(null);
    }
  }

  return {
    pendingAction,
    error,
    queueRecommendation: (recommendationId: string) => mutate(`queue:${recommendationId}`, () => queue.mutateAsync(recommendationId)),
    approve: (queueItemId: string) => mutate(`approve:${queueItemId}`, () => approve.mutateAsync(queueItemId)),
    reject: (queueItemId: string) => mutate(`reject:${queueItemId}`, () => reject.mutateAsync(queueItemId)),
    execute: (queueItemId: string) => mutate(`execute:${queueItemId}`, () => execute.mutateAsync(queueItemId))
  };
}
