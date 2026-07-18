import { describe, expect, it, vi, beforeEach } from "vitest";
import { renderWithRouter, screen } from "../../../test/testUtils";
import {
  BriefHistoryPanel,
  ChiefOfStaffDashboardSummary,
  ChiefOfStaffPanel,
  SinceLastVisitWidget,
  TopPrioritiesWidget,
  WeeklyBriefPanel,
  getChiefOfStaffSummary,
  getPlatformCheckInRecommendationText
} from "../index";
import { generateWeeklyBrief, updateChiefOfStaffMemory } from "../api";
import type { ActorCommandCenter, CareerMemory, ExecutiveBrief } from "../../../types/domain";

vi.mock("../api", () => ({
  generateWeeklyBrief: vi.fn(async () => ({})),
  listExecutiveBriefs: vi.fn(async () => []),
  updateChiefOfStaffMemory: vi.fn(async () => ({}))
}));

function priority(rank: number, title: string) {
  return {
    rank,
    title,
    category: "Platform",
    reason: `${title} needs attention.`,
    action_label: "Review",
    target_path: "/settings",
    urgency: 5
  };
}

function commandCenter(overrides: Partial<ActorCommandCenter> = {}): ActorCommandCenter {
  return {
    today_opportunities: [],
    executive_priorities: [],
    chief_of_staff_priorities: [priority(1, "Check Actors Access"), priority(2, "Review matching breakdown")],
    since_last_visit: [{ message: "2 new Film/TV breakdowns matched your profile." }],
    upcoming_attention: [],
    today_career_recommendation: null,
    platform_check_ins: [
      {
        id: "check-1",
        platform_subscription_id: "sub-1",
        platform_name: "Actors Access",
        has_subscription: true,
        subscription_level: "Plus",
        active: true,
        check_date: "2026-07-14",
        timezone: "America/New_York",
        checked_today: false,
        checked_at: null,
        notes: null,
        created_at: "2026-07-14",
        updated_at: "2026-07-14"
      }
    ],
    queued_submissions: [],
    upcoming_deadlines: [],
    outcome_nudges: [],
    career_tasks: [],
    material_gaps: [],
    asset_performance: [],
    ...overrides
  };
}

function brief(overrides: Partial<ExecutiveBrief> = {}): ExecutiveBrief {
  return {
    id: "brief-1",
    actor_profile_id: null,
    period_start: "2026-07-06",
    period_end: "2026-07-12",
    brief_type: "Weekly",
    new_matching_breakdowns: [{ id: "breakdown-1" }],
    submissions_completed: [{ id: "submission-1" }],
    callbacks_received: [],
    bookings: [],
    materials_used: [],
    career_progress: [],
    recommended_priorities: ["Check platforms", "Finish self-tape"],
    summary: "You made progress on matching breakdowns and materials.",
    created_at: "2026-07-12",
    updated_at: "2026-07-12",
    ...overrides
  };
}

function memory(): CareerMemory {
  return {
    id: "memory-1",
    actor_profile_id: null,
    current_career_goals: ["Book more guest star roles"],
    current_focus: "Film/TV",
    stretch_archetypes: ["Attorney"],
    preferred_project_types: ["TV", "Film"],
    preferred_markets: ["New York"],
    unavailable_dates: [],
    career_notes: "Prioritize comedy and authority.",
    executive_notes: "Check platforms daily.",
    created_at: "2026-07-01",
    updated_at: "2026-07-01"
  };
}

function workflowData(commandCenterValue: ActorCommandCenter | null = commandCenter()) {
  return { commandCenter: commandCenterValue } as never;
}

describe("Chief of Staff feature", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders top priorities in rank order", () => {
    renderWithRouter(<TopPrioritiesWidget priorities={[priority(1, "Submit self-tape"), priority(2, "Check Casting Networks")]} />);

    expect(screen.getByText("1. Submit self-tape")).toBeInTheDocument();
    expect(screen.getByText("2. Check Casting Networks")).toBeInTheDocument();
  });

  it("renders Since Your Last Visit meaningful changes", () => {
    renderWithRouter(<SinceLastVisitWidget changes={commandCenter().since_last_visit ?? []} />);

    expect(screen.getByText("2 new Film/TV breakdowns matched your profile.")).toBeInTheDocument();
  });

  it("shows an empty state when nothing changed", () => {
    renderWithRouter(<SinceLastVisitWidget changes={[]} />);

    expect(screen.getByText("No meaningful changes since your last dashboard visit.")).toBeInTheDocument();
  });

  it("renders weekly brief signals", () => {
    renderWithRouter(<WeeklyBriefPanel brief={brief()} />);

    expect(screen.getByText("Weekly Brief")).toBeInTheDocument();
    expect(screen.getByText("You made progress on matching breakdowns and materials.")).toBeInTheDocument();
    expect(screen.getByText("2 priorities")).toBeInTheDocument();
  });

  it("renders the Career archive without duplicating daily Dashboard widgets", () => {
    renderWithRouter(<BriefHistoryPanel briefs={[brief()]} />);

    expect(screen.getByText("Weekly Brief")).toBeInTheDocument();
    expect(screen.queryByText("Today's Platform Check-In")).not.toBeInTheDocument();
  });

  it("displays platform check-in recommendations without implying automatic scraping", () => {
    renderWithRouter(<ChiefOfStaffDashboardSummary data={workflowData()} />);

    expect(screen.getByText(/Actors Access has not been manually checked today/i)).toBeInTheDocument();
    expect(screen.getByText(/does not log in, scrape, or submit/i)).toBeInTheDocument();
  });

  it("accepts compact command-center input contracts", () => {
    const summary = getChiefOfStaffSummary({ commandCenter: commandCenter() });

    expect(summary.priorities).toHaveLength(2);
    expect(summary.sinceLastVisit).toHaveLength(1);
    expect(getPlatformCheckInRecommendationText({ commandCenter: commandCenter() })).toMatch(/Actors Access/);
  });

  it("saves memory and generates weekly briefs through existing API contracts", async () => {
    const { user } = renderWithRouter(<ChiefOfStaffPanel memory={memory()} onSaveMemory={(patch) => updateChiefOfStaffMemory(patch as Parameters<typeof updateChiefOfStaffMemory>[0])} />);

    await user.click(screen.getByRole("button", { name: /generate weekly brief/i }));
    expect(generateWeeklyBrief).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole("button", { name: /save career memory/i }));
    expect(updateChiefOfStaffMemory).toHaveBeenCalledWith(
      expect.objectContaining({
        current_focus: "Film/TV",
        current_career_goals: ["Book more guest star roles"]
      })
    );
  });
});
