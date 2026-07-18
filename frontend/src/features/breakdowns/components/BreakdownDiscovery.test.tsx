import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithRouter, screen } from "../../../test/testUtils";
import type { DiscoveryRunResult, SystemCapabilities } from "../types";
import { useBreakdownDiscovery, useSubmissionQueueActions } from "../hooks/useBreakdownDiscovery";
import { AutomationDashboard } from "./BreakdownDiscovery";

vi.mock("../hooks/useBreakdownDiscovery", () => ({
  useBreakdownDiscovery: vi.fn(),
  useSubmissionQueueActions: vi.fn()
}));

const capabilities = {
  flags: { source_discovery_configured: true }
} as SystemCapabilities;

const discoveryResult: DiscoveryRunResult = {
  discovery_mode: "FilmTV",
  search_modes: ["Match My Profile"],
  opportunities_created: 1,
  opportunities_hidden: 0,
  opportunities_rejected: 0,
  total_found: 1,
  total_rejected: 0,
  total_hidden: 0,
  total_visible: 1,
  limit_reached: false,
  rejection_reasons_summary: {},
  sources_run: 1,
  coverage: {
    approved_active_sources_checked: 1,
    approved_active_source_names_checked: ["Example"],
    eligible_sources_skipped: 0,
    skipped_source_reasons: [],
    approved_mode_sources_available: 1,
    approved_mode_sources_label: "Film/TV sources",
    suggested_sources_awaiting_approval: 0,
    coverage_level: "Limited",
    scope_note: "Approved sources only."
  },
  discovery_report: {
    parallel_queries_run: 2,
    candidate_pages_returned: 3,
    candidate_pages_fetched: 3,
    candidate_pages_parsed: 2,
    accepted: 1,
    rejected: 1,
    top_rejection_reasons: { expired: 1 },
    average_parser_confidence: 87,
    approved_source_hits: 1,
    public_web_hits: 1,
    candidates: []
  }
};

function renderDashboard() {
  return renderWithRouter(
    <AutomationDashboard
      plugins={[]}
      hiddenOpportunities={[]}
      recommendations={[]}
      queueItems={[]}
      opportunities={[]}
      sourceResearchItems={[]}
      capabilities={capabilities}
    />
  );
}

describe("AutomationDashboard discovery state", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useSubmissionQueueActions).mockReturnValue({
      pendingAction: null,
      error: null,
      queueRecommendation: vi.fn(),
      approve: vi.fn(),
      reject: vi.fn(),
      execute: vi.fn()
    });
  });

  it("displays discovery errors supplied by the feature hook", () => {
    vi.mocked(useBreakdownDiscovery).mockReturnValue({
      discovering: false,
      error: "Discovery provider unavailable",
      clearError: vi.fn(),
      run: vi.fn()
    });

    renderDashboard();

    expect(screen.getByText("Discovery provider unavailable")).toBeInTheDocument();
  });

  it("loads and displays the Discovery Report returned by the feature hook", async () => {
    vi.mocked(useBreakdownDiscovery).mockReturnValue({
      discovering: false,
      error: null,
      clearError: vi.fn(),
      run: vi.fn(async () => discoveryResult)
    });
    const { user } = renderDashboard();

    await user.click(screen.getByRole("button", { name: "Find Film/TV Breakdowns" }));
    await user.click(await screen.findByRole("button", { name: "View Discovery Report" }));

    expect(screen.getByText("Parallel queries run")).toBeInTheDocument();
    expect(screen.getByText("87%")).toBeInTheDocument();
  });

  it("composes the submission queue workspace without coupling it to discovery success", () => {
    vi.mocked(useBreakdownDiscovery).mockReturnValue({
      discovering: false,
      error: "Discovery provider unavailable",
      clearError: vi.fn(),
      run: vi.fn()
    });
    vi.mocked(useSubmissionQueueActions).mockReturnValue({
      pendingAction: null,
      error: "Queue provider unavailable",
      queueRecommendation: vi.fn(),
      approve: vi.fn(),
      reject: vi.fn(),
      execute: vi.fn()
    });

    renderDashboard();

    expect(screen.getByText("Queue From Recommendation")).toBeInTheDocument();
    expect(screen.getByText("No queued submission automation items.")).toBeInTheDocument();
    expect(screen.getByText("Discovery provider unavailable")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("Queue provider unavailable");
  });
});
