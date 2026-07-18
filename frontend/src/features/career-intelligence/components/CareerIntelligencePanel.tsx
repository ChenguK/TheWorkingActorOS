import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react";
import { useLocation } from "react-router-dom";
import { Badge, Button, DetailDisclosure, EmptyState, Field, Section, inputClass } from "../../../components/ui";
import { simulateCareerPath } from "../api";
import {
  useCareerTasks, useCareerSwot, useCastingOffices, useQuarterlyReviews, useDreamReadiness,
  useCastingGoals, useWatchLists, useCareerMemory, useCompleteCareerTask, useCreateWatchList,
  useUpdateWatchList, useDeleteWatchList, useGenerateQuarterlyReview, useCreateCastingGoal,
  useUpdateCastingGoal, useDeleteCastingGoal, useGenerateCareerSwot, useUpdateCareerMemory
} from "../hooks/useCareerQueries";
import {
  AIIntelligencePanel,
  CareerDevelopmentDashboard
} from "./CareerLegacyPanels";
import { ChiefOfStaffPanel } from "@/features/chief-of-staff";
import type { CareerDevelopmentTask, CareerMemory, CareerPathSimulation, CareerSwotAnalysis, CastingGoal, CastingGoalStatus, CastingGoalType, CastingOffice, DreamRoleReadiness, IndustryTrendDashboard, IntelligenceDashboard, QuarterlyCareerReview, WatchList, WatchListCategory } from "../../../types/domain";
import { useIndustryTrends, useIntelligenceDashboard } from "../../analytics";
import type { RelationshipAnalytics } from "../../../types/domain";
import { useRelationshipAnalytics } from "../../relationships";
import { useMaterialOptions } from "../../materials";
import { useActorProfile } from "../../profile";
import { useBreakdowns } from "../../breakdowns";

const goalTypes: CastingGoalType[] = ["TV", "Film", "Streaming", "Guest Star", "Recurring", "Lead", "Supporting", "Commercial", "Voiceover", "Theater", "Other"];
const goalStatuses: CastingGoalStatus[] = ["Active", "Paused", "Completed", "Archived"];
const watchListCategories: WatchListCategory[] = ["Studios", "Networks", "Streaming Platforms", "Shows", "Genres", "Project Types", "Casting Offices", "Casting Directors", "Production Companies", "Archetypes", "Role Types", "Markets", "Cities", "States", "Countries", "Keywords"];
const priorityOptions: WatchList["priority"][] = ["Low", "Medium", "High"];

type CareerPageInputs = { capabilities: import("../../../types/domain").SystemCapabilities | null; submissions: import("../../../types/domain").Submission[] };
type CareerReadData = CareerPageInputs & {
  actor: import("../../../types/domain").ActorProfile | null;
  opportunities: import("../../../types/domain").Opportunity[];
  intelligenceDashboard: IntelligenceDashboard | null;
  industryTrends: IndustryTrendDashboard | null;
  careerTasks: CareerDevelopmentTask[];
  careerSwot: CareerSwotAnalysis | null;
  castingOffices: CastingOffice[];
  quarterlyReviews: QuarterlyCareerReview[];
  dreamReadiness: DreamRoleReadiness[];
  castingGoals: CastingGoal[];
  watchLists: WatchList[];
};

export function CareerIntelligencePanel({ data }: { data: CareerPageInputs }) {
  const location = useLocation();
  const relationshipAnalytics = useRelationshipAnalytics();
  const intelligenceDashboard = useIntelligenceDashboard();
  const industryTrends = useIndustryTrends();
  const tasks = useCareerTasks(); const swot = useCareerSwot(); const offices = useCastingOffices();
  const reviews = useQuarterlyReviews(); const readiness = useDreamReadiness(); const goals = useCastingGoals(); const watchLists = useWatchLists();
  const memory = useCareerMemory(); const updateMemory = useUpdateCareerMemory();
  const materialOptions = useMaterialOptions();
  const actor = useActorProfile();
  const opportunities = useBreakdowns();
  const careerQueries = [
    ["tasks", tasks], ["SWOT", swot], ["casting offices", offices], ["quarterly reviews", reviews],
    ["dream readiness", readiness], ["casting goals", goals], ["watch lists", watchLists], ["career memory", memory]
  ] as const;
  const readData: CareerReadData = { ...data, actor: actor.data ?? null, opportunities: opportunities.data ?? [], intelligenceDashboard: intelligenceDashboard.data ?? null, industryTrends: industryTrends.data ?? null,
    careerTasks: tasks.data ?? [], careerSwot: swot.data ?? null, castingOffices: offices.data ?? [], quarterlyReviews: reviews.data ?? [],
    dreamReadiness: readiness.data ?? [], castingGoals: goals.data ?? [], watchLists: watchLists.data ?? [] };

  useEffect(() => {
    if (!location.hash) return;
    window.requestAnimationFrame(() => {
      document.querySelector(location.hash)?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }, [location.hash]);

  return (
    <div className="grid gap-4">
      {careerQueries.some(([, query]) => query.isLoading) && <p className="text-sm text-slate-600" role="status">Loading Career data...</p>}
      {careerQueries.filter(([, query]) => query.isError).map(([label]) => (
        <p key={label} className="rounded bg-red-50 p-2 text-sm text-red-700" role="alert">Career {label} could not load. Other sections remain usable.</p>
      ))}
      <CareerIntelligenceHeader data={readData} />
      <CareerPageGroup
        title="Career Planning"
        subtitle="What should I build next?"
      >
        <NextBestActionWidget data={readData} />
        <CareerRoadmapSection data={readData} />
        <div id="script-finder">
          <CareerDevelopmentDashboard actor={actor.data ?? null} tasks={readData.careerTasks} assets={materialOptions.data ?? []} />
        </div>
        <RolePursuitSection data={readData} />
        <MaterialGapAnalysisSection data={readData} />
        <DreamRolesSection data={readData} />
        <CastingGoalsPanel data={readData} />
        <WatchListDashboard data={readData} />
        <QuarterlyReviewsSection data={readData} />
        <CareerPathSimulatorSection />
        <CareerSwotSection data={readData} />
      </CareerPageGroup>
      <CareerPageGroup
        title="Career Intelligence"
        subtitle="What have I learned about my career?"
      >
        <ChiefOfStaffPanel memory={memory.data ?? null} onSaveMemory={(patch) => updateMemory.mutateAsync(patch)} />
        <AIIntelligencePanel
          dashboard={readData.intelligenceDashboard}
          castingOffices={readData.castingOffices}
          opportunities={readData.opportunities}
          careerTasks={readData.careerTasks}
          capabilities={data.capabilities}
        />
        <RoleSimilaritySection data={readData} />
        <IndustryTrendsSection data={readData} />
        <RelationshipInsightsSection analytics={relationshipAnalytics.data ?? null} />
        <CareerTimelineSection data={readData} />
      </CareerPageGroup>
    </div>
  );
}

function CareerPageGroup({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <section className="grid gap-4 rounded-lg border border-slate-200 bg-white/60 p-3">
      <div>
        <h2 className="text-lg font-bold text-ink">{title}</h2>
        <p className="mt-1 text-sm text-slate-600">{subtitle}</p>
      </div>
      {children}
    </section>
  );
}

function CareerIntelligenceHeader({ data }: { data: CareerReadData }) {
  const activeTasks = data.careerTasks.filter((task) => task.status !== "Completed");
  const callbacks = data.submissions.filter((submission) => ["Requested", "Self-Tape Callback", "In-Person Callback", "Pinned", "Booked"].includes(submission.current_status)).length;
  const bookings = data.submissions.filter((submission) => submission.current_status === "Booked").length;
  const topArchetypes = data.intelligenceDashboard?.archetype_performance.best_performing_archetypes ?? [];
  const careerState = data.capabilities?.states.career_agent_recommendations;
  return (
    <Section title="Career Intelligence Center">
      <div className="grid gap-4">
        <div>
          <h2 className="text-xl font-semibold text-ink">Where am I today?</h2>
          <p className="mt-1 text-sm text-slate-600">
            This center turns outcomes, materials, goals, relationships, your casting patterns, and watch lists into explainable next steps.
          </p>
          {careerState && careerState.state === "Early Recommendation" && (
            <p className="mt-2 inline-flex rounded-md border border-amber-200 bg-amber-50 px-2 py-1 text-xs font-medium text-amber-900">
              Early Recommendation: {careerState.explanation}
            </p>
          )}
        </div>
        <div className="grid gap-3 md:grid-cols-4">
          <CareerMetric title="Submissions" value={data.submissions.length} note={`${callbacks} callback or better`} />
          <CareerMetric title="Bookings" value={bookings} note="Manual outcomes tracked" />
          <CareerMetric title="Open Tasks" value={activeTasks.length} note="Career materials and goals" />
          <CareerMetric title="Top Lanes" value={topArchetypes.length || "TBD"} note={topArchetypes.slice(0, 2).join(", ") || "Track outcomes to learn"} />
        </div>
      </div>
    </Section>
  );
}

function CareerMetric({ title, value, note }: { title: string; value: string | number; note: string }) {
  return (
    <div className="rounded-md border border-slate-200 bg-white p-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</p>
      <p className="mt-1 text-2xl font-semibold text-ink">{value}</p>
      <p className="mt-1 text-sm text-slate-600">{note}</p>
    </div>
  );
}

function NextBestActionWidget({ data }: { data: CareerReadData }) {
  const completeTask = useCompleteCareerTask();
  const action = useMemo(() => nextBestAction(data), [data]);
  return (
    <Section title="Next Best Action">
      <div className="rounded-md border border-amber-200 bg-amber-50 p-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <Badge>{action.priority}</Badge>
            <h3 className="mt-2 text-lg font-semibold text-ink">{action.title}</h3>
            <p className="mt-1 text-sm text-slate-700">{action.description}</p>
            <p className="mt-2 text-sm text-amber-900"><strong>Why:</strong> {action.why}</p>
          </div>
          {action.taskId ? (
            <Button variant="secondary" onClick={() => completeTask.mutateAsync(action.taskId)}>Mark Complete</Button>
          ) : null}
        </div>
      </div>
    </Section>
  );
}

function nextBestAction(data: CareerReadData) {
  const highTask = data.careerTasks.find((task) => task.status !== "Completed" && task.priority === "High");
  if (highTask) {
    return {
      title: highTask.title,
      description: highTask.description,
      priority: "High Impact",
      why: highTask.reason || "This task is already tied to a career recommendation or material gap.",
      taskId: highTask.id
    };
  }
  const watch = data.watchLists.find((item) => item.enabled && item.priority === "High");
  if (watch) {
    return {
      title: `Target ${watch.terms[0] ?? watch.title}`,
      description: `Prioritize breakdowns and materials connected to ${watch.title}.`,
      priority: "Watch List",
      why: "You explicitly told the app this is important to watch for.",
      taskId: null
    };
  }
  return {
    title: "Create a career development task",
    description: "Add one material, role, or relationship action so recommendations can become trackable progress.",
    priority: "Setup",
    why: "The app needs an actionable goal or task to connect recommendations to measurable career movement.",
    taskId: null
  };
}

function CareerRoadmapSection({ data }: { data: CareerReadData }) {
  const working = data.intelligenceDashboard?.archetype_performance.best_performing_archetypes ?? [];
  const stopDoing = data.intelligenceDashboard?.archetype_performance.overused_archetypes ?? [];
  const nextBuilds = data.careerTasks.filter((task) => task.status !== "Completed").slice(0, 4);
  const archetypeState = data.capabilities?.states.archetype_performance;
  const hasArchetypePerformance = !archetypeState || archetypeState.state === "Configured";
  return (
    <Section title="Career Roadmap">
      <div className="grid gap-3 lg:grid-cols-3">
        <RoadmapCard title="What is working?" items={hasArchetypePerformance ? working : []} empty={hasArchetypePerformance ? "Outcome data will identify your strongest archetypes." : "Insufficient Data. Track more submissions to unlock this insight."} />
        <RoadmapCard title="What should I build next?" items={nextBuilds.map((task) => task.title)} empty="Create tasks or run Career recommendations to generate material steps." />
        <RoadmapCard title="What should I stop doing?" items={hasArchetypePerformance ? stopDoing : []} empty={hasArchetypePerformance ? "No overused lanes detected yet." : "Add Data First. Track more submissions to unlock this insight."} />
      </div>
    </Section>
  );
}

function RoadmapCard({ title, items, empty }: { title: string; items: string[]; empty: string }) {
  return (
    <div className="rounded-md border border-slate-200 p-3 text-sm">
      <h3 className="font-semibold text-ink">{title}</h3>
      {items.length === 0 ? <p className="mt-2 text-slate-500">{empty}</p> : (
        <ul className="mt-2 grid gap-1">
          {items.slice(0, 5).map((item) => <li key={item}>{item}</li>)}
        </ul>
      )}
    </div>
  );
}

function WatchListDashboard({ data }: { data: CareerReadData }) {
  const create = useCreateWatchList(); const update = useUpdateWatchList(); const remove = useDeleteWatchList();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState({
    title: "",
    category: "Keywords" as WatchListCategory,
    terms: "",
    enabled: true,
    priority: "High" as WatchList["priority"],
    notes: ""
  });

  function resetForm() {
    setEditingId(null);
    setForm({ title: "", category: "Keywords", terms: "", enabled: true, priority: "High", notes: "" });
  }

  function editWatchList(item: WatchList) {
    setEditingId(item.id);
    setForm({
      title: item.title,
      category: item.category,
      terms: item.terms.join(", "),
      enabled: item.enabled,
      priority: item.priority,
      notes: item.notes ?? ""
    });
  }

  async function saveWatchList(event: FormEvent) {
    event.preventDefault();
    const payload = {
      actor_profile_id: data.actor?.id ?? null,
      title: form.title.trim(),
      category: form.category,
      terms: splitGoalList(form.terms),
      enabled: form.enabled,
      priority: form.priority,
      notes: form.notes.trim() || null
    };
    if (editingId) {
      await update.mutateAsync({ id: editingId, patch: payload });
    } else {
      await create.mutateAsync(payload);
    }
    resetForm();
  }

  return (
    <Section title="Watch List Dashboard">
      <div className="grid gap-4">
        <form className="grid gap-3 rounded-md border border-slate-200 p-3 lg:grid-cols-4" onSubmit={saveWatchList}>
          <Field label="Watch List Name"><input className={inputClass} value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} required placeholder="Attorney roles on streaming dramas" /></Field>
          <Field label="Category"><select className={inputClass} value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value as WatchListCategory })}>{watchListCategories.map((category) => <option key={category}>{category}</option>)}</select></Field>
          <Field label="Priority"><select className={inputClass} value={form.priority} onChange={(event) => setForm({ ...form, priority: event.target.value as WatchList["priority"] })}>{priorityOptions.map((priority) => <option key={priority}>{priority}</option>)}</select></Field>
          <label className="flex items-center gap-2 text-sm text-slate-700"><input name="watch_list_enabled" type="checkbox" checked={form.enabled} onChange={(event) => setForm({ ...form, enabled: event.target.checked })} />Enabled</label>
          <div className="lg:col-span-2"><Field label="Terms To Watch For"><input className={inputClass} value={form.terms} onChange={(event) => setForm({ ...form, terms: event.target.value })} required placeholder="Attorney, Detective, Political Drama, Recurring" /></Field></div>
          <div className="lg:col-span-2"><Field label="Notes"><input className={inputClass} value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} /></Field></div>
          <div className="flex flex-wrap items-end gap-2 lg:col-span-4">
            <Button type="submit">{editingId ? "Save Watch List" : "Create Watch List"}</Button>
            {editingId && <Button variant="secondary" onClick={resetForm}>Cancel Edit</Button>}
          </div>
        </form>

        {data.watchLists.length === 0 ? <EmptyState>No Watch Lists yet. Add studios, roles, markets, offices, or keywords you want the app to prioritize.</EmptyState> : (
          <div className="grid gap-3 lg:grid-cols-2">
            {data.watchLists.map((item) => (
              <article key={item.id} className="rounded-md border border-slate-200 p-3 text-sm">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="font-semibold">{item.title}</h3>
                    <p className="text-slate-600">{item.category} · {item.priority} priority</p>
                  </div>
                  <Badge>{item.enabled ? "Enabled" : "Disabled"}</Badge>
                </div>
                <p className="mt-2"><strong>Watching:</strong> {item.terms.join(", ")}</p>
                {item.notes && <p className="mt-1 text-slate-600">{item.notes}</p>}
                <p className="mt-2 text-xs text-slate-500">
                  Matches: {item.match_count}{item.last_matched_at ? ` · Last matched ${new Date(item.last_matched_at).toLocaleString()}` : ""}
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button variant="secondary" onClick={() => editWatchList(item)}>Edit</Button>
                  <Button variant="secondary" onClick={() => update.mutateAsync({ id: item.id, patch: { enabled: !item.enabled } })}>{item.enabled ? "Disable" : "Enable"}</Button>
                  <Button variant="danger" onClick={() => remove.mutateAsync(item.id)}>Delete</Button>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </Section>
  );
}

function RolePursuitSection({ data }: { data: CareerReadData }) {
  return (
    <Section title="Roles To Pursue">
      <div className="grid gap-4 lg:grid-cols-3">
        <RoleColumn title="Strong Matches" roles={[]} fallback="Bookings, callbacks, and asset coverage will identify strong matches." />
        <RoleColumn title="Growth Roles" roles={[]} fallback="Adjacent role lanes appear after you add assets, outcomes, or goals." />
        <RoleColumn title="Stretch Roles" roles={[]} fallback="Stretch roles appear when the Career Agent sees plausible expansion lanes." />
      </div>
    </Section>
  );
}

function RoleColumn({ title, roles, fallback }: { title: string; roles: unknown[]; fallback: string }) {
  return (
    <div className="rounded-md border border-slate-200 p-3 text-sm">
      <h3 className="font-semibold text-ink">{title}</h3>
      {roles.length === 0 ? <p className="mt-2 text-slate-500">{fallback}</p> : (
        <div className="mt-3 grid gap-2">
          {roles.slice(0, 6).map((role, index) => {
            const item = role as Record<string, unknown>;
            return (
              <div key={`${title}-${index}`} className="rounded bg-slate-50 p-2">
                <p className="font-semibold">{displayRoleName(role)}</p>
                {typeof item.archetype === "string" && <p>Archetype: {item.archetype}</p>}
                {typeof item.why === "string" && <DetailDisclosure label="Why?">{item.why}</DetailDisclosure>}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function displayRoleName(value: unknown): string {
  if (typeof value === "string") return value;
  if (value && typeof value === "object") {
    const item = value as Record<string, unknown>;
    return String(item.role ?? item.archetype ?? item.match_type ?? "Role");
  }
  return "Role";
}

function MaterialGapAnalysisSection({ data }: { data: CareerReadData }) {
  const materialTasks = data.careerTasks.filter((task) =>
    /headshot|reel|scene|slate|resume|material|self-tape/i.test(`${task.title} ${task.description}`)
  );
  const stretchGaps: string[] = ([] as unknown[]).flatMap((role) => {
    const item = role as Record<string, unknown>;
    return Array.isArray(item.missing_assets) ? item.missing_assets.map((asset) => `${String(item.role ?? item.archetype)}: ${String(asset)}`) : [];
  });
  return (
    <Section title="Material Gap Analysis">
      <div className="grid gap-3 lg:grid-cols-2">
        <div className="rounded-md border border-slate-200 p-3 text-sm">
          <h3 className="font-semibold">Missing Materials</h3>
          {[...stretchGaps, ...materialTasks.map((task) => task.title)].length === 0 ? (
            <p className="mt-2 text-slate-500">No material gaps identified yet.</p>
          ) : (
            <ul className="mt-2 grid gap-1">
              {[...stretchGaps, ...materialTasks.map((task) => task.title)].slice(0, 10).map((item) => <li key={item}>{item}</li>)}
            </ul>
          )}
        </div>
        <div className="rounded-md border border-slate-200 p-3 text-sm">
          <h3 className="font-semibold">Actionable Tasks</h3>
          {materialTasks.length === 0 ? <p className="mt-2 text-slate-500">Create a material task to connect this gap to action.</p> : materialTasks.slice(0, 6).map((task) => (
            <div key={task.id} className="mt-2 rounded bg-slate-50 p-2">
              <p className="font-semibold">{task.title}</p>
              <p>{task.status} · {task.priority} · impact {task.estimated_impact}</p>
              {task.reason && <DetailDisclosure label="Why?">{task.reason}</DetailDisclosure>}
            </div>
          ))}
        </div>
      </div>
    </Section>
  );
}

function DreamRolesSection({ data }: { data: CareerReadData }) {
  return (
    <Section title="Dream Roles">
      {data.dreamReadiness.length === 0 ? <EmptyState>No dream roles yet. Add dream targets in the advanced intelligence workflow or create Casting Goals to guide recommendations.</EmptyState> : (
        <div className="grid gap-3 lg:grid-cols-3">
          {data.dreamReadiness.map((item) => (
            <article key={item.target.id} className="rounded-md border border-slate-200 p-3 text-sm">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="font-semibold">{item.target.name}</h3>
                  <p className="text-slate-600">{item.target.target_type}</p>
                </div>
                <Badge>{item.current_readiness_score}%</Badge>
              </div>
              <p className="mt-2">{item.explanation}</p>
              <p className="mt-2"><strong>Missing:</strong> {item.missing_materials.join(", ") || "No major gaps"}</p>
              <p><strong>Actions:</strong> {item.recommended_actions.join(", ") || "No actions yet"}</p>
            </article>
          ))}
        </div>
      )}
    </Section>
  );
}

function QuarterlyReviewsSection({ data }: { data: CareerReadData }) {
  const generate = useGenerateQuarterlyReview();
  const now = new Date();
  const [form, setForm] = useState({ year: String(now.getFullYear()), quarter: String(Math.floor(now.getMonth() / 3) + 1) });
  async function generateReview(event: FormEvent) {
    event.preventDefault();
    await generate.mutateAsync({ year: Number(form.year), quarter: Number(form.quarter) });
  }
  return (
    <Section title="Quarterly Reviews">
      <div className="grid gap-4 lg:grid-cols-3">
        <form className="rounded-md border border-slate-200 p-3" onSubmit={generateReview}>
          <h3 className="font-semibold">Generate Review</h3>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            <Field label="Year"><input className={inputClass} type="number" value={form.year} onChange={(event) => setForm({ ...form, year: event.target.value })} /></Field>
            <Field label="Quarter"><select className={inputClass} value={form.quarter} onChange={(event) => setForm({ ...form, quarter: event.target.value })}><option value="1">Q1</option><option value="2">Q2</option><option value="3">Q3</option><option value="4">Q4</option></select></Field>
          </div>
          <Button type="submit">Generate Review</Button>
        </form>
        <div className="grid gap-3 lg:col-span-2">
          {data.quarterlyReviews.length === 0 ? <EmptyState>No quarterly reviews yet.</EmptyState> : data.quarterlyReviews.slice(0, 3).map((review) => (
            <article key={review.id} className="rounded-md border border-slate-200 p-3 text-sm">
              <h3 className="font-semibold">Q{review.quarter} {review.year}</h3>
              <p className="mt-1">{review.explanation}</p>
              <DetailDisclosure label="Report">
                <pre className="whitespace-pre-wrap rounded bg-slate-50 p-2 text-xs">{JSON.stringify(review.report, null, 2)}</pre>
              </DetailDisclosure>
            </article>
          ))}
        </div>
      </div>
    </Section>
  );
}

function CareerPathSimulatorSection() {
  const [goal, setGoal] = useState("If I want to book recurring TV roles within 2 years, what should I do next?");
  const [simulation, setSimulation] = useState<CareerPathSimulation | null>(null);
  async function simulate(event: FormEvent) {
    event.preventDefault();
    setSimulation(await simulateCareerPath(goal));
  }
  return (
    <Section title="Career Path Simulator">
      <form className="grid gap-3 rounded-md border border-slate-200 p-3" onSubmit={simulate}>
        <Field label="Career Question">
          <textarea className={inputClass} value={goal} onChange={(event) => setGoal(event.target.value)} />
        </Field>
        <Button type="submit">Simulate Path</Button>
      </form>
      {simulation && (
        <div className="mt-3 rounded-md border border-blue-200 bg-blue-50 p-3 text-sm">
          <h3 className="font-semibold">Recommended Path</h3>
          <pre className="mt-2 whitespace-pre-wrap rounded bg-white p-2 text-xs">{JSON.stringify(simulation.result, null, 2)}</pre>
          <p className="mt-2"><strong>Why:</strong> {simulation.explanation}</p>
        </div>
      )}
    </Section>
  );
}

function CastingGoalsPanel({ data }: { data: CareerReadData }) {
  const create = useCreateCastingGoal(); const update = useUpdateCastingGoal(); const remove = useDeleteCastingGoal();
  const [form, setForm] = useState({
    title: "",
    goal_type: "TV" as CastingGoalType,
    target_archetypes: "",
    target_role_types: "",
    target_project_types: "",
    target_markets: "",
    target_casting_offices: "",
    target_deadline: "",
    priority: "High" as CastingGoal["priority"],
    status: "Active" as CastingGoalStatus,
    notes: ""
  });

  async function createGoal(event: FormEvent) {
    event.preventDefault();
    await create.mutateAsync({
      actor_profile_id: data.actor?.id ?? null,
      title: form.title,
      goal_type: form.goal_type,
      target_archetypes: splitGoalList(form.target_archetypes),
      target_role_types: splitGoalList(form.target_role_types),
      target_project_types: splitGoalList(form.target_project_types),
      target_markets: splitGoalList(form.target_markets),
      target_casting_offices: splitGoalList(form.target_casting_offices),
      target_deadline: form.target_deadline || null,
      priority: form.priority,
      status: form.status,
      notes: form.notes || null
    });
    setForm({ title: "", goal_type: "TV", target_archetypes: "", target_role_types: "", target_project_types: "", target_markets: "", target_casting_offices: "", target_deadline: "", priority: "High", status: "Active", notes: "" });
  }

  return (
    <Section title="Casting Goals">
      <div className="grid gap-4">
        <form className="grid gap-3 rounded-md border border-slate-200 p-3 lg:grid-cols-4" onSubmit={createGoal}>
          <Field label="Goal Title"><input className={inputClass} value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} required placeholder="Build toward recurring TV roles" /></Field>
          <Field label="Goal Type"><select className={inputClass} value={form.goal_type} onChange={(event) => setForm({ ...form, goal_type: event.target.value as CastingGoalType })}>{goalTypes.map((type) => <option key={type}>{type}</option>)}</select></Field>
          <Field label="Priority"><select className={inputClass} value={form.priority} onChange={(event) => setForm({ ...form, priority: event.target.value as CastingGoal["priority"] })}><option>Low</option><option>Medium</option><option>High</option></select></Field>
          <Field label="Status"><select className={inputClass} value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value as CastingGoalStatus })}>{goalStatuses.map((status) => <option key={status}>{status}</option>)}</select></Field>
          <Field label="Target Archetypes"><input className={inputClass} value={form.target_archetypes} onChange={(event) => setForm({ ...form, target_archetypes: event.target.value })} placeholder="Attorney, Executive" /></Field>
          <Field label="Target Role Types"><input className={inputClass} value={form.target_role_types} onChange={(event) => setForm({ ...form, target_role_types: event.target.value })} placeholder="Guest Star, Recurring" /></Field>
          <Field label="Target Project Types"><input className={inputClass} value={form.target_project_types} onChange={(event) => setForm({ ...form, target_project_types: event.target.value })} placeholder="TV, Streaming" /></Field>
          <Field label="Target Markets"><input className={inputClass} value={form.target_markets} onChange={(event) => setForm({ ...form, target_markets: event.target.value })} placeholder="NY, Atlanta" /></Field>
          <Field label="Target Casting Offices"><input className={inputClass} value={form.target_casting_offices} onChange={(event) => setForm({ ...form, target_casting_offices: event.target.value })} /></Field>
          <Field label="Target Deadline"><input className={inputClass} type="date" value={form.target_deadline} onChange={(event) => setForm({ ...form, target_deadline: event.target.value })} /></Field>
          <div className="lg:col-span-2"><Field label="Notes"><input className={inputClass} value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} /></Field></div>
          <div className="flex items-end"><Button type="submit">Add Goal</Button></div>
        </form>

        {data.castingGoals.length === 0 ? <EmptyState>No casting goals yet.</EmptyState> : (
          <div className="grid gap-3 lg:grid-cols-2">
            {data.castingGoals.map((goal) => (
              <article key={goal.id} className="rounded-md border border-slate-200 p-3 text-sm">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="font-semibold">{goal.title}</h3>
                    <p className="text-slate-600">{goal.goal_type} · {goal.priority} · {goal.status}</p>
                  </div>
                  <div className="flex gap-2">
                    <select name={`casting_goal_status_${goal.id}`} className={inputClass} value={goal.status} onChange={(event) => update.mutateAsync({ id: goal.id, patch: { status: event.target.value as CastingGoalStatus } })}>
                      {goalStatuses.map((status) => <option key={status}>{status}</option>)}
                    </select>
                    <Button variant="danger" onClick={() => remove.mutateAsync(goal.id)}>Delete</Button>
                  </div>
                </div>
                <div className="mt-3 grid gap-1 text-slate-700">
                  {goal.target_archetypes.length > 0 && <p><strong>Archetypes:</strong> {goal.target_archetypes.join(", ")}</p>}
                  {goal.target_role_types.length > 0 && <p><strong>Role types:</strong> {goal.target_role_types.join(", ")}</p>}
                  {goal.target_project_types.length > 0 && <p><strong>Projects:</strong> {goal.target_project_types.join(", ")}</p>}
                  {goal.target_casting_offices.length > 0 && <p><strong>Casting offices:</strong> {goal.target_casting_offices.join(", ")}</p>}
                  {goal.notes && <p>{goal.notes}</p>}
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </Section>
  );
}

function CareerSwotSection({ data }: { data: CareerReadData }) {
  const generate = useGenerateCareerSwot();
  return (
    <Section title="Career SWOT Analysis">
      <div className="flex flex-col gap-3">
        <p className="text-sm font-medium text-slate-600">Strengths • Weaknesses • Opportunities • Threats</p>
        <div className="flex justify-end">
          <Button variant="secondary" onClick={() => generate.mutateAsync()}>Generate SWOT</Button>
        </div>
        {!data.careerSwot ? <EmptyState>Generate a SWOT to see strengths, weaknesses, opportunities, and threats.</EmptyState> : (
          <div className="grid gap-3 md:grid-cols-2">
            <SwotBox title="Strengths" items={data.careerSwot.strengths} />
            <SwotBox title="Weaknesses" items={data.careerSwot.weaknesses} />
            <SwotBox title="Opportunities" items={data.careerSwot.opportunities} />
            <SwotBox title="Threats" items={data.careerSwot.threats} />
            <div className="md:col-span-2"><DetailDisclosure label="Why?">{data.careerSwot.explanation}</DetailDisclosure></div>
          </div>
        )}
      </div>
    </Section>
  );
}

function SwotBox({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-md border border-slate-200 p-3 text-sm">
      <h3 className="font-semibold">{title}</h3>
      {items.length === 0 ? <p className="mt-2 text-slate-500">No signal yet.</p> : (
        <ul className="mt-2 grid gap-1">
          {items.map((item) => <li key={item}>{item}</li>)}
        </ul>
      )}
    </div>
  );
}

function RoleSimilaritySection({ data }: { data: CareerReadData }) {
  const items = data.intelligenceDashboard?.role_similarity ?? [];
  return (
    <Section title="Role Similarity">
      {items.length === 0 ? <EmptyState>Callbacks or bookings will unlock similar-role suggestions.</EmptyState> : (
        <div className="grid gap-3 lg:grid-cols-3">
          {items.map((item) => (
            <article key={item.source_role} className="rounded-md border border-slate-200 p-3 text-sm">
              <h3 className="font-semibold">From {item.source_role}</h3>
              <p className="mt-2">{item.similar_roles.map((role) => String(role.role)).join(", ")}</p>
              <DetailDisclosure label="Why?">{item.explanation}</DetailDisclosure>
            </article>
          ))}
        </div>
      )}
    </Section>
  );
}

function IndustryTrendsSection({ data }: { data: CareerReadData }) {
  const trends = data.industryTrends;
  const trendState = data.capabilities?.states.industry_trend_analysis;
  return (
    <Section title="Your Casting Patterns">
      {trendState && trendState.state !== "Configured" ? (
        <EmptyState>Add or track a few more auditions to unlock casting pattern insights.</EmptyState>
      ) : !trends ? <EmptyState>Your tracked breakdowns, auditions, submissions, callbacks, bookings, and materials will generate casting pattern insights.</EmptyState> : (
        <div className="grid gap-3 lg:grid-cols-3">
          <TrendCard title={trends.pattern_stage || "Early Signals"} items={[{ label: trends.unlock_message, insight: trends.unlock_message, count: trends.tracked_breakdowns_or_auditions }]} />
          <TrendCard title="What you are seeing" items={trends.insights.map((insight) => ({ label: insight, insight, count: 0 }))} />
          <TrendCard title="Archetypes" items={trends.archetype} />
          <TrendCard title="Role Types" items={trends.role_type} />
          <TrendCard title="Project Types" items={trends.project_type} />
          <TrendCard title="Locations" items={trends.location} />
          <TrendCard title="Sources" items={trends.submission_source} />
          <TrendCard title="Callback Signals" items={trends.callback_archetype} />
        </div>
      )}
    </Section>
  );
}

function TrendCard({ title, items }: { title: string; items: Array<{ label: string; count: number; insight?: string; recommended_action?: string | null }> }) {
  return (
    <div className="rounded-md border border-slate-200 p-3 text-sm">
      <h3 className="font-semibold">{title}</h3>
      {items.length === 0 ? <p className="mt-2 text-slate-500">No signal yet.</p> : items.slice(0, 5).map((item) => (
        <div key={`${title}-${item.label}`} className="mt-2 rounded bg-slate-50 p-2">
          <p className="font-medium">{item.label}{item.count ? ` · ${item.count}` : ""}</p>
          {item.insight && <p>{item.insight}</p>}
          {item.recommended_action && <p className="text-slate-600">Action: {item.recommended_action}</p>}
        </div>
      ))}
    </div>
  );
}

function RelationshipInsightsSection({ analytics }: { analytics: RelationshipAnalytics | null }) {
  const rows = analytics?.rows ?? [];
  return (
    <Section title="Relationship Insights">
      {rows.length === 0 ? <EmptyState>Relationships and outcomes will reveal which offices and people correlate with callbacks or bookings.</EmptyState> : (
        <div className="grid gap-3 lg:grid-cols-3">
          {rows.slice(0, 6).map((row) => (
            <article key={row.relationship_id} className="rounded-md border border-slate-200 p-3 text-sm">
              <h3 className="font-semibold">{row.name}</h3>
              <p className="text-slate-600">{row.role_title} · {row.relationship_strength}</p>
              <p className="mt-2">{row.submissions} submissions · {Math.round(row.callback_rate * 100)}% callback · {Math.round(row.booking_rate * 100)}% booking</p>
              <p className="mt-1">{row.correlation_signal}</p>
            </article>
          ))}
          {analytics?.relationship_agent_explanation && (
            <div className="lg:col-span-3"><DetailDisclosure label="Why?">{analytics.relationship_agent_explanation}</DetailDisclosure></div>
          )}
        </div>
      )}
    </Section>
  );
}

function CareerTimelineSection({ data }: { data: CareerReadData }) {
  const items = [
    ...data.submissions.map((submission) => ({
      date: submission.submitted_at || submission.updated_at,
      title: submission.opportunity ? `${submission.current_status}: ${submission.opportunity.role}` : submission.current_status,
      detail: submission.opportunity?.project ?? "Submission",
    })),
    ...data.careerTasks.map((task) => ({
      date: task.completed_at || task.updated_at,
      title: `${task.status}: ${task.title}`,
      detail: task.related_archetype || task.estimated_impact,
    })),
    ...data.quarterlyReviews.map((review) => ({
      date: review.created_at,
      title: `Q${review.quarter} ${review.year} Career Review`,
      detail: review.explanation,
    })),
  ].sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
  return (
    <Section title="Career Timeline">
      {items.length === 0 ? <EmptyState>Your timeline will show submissions, callbacks, bookings, tasks, and reviews.</EmptyState> : (
        <div className="grid gap-2">
          {items.slice(0, 12).map((item, index) => (
            <div key={`${item.date}-${item.title}-${index}`} className="rounded-md border border-slate-200 p-3 text-sm">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{new Date(item.date).toLocaleDateString()}</p>
              <p className="font-semibold">{item.title}</p>
              <p className="text-slate-600">{item.detail}</p>
            </div>
          ))}
        </div>
      )}
    </Section>
  );
}

function splitGoalList(value: string) {
  return value.split(/[,;|]/).map((item) => item.trim()).filter(Boolean);
}
