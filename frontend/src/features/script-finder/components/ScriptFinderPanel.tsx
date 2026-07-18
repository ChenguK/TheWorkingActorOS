import type { FormEvent } from "react";
import { Badge, Button, Field, inputClass } from "../../../components/ui";
import { scriptRightsStatuses, scriptSourceTypes, hasExplicitRights } from "../constants";
import type { CareerDevelopmentTask, MaterialCreationPlan, SceneCandidate, ScriptSource, ScriptSourceFormState } from "../types";

type ScriptFinderPanelProps = {
  scriptSources: ScriptSource[];
  sceneOptions: SceneCandidate[];
  sceneResources: SceneCandidate[];
  scriptSourceFormOpen: boolean;
  scriptSourceForm: ScriptSourceFormState;
  sceneFinderMessage: string | null;
  sceneFinderError: string | null;
  onToggleSourceForm: () => void;
  onSourceFormChange: (form: ScriptSourceFormState) => void;
  onCreateScriptSource: (event: FormEvent) => void;
  onUpdateSceneCandidate: (candidate: SceneCandidate, actionStatus: SceneCandidate["action_status"]) => Promise<void>;
  onGenerateOriginalSceneBrief: (candidate?: SceneCandidate) => Promise<void>;
};

export function ScriptFinderPanel({
  scriptSources,
  sceneOptions,
  sceneResources,
  scriptSourceFormOpen,
  scriptSourceForm,
  sceneFinderMessage,
  sceneFinderError,
  onToggleSourceForm,
  onSourceFormChange,
  onCreateScriptSource,
  onUpdateSceneCandidate,
  onGenerateOriginalSceneBrief
}: ScriptFinderPanelProps) {
  return (
    <>
      <div className="mb-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
        Always confirm usage rights before filming or publishing a scene from an existing script. Script access is not the same as permission to film, post, or use the material in a reel.
      </div>
      <div id="script-reel-scene-finder" className="mb-4 rounded-md border border-slate-200 bg-white p-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-semibold text-ink">Script / Reel Scene Finder</h3>
            <p className="text-xs text-slate-600">Use approved rights-safe sources, or create an original scene brief when no safe source is available.</p>
          </div>
          <Button variant="secondary" onClick={onToggleSourceForm}>{scriptSourceFormOpen ? "Hide Source Form" : "Add Script Source"}</Button>
        </div>
        {scriptSourceFormOpen && (
          <form className="mt-3 grid gap-3 rounded-md bg-slate-50 p-3 lg:grid-cols-3" onSubmit={onCreateScriptSource}>
            <Field label="Source Name">
              <input className={inputClass} value={scriptSourceForm.name} onChange={(event) => onSourceFormChange({ ...scriptSourceForm, name: event.target.value })} required />
            </Field>
            <Field label="Source Type">
              <select className={inputClass} value={scriptSourceForm.source_type} onChange={(event) => onSourceFormChange({ ...scriptSourceForm, source_type: event.target.value })}>
                {scriptSourceTypes.map((type) => <option key={type}>{type}</option>)}
              </select>
            </Field>
            <Field label="Rights Status">
              <select className={inputClass} value={scriptSourceForm.rights_status} onChange={(event) => onSourceFormChange({ ...scriptSourceForm, rights_status: event.target.value })}>
                {scriptRightsStatuses.map((status) => <option key={status}>{status}</option>)}
              </select>
            </Field>
            <Field label="Source URL">
              <input className={inputClass} type="url" value={scriptSourceForm.url} onChange={(event) => onSourceFormChange({ ...scriptSourceForm, url: event.target.value })} />
            </Field>
            <label className="flex items-center gap-2 text-xs text-slate-700">
              <input type="checkbox" checked={scriptSourceForm.approved} onChange={(event) => onSourceFormChange({ ...scriptSourceForm, approved: event.target.checked })} />
              Approved for scene research
            </label>
            <div className="lg:col-span-3">
              <Field label="Notes">
                <textarea className={inputClass} value={scriptSourceForm.notes} onChange={(event) => onSourceFormChange({ ...scriptSourceForm, notes: event.target.value })} />
              </Field>
            </div>
            <Button type="submit">Save Source</Button>
          </form>
        )}
        <div className="mt-3 flex flex-wrap gap-2">
          {scriptSources.length === 0 ? <p className="text-xs text-slate-500">No script sources yet. Add public domain, royalty-free, licensed, or original/user-owned sources before searching.</p> : scriptSources.slice(0, 6).map((source) => (
            <Badge key={source.id}>{source.name} · {source.rights_status}</Badge>
          ))}
        </div>
      </div>
      {(sceneFinderMessage || sceneFinderError || sceneOptions.length > 0 || sceneResources.length > 0) && (
        <div className="mb-4 rounded-md border border-blue-200 bg-blue-50 p-3">
          {sceneFinderMessage && <p className="text-xs font-medium text-blue-900">{sceneFinderMessage}</p>}
          {sceneFinderError && <p className="mt-1 text-xs font-medium text-amber-900">{sceneFinderError}</p>}
          <div className="mt-3 grid gap-4">
            <SceneOptionsSection
              sceneOptions={sceneOptions}
              onUpdateSceneCandidate={onUpdateSceneCandidate}
              onGenerateOriginalSceneBrief={onGenerateOriginalSceneBrief}
            />
            {sceneResources.length > 0 && (
              <ResourcesToBrowseSection
                sceneResources={sceneResources}
                onUpdateSceneCandidate={onUpdateSceneCandidate}
                onGenerateOriginalSceneBrief={onGenerateOriginalSceneBrief}
              />
            )}
          </div>
        </div>
      )}
    </>
  );
}

export function FindSceneOptionsButton({
  searching,
  onClick
}: {
  searching: boolean;
  onClick: () => void;
}) {
  return (
    <Button variant="secondary" disabled={searching} onClick={onClick}>
      {searching ? "Searching..." : "Find Scene Options"}
    </Button>
  );
}

export function MaterialPlanReviewCard({
  task,
  scenePlan,
  onApprove,
  onDeny
}: {
  task: CareerDevelopmentTask;
  scenePlan: MaterialCreationPlan;
  onApprove: () => void;
  onDeny: () => void;
}) {
  return (
    <div className="mb-3 grid gap-2 rounded border border-amber-200 bg-amber-50 p-3 text-xs text-amber-950">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="font-semibold">Approve material plan before searching</p>
          <p>{scenePlan.explanation}</p>
        </div>
        <Badge>{scenePlan.plan_status}</Badge>
      </div>
      <dl className="grid gap-1 sm:grid-cols-2">
        <div><dt className="font-semibold">Scene concept</dt><dd>{String(scenePlan.plan.scene_concept ?? scenePlan.missing_asset)}</dd></div>
        <div><dt className="font-semibold">Tone</dt><dd>{String(scenePlan.plan.tone ?? "Actor-forward")}</dd></div>
        <div><dt className="font-semibold">Conflict</dt><dd>{String(scenePlan.plan.conflict ?? "Clear character conflict")}</dd></div>
        <div><dt className="font-semibold">Character type</dt><dd>{String(scenePlan.plan.character_type ?? scenePlan.target_archetype ?? task.related_archetype ?? "Actor-forward role")}</dd></div>
      </dl>
      <div className="flex flex-wrap gap-2">
        <Button onClick={onApprove}>Approve Plan</Button>
        <Button variant="secondary" onClick={onDeny}>Deny Plan</Button>
      </div>
    </div>
  );
}

function SceneOptionsSection({
  sceneOptions,
  onUpdateSceneCandidate,
  onGenerateOriginalSceneBrief
}: {
  sceneOptions: SceneCandidate[];
  onUpdateSceneCandidate: (candidate: SceneCandidate, actionStatus: SceneCandidate["action_status"]) => Promise<void>;
  onGenerateOriginalSceneBrief: (candidate?: SceneCandidate) => Promise<void>;
}) {
  return (
    <div>
      <h4 className="text-sm font-semibold text-ink">Scene Options</h4>
      {sceneOptions.length === 0 ? (
        <div className="mt-2 rounded-md border border-blue-100 bg-white p-3 text-xs text-slate-700">
          <p>No rights-safe specific scene was found. Generate an original scene brief instead.</p>
          <button className="mt-2 font-semibold text-accent hover:underline" onClick={() => void onGenerateOriginalSceneBrief()}>
            Generate Original Scene Brief
          </button>
        </div>
      ) : (
        <div className="mt-2 grid gap-3 lg:grid-cols-3">
          {sceneOptions.map((candidate) => <SceneCandidateCard key={candidate.id} candidate={candidate} onUpdate={onUpdateSceneCandidate} onGenerateOriginal={onGenerateOriginalSceneBrief} />)}
        </div>
      )}
    </div>
  );
}

function ResourcesToBrowseSection({
  sceneResources,
  onUpdateSceneCandidate,
  onGenerateOriginalSceneBrief
}: {
  sceneResources: SceneCandidate[];
  onUpdateSceneCandidate: (candidate: SceneCandidate, actionStatus: SceneCandidate["action_status"]) => Promise<void>;
  onGenerateOriginalSceneBrief: (candidate?: SceneCandidate) => Promise<void>;
}) {
  return (
    <div>
      <h4 className="text-sm font-semibold text-ink">Resources to Browse</h4>
      <div className="mt-2 grid gap-3 lg:grid-cols-3">
        {sceneResources.map((candidate) => <SceneCandidateCard key={candidate.id} candidate={candidate} onUpdate={onUpdateSceneCandidate} onGenerateOriginal={onGenerateOriginalSceneBrief} />)}
      </div>
    </div>
  );
}

function SceneCandidateCard({
  candidate,
  onUpdate,
  onGenerateOriginal
}: {
  candidate: SceneCandidate;
  onUpdate: (candidate: SceneCandidate, actionStatus: SceneCandidate["action_status"]) => Promise<void>;
  onGenerateOriginal: (candidate?: SceneCandidate) => Promise<void>;
}) {
  const rightsAreExplicit = hasExplicitRights(candidate);
  return (
    <article className="rounded-md border border-blue-100 bg-white p-3 text-xs">
      <div className="flex items-start justify-between gap-2">
        <h3 className="font-semibold text-ink">{candidate.title}</h3>
        <div className="flex flex-wrap justify-end gap-1">
          <Badge>{candidate.result_type}</Badge>
          <Badge>{candidate.rights_status}</Badge>
        </div>
      </div>
      <p className="mt-2 text-slate-700">{candidate.logline}</p>
      <p className={`mt-2 rounded p-2 font-medium ${rightsAreExplicit ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-900"}`}>
        {rightsAreExplicit ? "Rights appear explicit. Still confirm terms before filming or publishing." : "Rights are not clear. Do not film or publish without permission."}
      </p>
      <p className="mt-2 font-semibold text-slate-700">{String(candidate.scene_brief.label ?? "")}</p>
      <dl className="mt-2 grid gap-1 text-slate-600">
        <div><dt className="font-semibold">Character</dt><dd>{String(candidate.scene_brief.character_type ?? "Actor-forward role")}</dd></div>
        <div><dt className="font-semibold">Conflict</dt><dd>{String(candidate.scene_brief.conflict ?? "Clear two-person conflict")}</dd></div>
        <div><dt className="font-semibold">Length</dt><dd>{String(candidate.scene_brief.length ?? "60-90 seconds")}</dd></div>
      </dl>
      {candidate.source_url && <a className="mt-2 inline-block font-semibold text-accent hover:underline" href={candidate.source_url} target="_blank" rel="noreferrer">Open source</a>}
      <div className="mt-3 flex flex-wrap gap-2">
        <button className="text-xs font-semibold text-accent hover:underline" onClick={() => void onUpdate(candidate, "Saved")}>Save Scene Idea</button>
        {!rightsAreExplicit && (
          <button className="text-xs font-semibold text-accent hover:underline" onClick={() => void onUpdate(candidate, "Permission Requested")}>Mark Permission Requested</button>
        )}
        <button className="text-xs font-semibold text-accent hover:underline" onClick={() => void onGenerateOriginal(candidate)}>Generate Original Scene Brief</button>
      </div>
    </article>
  );
}
