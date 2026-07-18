import type { ReactNode } from "react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { act, createTestQueryWrapper, renderHook, renderWithRouter, screen, waitFor } from "../../../test/testUtils";
import type { DashboardWidget } from "../types";
import type { ActorCommandCenter, CareerDevelopmentTask } from "../../../types/domain";
import { DashboardPanel, DashboardQuickActions, PlatformCheckInWidget } from "./DashboardPanel";
import { useDashboardWidgets } from "../hooks/useDashboardWidgets";
import { getDashboardQuickActionLinks, getPlatformCheckInSummary, moveDashboardWidget, toggleDashboardWidget } from "../utils";
import { getChiefOfStaffPriorities, useCommandCenter, usePlatformCheckIn } from "@/features/chief-of-staff";
import { getFocusMode, listDashboardWidgets, resetDashboardWidgets, saveDashboardWidgets, updateFocusMode } from "../api";

const chiefMocks = vi.hoisted(() => ({ checkIn: vi.fn() }));

vi.mock("@dnd-kit/core", () => ({
  DndContext: ({ children }: { children: ReactNode }) => <div data-testid="dnd-context">{children}</div>,
  KeyboardSensor: function KeyboardSensor() {},
  PointerSensor: function PointerSensor() {},
  closestCenter: () => null,
  useSensor: () => ({}),
  useSensors: () => []
}));

vi.mock("@dnd-kit/sortable", () => ({
  SortableContext: ({ children }: { children: ReactNode }) => <div data-testid="sortable-context">{children}</div>,
  rectSortingStrategy: {},
  sortableKeyboardCoordinates: () => undefined,
  useSortable: () => ({
    attributes: {},
    listeners: {},
    setNodeRef: () => undefined,
    transform: null,
    transition: undefined,
    isDragging: false
  })
}));

vi.mock("@dnd-kit/utilities", () => ({
  CSS: {
    Transform: {
      toString: () => ""
    }
  }
}));

vi.mock("../api", () => ({
  listDashboardWidgets: vi.fn(),
  getFocusMode: vi.fn(),
  resetDashboardWidgets: vi.fn(),
  saveDashboardWidgets: vi.fn(async () => []),
  updateFocusMode: vi.fn(async () => undefined)
}));

vi.mock("@/features/chief-of-staff", async () => {
  const actual = await vi.importActual<typeof import("@/features/chief-of-staff")>("@/features/chief-of-staff");
  return { ...actual, useCommandCenter: vi.fn(), usePlatformCheckIn: vi.fn() };
});

function widget(widget_id: string, display_name: string, sort_order: number, enabled = true): DashboardWidget {
  return {
    id: widget_id,
    widget_id,
    display_name,
    enabled,
    sort_order,
    size: "medium",
    created_at: "2026-01-01",
    updated_at: "2026-01-01"
  };
}

function widgets() {
  return [
    widget("executive_top_priorities", "Today's Top 3 Priorities", 0),
    widget("platform_check_in", "Today's Platform Check-In", 1),
    widget("career_development_tasks", "Career Development Tasks", 2),
    widget("quick_actions", "Quick Actions", 3)
  ];
}

type DashboardFixtureData = { careerTasks: CareerDevelopmentTask[]; commandCenter: ActorCommandCenter };
function dashboardData(overrides: Partial<DashboardFixtureData> = {}): DashboardFixtureData {
  return {
    careerTasks: [{ id: "task-1", title: "Create Attorney Reel Scene", description: "Film a material scene.", priority: "High", status: "Not Started", related_archetype: "Authority", target_role_types: ["Attorney"], estimated_impact: "High", reason: "Material gap", supported_archetypes: ["Authority"], created_by_agent: true, created_at: "2026-01-01", updated_at: "2026-01-01" }],
    commandCenter: {
      today_opportunities: [],
      executive_priorities: [],
      chief_of_staff_priorities: [
        {
          rank: 1,
          title: "Check Actors Access",
          category: "Platform",
          reason: "Manual check-in is due today.",
          action_label: "Open check-in",
          target_path: "/",
          urgency: 5
        }
      ],
      since_last_visit: [{ message: "1 new Film/TV breakdown matched your profile." }],
      queued_submissions: [],
      upcoming_deadlines: [],
      outcome_nudges: [],
      career_tasks: [],
      material_gaps: [],
      asset_performance: [],
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
      ]
    },
    ...overrides
  };
}

describe("Dashboard feature", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(resetDashboardWidgets).mockResolvedValue(widgets());
    vi.mocked(saveDashboardWidgets).mockResolvedValue([]);
    vi.mocked(listDashboardWidgets).mockResolvedValue(widgets());
    vi.mocked(getFocusMode).mockResolvedValue({ id: "focus-1", active_mode: "Audition Mode", created_at: "2026-01-01", updated_at: "2026-01-01" });
    vi.mocked(updateFocusMode).mockResolvedValue({ id: "focus-1", active_mode: "Audition Mode", created_at: "2026-01-01", updated_at: "2026-01-01" });
    chiefMocks.checkIn.mockResolvedValue({});
    vi.mocked(useCommandCenter).mockReturnValue({ data: dashboardData().commandCenter, isLoading: false, isError: false } as never);
    vi.mocked(usePlatformCheckIn).mockReturnValue({ mutateAsync: chiefMocks.checkIn, isPending: false, isError: false } as never);
  });

  it("reads compact Chief of Staff priority data without owning the calculation", () => {
    const priorities = getChiefOfStaffPriorities(dashboardData());

    expect(priorities[0]).toEqual(expect.objectContaining({ title: "Check Actors Access", target_path: "/" }));
  });

  it("summarizes platform check-in status without implying scraping", () => {
    const summary = getPlatformCheckInSummary(dashboardData());

    expect(summary).toEqual(expect.objectContaining({ checkedCount: 0, totalCount: 1, platformNames: ["Actors Access"] }));
    expect(summary.safetyCopy).toMatch(/does not log in, scrape, or submit/i);
  });

  it("links Find Scene Options directly to Script Finder when a material task is open", () => {
    const actions = getDashboardQuickActionLinks(dashboardData().careerTasks);

    expect(actions).toEqual(
      expect.arrayContaining([expect.objectContaining({ label: "Find Scene Options", to: "/career#script-reel-scene-finder" })])
    );
  });

  it("shows and hides widgets through dashboard layout helpers", () => {
    expect(toggleDashboardWidget(widgets(), "career_development_tasks", false)).toEqual(
      expect.arrayContaining([expect.objectContaining({ widget_id: "career_development_tasks", enabled: false })])
    );
  });

  it("reorders widgets through dashboard layout helpers", () => {
    const [first] = moveDashboardWidget(widgets(), 2, 0);

    expect(first).toEqual(expect.objectContaining({ widget_id: "career_development_tasks" }));
  });

  it("renders the Dashboard shell without entering browser-only sortable behavior", () => {
    vi.mocked(listDashboardWidgets).mockResolvedValue(widgets().map((dashboardWidget) => ({ ...dashboardWidget, enabled: false })));
    renderWithRouter(<DashboardPanel />);

    expect(screen.getByRole("heading", { name: "The Working Actor OS" })).toBeInTheDocument();
    expect(screen.getByText("All dashboard widgets are hidden. Open Widgets and turn at least one back on.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /add audition/i })).toHaveAttribute("href", "/auditions");
  });

  it("persists widget show/hide changes through the widget hook", async () => {
    const initialWidgets = widgets();
    const { result } = renderHook(() => useDashboardWidgets({ initialWidgets }), { wrapper: createTestQueryWrapper() });

    await act(async () => {
      await result.current.toggleWidget("career_development_tasks", false);
    });

    expect(saveDashboardWidgets).toHaveBeenCalledWith(
      expect.arrayContaining([expect.objectContaining({ widget_id: "career_development_tasks", enabled: false })])
    );
  });

  it("restores the previous widget layout when save fails", async () => {
    vi.mocked(saveDashboardWidgets).mockRejectedValue(new Error("save failed"));
    const initialWidgets = widgets();
    const { result } = renderHook(() => useDashboardWidgets({ initialWidgets }), { wrapper: createTestQueryWrapper() });
    await act(async () => { await result.current.toggleWidget("career_development_tasks", false).catch(() => undefined); });
    expect(result.current.widgets.find((item) => item.widget_id === "career_development_tasks")?.enabled).toBe(true);
    expect(result.current.mutationError).toBeInstanceOf(Error);
  });

  it("keeps the previous widget layout when reset fails", async () => {
    vi.mocked(resetDashboardWidgets).mockRejectedValue(new Error("reset failed"));
    const initialWidgets = widgets();
    const { result } = renderHook(() => useDashboardWidgets({ initialWidgets }), { wrapper: createTestQueryWrapper() });
    await act(async () => { await result.current.resetLayout().catch(() => undefined); });
    expect(result.current.widgets).toEqual(initialWidgets);
    expect(result.current.mutationError).toBeInstanceOf(Error);
  });

  it("updates platform check-ins through the public Chief of Staff boundary", async () => {
    const data = dashboardData();
    const { user } = renderWithRouter(<PlatformCheckInWidget commandCenter={data.commandCenter} />);

    await user.click(screen.getByRole("checkbox", { name: /actors access/i }));

    await waitFor(() => expect(chiefMocks.checkIn).toHaveBeenCalledWith({ subscriptionId: "sub-1", checkedToday: true }));
  });

  it("shows a platform check-in error without hiding its current status", () => {
    const data = dashboardData();
    vi.mocked(usePlatformCheckIn).mockReturnValue({ mutateAsync: chiefMocks.checkIn, isPending: false, isError: true } as never);
    renderWithRouter(<PlatformCheckInWidget commandCenter={data.commandCenter} />);
    expect(screen.getByRole("alert")).toHaveTextContent(/could not update/i);
    expect(screen.getByText("0/1")).toBeInTheDocument();
  });

  it("renders quick actions as navigation links, including the Script Finder deep link", () => {
    renderWithRouter(<DashboardQuickActions careerTasks={dashboardData().careerTasks} />);

    expect(screen.getByRole("link", { name: /add audition/i })).toHaveAttribute("href", "/auditions");
    expect(screen.getByRole("link", { name: /find scene options/i })).toHaveAttribute(
      "href",
      "/career#script-reel-scene-finder"
    );
  });

  it("keeps reorder behavior in the widget hook and persists the saved order", async () => {
    const initialWidgets = widgets();
    const { result } = renderHook(() => useDashboardWidgets({ initialWidgets }), { wrapper: createTestQueryWrapper() });

    await act(async () => {
      await result.current.onDragEnd({
        active: { id: "career_development_tasks" },
        over: { id: "executive_top_priorities" }
      });
    });

    await waitFor(() => expect(saveDashboardWidgets).toHaveBeenCalledTimes(1));
    expect(saveDashboardWidgets).toHaveBeenCalledWith([
      expect.objectContaining({ widget_id: "career_development_tasks" }),
      expect.objectContaining({ widget_id: "executive_top_priorities" }),
      expect.objectContaining({ widget_id: "platform_check_in" }),
      expect.objectContaining({ widget_id: "quick_actions" })
    ]);
  });
});
