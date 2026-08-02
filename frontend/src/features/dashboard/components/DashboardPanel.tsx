import { useState, type ComponentType, type ReactNode } from "react";
import { Link } from "react-router-dom";
import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  rectSortingStrategy,
  type SortableContextProps
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { BookOpenCheck, BriefcaseBusiness, Clapperboard, FilePlus2, FolderUp, GripVertical, Lightbulb, RotateCcw, Search, SlidersHorizontal, Sparkles } from "lucide-react";
import { Badge, Button, EmptyState } from "../../../components/ui";
import type { CommandCenterCard, DashboardWidget, FocusModeName, OpportunityIntelligenceSummary } from "../../../types/domain";
import type { ActorRelationship, AuditionCalendarEvent, SourceResearchItem } from "../../../types/domain";
import type { IndustryTrendDashboard, IntelligenceDashboard, OperationsDashboard } from "../../../types/domain";
import { useIndustryTrends, useIntelligenceDashboard, useOperationsDashboard } from "../../analytics";
import { useCalendarEvents } from "../../calendar";
import { useRelationships } from "../../relationships";
import { useSourceResearchItems } from "../../source-library";
import { focusModes, focusWidgetMap } from "../constants";
import { useDashboardWidgets } from "../hooks/useDashboardWidgets";
import { useDashboardWidgetQuery, useFocusMode, useUpdateFocusMode } from "../hooks/useDashboardQueries";
import { getDashboardQuickActionLinks, getPlatformCheckInSummary, sortWidgets } from "../utils";
import { getChiefOfStaffPriorities, getSinceLastVisitChanges, SinceLastVisitWidget, TopPrioritiesWidget, useCommandCenter, usePlatformCheckIn } from "@/features/chief-of-staff";
import { useCareerTasks, useCareerSwot, useQuarterlyReviews, useCastingGoals } from "@/features/career-intelligence";
import type { CareerDevelopmentTask, CareerSwotAnalysis, CastingGoal, QuarterlyCareerReview } from "../../../types/domain";
import { useAuditionReadiness, useBreakdownRecommendations, useBreakdowns, useHiddenBreakdowns } from "../../breakdowns";
import { useSubmissions, useWorkflowSelfTapes } from "../../auditions";
import { useSystemCapabilities } from "../../../services/system";
import type { AgentRecommendation, AuditionReadiness, Opportunity } from "../../../types/domain";

type WidgetDefinition = {
  id: string;
  linkTo: string;
  render: (data: DashboardReadData) => ReactNode;
};

type DashboardReadData = {
  capabilities: import("../../../types/domain").SystemCapabilities | null;
  commandCenter: import("../../../types/domain").ActorCommandCenter | null;
  submissions: import("../../../types/domain").Submission[];
  selfTapes: import("../../../types/domain").SelfTapeWorkflow[];
  calendarEvents: AuditionCalendarEvent[];
  relationships: ActorRelationship[];
  sourceResearchItems: SourceResearchItem[];
  operationsDashboard: OperationsDashboard | null;
  intelligenceDashboard: IntelligenceDashboard | null;
  industryTrends: IndustryTrendDashboard | null;
  careerTasks: CareerDevelopmentTask[];
  careerSwot: CareerSwotAnalysis | null;
  quarterlyReviews: QuarterlyCareerReview[];
  castingGoals: CastingGoal[];
  opportunities: Opportunity[];
  hiddenOpportunities: Opportunity[];
  recommendations: AgentRecommendation[];
  auditionReadiness: AuditionReadiness[];
};

const SortableContextCompat = SortableContext as unknown as ComponentType<
  SortableContextProps & { children: ReactNode }
>;

const widgetDefinitions: WidgetDefinition[] = [
  {
    id: "executive_top_priorities",
    linkTo: "/",
    render: (data) => (
      <TopPrioritiesWidget priorities={getChiefOfStaffPriorities(data)} />
    )
  },
  {
    id: "since_last_visit",
    linkTo: "/",
    render: (data) => <SinceLastVisitWidget changes={getSinceLastVisitChanges(data)} />
  },
  {
    id: "platform_check_in",
    linkTo: "/settings",
    render: (data) => <PlatformCheckInWidget commandCenter={data.commandCenter} />
  },
  {
    id: "todays_priorities",
    linkTo: "/breakdowns",
    render: (data) => (
      <OpportunityPrioritiesWidget
        opportunities={data.commandCenter?.today_opportunities ?? []}
      />
    )
  },
  {
    id: "self_tapes_due",
    linkTo: "/auditions",
    render: (data) => {
      const due = data.selfTapes
        .filter((tape) => tape.status !== "Completed")
        .sort((a, b) => String(a.tape_due_at ?? "").localeCompare(String(b.tape_due_at ?? "")));
      return (
        <WidgetBody
          metric={due.length}
          items={due.slice(0, 3).map((tape) => `${findOpportunityLabel(data, tape.opportunity_id)} · ${formatDate(tape.tape_due_at)}`)}
          empty="No active self-tapes due."
        />
      );
    }
  },
  {
    id: "upcoming_deadlines",
    linkTo: "/calendar",
    render: (data) => {
      const events = [...data.calendarEvents]
        .sort((a, b) => a.start_datetime.localeCompare(b.start_datetime))
        .slice(0, 4);
      const opportunityDeadlines = data.opportunities
        .filter((opportunity) => opportunity.submission_deadline || opportunity.audition_deadline)
        .map((opportunity) => `${opportunity.role} · ${formatDate(opportunity.audition_deadline ?? opportunity.submission_deadline)}`)
        .slice(0, 3);
      return (
        <WidgetBody
          metric={events.length + opportunityDeadlines.length}
          items={[...events.map((event) => `${event.title} · ${formatDate(event.start_datetime)}`), ...opportunityDeadlines].slice(0, 4)}
          empty="No upcoming deadlines."
        />
      );
    }
  },
  {
    id: "upcoming_callbacks",
    linkTo: "/auditions",
    render: (data) => {
      const callbackSubmissions = data.submissions.filter((submission) =>
        ["Requested", "Self-Tape Callback", "In-Person Callback", "Pinned"].includes(submission.current_status)
      );
      return (
        <WidgetBody
          metric={callbackSubmissions.length}
          items={callbackSubmissions.slice(0, 3).map((submission) => `${submission.opportunity?.role ?? "Audition"} · ${submission.current_status}`)}
          empty="No callback reminders yet."
        />
      );
    }
  },
  {
    id: "new_opportunities",
    linkTo: "/breakdowns",
    render: (data) => (
      <WidgetBody
        metric={data.opportunities.length}
        items={[...data.opportunities]
          .sort((a, b) => b.created_at.localeCompare(a.created_at))
          .slice(0, 3)
          .map((opportunity) => `${opportunity.role} · ${opportunity.project}`)}
        empty="No breakdowns found yet."
      />
    )
  },
  {
    id: "strong_matches",
    linkTo: "/breakdowns",
    render: (data) => (
      <WidgetBody
        metric={recommendationsByType(data, "Strong Match").length}
        items={recommendationsByType(data, "Strong Match").slice(0, 3).map((recommendation) => recommendationLabel(data, recommendation.opportunity_id))}
        empty="No strong matches yet."
      />
    )
  },
  {
    id: "growth_matches",
    linkTo: "/breakdowns",
    render: (data) => (
      <WidgetBody
        metric={recommendationsByType(data, "Growth Match").length}
        items={recommendationsByType(data, "Growth Match").slice(0, 3).map((recommendation) => recommendationLabel(data, recommendation.opportunity_id))}
        empty="No growth matches yet."
      />
    )
  },
  {
    id: "stretch_matches",
    linkTo: "/career",
    render: (data) => {
      const stretchRoles: unknown[] = [];
      return (
        <WidgetBody
          metric={stretchRoles.length}
          items={stretchRoles.slice(0, 3).map(() => "Stretch role")}
          empty="Run career guidance to identify stretch roles."
        />
      );
    }
  },
  {
    id: "career_development_tasks",
    linkTo: "/career",
    render: (data) => {
      const openTasks = data.careerTasks.filter((task) => task.status !== "Completed");
      return (
        <WidgetBody
          metric={openTasks.length}
          items={openTasks.slice(0, 3).map((task) => `${task.title} · ${task.priority}`)}
          empty="No active career tasks."
        />
      );
    }
  },
  {
    id: "material_recommendations",
    linkTo: "/materials",
    render: (data) => (
      <WidgetBody
        metric={data.commandCenter?.material_gaps.length ?? 0}
        items={(data.commandCenter?.material_gaps ?? []).slice(0, 3).map((gap) => `${gap.archetype ?? "Material"} · ${gap.recommended_action ?? gap.message ?? "Review"}`)}
        empty="No material recommendations right now."
      />
    )
  },
  {
    id: "asset_freshness_warnings",
    linkTo: "/materials",
    render: (data) => (
      <WidgetBody
        metric={data.operationsDashboard?.freshness_warnings.length ?? 0}
        items={(data.operationsDashboard?.freshness_warnings ?? []).slice(0, 3).map((warning) => `${warning.asset_name} · ${warning.freshness_status}`)}
        empty="All tracked materials look current."
      />
    )
  },
  {
    id: "audition_calendar_preview",
    linkTo: "/calendar",
    render: (data) => (
      <WidgetBody
        metric={data.calendarEvents.length}
        items={[...data.calendarEvents]
          .sort((a, b) => a.start_datetime.localeCompare(b.start_datetime))
          .slice(0, 3)
          .map((event) => `${event.title} · ${formatDate(event.start_datetime)}`)}
        empty="No calendar events scheduled."
      />
    )
  },
  {
    id: "analytics_snapshot",
    linkTo: "/analytics",
    render: (data) => {
      const cost = data.operationsDashboard?.cost_dashboard;
      const topArchetype = data.intelligenceDashboard?.archetype_performance.best_performing_archetypes[0];
      return (
        <WidgetBody
          metric={data.submissions.length}
          items={[
            `Total spent: $${Number(cost?.total_spent ?? 0).toFixed(2)}`,
            `Cost/callback: $${Number(cost?.cost_per_callback ?? 0).toFixed(2)}`,
            `Top archetype: ${topArchetype ?? "Needs data"}`
          ]}
          empty="Analytics will appear after submissions."
        />
      );
    }
  },
  {
    id: "quarterly_progress",
    linkTo: "/career",
    render: (data) => {
      const latest = data.quarterlyReviews[0];
      const booked = data.submissions.filter((submission) => submission.current_status === "Booked").length;
      const callbacks = data.submissions.filter((submission) => ["Requested", "Self-Tape Callback", "In-Person Callback", "Pinned", "Booked"].includes(submission.current_status)).length;
      return (
        <WidgetBody
          metric={latest ? latest.quarter : data.quarterlyReviews.length}
          items={[
            latest ? `Latest review: Q${latest.quarter} ${latest.year}` : "Generate your first quarterly review.",
            `${callbacks} callback-or-better outcomes`,
            `${booked} bookings tracked`
          ]}
          empty="Quarterly progress will appear after a review."
        />
      );
    }
  },
  {
    id: "industry_trends",
    linkTo: "/analytics",
    render: (data) => {
      const trendState = data.capabilities?.states.industry_trend_analysis;
      if (trendState && trendState.state !== "Configured") {
        return (
          <WidgetBody
            metric={0}
            items={[`${trendState.state}: ${trendState.explanation}`, "Add or track a few more auditions to unlock casting pattern insights."]}
            empty="Add Data First."
          />
        );
      }
      return (
        <WidgetBody
          metric={data.industryTrends?.tracked_breakdowns_or_auditions ?? 0}
          items={[data.industryTrends?.pattern_stage ?? "Add Data First", ...(data.industryTrends?.insights ?? []).slice(0, 2)]}
          empty="Add or track a few more auditions to unlock casting pattern insights."
        />
      );
    }
  },
  {
    id: "readiness_score",
    linkTo: "/breakdowns",
    render: (data) => {
      const readyItems = data.auditionReadiness.filter((item) => ["Ready", "Mostly Ready"].includes(item.readiness_label));
      return (
        <WidgetBody
          metric={readyItems.length}
          items={data.auditionReadiness.slice(0, 3).map((item) => `${item.opportunity_label} · ${item.readiness_label}`)}
          empty="Upload materials and add breakdowns to calculate readiness."
        />
      );
    }
  },
  {
    id: "relationship_reminders",
    linkTo: "/relationships",
    render: (data) => {
      const reminders = data.relationships
        .filter((relationship) => relationship.relationship_strength !== "Cold")
        .slice(0, 3);
      return (
        <WidgetBody
          metric={data.relationships.length}
          items={reminders.map((relationship) => `${relationship.name} · ${relationship.role_title}`)}
          empty="No relationship reminders yet."
        />
      );
    }
  },
  {
    id: "career_insight",
    linkTo: "/career",
    render: (data) => (
      <WidgetBody
        metric={data.careerSwot ? 1 : 0}
        items={[
          data.careerSwot?.strengths[0] ? `Strength: ${data.careerSwot.strengths[0]}` : "Run SWOT for current career signal.",
          data.careerSwot?.opportunities[0] ? `Career opening: ${data.careerSwot.opportunities[0]}` : "Career insight will appear here."
        ]}
        empty="No career insight yet."
      />
    )
  },
  {
    id: "casting_goals",
    linkTo: "/career",
    render: (data) => (
      <WidgetBody
        metric={data.castingGoals.filter((goal) => goal.status === "Active").length}
        items={data.castingGoals.filter((goal) => goal.status === "Active").slice(0, 3).map((goal) => `${goal.title} · ${goal.priority}`)}
        empty="Add casting goals to guide recommendations."
      />
    )
  },
  {
    id: "quick_actions",
    linkTo: "/",
    render: (data) => <DashboardQuickActions compact careerTasks={data.careerTasks} />
  }
];

export function DashboardPanel() {
  const commandCenter = useCommandCenter();
  const dashboardWidgets = useDashboardWidgetQuery();
  const focusMode = useFocusMode();
  const updateFocus = useUpdateFocusMode();
  const capabilities = useSystemCapabilities();
  const submissions = useSubmissions();
  const selfTapes = useWorkflowSelfTapes();
  const calendarEvents = useCalendarEvents();
  const relationships = useRelationships();
  const sourceResearchItems = useSourceResearchItems();
  const operationsDashboard = useOperationsDashboard();
  const intelligenceDashboard = useIntelligenceDashboard();
  const industryTrends = useIndustryTrends();
  const careerTasks = useCareerTasks(); const careerSwot = useCareerSwot(); const quarterlyReviews = useQuarterlyReviews(); const castingGoals = useCastingGoals();
  const opportunities = useBreakdowns(); const hiddenOpportunities = useHiddenBreakdowns();
  const recommendations = useBreakdownRecommendations(); const readiness = useAuditionReadiness();
  const readData: DashboardReadData = {
    capabilities: capabilities.data ?? null,
    commandCenter: commandCenter.data ?? null,
    submissions: submissions.data ?? [],
    selfTapes: selfTapes.data ?? [],
    calendarEvents: calendarEvents.data ?? [],
    relationships: relationships.data ?? [],
    sourceResearchItems: sourceResearchItems.data ?? [],
    operationsDashboard: operationsDashboard.data ?? null,
    intelligenceDashboard: intelligenceDashboard.data ?? null,
    industryTrends: industryTrends.data ?? null,
    careerTasks: careerTasks.data ?? [], careerSwot: careerSwot.data ?? null,
    quarterlyReviews: quarterlyReviews.data ?? [], castingGoals: castingGoals.data ?? [],
    opportunities: opportunities.data ?? [], hiddenOpportunities: hiddenOpportunities.data ?? [],
    recommendations: recommendations.data ?? [], auditionReadiness: readiness.data ?? []
  };
  const [customizing, setCustomizing] = useState(false);
  const activeFocusMode = focusMode.data?.active_mode ?? "Audition Mode";
  const focusedWidgetIds = focusWidgetMap[activeFocusMode];
  const sourcesNeedingApproval = readData.sourceResearchItems.filter((source) =>
    !source.deleted && ["Suggested", "Researching"].includes(source.status)
  ).length;
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );
  const { enabledIds, enabledWidgets, onDragEnd, resetLayout, toggleWidget, widgets, mutationError, mutationPending } = useDashboardWidgets({
    initialWidgets: dashboardWidgets.data ?? []
  });

  async function updateFocusMode(active_mode: FocusModeName) {
    try {
      await updateFocus.mutateAsync(active_mode);
    } catch {
      // Mutation state retains the standardized error for presentation.
    }
  }

  return (
    <div className="grid gap-4">
      {commandCenter.isLoading && <p className="text-sm text-slate-600" role="status">Loading command center...</p>}
      {commandCenter.isError && <p className="rounded bg-red-50 p-2 text-sm text-red-700" role="alert">Command center could not load. Other Dashboard sections remain usable.</p>}
      {(dashboardWidgets.isLoading || focusMode.isLoading) && <p className="text-sm text-slate-600" role="status">Loading Dashboard preferences...</p>}
      {dashboardWidgets.isError && <p className="rounded bg-red-50 p-2 text-sm text-red-700" role="alert">Dashboard widgets could not load. Other sections remain usable.</p>}
      {focusMode.isError && <p className="rounded bg-red-50 p-2 text-sm text-red-700" role="alert">Focus mode could not load. Other sections remain usable.</p>}
      {Boolean(mutationError) && <p className="rounded bg-red-50 p-2 text-sm text-red-700" role="alert">Dashboard layout could not be saved. The previous layout was restored.</p>}
      {updateFocus.isError && <p className="rounded bg-red-50 p-2 text-sm text-red-700" role="alert">Focus mode could not be saved.</p>}
      <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-lg font-bold text-ink">The Working Actor OS</h2>
            <p className="mt-1 text-sm text-slate-600">
              {capabilities.data?.flags.ai_configured
                ? "The Working Actor OS helps actors manage breakdowns, auditions, materials, relationships, analytics, and career strategy in one AI-powered workspace."
                : "The Working Actor OS helps actors manage breakdowns, auditions, materials, relationships, analytics, and career strategy in one workspace. AI-powered features are labeled when configured."}
            </p>
            {!capabilities.data?.flags.ai_configured && (
              <p className="mt-2 inline-flex rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-medium text-slate-700">
                Deterministic Recommendation
              </p>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            <select
              name="active_focus_mode"
              className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-ink"
              value={activeFocusMode}
              disabled={updateFocus.isPending}
              onChange={(event) => void updateFocusMode(event.target.value as FocusModeName)}
            >
              {focusModes.map((mode) => <option key={mode}>{mode}</option>)}
            </select>
            <Button variant="secondary" onClick={() => setCustomizing((current) => !current)}>
              <SlidersHorizontal className="mr-2 h-4 w-4" />
              Widgets
            </Button>
            <Button variant="secondary" disabled={mutationPending} onClick={() => void resetLayout().catch(() => undefined)}>
              <RotateCcw className="mr-2 h-4 w-4" />
              Reset Layout
            </Button>
          </div>
        </div>

        {customizing && (
          <div className="mt-4 grid gap-2 rounded-md border border-slate-200 bg-slate-50 p-3 sm:grid-cols-2 lg:grid-cols-3">
            {[...widgets].sort(sortWidgets).map((widget) => (
              <label key={widget.widget_id} className="flex items-center justify-between gap-3 rounded bg-white px-3 py-2 text-sm">
                <span>{widget.display_name}</span>
                <input
                  type="checkbox"
                  checked={widget.enabled}
                  disabled={mutationPending}
                  onChange={(event) => void toggleWidget(widget.widget_id, event.target.checked).catch(() => undefined)}
                />
              </label>
            ))}
          </div>
        )}
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
        <DashboardQuickActions careerTasks={readData.careerTasks} />
      </section>

      {sourcesNeedingApproval > 0 && (
        <Link
          to="/breakdowns"
          className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm font-medium text-amber-900 shadow-sm transition hover:border-amber-300"
        >
          {sourcesNeedingApproval} new breakdown source{sourcesNeedingApproval === 1 ? "" : "s"} need approval.
        </Link>
      )}

      {enabledWidgets.length === 0 ? (
        <EmptyState>All dashboard widgets are hidden. Open Widgets and turn at least one back on.</EmptyState>
      ) : (
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={(event) => void onDragEnd(event).catch(() => undefined)}>
          <SortableContextCompat items={enabledIds} strategy={rectSortingStrategy}>
            <div className="grid auto-rows-fr gap-4 md:grid-cols-2 xl:grid-cols-4">
              {enabledWidgets.map((widget) => (
                <DashboardSortableWidget key={widget.widget_id} widget={widget} focused={focusedWidgetIds.includes(widget.widget_id)}>
                  {widgetDefinitions.find((definition) => definition.id === widget.widget_id)?.render(readData) ?? (
                    <WidgetBody metric={0} items={[]} empty="Widget not configured." />
                  )}
                </DashboardSortableWidget>
              ))}
            </div>
          </SortableContextCompat>
        </DndContext>
      )}

      <div className="sr-only">
        {widgetDefinitions.map((definition) => (
          <Link key={definition.id} to={definition.linkTo}>{definition.id}</Link>
        ))}
      </div>
    </div>
  );
}

export function DashboardQuickActions({ compact = false, careerTasks = [] }: { compact?: boolean; careerTasks?: CareerDevelopmentTask[] }) {
  const quickActions = getDashboardQuickActions(careerTasks);
  return (
    <div className={`grid gap-2 ${compact ? "sm:grid-cols-2" : "sm:grid-cols-2 lg:grid-cols-4"}`}>
      {quickActions.map((action) => {
        const Icon = action.icon;
        return (
          <Link
            key={action.label}
            to={action.to}
            className="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-ink transition hover:bg-slate-50"
          >
            <Icon className="h-4 w-4 text-accent" />
            {action.label}
          </Link>
        );
      })}
    </div>
  );
}

export function getDashboardQuickActions(careerTasks: CareerDevelopmentTask[] = []) {
  const icons = {
    "Add Audition": Clapperboard,
    "Import Breakdown": BriefcaseBusiness,
    "Upload Material": FolderUp,
    "Prepare Audition": BookOpenCheck,
    "Create Career Task": Lightbulb,
    "Generate Strategy": Sparkles,
    "Create Stretch Role Plan": FilePlus2,
    "Generate Quarterly Review": RotateCcw,
    "Find Scene Options": Search
  };
  return getDashboardQuickActionLinks(careerTasks).map((action) => ({
    ...action,
    icon: icons[action.label as keyof typeof icons]
  }));
}

function DashboardSortableWidget({ widget, children, focused }: { widget: DashboardWidget; children: ReactNode; focused: boolean }) {
  const definition = widgetDefinitions.find((item) => item.id === widget.widget_id);
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: widget.widget_id });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition
  };
  const sizeClass = widget.size === "large" ? "md:col-span-2" : widget.size === "small" ? "" : "";

  return (
    <article
      ref={setNodeRef}
      style={style}
      className={`flex min-h-48 flex-col rounded-lg border bg-white p-4 shadow-sm ${sizeClass} ${focused ? "border-blue-300 ring-2 ring-blue-100" : "border-slate-200"} ${isDragging ? "z-10 opacity-80 ring-2 ring-accent" : ""}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="font-semibold text-ink">{widget.display_name}</h3>
          {focused && <Badge>Focus</Badge>}
          <Link className="mt-1 inline-block text-xs font-semibold text-accent hover:underline" to={definition?.linkTo ?? "/"}>
            Open full page
          </Link>
        </div>
        <button
          type="button"
          className="rounded-md border border-slate-200 p-2 text-slate-500 hover:bg-slate-50"
          aria-label={`Drag ${widget.display_name}`}
          {...attributes}
          {...listeners}
        >
          <GripVertical className="h-4 w-4" />
        </button>
      </div>
      <div className="mt-4 flex flex-1 flex-col">{children}</div>
    </article>
  );
}

function WidgetBody({ metric, items, empty }: { metric: number; items: string[]; empty: string }) {
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

function OpportunityPrioritiesWidget({ opportunities }: { opportunities: CommandCenterCard[] }) {
  return (
    <div className="flex flex-1 flex-col">
      <div className="flex items-center justify-between gap-2">
        <p className="text-3xl font-bold text-ink">{opportunities.length}</p>
        {opportunities.length > 0 && <Badge>Active</Badge>}
      </div>
      <div className="mt-3 grid gap-2 text-sm text-slate-700">
        {opportunities.length === 0 ? (
          <p className="text-slate-500">No priority breakdowns today.</p>
        ) : opportunities.slice(0, 3).map((opportunity, index) => (
          <OpportunityPriorityCard
            key={opportunity.id ?? `${opportunity.role ?? "role"}-${index}`}
            opportunity={opportunity}
          />
        ))}
      </div>
    </div>
  );
}

export function OpportunityPriorityCard({ opportunity }: { opportunity: CommandCenterCard }) {
  const intelligence = isVersionOneIntelligence(opportunity.intelligence)
    ? opportunity.intelligence
    : null;
  const contributors = intelligence
    ? [
        ...intelligence.top_positive_contributors.map((item) => ({ ...item, kind: "Positive" })),
        ...intelligence.top_negative_contributors.map((item) => ({ ...item, kind: "Negative" }))
      ]
    : [];

  return (
    <div className="rounded bg-slate-50 px-2 py-1">
      <p className="font-medium text-ink">{String(opportunity.role ?? "Role")}</p>
      <p>{String(opportunity.project ?? "Project")}</p>
      {intelligence && (
        <div
          className="mt-1 grid gap-1"
          aria-label={`Opportunity intelligence: ${intelligence.action_label}; score ${intelligence.overall_score} of 100`}
        >
          <p><span className="font-semibold">{intelligence.action_label}</span></p>
          <p>Score {intelligence.overall_score} of 100 · {intelligence.confidence.level} confidence</p>
          {intelligence.hard_override_reason && (
            <p>Reason: {intelligence.hard_override_reason.split("_").join(" ")}</p>
          )}
          {contributors.length > 0 && (
            <details>
              <summary className="cursor-pointer font-medium">Why this score</summary>
              <ul className="mt-1 grid gap-1">
                {contributors.map((contributor) => (
                  <li key={`${contributor.kind}-${contributor.id}`}>
                    {contributor.kind}: {contributor.explanation ?? contributor.id} ({contributor.points > 0 ? "+" : ""}{contributor.points})
                  </li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}
    </div>
  );
}

function isVersionOneIntelligence(
  value: CommandCenterCard["intelligence"]
): value is OpportunityIntelligenceSummary {
  return Boolean(
    value
      && value.version === 1
      && "overall_score" in value
      && typeof value.overall_score === "number"
      && value.overall_score >= 0
      && value.overall_score <= 100
      && "action_label" in value
      && "confidence" in value
      && "top_positive_contributors" in value
      && Array.isArray(value.top_positive_contributors)
      && "top_negative_contributors" in value
      && Array.isArray(value.top_negative_contributors)
  );
}

export function PlatformCheckInWidget({ commandCenter }: { commandCenter: import("../../../types/domain").ActorCommandCenter | null }) {
  const checkIn = usePlatformCheckIn();
  const checkIns = commandCenter?.platform_check_ins ?? [];
  async function toggle(subscriptionId: string, checked: boolean) {
    try {
      await checkIn.mutateAsync({ subscriptionId, checkedToday: checked });
    } catch {
      // Mutation error remains available for standardized presentation below.
    }
  }
  if (checkIns.length === 0) {
    return (
      <div className="grid gap-2 text-sm text-slate-600">
        <p>No active subscribed platforms are configured.</p>
        <Link to="/settings" className="font-semibold text-accent hover:underline">Set up platform subscriptions</Link>
      </div>
    );
  }
  const { checkedCount, totalCount } = getPlatformCheckInSummary({ commandCenter });
  return (
    <div className="grid gap-3">
      {checkIn.isError && <p className="text-xs text-red-700" role="alert">Could not update this platform check-in.</p>}
      <div className="flex items-center justify-between gap-2">
        <p className="text-3xl font-bold text-ink">{checkedCount}/{totalCount}</p>
        <Badge>{checkedCount === totalCount ? "Done" : "Check Today"}</Badge>
      </div>
      <div className="grid gap-2">
        {checkIns.map((item) => (
          <label key={item.id} className="flex items-center justify-between gap-3 rounded bg-slate-50 px-2 py-2 text-sm">
            <span>
              <span className="font-semibold text-ink">{item.platform_name}</span>
              {item.subscription_level && <span className="ml-1 text-slate-500">· {item.subscription_level}</span>}
            </span>
            <input
              name={`platform_check_in_${item.platform_subscription_id}`}
              disabled={checkIn.isPending}
              type="checkbox"
              checked={item.checked_today}
              onChange={(event) => void toggle(item.platform_subscription_id, event.target.checked)}
            />
          </label>
        ))}
      </div>
      <p className="text-xs text-slate-500">Manual check-in only. The app does not log in, scrape, or submit.</p>
    </div>
  );
}

function recommendationsByType(data: DashboardReadData, matchType: string) {
  return data.recommendations.filter((recommendation) => recommendation.match_type === matchType);
}

function recommendationLabel(data: DashboardReadData, opportunityId: string) {
  return findOpportunityLabel(data, opportunityId);
}

function findOpportunityLabel(data: DashboardReadData, opportunityId: string) {
  const opportunity = [...data.opportunities, ...data.hiddenOpportunities].find((item) => item.id === opportunityId);
  return opportunity ? `${opportunity.role} · ${opportunity.project}` : "Breakdown";
}

function formatDate(value?: string | null) {
  if (!value) return "No date";
  return new Date(value).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}
