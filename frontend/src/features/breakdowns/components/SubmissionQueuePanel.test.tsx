import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithRouter, screen } from "../../../test/testUtils";
import { useSubmissionQueueActions } from "../hooks/useBreakdownDiscovery";
import type { AgentRecommendation, Opportunity, SubmissionAutomationQueueItem } from "../types";
import { SubmissionQueuePanel } from "./SubmissionQueuePanel";

vi.mock("../hooks/useBreakdownDiscovery", () => ({
  useSubmissionQueueActions: vi.fn()
}));

const opportunity = {
  id: "opportunity-1",
  role: "Detective",
  project: "City Stories",
  original_post_url: null,
  source_metadata: {}
} as Opportunity;

const recommendation = {
  id: "recommendation-1",
  opportunity_id: opportunity.id,
  match_type: "Strong Match"
} as AgentRecommendation;

const queueItem = {
  id: "queue-1",
  opportunity_id: opportunity.id,
  adapter_key: "mock",
  submission_mode: "Manual Review",
  approval_status: "Pending Approval",
  automation_status: "Prepared",
  retry_count: 0,
  max_retries: 3,
  error_message: null,
  prepared_payload: {},
  execution_log: [],
  created_at: "2026-07-17T12:00:00Z",
  updated_at: "2026-07-17T12:00:00Z"
} satisfies SubmissionAutomationQueueItem;

const actions = {
  pendingAction: null,
  error: null,
  queueRecommendation: vi.fn(),
  approve: vi.fn(),
  reject: vi.fn(),
  execute: vi.fn()
};

function renderPanel(overrides?: {
  recommendations?: AgentRecommendation[];
  queueItems?: SubmissionAutomationQueueItem[];
}) {
  return renderWithRouter(
    <SubmissionQueuePanel
      recommendations={overrides?.recommendations ?? [recommendation]}
      queueItems={overrides?.queueItems ?? [queueItem]}
      opportunities={[opportunity]}
      hiddenOpportunities={[]}
    />
  );
}

describe("SubmissionQueuePanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useSubmissionQueueActions).mockReturnValue(actions);
  });

  it("renders recommendation and queue state and coordinates its actions", async () => {
    const { user } = renderPanel();

    expect(screen.getAllByText("Detective · City Stories")).toHaveLength(2);
    expect(screen.getByText("Manual Review · mock")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Queue" }));
    await user.click(screen.getByRole("button", { name: "Approve" }));
    await user.click(screen.getByRole("button", { name: "Reject" }));

    expect(actions.queueRecommendation).toHaveBeenCalledWith(recommendation.id);
    expect(actions.approve).toHaveBeenCalledWith(queueItem.id);
    expect(actions.reject).toHaveBeenCalledWith(queueItem.id);
  });

  it("renders its empty states without hiding the workspace", () => {
    renderPanel({ recommendations: [], queueItems: [] });

    expect(screen.getByText("No recommendations to queue.")).toBeInTheDocument();
    expect(screen.getByText("No queued submission automation items.")).toBeInTheDocument();
  });

  it("announces section-owned mutation failures", () => {
    vi.mocked(useSubmissionQueueActions).mockReturnValue({ ...actions, error: "Queue provider unavailable" });
    renderPanel();

    expect(screen.getByRole("alert")).toHaveTextContent("Queue provider unavailable");
    expect(screen.getByText("Detective · City Stories", { selector: "h3 *" })).toBeInTheDocument();
  });

  it("disables only the action currently pending", () => {
    vi.mocked(useSubmissionQueueActions).mockReturnValue({ ...actions, pendingAction: `approve:${queueItem.id}` });
    renderPanel();

    expect(screen.getByRole("button", { name: "Approve" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Reject" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Queue" })).toBeEnabled();
  });
});
