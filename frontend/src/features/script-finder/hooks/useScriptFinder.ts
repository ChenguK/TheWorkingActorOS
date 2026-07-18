import { useMemo, useState, type FormEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "../../../services/api/queryKeys";
import { queryStaleTimes } from "../../../services/api/queryPolicy";
import type { CareerDevelopmentTask, MaterialCreationPlan, SceneCandidate, ScriptSource, ScriptSourceFormState } from "../types";
import {
  approveMaterialPlan,
  createMaterialPlan,
  createScriptSource as createScriptSourceRequest,
  denyMaterialPlan,
  findSceneOptions,
  getScriptFinderCapabilities,
  listScriptSources,
  saveSceneCandidate
} from "../api";
import { primarySceneResultTypes, resourceSceneResultTypes } from "../constants";

export function useScriptFinder() {
  const queryClient = useQueryClient();
  const scriptSourcesKey = queryKeys.scriptFinder.list({ resource: "sources" });
  const scriptSourcesQuery = useQuery({ queryKey: scriptSourcesKey, queryFn: listScriptSources, staleTime: queryStaleTimes.reference });
  const scriptSources: ScriptSource[] = scriptSourcesQuery.data ?? [];
  const [sceneCandidates, setSceneCandidates] = useState<SceneCandidate[]>([]);
  const [scriptSourceFormOpen, setScriptSourceFormOpen] = useState(false);
  const [sceneFinderMessage, setSceneFinderMessage] = useState<string | null>(null);
  const [sceneFinderError, setSceneFinderError] = useState<string | null>(null);
  const [searchingSceneTaskId, setSearchingSceneTaskId] = useState<string | null>(null);
  const [scenePlansByTaskId, setScenePlansByTaskId] = useState<Record<string, MaterialCreationPlan>>({});
  const [scriptSourceForm, setScriptSourceForm] = useState<ScriptSourceFormState>({
    name: "",
    url: "",
    source_type: "Original scenes",
    rights_status: "Original / User-Owned",
    notes: "",
    approved: true
  });

  const sceneOptions = useMemo(
    () => sceneCandidates.filter((candidate) => primarySceneResultTypes.includes(candidate.result_type)),
    [sceneCandidates]
  );
  const sceneResources = useMemo(
    () => sceneCandidates.filter((candidate) => resourceSceneResultTypes.includes(candidate.result_type)),
    [sceneCandidates]
  );

  async function createScriptSource(event: FormEvent) {
    event.preventDefault();
    await createScriptSourceRequest({
      ...scriptSourceForm,
      url: scriptSourceForm.url || null,
      notes: scriptSourceForm.notes || null
    });
    setScriptSourceForm({ name: "", url: "", source_type: "Original scenes", rights_status: "Original / User-Owned", notes: "", approved: true });
    setScriptSourceFormOpen(false);
    await queryClient.invalidateQueries({ queryKey: scriptSourcesKey });
  }

  async function requestScenePlan(task: CareerDevelopmentTask) {
    const existingPlan = scenePlansByTaskId[task.id];
    if (existingPlan?.plan_status === "Approved") {
      await findSceneForTask(task, existingPlan);
      return;
    }
    const plan = await createMaterialPlan({
      career_task_id: task.id,
      missing_asset: task.title,
      target_archetype: task.related_archetype || task.supported_archetypes[0] || null
    });
    setScenePlansByTaskId((current) => ({ ...current, [task.id]: plan }));
    setSceneFinderMessage("Review the material plan, then approve it before searching for scene options.");
  }

  async function approveScenePlan(task: CareerDevelopmentTask, plan: MaterialCreationPlan) {
    const updated = await approveMaterialPlan(plan.id);
    setScenePlansByTaskId((current) => ({ ...current, [task.id]: updated }));
    await findSceneForTask(task, updated);
  }

  async function denyScenePlan(task: CareerDevelopmentTask, plan: MaterialCreationPlan) {
    await denyMaterialPlan(plan.id);
    setScenePlansByTaskId((current) => {
      const next = { ...current };
      delete next[task.id];
      return next;
    });
    setSceneFinderMessage("Material plan denied. No script search was run.");
  }

  async function findSceneForTask(task: CareerDevelopmentTask, plan: MaterialCreationPlan) {
    setSearchingSceneTaskId(task.id);
    setSceneFinderError(null);
    setSceneFinderMessage(null);
    try {
      const capabilities = await getScriptFinderCapabilities();
      const parallelConfigured = capabilities.integrations.some((integration) => integration.id === "parallel_public_web_search" && integration.configured);
      if (!parallelConfigured) {
        setSceneFinderError("Scene search is not configured. You can still create an original scene brief.");
      }
      const candidates = await findSceneOptions({
        material_plan_id: plan.id,
        career_task_id: task.id,
        target_archetype: plan.target_archetype || task.related_archetype || task.supported_archetypes[0] || null,
        material_goal: String(plan.plan.scene_concept ?? plan.missing_asset ?? task.title)
      });
      setSceneCandidates(candidates);
      const hasOriginal = candidates.some((candidate) => candidate.action_status === "Original Brief");
      const hasWebCandidate = candidates.some((candidate) => candidate.notes?.includes("Parallel public web search"));
      const specificCount = candidates.filter((candidate) => primarySceneResultTypes.includes(candidate.result_type)).length;
      setSceneFinderMessage(hasOriginal
        ? "No rights-safe scene was found, so an original scene brief was created."
        : hasWebCandidate && specificCount > 0
          ? "Scene options found from approved sources and public web search. Confirm rights before filming or publishing."
          : "Resources to browse were found. Specific scene options still require rights review or an original scene brief.");
    } catch (error) {
      setSceneFinderError(error instanceof Error ? error.message : "Scene search failed. You can still create an original scene brief.");
    } finally {
      setSearchingSceneTaskId(null);
    }
  }

  async function updateSceneCandidate(candidate: SceneCandidate, action_status: SceneCandidate["action_status"]) {
    const updated = await saveSceneCandidate(candidate.id, action_status);
    setSceneCandidates((current) => current.map((item) => item.id === updated.id ? updated : item));
  }

  async function generateOriginalSceneBrief(candidate?: SceneCandidate) {
    const created = await findSceneOptions({
      career_task_id: candidate?.career_task_id || null,
      target_archetype: candidate ? String(candidate.scene_brief.character_type ?? "") || null : null,
      material_goal: candidate?.title || "Original reel scene brief",
      generate_original_only: true
    });
    setSceneCandidates((current) => [...created, ...current]);
    setSceneFinderMessage("Original scene brief created. This is not a copied script.");
  }

  return {
    scriptSources,
    sceneCandidates,
    sceneOptions,
    sceneResources,
    scriptSourceFormOpen,
    setScriptSourceFormOpen,
    scriptSourceForm,
    setScriptSourceForm,
    sceneFinderMessage,
    sceneFinderError,
    searchingSceneTaskId,
    scenePlansByTaskId,
    createScriptSource,
    requestScenePlan,
    approveScenePlan,
    denyScenePlan,
    updateSceneCandidate,
    generateOriginalSceneBrief
  };
}
