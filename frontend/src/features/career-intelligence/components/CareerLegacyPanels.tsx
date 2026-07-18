import { useState, type FormEvent } from "react";
import { Brain, Lightbulb } from "lucide-react";
import { ActionCard, Badge, Button, DetailDisclosure, EmptyState, Field, Section, inputClass } from "../../../components/ui";
import { useAnalyzeMaterial, useUploadMaterial, type MaterialOption } from "../../materials";
import { FindSceneOptionsButton, MaterialPlanReviewCard, ScriptFinderPanel, useScriptFinder } from "../../script-finder";
import {
  createMaterialPlan,
  prepareOpportunity,
  simulateCareerPath
} from "../api";
import { useCompleteCareerTask, useCreateCareerTask, useCreateCastingOffice, useDeleteCareerTask, useGenerateCareerSwot, useUpdateCareerTask } from "../hooks/useCareerQueries";
import { assetTypes } from "../../../constants/workflowOptions";
import { joinList, splitList } from "../../../utils/tags";
import { formatDateTime } from "../../../utils/dateTime";
import type {
  ActorProfile,
  AgentRecommendation,
  AssetType,
  AuditionPreparationBrief,
  CareerDevelopmentTask,
  CareerPathSimulation,
  CareerRecommendation,
  CareerSwotAnalysis,
  CastingOffice,
  IntelligenceDashboard,
  LearningInsight,
  MaterialCreationPlan,
  Opportunity,
  SystemCapabilities
} from "../../../types/domain";

function IntelligenceList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-md border border-slate-200 p-3">
      <p className="text-sm font-semibold">{title}</p>
      <div className="mt-2 flex flex-wrap gap-1">
        {items.length === 0 ? <span className="text-sm text-slate-500">Not enough data</span> : items.map((item) => <Badge key={item}>{item}</Badge>)}
      </div>
    </div>
  );
}

function SufficiencyGate({ state, message }: { state: string; message: string }) {
  return (
    <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950">
      <div className="flex flex-wrap items-center gap-2">
        <Badge>{state}</Badge>
        <span className="font-semibold">Track more submissions to unlock this insight.</span>
      </div>
      <p className="mt-2">{message}</p>
      <p className="mt-1 text-amber-900">Next step: keep linking submissions, materials, archetypes, outcomes, and casting offices as you work.</p>
    </div>
  );
}

function GeneratedOutput({ title, data, explanation }: { title: string; data: Record<string, unknown>; explanation: string }) {
  return (
    <div className="rounded-md border border-blue-200 bg-blue-50 p-4 text-sm">
      <h3 className="font-semibold">{title}</h3>
      <div className="mt-3 grid gap-2">
        {Object.entries(data).map(([key, value]) => (
          <p key={key}><strong>{key.replace(/_/g, " ")}:</strong> {formatGeneratedValue(value)}</p>
        ))}
      </div>
      <p className="mt-3 text-blue-900"><strong>Why:</strong> {explanation}</p>
    </div>
  );
}

function formatGeneratedValue(value: unknown): string {
  if (Array.isArray(value)) return value.map(formatGeneratedValue).join(", ");
  if (value && typeof value === "object") return JSON.stringify(value);
  return String(value ?? "");
}

export function AIIntelligencePanel({
  dashboard,
  castingOffices,
  opportunities,
  careerTasks,
  capabilities
}: {
  dashboard: IntelligenceDashboard | null;
  castingOffices: CastingOffice[];
  opportunities: Opportunity[];
  careerTasks: CareerDevelopmentTask[];
  capabilities?: SystemCapabilities | null;
}) {
  const createOffice = useCreateCastingOffice();
  const [prep, setPrep] = useState<AuditionPreparationBrief | null>(null);
  const [materialPlan, setMaterialPlan] = useState<MaterialCreationPlan | null>(null);
  const [simulation, setSimulation] = useState<CareerPathSimulation | null>(null);
  const [careerGoal, setCareerGoal] = useState("If I want to book recurring TV roles within 2 years, what should I do next?");
  const [officeForm, setOfficeForm] = useState({ name: "", source_platform: "", notes: "" });
  const archetypeState = capabilities?.states.archetype_performance;
  const officeState = capabilities?.states.casting_office_intelligence;

  return (
    <Section title="Career Intelligence" actions={<Brain className="h-5 w-5 text-slate-500" />}>
      {!dashboard ? <EmptyState>Loading intelligence signals.</EmptyState> : (
        <div className="grid gap-4">
          <div className="grid gap-3 xl:grid-cols-4">
            <IntelligenceList title="Best Archetypes" items={dashboard.archetype_performance.best_performing_archetypes} />
            <IntelligenceList title="Underused" items={dashboard.archetype_performance.underused_archetypes} />
            <IntelligenceList title="Overused" items={dashboard.archetype_performance.overused_archetypes} />
            <IntelligenceList title="Stretch Potential" items={dashboard.archetype_performance.high_potential_stretch_archetypes} />
          </div>

          <div className="grid gap-3 xl:grid-cols-3">
            <div className="rounded-md border border-slate-200 p-3">
              <h3 className="font-semibold">Archetype Performance</h3>
              <div className="mt-3 grid gap-2 text-sm">
                {archetypeState && archetypeState.state !== "Configured" ? (
                  <SufficiencyGate state={archetypeState.state} message={archetypeState.explanation} />
                ) : dashboard.archetype_performance.metrics.length === 0 ? <p className="text-slate-500">Add Data First. Track more submissions to unlock this insight.</p> : dashboard.archetype_performance.metrics.slice(0, 6).map((row) => (
                  <div key={row.archetype} className="rounded bg-slate-50 p-2">
                    <p className="font-semibold">{row.archetype}</p>
                    <p>{row.submissions} submissions · {Math.round(row.callback_rate * 100)}% callback · {Math.round(row.booking_rate * 100)}% booking</p>
                    <p>Booked {row.booked} · Pinned {row.pinned} · Passed {row.passed} · No response {row.no_response}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-md border border-slate-200 p-3">
              <h3 className="font-semibold">Casting Office Intelligence</h3>
              <div className="mt-3 grid gap-2 text-sm">
                {officeState && officeState.state !== "Configured" ? (
                  <SufficiencyGate state={officeState.state} message={officeState.explanation} />
                ) : dashboard.casting_office_analytics.length === 0 ? <p className="text-slate-500">Add Data First. Link at least 3 submissions to a casting office to unlock this insight.</p> : dashboard.casting_office_analytics.slice(0, 6).map((office) => (
                  <div key={office.casting_office_id ?? office.casting_office} className="rounded bg-slate-50 p-2">
                    <p className="font-semibold">{office.casting_office}</p>
                    <p>{office.submissions} submissions · {Math.round(office.callback_rate * 100)}% callback · {Math.round(office.booking_rate * 100)}% booking</p>
                    <p>Best materials: {office.best_materials.join(", ") || "Not enough data"}</p>
                    <p>Stretch signal: {office.stretch_response_signal}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-md border border-slate-200 p-3">
              <h3 className="font-semibold">Role Similarity Engine</h3>
              <div className="mt-3 grid gap-2 text-sm">
                {dashboard.role_similarity.length === 0 ? <p className="text-slate-500">Callbacks or bookings will unlock similar-role suggestions.</p> : dashboard.role_similarity.slice(0, 4).map((item) => (
                  <div key={item.source_role} className="rounded bg-slate-50 p-2">
                    <p className="font-semibold">From {item.source_role}</p>
                    <p>{item.similar_roles.map((role) => String(role.role)).join(", ")}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <form className="grid gap-3 rounded-md border border-slate-200 p-3 lg:grid-cols-4" onSubmit={async (event) => {
            event.preventDefault();
            await createOffice.mutateAsync({
              name: officeForm.name,
              source_platform: officeForm.source_platform || null,
              notes: officeForm.notes || null
            });
            setOfficeForm({ name: "", source_platform: "", notes: "" });
          }}>
            <div>
              <h3 className="font-semibold">Casting Offices</h3>
              <p className="mt-1 text-sm text-slate-600">{castingOffices.length} tracked</p>
            </div>
            <Field label="Office">
              <input className={inputClass} value={officeForm.name} onChange={(event) => setOfficeForm({ ...officeForm, name: event.target.value })} required />
            </Field>
            <Field label="Source Platform">
              <input className={inputClass} value={officeForm.source_platform} onChange={(event) => setOfficeForm({ ...officeForm, source_platform: event.target.value })} />
            </Field>
            <Field label="Notes">
              <input className={inputClass} value={officeForm.notes} onChange={(event) => setOfficeForm({ ...officeForm, notes: event.target.value })} />
            </Field>
            <div className="lg:col-start-2"><Button type="submit">Add Casting Office</Button></div>
            <div className="flex flex-wrap gap-1 lg:col-span-3">
              {castingOffices.slice(0, 8).map((office) => <Badge key={office.id}>{office.name}</Badge>)}
            </div>
          </form>

          <div className="grid gap-3 xl:grid-cols-3">
            <div className="rounded-md border border-slate-200 p-3">
              <h3 className="font-semibold">Audition Preparation</h3>
              <div className="mt-3 grid gap-2">
                {opportunities.slice(0, 5).map((opportunity) => (
                  <Button key={opportunity.id} variant="secondary" onClick={async () => setPrep(await prepareOpportunity(opportunity.id))}>
                    Prepare {opportunity.role}
                  </Button>
                ))}
              </div>
            </div>

            <div className="rounded-md border border-slate-200 p-3">
              <h3 className="font-semibold">Material Plan Generator</h3>
              <div className="mt-3 grid gap-2">
                {(careerTasks.length ? careerTasks.slice(0, 5) : [{ id: "", title: "Attorney Reel Scene", related_archetype: "Attorney" } as CareerDevelopmentTask]).map((task) => (
                  <Button key={task.id || task.title} variant="secondary" onClick={async () => setMaterialPlan(await createMaterialPlan({
                    career_task_id: task.id || null,
                    missing_asset: task.title,
                    target_archetype: task.related_archetype || null
                  }))}>
                    Plan {task.title}
                  </Button>
                ))}
              </div>
            </div>

            <form className="rounded-md border border-slate-200 p-3" onSubmit={async (event) => {
              event.preventDefault();
              setSimulation(await simulateCareerPath(careerGoal));
            }}>
              <h3 className="font-semibold">Career Path Simulator</h3>
              <Field label="Goal">
                <textarea className={inputClass} value={careerGoal} onChange={(event) => setCareerGoal(event.target.value)} />
              </Field>
              <Button type="submit">Simulate Path</Button>
            </form>
          </div>

          {prep && <GeneratedOutput title="Audition Prep Brief" data={prep.brief} explanation={prep.explanation} />}
          {materialPlan && <GeneratedOutput title="Material Creation Plan" data={materialPlan.plan} explanation={materialPlan.explanation} />}
          {simulation && <GeneratedOutput title="Career Path Simulation" data={simulation.result} explanation={simulation.explanation} />}
        </div>
      )}
    </Section>
  );
}

export function CareerPanel({
  career,
  swot,
  learning
}: {
  career: CareerRecommendation | null;
  swot: CareerSwotAnalysis | null;
  learning: LearningInsight | null;
}) {
  const generateSwot = useGenerateCareerSwot();
  return (
    <Section title="Career Recommendations" actions={<Lightbulb className="h-5 w-5 text-slate-500" />}>
      {!career && !learning && !swot ? <EmptyState>Create casting goals and track outcomes to unlock personalized career recommendations.</EmptyState> : (
        <div className="grid gap-4 lg:grid-cols-2">
          {learning && (
            <ActionCard title="What’s Working" status={<Badge>Insight</Badge>}>
              <DetailDisclosure label="Why?">{learning.explanation}</DetailDisclosure>
            </ActionCard>
          )}
          {career && (
            <ActionCard
              title="Career Direction"
              status={<Badge>{career.archetypes_to_expand.length} growth areas</Badge>}
              details={<DetailDisclosure label="Why?">{career.explanation}</DetailDisclosure>}
            >
              <p><strong>Strengths:</strong> {career.strengths.join(", ") || "Not enough data"}</p>
              <p className="mt-1"><strong>Explore next:</strong> {career.archetypes_to_expand.join(", ") || "None"}</p>
              <DetailDisclosure label="Role Ideas">
                <p><strong>Strong:</strong> {career.strong_match_roles.map(displayRoleValue).join(", ") || "None"}</p>
                <p className="mt-1"><strong>Growth:</strong> {career.growth_match_roles.map(displayRoleValue).join(", ") || "None"}</p>
              </DetailDisclosure>
            </ActionCard>
          )}
          <div className="rounded-md border border-slate-200 p-3">
            <div className="flex items-start justify-between gap-3">
              <h3 className="font-semibold">Personal Casting SWOT</h3>
              <Button variant="secondary" onClick={() => generateSwot.mutateAsync()}>Generate SWOT</Button>
            </div>
            {!swot ? (
              <p className="mt-2 text-sm text-slate-500">Generate a snapshot to see strengths, gaps, opportunities, and risks.</p>
            ) : (
              <div className="mt-3 grid gap-3 text-sm sm:grid-cols-2">
                <SwotList title="Strengths" items={swot.strengths} />
                <SwotList title="Weaknesses" items={swot.weaknesses} />
                <SwotList title="Opportunities" items={swot.opportunities} />
                <SwotList title="Threats" items={swot.threats} />
                <div className="sm:col-span-2"><DetailDisclosure label="Why?">{swot.explanation}</DetailDisclosure></div>
              </div>
            )}
          </div>
          {career?.stretch_roles.map((role, index) => (
            <ActionCard
              key={index}
              title={`${String(role.match_type ?? "Stretch Role")}: ${String(role.role)}`}
              status={<Badge>{String(role.confidence)} Confidence</Badge>}
              meta={`Archetype: ${String(role.archetype ?? "General")}`}
              details={(
                <div className="grid gap-2">
                  <DetailDisclosure label="Missing Materials">
                    {Array.isArray(role.missing_assets) ? role.missing_assets.join(", ") : "No material gaps listed."}
                  </DetailDisclosure>
                  <DetailDisclosure label="Why?">{String(role.why)}</DetailDisclosure>
                </div>
              )}
            />
          ))}
        </div>
      )}
    </Section>
  );
}

function SwotList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded bg-slate-50 p-2">
      <p className="font-semibold">{title}</p>
      <ul className="mt-1 grid gap-1">
        {items.map((item) => <li key={item}>{item}</li>)}
      </ul>
    </div>
  );
}

function displayRoleValue(value: unknown): string {
  if (typeof value === "string") return value;
  if (value && typeof value === "object" && "role" in value) return String((value as { role: unknown }).role);
  return String(value ?? "");
}

export function CareerDevelopmentDashboard({
  actor,
  tasks,
  assets
}: {
  actor: ActorProfile | null;
  tasks: CareerDevelopmentTask[];
  assets: MaterialOption[];
}) {
  const createTaskMutation = useCreateCareerTask(); const updateTaskMutation = useUpdateCareerTask();
  const completeTaskMutation = useCompleteCareerTask(); const deleteTaskMutation = useDeleteCareerTask();
  const uploadMaterial = useUploadMaterial(); const analyzeMaterial = useAnalyzeMaterial();
  const [filters, setFilters] = useState({ status: "", archetype: "", priority: "" });
  const [formOpen, setFormOpen] = useState(tasks.length === 0);
  const [materialTaskId, setMaterialTaskId] = useState<string | null>(null);
  const [materialFile, setMaterialFile] = useState<File | null>(null);
  const [materialForm, setMaterialForm] = useState({
    asset_name: "",
    asset_type: "Reel" as AssetType,
    tags: "",
    archetype_names: "",
    description: ""
  });
  const [editingTaskId, setEditingTaskId] = useState<string | null>(null);
  const [taskEditForm, setTaskEditForm] = useState({ title: "", description: "" });
  const scriptFinder = useScriptFinder();
  const [form, setForm] = useState({
    title: "",
    description: "",
    priority: "Medium",
    status: "Not Started",
    related_archetype: "",
    target_role_types: "",
    estimated_impact: "Medium",
    reason: "",
    supported_archetypes: "",
    asset_id: ""
  });

  const archetypes = Array.from(
    new Set(tasks.map((task) => task.related_archetype).filter(Boolean) as string[])
  );
  const visibleTasks = tasks.filter((task) => {
    if (filters.status && task.status !== filters.status) return false;
    if (filters.priority && task.priority !== filters.priority) return false;
    if (filters.archetype && task.related_archetype !== filters.archetype) return false;
    return true;
  });

  async function createTask(event: FormEvent) {
    event.preventDefault();
    await createTaskMutation.mutateAsync({
      ...form,
      related_archetype: form.related_archetype || null,
      asset_id: form.asset_id || null,
      target_role_types: splitList(form.target_role_types),
      supported_archetypes: splitList(form.supported_archetypes),
      reason: form.reason || null,
      created_by_agent: false
    });
    setForm({
      title: "",
      description: "",
      priority: "Medium",
      status: "Not Started",
      related_archetype: "",
      target_role_types: "",
      estimated_impact: "Medium",
      reason: "",
      supported_archetypes: "",
      asset_id: ""
    });
  }

  function openMaterialWorkflow(task: CareerDevelopmentTask) {
    const archetype = task.related_archetype || task.supported_archetypes[0] || "";
    setMaterialTaskId(task.id);
    setMaterialFile(null);
    setMaterialForm({
      asset_name: task.title,
      asset_type: inferAssetType(task.title),
      tags: joinList([task.priority, task.estimated_impact, ...task.target_role_types].filter(Boolean)),
      archetype_names: joinList([archetype, ...task.supported_archetypes].filter(Boolean)),
      description: task.reason || task.description
    });
  }

  function openTaskEditor(task: CareerDevelopmentTask) {
    setEditingTaskId(task.id);
    setTaskEditForm({ title: task.title, description: task.description });
  }

  async function saveTaskEditor(event: FormEvent) {
    event.preventDefault();
    if (!editingTaskId) return;
    await updateTaskMutation.mutateAsync({ id: editingTaskId, patch: taskEditForm });
    setEditingTaskId(null);
    setTaskEditForm({ title: "", description: "" });
  }

  async function uploadMaterialForTask(task: CareerDevelopmentTask) {
    if (!actor || !materialFile) return;
    const data = new FormData();
    data.set("actor_profile_id", actor.id);
    data.set("asset_name", materialForm.asset_name);
    data.set("asset_type", materialForm.asset_type);
    data.set("description", materialForm.description);
    data.set("tags", materialForm.tags);
    data.set("archetype_names", materialForm.archetype_names);
    data.set("career_task_id", task.id);
    data.set("file", materialFile);
    const asset = await uploadMaterial.mutateAsync(data);
    await analyzeMaterial.mutateAsync(asset.id);
    setMaterialTaskId(null);
    setMaterialFile(null);
  }

  return (
    <Section title="Career Development" actions={<Button onClick={() => setFormOpen((current) => !current)}>{formOpen ? "Hide Form" : "Add Career Task"}</Button>}>
      <ScriptFinderPanel
        scriptSources={scriptFinder.scriptSources}
        sceneOptions={scriptFinder.sceneOptions}
        sceneResources={scriptFinder.sceneResources}
        scriptSourceFormOpen={scriptFinder.scriptSourceFormOpen}
        scriptSourceForm={scriptFinder.scriptSourceForm}
        sceneFinderMessage={scriptFinder.sceneFinderMessage}
        sceneFinderError={scriptFinder.sceneFinderError}
        onToggleSourceForm={() => scriptFinder.setScriptSourceFormOpen((current) => !current)}
        onSourceFormChange={scriptFinder.setScriptSourceForm}
        onCreateScriptSource={scriptFinder.createScriptSource}
        onUpdateSceneCandidate={scriptFinder.updateSceneCandidate}
        onGenerateOriginalSceneBrief={scriptFinder.generateOriginalSceneBrief}
      />
      {formOpen && (
        <form className="mb-4 grid gap-3 rounded-md border border-slate-200 bg-slate-50 p-3 lg:grid-cols-4" onSubmit={createTask}>
          <Field label="Task Title">
            <input className={inputClass} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
          </Field>
          <Field label="Priority">
            <select className={inputClass} value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}>
              <option>Low</option><option>Medium</option><option>High</option>
            </select>
          </Field>
          <Field label="Status">
            <select className={inputClass} value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
              <option>Not Started</option><option>In Progress</option><option>Partially Completed</option><option>Completed</option>
            </select>
          </Field>
          <Field label="Impact">
            <select className={inputClass} value={form.estimated_impact} onChange={(e) => setForm({ ...form, estimated_impact: e.target.value })}>
              <option>Low</option><option>Medium</option><option>High</option>
            </select>
          </Field>
          <Field label="Related Archetype">
            <input className={inputClass} value={form.related_archetype} onChange={(e) => setForm({ ...form, related_archetype: e.target.value })} placeholder="Attorney" />
          </Field>
          <Field label="Target Role Types">
            <input className={inputClass} value={form.target_role_types} onChange={(e) => setForm({ ...form, target_role_types: e.target.value })} placeholder="Attorney, Judge" />
          </Field>
          <Field label="Supported Archetypes">
            <input className={inputClass} value={form.supported_archetypes} onChange={(e) => setForm({ ...form, supported_archetypes: e.target.value })} placeholder="Authority Figure" />
          </Field>
          <Field label="Linked Asset">
            <select className={inputClass} value={form.asset_id} onChange={(e) => setForm({ ...form, asset_id: e.target.value })}>
              <option value="">None</option>
              {assets.map((asset) => <option key={asset.id} value={asset.id}>{asset.asset_name}</option>)}
            </select>
          </Field>
          <div className="lg:col-span-2">
            <Field label="Description">
              <textarea className={inputClass} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} required />
            </Field>
          </div>
          <div className="lg:col-span-2">
            <Field label="Reason">
              <textarea className={inputClass} value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} />
            </Field>
          </div>
          <Button type="submit">Create Task</Button>
        </form>
      )}

      <div className="mb-4 grid gap-3 md:grid-cols-3">
        <Field label="Filter Status">
          <select className={inputClass} value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })}>
            <option value="">All</option><option>Not Started</option><option>In Progress</option><option>Partially Completed</option><option>Completed</option>
          </select>
        </Field>
        <Field label="Filter Priority">
          <select className={inputClass} value={filters.priority} onChange={(e) => setFilters({ ...filters, priority: e.target.value })}>
            <option value="">All</option><option>Low</option><option>Medium</option><option>High</option>
          </select>
        </Field>
        <Field label="Filter Archetype">
          <select className={inputClass} value={filters.archetype} onChange={(e) => setFilters({ ...filters, archetype: e.target.value })}>
            <option value="">All</option>
            {archetypes.map((archetype) => <option key={archetype}>{archetype}</option>)}
          </select>
        </Field>
      </div>

      <div className="grid gap-3 lg:grid-cols-3">
        {visibleTasks.length === 0 ? <EmptyState>No career development tasks match the current filters. Create a task to track a material, role, or career goal.</EmptyState> : visibleTasks.map((task) => (
          (() => {
            const scenePlan = scriptFinder.scenePlansByTaskId[task.id];
            return (
          <ActionCard
            key={task.id}
            title={task.title}
            status={<Badge>{task.status}</Badge>}
            meta={`${task.related_archetype || "General"} · ${task.priority} priority · ${task.estimated_impact} impact`}
            primaryAction={(
              <>
              {task.created_by_agent && task.status === "Not Started" && (
                <Button onClick={() => updateTaskMutation.mutateAsync({ id: task.id, patch: { status: "In Progress" } })}>Approve</Button>
              )}
              <Button variant="secondary" onClick={() => openTaskEditor(task)}>Edit</Button>
              <Button variant="secondary" onClick={() => openMaterialWorkflow(task)}>Add Material</Button>
              <FindSceneOptionsButton
                searching={scriptFinder.searchingSceneTaskId === task.id}
                onClick={() => void scriptFinder.requestScenePlan(task)}
              />
              {task.status !== "Completed" && <Button onClick={() => completeTaskMutation.mutateAsync(task.id)}>Complete</Button>}
              <Button variant="danger" onClick={() => deleteTaskMutation.mutateAsync(task.id)}>Reject</Button>
              </>
            )}
	            details={(
	              <div className="grid gap-2">
                  {editingTaskId === task.id && (
                    <form className="grid gap-3 rounded-md border border-slate-200 bg-slate-50 p-3" onSubmit={saveTaskEditor}>
                      <Field label="Task Title">
                        <input
                          className={inputClass}
                          value={taskEditForm.title}
                          onChange={(event) => setTaskEditForm({ ...taskEditForm, title: event.target.value })}
                          required
                        />
                      </Field>
                      <Field label="Description">
                        <textarea
                          className={inputClass}
                          value={taskEditForm.description}
                          onChange={(event) => setTaskEditForm({ ...taskEditForm, description: event.target.value })}
                          required
                        />
                      </Field>
                      <div className="flex flex-wrap gap-2">
                        <Button type="submit">Save</Button>
                        <Button
                          type="button"
                          variant="secondary"
                          onClick={() => {
                            setEditingTaskId(null);
                            setTaskEditForm({ title: "", description: "" });
                          }}
                        >
                          Cancel
                        </Button>
                      </div>
                    </form>
                  )}
	                <DetailDisclosure label="Details">
	                  <p>{task.description}</p>
                  {task.reason && <p className="mt-2">Reason: {task.reason}</p>}
                  <p className="mt-2">Roles: {task.target_role_types.join(", ") || "None"}</p>
                  <p>Supported archetypes: {task.supported_archetypes.join(", ") || "None"}</p>
                  {task.created_by_agent && <p className="mt-2">Recommended by the app based on your career data.</p>}
                  {task.asset_id && <p className="mt-2">Linked material: {assets.find((asset) => asset.id === task.asset_id)?.asset_name ?? "Attached"}</p>}
                </DetailDisclosure>
              </div>
            )}
          >
            {scenePlan?.plan_status === "Pending Review" && (
              <MaterialPlanReviewCard
                task={task}
                scenePlan={scenePlan}
                onApprove={() => void scriptFinder.approveScenePlan(task, scenePlan)}
                onDeny={() => void scriptFinder.denyScenePlan(task, scenePlan)}
              />
            )}
            {materialTaskId === task.id && (
              <div className="mt-3 grid gap-2 rounded bg-slate-50 p-3">
                {!actor && <p className="text-sm text-red-700">Create an actor profile before uploading materials.</p>}
                <Field label="Asset Name">
                  <input className={inputClass} value={materialForm.asset_name} onChange={(e) => setMaterialForm({ ...materialForm, asset_name: e.target.value })} />
                </Field>
                <div className="grid gap-2 sm:grid-cols-2">
                  <Field label="Asset Type">
                    <select className={inputClass} value={materialForm.asset_type} onChange={(e) => setMaterialForm({ ...materialForm, asset_type: e.target.value as AssetType })}>
                      {assetTypes.map((type) => <option key={type}>{type}</option>)}
                    </select>
                  </Field>
                  <Field label="File">
                    <input className={inputClass} type="file" onChange={(e) => setMaterialFile(e.target.files?.[0] ?? null)} />
                  </Field>
                </div>
                <Field label="Suggested Tags">
                  <input className={inputClass} value={materialForm.tags} onChange={(e) => setMaterialForm({ ...materialForm, tags: e.target.value })} />
                </Field>
                <Field label="Suggested Archetypes">
                  <input className={inputClass} value={materialForm.archetype_names} onChange={(e) => setMaterialForm({ ...materialForm, archetype_names: e.target.value })} />
                </Field>
                <Field label="Description">
                  <textarea className={inputClass} value={materialForm.description} onChange={(e) => setMaterialForm({ ...materialForm, description: e.target.value })} />
                </Field>
                <div className="flex flex-wrap gap-2">
                  <Button disabled={!actor || !materialFile} onClick={() => uploadMaterialForTask(task)}>Upload & Analyze</Button>
                  <Button variant="secondary" onClick={() => setMaterialTaskId(null)}>Cancel</Button>
                </div>
              </div>
            )}
          </ActionCard>
            );
          })()
        ))}
      </div>
    </Section>
  );
}

function inferAssetType(title: string): AssetType {
  const value = title.toLowerCase();
  if (value.includes("headshot")) return "Headshot";
  if (value.includes("slate")) return "Slate";
  if (value.includes("resume")) return "Resume";
  return "Reel";
}
