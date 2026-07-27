import { beforeEach, describe, expect, it, vi } from "vitest";
import { AnalyticsPanel } from "./AnalyticsPanel";
import { createTestQueryClient, createTestQueryWrapper, render, renderWithRouter, screen } from "../../../test/testUtils";
import type { IndustryTrendDashboard, IntelligenceDashboard, MaterialPerformance, OperationsDashboard, Submission, SystemCapabilities } from "../../../types/domain";
import { getCastingPatterns, getIntelligenceDashboard, getMaterialPerformance, getOperationsDashboard } from "../api";
import { analyticsKeys } from "../hooks/useAnalyticsQueries";

vi.mock("../api", () => ({ getCastingPatterns: vi.fn(), getIntelligenceDashboard: vi.fn(), getMaterialPerformance: vi.fn(), getOperationsDashboard: vi.fn() }));

type AnalyticsFixture = {
  operationsDashboard: OperationsDashboard;
  submissions: Submission[];
  industryTrends: IndustryTrendDashboard;
  materialPerformance: MaterialPerformance[];
  intelligenceDashboard: IntelligenceDashboard | null;
  systemCapabilities: SystemCapabilities;
};

function analyticsData(overrides: Partial<AnalyticsFixture> = {}): AnalyticsFixture {
  return {
    operationsDashboard: {
      alerts: [],
      upcoming_events: [],
      freshness_warnings: [],
      cost_dashboard: {
        total_spent: 125,
        cost_per_callback: 62.5,
        cost_per_booking: 0,
        costs_by_platform: { "Actors Access": 25 },
        costs_by_archetype: { Mom: 50 },
        subscriptions: { "Actors Access": 9.99 },
        subscription_monthly_total: 9.99,
        subscription_annual_total: 0,
        estimated_monthly_subscription_spend: 9.99,
        submission_fees_total: 25,
        media_fees_total: 15,
        travel_housing_total: 75,
        other_costs_total: 10
      }
    },
    submissions: [
      { id: "submission-1", current_status: "Submitted" },
      { id: "submission-2", current_status: "Self-Tape Callback" },
      { id: "submission-3", current_status: "Booked" }
    ],
    industryTrends: {
      role_type: [{ trend_type: "role_type", label: "Co-Star", count: 3, insight: "Co-star roles are showing up." }],
      archetype: [{ trend_type: "archetype", label: "Mom", count: 4, insight: "Parent roles are common." }],
      project_type: [],
      union_status: [],
      location: [],
      audition_type: [],
      submission_source: [],
      submitted_project_type: [],
      callback_archetype: [],
      booking_archetype: [],
      insights: ["You are seeing more mom / parent roles than authority roles."],
      pattern_stage: "Emerging Patterns",
      stage: "Emerging Patterns",
      tracked_breakdowns_or_auditions: 10,
      submission_count: 3,
      outcome_count: 2,
      unlock_message: "Emerging Patterns based on your tracked work."
    },
    materialPerformance: [
      {
        asset_id: "asset-1",
        asset_name: "Warm Mom Headshot",
        asset_type: "Headshot",
        times_recommended: 5,
        times_selected: 4,
        submissions: 5,
        callbacks: 2,
        bookings: 1,
        callback_rate: 0.4,
        booking_rate: 0.2
      }
    ],
    intelligenceDashboard: {
      archetype_performance: {
        metrics: [
          {
            archetype: "Mom",
            submissions: 5,
            requested: 1,
            self_tape_callbacks: 1,
            in_person_callbacks: 0,
            pinned: 0,
            booked: 1,
            passed: 1,
            no_response: 2,
            callback_rate: 0.4,
            booking_rate: 0.2
          }
        ],
        best_performing_archetypes: ["Mom"],
        underused_archetypes: [],
        overused_archetypes: [],
        high_potential_stretch_archetypes: []
      },
      casting_office_analytics: [
        {
          casting_office_id: "office-1",
          casting_office: "Example Casting",
          submissions: 3,
          callbacks: 1,
          bookings: 1,
          callback_rate: 0.33,
          booking_rate: 0.33,
          best_materials: ["Warm Mom Headshot"],
          stretch_response_signal: "Early positive signal"
        }
      ],
      role_similarity: []
    },
    systemCapabilities: {
      flags: {
        travel_provider_configured: true,
        ai_configured: true,
        scheduler_configured: false,
        notifications_configured: false,
        source_discovery_configured: true,
        public_profile_import_configured: true,
        supervised_browser_available: false,
        persistent_file_storage_available: false,
        portfolio_demo: true
      },
      states: {},
      integrations: [],
      labels: {
        not_configured: "Not Configured",
        needs_info: "Needs Info",
        manual_override: "Manual Override",
        user_entered_estimate: "User-entered estimate",
        add_data_first: "Add Data First",
        insufficient_data: "Insufficient Data",
        dashboard_alerts_only: "Dashboard Alerts Only",
        manual_check_in: "Manual Check-In",
        suggested_tags: "Suggested Tags",
        deterministic_recommendation: "Deterministic Recommendation"
      }
    },
    ...overrides
  } as AnalyticsFixture;
}

function renderAnalytics(overrides: Partial<AnalyticsFixture> = {}) {
  const fixture = analyticsData(overrides);
  vi.mocked(getOperationsDashboard).mockResolvedValue(fixture.operationsDashboard);
  vi.mocked(getIntelligenceDashboard).mockResolvedValue(fixture.intelligenceDashboard!);
  vi.mocked(getCastingPatterns).mockResolvedValue(fixture.industryTrends);
  vi.mocked(getMaterialPerformance).mockResolvedValue(fixture.materialPerformance);
  return renderWithRouter(<AnalyticsPanel submissions={fixture.submissions} capabilities={fixture.systemCapabilities} />);
}

describe("AnalyticsPanel", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders cost, material, archetype, casting office, callback, and booking metrics", async () => {
    const { container } = renderAnalytics();

    expect(await screen.findByText("Cost Analytics")).toBeInTheDocument();
    expect(screen.getByText("$125.00")).toBeInTheDocument();
    expect(screen.getByText("Callback and Booking Rates")).toBeInTheDocument();
    expect(screen.getByText("Warm Mom Headshot")).toBeInTheDocument();
    expect(screen.getByText("Archetype Performance")).toBeInTheDocument();
    expect(screen.getByText("Casting Office Performance")).toBeInTheDocument();
    expect(screen.getByText("Example Casting")).toBeInTheDocument();
    expect(container.textContent).not.toContain("Industry Trends");
  });

  it("preserves user-specific casting pattern stages", async () => {
    renderAnalytics();

    expect(await screen.findByText("Your Casting Patterns")).toBeInTheDocument();
    expect(screen.getByText("Emerging Patterns")).toBeInTheDocument();
    expect(screen.getByText("You are seeing more mom / parent roles than authority roles.")).toBeInTheDocument();
  });

  it("shows data sufficiency gates when analytics are not configured yet", async () => {
    renderAnalytics({
          materialPerformance: [],
          intelligenceDashboard: null,
          systemCapabilities: {
            ...analyticsData().systemCapabilities!,
            states: {
              material_performance_analytics: {
                state: "Insufficient Data",
                explanation: "At least 5 submissions using that material are needed.",
                safe_fallback: "Add Data First"
              },
              archetype_performance: {
                state: "Add Data First",
                explanation: "At least 5 submissions tagged with that archetype are needed.",
                safe_fallback: "Add Data First"
              },
              casting_office_intelligence: {
                state: "Insufficient Data",
                explanation: "At least 3 submissions linked to that office are needed.",
                safe_fallback: "Add Data First"
              }
            }
          }
        });

    expect((await screen.findAllByText("Track more submissions to unlock this insight.")).length).toBeGreaterThanOrEqual(3);
    expect(screen.getByText("At least 5 submissions using that material are needed.")).toBeInTheDocument();
  });

  it("shows independent loading and partial aggregate errors", async () => {
    const fixture = analyticsData();
    vi.mocked(getOperationsDashboard).mockRejectedValue(new Error("Cost analytics unavailable"));
    vi.mocked(getIntelligenceDashboard).mockResolvedValue(fixture.intelligenceDashboard!);
    vi.mocked(getCastingPatterns).mockResolvedValue(fixture.industryTrends);
    vi.mocked(getMaterialPerformance).mockResolvedValue(fixture.materialPerformance);
    renderWithRouter(<AnalyticsPanel submissions={fixture.submissions} capabilities={fixture.systemCapabilities} />);
    expect(screen.getByText("Loading cost analytics…")).toBeInTheDocument();
    expect(await screen.findByText("Cost analytics unavailable")).toBeInTheDocument();
    expect(screen.getByText("Your Casting Patterns")).toBeInTheDocument();
    expect(screen.getByText("Warm Mom Headshot")).toBeInTheDocument();
  });

  it("preserves cached aggregates during a background refetch", async () => {
    const fixture = analyticsData();
    const pending = new Promise<never>(() => undefined);
    vi.mocked(getOperationsDashboard).mockReturnValue(pending);
    vi.mocked(getIntelligenceDashboard).mockReturnValue(pending);
    vi.mocked(getCastingPatterns).mockReturnValue(pending);
    vi.mocked(getMaterialPerformance).mockReturnValue(pending);
    const client = createTestQueryClient();
    client.setQueryData(analyticsKeys.operations, fixture.operationsDashboard);
    client.setQueryData(analyticsKeys.intelligence, fixture.intelligenceDashboard);
    client.setQueryData(analyticsKeys.industryTrends, fixture.industryTrends);
    client.setQueryData(analyticsKeys.materialPerformance, fixture.materialPerformance);
    render(<AnalyticsPanel submissions={fixture.submissions} capabilities={fixture.systemCapabilities} />, { wrapper: createTestQueryWrapper(client) });
    expect(screen.getByText("Refreshing analytics…")).toBeInTheDocument();
    expect(screen.getByText("$125.00")).toBeInTheDocument();
    expect(screen.getByText("Warm Mom Headshot")).toBeInTheDocument();
  });
});
