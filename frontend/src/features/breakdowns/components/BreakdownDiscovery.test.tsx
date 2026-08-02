import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithRouter, screen } from "../../../test/testUtils";
import { api } from "../../../services/api";
import type { DiscoveryRunResult, SystemCapabilities } from "../types";
import { useBreakdownDiscovery, useSubmissionQueueActions } from "../hooks/useBreakdownDiscovery";
import { AutomationDashboard } from "./BreakdownDiscovery";

vi.mock("../hooks/useBreakdownDiscovery", () => ({
  useBreakdownDiscovery: vi.fn(),
  useSubmissionQueueActions: vi.fn()
}));
vi.mock("../../../services/api", () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() }
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
    approved_source_records: 3,
    approved_source_record_names: ["Example", "Placeholder", "Paused"],
    active_source_records: 2,
    operational_mode_sources_available: 1,
    operational_mode_source_names: ["Example"],
    sources_attempted: 1,
    source_names_attempted: ["Example"],
    successful_source_checks: 1,
    source_candidates_returned: 1,
    sources_returning_candidates: 1,
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

  it("does not request a standalone Discovery Report on initial render", () => {
    vi.mocked(useBreakdownDiscovery).mockReturnValue({
      discovering: false,
      error: null,
      clearError: vi.fn(),
      run: vi.fn()
    });

    renderDashboard();

    expect(api.get).not.toHaveBeenCalled();
  });

  it("preserves discovery loading state", () => {
    vi.mocked(useBreakdownDiscovery).mockReturnValue({
      discovering: true,
      error: null,
      clearError: vi.fn(),
      run: vi.fn()
    });

    renderDashboard();

    expect(screen.getByRole("button", { name: "Finding..." })).toBeDisabled();
  });

  it("loads and displays the Discovery Report returned by the feature hook", async () => {
    const run = vi.fn(async () => discoveryResult);
    vi.mocked(useBreakdownDiscovery).mockReturnValue({
      discovering: false,
      error: null,
      clearError: vi.fn(),
      run
    });
    const { user } = renderDashboard();

    await user.click(screen.getByRole("button", { name: "Find Film/TV Breakdowns" }));
    await user.click(await screen.findByRole("button", { name: "View Discovery Report" }));

    expect(screen.getByText(/3 approved source record\(s\)/)).toBeInTheDocument();
    expect(screen.getByText(/1 operational Film\/TV source adapter\(s\)/)).toBeInTheDocument();
    expect(screen.getByText(/1 attempted; 1 checked successfully/)).toBeInTheDocument();
    expect(screen.getByText("Approved source records:")).toBeInTheDocument();
    expect(screen.getByText("Operational sources:")).toBeInTheDocument();
    expect(screen.getByText("Parallel queries run")).toBeInTheDocument();
    expect(screen.getByText("87%")).toBeInTheDocument();
    expect(run).toHaveBeenCalledTimes(1);
    expect(run).toHaveBeenCalledWith({
      mode: "FilmTV",
      searchModes: ["Match My Profile", "Match My Archetypes"],
      specificArchetype: ""
    });
    expect(screen.getByText("No candidate pages were returned for this run.")).toBeInTheDocument();
  });

  it("shows bounded provider evidence with the canonical source link", async () => {
    const resultWithEvidence: DiscoveryRunResult = {
      ...discoveryResult,
      discovery_report: {
        ...discoveryResult.discovery_report!,
        candidates: [{
          page_title: "Fallback title",
          url: "https://casting.example.test/uncanonical#fragment",
          source: "Parallel Public Web Search",
          decision: "Accepted",
          outcome: "accept_visible",
          reason_code: "direct_eligible_notice",
          explanation: "Direct actionable acting notice passed current eligibility and trust checks.",
          rejection_reason: null,
          provider_evidence: {
            provider: "Parallel",
            canonical_url: "https://casting.example.test/role",
            title: "Fictional Feature Role",
            snippet: "A provider-supplied summary, not verified page content.",
            published_date: "2026-08-01"
          }
        }]
      }
    };
    vi.mocked(useBreakdownDiscovery).mockReturnValue({
      discovering: false,
      error: null,
      clearError: vi.fn(),
      run: vi.fn(async () => resultWithEvidence)
    });
    const { user } = renderDashboard();

    await user.click(screen.getByRole("button", { name: "Find Film/TV Breakdowns" }));
    await user.click(await screen.findByRole("button", { name: "View Discovery Report" }));

    expect(screen.getByRole("link", { name: "Fictional Feature Role" })).toHaveAttribute("href", "https://casting.example.test/role");
    expect(screen.getByText("Search provider: Parallel")).toBeInTheDocument();
    expect(screen.getByText(/A provider-supplied summary/)).toBeInTheDocument();
    expect(screen.getByText(/Provider publication date: 2026-08-01/)).toBeInTheDocument();
    expect(screen.getByText(/Direct actionable acting notice/)).toBeInTheDocument();
    expect(screen.getByText(/direct_eligible_notice/)).toBeInTheDocument();
  });

  it("distinguishes hidden review from discarded rejection", async () => {
    const resultWithDecisions: DiscoveryRunResult = {
      ...discoveryResult,
      discovery_report: {
        ...discoveryResult.discovery_report!,
        reviewed: 1,
        candidates: [
          {
            page_title: "Reviewable role",
            decision: "Needs Review",
            outcome: "review_hidden",
            reason_code: "medium_parse_confidence",
            explanation: "Parse confidence is below the 70% visible threshold."
          },
          {
            page_title: "Crew listing",
            decision: "Rejected",
            outcome: "reject_discarded",
            reason_code: "crew_or_staff_listing",
            explanation: "The candidate is not an actor-facing role notice."
          },
          {
            page_title: "Travel review",
            decision: "Needs Review",
            outcome: "review_hidden",
            reason_code: "travel_uncertain",
            explanation: "In-person audition travel cannot be verified yet."
          }
        ]
      }
    };
    vi.mocked(useBreakdownDiscovery).mockReturnValue({
      discovering: false,
      error: null,
      clearError: vi.fn(),
      run: vi.fn(async () => resultWithDecisions)
    });
    const { user } = renderDashboard();

    await user.click(screen.getByRole("button", { name: "Find Film/TV Breakdowns" }));
    await user.click(await screen.findByRole("button", { name: "View Discovery Report" }));

    expect(screen.getAllByText("Needs Review")).toHaveLength(2);
    expect(screen.getAllByText("Rejected").length).toBeGreaterThan(0);
    expect(screen.getByText(/below the 70% visible threshold/)).toBeInTheDocument();
    expect(screen.getByText(/not an actor-facing role notice/)).toBeInTheDocument();
    expect(screen.getByText(/In-person audition travel cannot be verified yet/)).toBeInTheDocument();
    expect(screen.getByText(/travel_uncertain/)).toBeInTheDocument();
  });

  it("renders provider text inertly and hides absent optional evidence labels", async () => {
    const resultWithCandidates: DiscoveryRunResult = {
      ...discoveryResult,
      discovery_report: {
        ...discoveryResult.discovery_report!,
        candidates: [
          {
            url: "https://casting.example.test/safe",
            decision: "Rejected",
            rejection_reason: "Fetch failed",
            provider_evidence: {
              provider: "Parallel",
              canonical_url: "https://casting.example.test/safe",
              snippet: "<img onerror=alert(1)> plain context"
            }
          },
          {
            page_title: "Legacy candidate",
            url: "https://casting.example.test/legacy",
            source: "Parallel Public Web Search",
            decision: "Accepted"
          }
        ]
      }
    };
    vi.mocked(useBreakdownDiscovery).mockReturnValue({
      discovering: false,
      error: null,
      clearError: vi.fn(),
      run: vi.fn(async () => resultWithCandidates)
    });
    const { user, container } = renderDashboard();

    await user.click(screen.getByRole("button", { name: "Find Film/TV Breakdowns" }));
    await user.click(await screen.findByRole("button", { name: "View Discovery Report" }));

    expect(screen.getByText(/<img onerror=alert\(1\)> plain context/)).toBeInTheDocument();
    expect(container.querySelector("img")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Legacy candidate" })).toHaveAttribute("href", "https://casting.example.test/legacy");
    expect(screen.getAllByText(/Search-result context:/)).toHaveLength(1);
    expect(screen.queryByText(/Provider publication date:/)).not.toBeInTheDocument();
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
