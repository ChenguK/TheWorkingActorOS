import { useEffect, useRef, useState, type FormEvent } from "react";
import { Button, Field, inputClass } from "../../../components/ui";
import { sourceTypes, sourceTypeLabel } from "../constants";
import { useCreateBreakdown, useUpdateBreakdown } from "../hooks/useBreakdownQueries";
import type { Opportunity, Representation } from "../types";
import { createEmptyOpportunityDraft, formDraftToOpportunityRequest, opportunityToFormDraft, type OpportunityFormDraft } from "./opportunityFormModel";

export type OpportunityFormMode = { kind: "closed" } | { kind: "create" } | { kind: "edit"; opportunityId: string };
export type OpportunityFormWorkspaceProps = {
  mode: OpportunityFormMode;
  onModeChange: (mode: OpportunityFormMode) => void;
  opportunities: Opportunity[];
  representations: Representation[];
};

export function OpportunityFormWorkspace({ mode, onModeChange, opportunities, representations }: OpportunityFormWorkspaceProps) {
  const createMutation = useCreateBreakdown();
  const updateMutation = useUpdateBreakdown();
  const [draft, setDraft] = useState<OpportunityFormDraft>(createEmptyOpportunityDraft);
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sessionKey = mode.kind === "edit" ? `edit:${mode.opportunityId}` : mode.kind;
  const initializedSession = useRef<string>("closed");
  const opportunity = mode.kind === "edit" ? opportunities.find((item) => item.id === mode.opportunityId) : undefined;

  useEffect(() => {
    if (mode.kind === "closed") { initializedSession.current = "closed"; return; }
    if (initializedSession.current !== sessionKey) {
      setDraft(mode.kind === "edit" && opportunity ? opportunityToFormDraft(opportunity) : createEmptyOpportunityDraft());
      setDirty(false); setError(null); initializedSession.current = sessionKey;
      return;
    }
    if (mode.kind === "edit" && opportunity && !dirty) setDraft(opportunityToFormDraft(opportunity));
  }, [dirty, mode.kind, opportunity, sessionKey]);

  useEffect(() => {
    if (mode.kind === "edit" && !opportunity) onModeChange({ kind: "closed" });
  }, [mode, onModeChange, opportunity]);

  if (mode.kind === "closed" || (mode.kind === "edit" && !opportunity)) return null;
  const editingId = mode.kind === "edit" ? mode.opportunityId : null;
  const pending = createMutation.isPending || updateMutation.isPending;
  const change = (patch: Partial<OpportunityFormDraft>) => { setDraft((current) => ({ ...current, ...patch })); setDirty(true); };
  const close = () => { setDraft(createEmptyOpportunityDraft()); setDirty(false); setError(null); onModeChange({ kind: "closed" }); };

  async function submit(event: FormEvent) {
    event.preventDefault(); setError(null);
    try {
      const payload = formDraftToOpportunityRequest(draft);
      if (editingId) await updateMutation.mutateAsync({ id: editingId, patch: payload });
      else await createMutation.mutateAsync(payload);
      close();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : `Could not ${editingId ? "update" : "create"} this breakdown.`);
    }
  }

  return (
    <form className="mb-4 grid gap-3 rounded-md border border-slate-200 bg-slate-50 p-3 lg:grid-cols-4" onSubmit={submit} aria-busy={pending}>
      <div className="flex items-center justify-between gap-3 lg:col-span-4"><div><h3 className="font-semibold text-ink">{editingId ? "Edit Breakdown" : "Add Breakdown"}</h3><p className="mt-1 text-xs text-slate-600">{editingId ? "Update the collected breakdown information, then save." : "Enter the breakdown details you have. Optional fields can stay blank."}</p></div>{editingId && <Button type="button" variant="secondary" onClick={close}>Cancel Edit</Button>}</div>
      <Field label="Source Type"><select className={inputClass} value={draft.source_type} onChange={(e) => change({ source_type: e.target.value as Opportunity["source_type"], from_agent: e.target.value === "Agent Submission" ? true : draft.from_agent })}>{sourceTypes.map((type) => <option key={type} value={type}>{sourceTypeLabel(type)}</option>)}</select></Field>
      <Field label="Platform"><input className={inputClass} value={draft.platform} onChange={(e) => change({ platform: e.target.value })} placeholder="Casting Networks, Email" /></Field>
      <Field label="Agent / Agency"><select className={inputClass} value={representations.some((item) => item.id === draft.representation_id) ? draft.representation_id : ""} onChange={(e) => change({ representation_id: e.target.value })}><option value="">None</option>{representations.map((item) => <option key={item.id} value={item.id}>{item.agency_name} · {item.agent_name || item.representation_type}</option>)}</select></Field>
      <label className="flex items-center gap-2 text-sm text-slate-700"><input name="from_agent" type="checkbox" checked={draft.from_agent} onChange={(e) => change({ from_agent: e.target.checked })} />From Agent</label>
      <Field label="Role"><input className={inputClass} value={draft.role} onChange={(e) => change({ role: e.target.value })} required /></Field>
      <Field label="Project"><input className={inputClass} value={draft.project} onChange={(e) => change({ project: e.target.value })} required /></Field>
      <Field label="Production Company"><input className={inputClass} value={draft.production_company} onChange={(e) => change({ production_company: e.target.value })} placeholder="Not required" /></Field>
      <Field label="Project Type"><input className={inputClass} value={draft.project_type} onChange={(e) => change({ project_type: e.target.value })} placeholder="TV, Film, Commercial" /></Field>
      <Field label="Role Type"><input className={inputClass} value={draft.role_type} onChange={(e) => change({ role_type: e.target.value })} placeholder="Guest Star, Principal" /></Field>
      <Field label="Casting Office"><input className={inputClass} value={draft.casting_office} onChange={(e) => change({ casting_office: e.target.value })} /></Field>
      <Field label="Casting Contact"><input className={inputClass} value={draft.casting_contact} onChange={(e) => change({ casting_contact: e.target.value })} /></Field>
      <Field label="Archetypes"><input className={inputClass} value={draft.archetypes} onChange={(e) => change({ archetypes: e.target.value })} placeholder="Mom, Friendly, Detective" /></Field>
      <Field label="Union"><input className={inputClass} value={draft.union} onChange={(e) => change({ union: e.target.value })} required /></Field>
      <Field label="Rate"><input className={inputClass} value={draft.rate} onChange={(e) => change({ rate: e.target.value })} /></Field>
      <Field label="Shoot Location"><input className={inputClass} value={draft.location} onChange={(e) => change({ location: e.target.value })} required /></Field>
      <Field label="Audition Location"><input className={inputClass} value={draft.audition_location} onChange={(e) => change({ audition_location: e.target.value })} /></Field>
      <Field label="Audition Type"><select className={inputClass} value={draft.audition_type} onChange={(e) => change({ audition_type: e.target.value })}><option>Self-Tape</option><option>Virtual</option><option>In-Person</option><option>Unknown</option></select></Field>
      <Field label="Audition Travel Hours"><input className={inputClass} type="number" step="0.1" value={draft.audition_travel_hours} onChange={(e) => change({ audition_travel_hours: e.target.value })} /></Field>
      <Field label="Original Post URL"><input className={inputClass} type="url" value={draft.original_post_url} onChange={(e) => change({ original_post_url: e.target.value })} placeholder="https://..." /></Field>
      <Field label="Priority"><select className={inputClass} value={draft.priority} onChange={(e) => change({ priority: e.target.value })}><option>Low</option><option>Medium</option><option>High</option><option>Urgent</option></select></Field>
      <Field label="Audition/Tape Due Date"><input className={inputClass} type="datetime-local" value={draft.audition_deadline} onChange={(e) => change({ audition_deadline: e.target.value })} /></Field>
      <Field label="Callback Date"><input className={inputClass} type="datetime-local" value={draft.callback_date} onChange={(e) => change({ callback_date: e.target.value })} /></Field>
      <Field label="Shoot Start"><input className={inputClass} type="date" value={draft.shoot_start_date} onChange={(e) => change({ shoot_start_date: e.target.value })} /></Field>
      <Field label="Shoot End"><input className={inputClass} type="date" value={draft.shoot_end_date} onChange={(e) => change({ shoot_end_date: e.target.value })} /></Field>
      <Field label="Virtual Audition Link"><input className={inputClass} type="url" value={draft.virtual_audition_link} onChange={(e) => change({ virtual_audition_link: e.target.value })} /></Field>
      <Field label="Self-Tape Submission Link"><input className={inputClass} type="url" value={draft.self_tape_submission_link} onChange={(e) => change({ self_tape_submission_link: e.target.value })} /></Field>
      <label className="flex items-center gap-2 text-sm text-slate-700"><input name="travel_covered" type="checkbox" checked={draft.travel_covered} onChange={(e) => change({ travel_covered: e.target.checked })} />Travel Covered</label>
      <label className="flex items-center gap-2 text-sm text-slate-700"><input name="housing_covered" type="checkbox" checked={draft.housing_covered} onChange={(e) => change({ housing_covered: e.target.checked })} />Housing Covered</label>
      <div className="lg:col-span-2"><Field label="Preparation Instructions"><textarea className={inputClass} value={draft.preparation_instructions} onChange={(e) => change({ preparation_instructions: e.target.value })} /></Field></div>
      <div className="lg:col-span-2"><Field label="Submission Instructions"><textarea className={inputClass} value={draft.submission_instructions} onChange={(e) => change({ submission_instructions: e.target.value })} /></Field></div>
      <div className="lg:col-span-2"><Field label="Character Breakdown"><textarea className={inputClass} value={draft.description} onChange={(e) => change({ description: e.target.value })} required /></Field></div>
      <div className="lg:col-span-3"><Field label="Notes"><textarea className={inputClass} value={draft.notes} onChange={(e) => change({ notes: e.target.value })} /></Field></div>
      {error && <p role="alert" className="rounded bg-red-50 p-2 text-sm font-medium text-red-700 lg:col-span-4">{error}</p>}
      {pending && <p role="status" className="text-sm text-slate-600 lg:col-span-4">Saving breakdown…</p>}
      <Button type="submit" disabled={pending}>{pending ? "Saving..." : editingId ? "Save Breakdown" : "Create Breakdown"}</Button>
      {!editingId && <Button type="button" variant="secondary" onClick={close}>Cancel</Button>}
    </form>
  );
}
