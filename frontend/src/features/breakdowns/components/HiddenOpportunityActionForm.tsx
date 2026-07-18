import { useState, type FormEvent } from "react";
import { Button, Field, inputClass } from "../../../components/ui";
import { useDeepParseBreakdown, useParseBreakdownText, useUpdateBreakdown } from "../hooks/useBreakdownQueries";
import type { Opportunity } from "../types";
import {
  completeBreakdownInitialState,
  parseManualHours,
  travelInfoInitialState,
  type BreakdownRoleFormState,
  type HiddenBreakdownAction,
  type PasteBreakdownTextFormState
} from "./BreakdownDetails";

export function HiddenOpportunityActionForm({ action, opportunity, onCancel, onSaved }: {
  action: HiddenBreakdownAction;
  opportunity: Opportunity;
  onCancel: () => void;
  onSaved: () => void;
}) {
  const updateMutation = useUpdateBreakdown();
  const parseMutation = useParseBreakdownText();
  const deepParseMutation = useDeepParseBreakdown();
  const [completeForm, setCompleteForm] = useState(() => completeBreakdownInitialState(opportunity));
  const [travelForm, setTravelForm] = useState(() => travelInfoInitialState(opportunity));
  const [pasteForm, setPasteForm] = useState<PasteBreakdownTextFormState>({ raw_text: opportunity.description || "" });
  const [roleForm, setRoleForm] = useState<BreakdownRoleFormState>({ role_name: "", requirements: "", character_description: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError(null);
    try {
      if (action === "complete") {
        const hours = parseManualHours(completeForm.audition_travel_hours);
        if (Number.isNaN(hours)) { setError("Enter drive time as a number of hours, like 2.5."); return; }
        await updateMutation.mutateAsync({ id: opportunity.id, patch: {
          project_type: completeForm.project_type || null, role_type: completeForm.role_type || null,
          audition_type: completeForm.audition_type || "Unknown", audition_location: completeForm.audition_location || null,
          audition_travel_hours: hours, audition_deadline: completeForm.audition_deadline || null,
          location: completeForm.location || opportunity.location, union: completeForm.union || opportunity.union
        } });
      }
      if (action === "travel") {
        const hours = parseManualHours(travelForm.audition_travel_hours);
        if (Number.isNaN(hours)) { setError("Enter drive time as a number of hours, like 2.5."); return; }
        await updateMutation.mutateAsync({ id: opportunity.id, patch: {
          audition_location: travelForm.audition_location.trim() || null, audition_travel_hours: hours
        } });
      }
      if (action === "paste") {
        if (!pasteForm.raw_text.trim()) { setError("Paste breakdown text before re-running parsing."); return; }
        await parseMutation.mutateAsync({ id: opportunity.id, text: pasteForm.raw_text.trim() });
      }
      if (action === "role") {
        if (!roleForm.role_name.trim()) { setError("Role name is required."); return; }
        const available_roles = [...((opportunity.role_details?.available_roles as Array<Record<string, unknown>> | undefined) ?? []), {
          role_name: roleForm.role_name.trim(), role_type: "Needs Review",
          character_description: roleForm.character_description.trim() || roleForm.requirements.trim() || null,
          role_requirement_text: roleForm.requirements.trim() || roleForm.character_description.trim() || roleForm.role_name.trim()
        }];
        await updateMutation.mutateAsync({ id: opportunity.id, patch: { role_details: { ...opportunity.role_details, available_roles } } });
        await deepParseMutation.mutateAsync(opportunity.id);
      }
      onSaved();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save this breakdown update.");
    } finally { setSaving(false); }
  }

  const title = { complete: "Complete This Breakdown", travel: "Update Travel Info", paste: "Paste Actual Breakdown Text", role: "Manually Add Role" }[action];
  return (
    <form className="mt-3 grid gap-3 rounded-md border border-slate-200 bg-white p-3 text-sm text-slate-700" onSubmit={submit}>
      <div className="flex items-center justify-between gap-3"><h4 className="font-semibold text-ink">{title}</h4><button type="button" className="text-xs font-semibold text-slate-600 hover:underline" onClick={onCancel}>Cancel</button></div>
      {action === "complete" && <div className="grid gap-3 md:grid-cols-2">
        <Field label="Project Type"><input className={inputClass} value={completeForm.project_type} onChange={(e) => setCompleteForm({ ...completeForm, project_type: e.target.value })} /></Field>
        <Field label="Role Billing"><input className={inputClass} value={completeForm.role_type} onChange={(e) => setCompleteForm({ ...completeForm, role_type: e.target.value })} /></Field>
        <Field label="Audition Type"><input className={inputClass} value={completeForm.audition_type} onChange={(e) => setCompleteForm({ ...completeForm, audition_type: e.target.value })} /></Field>
        <Field label="Audition Location"><input className={inputClass} value={completeForm.audition_location} onChange={(e) => setCompleteForm({ ...completeForm, audition_location: e.target.value })} /></Field>
        <Field label="Manual Drive Time Estimate"><input className={inputClass} type="number" step="0.1" value={completeForm.audition_travel_hours} onChange={(e) => setCompleteForm({ ...completeForm, audition_travel_hours: e.target.value })} /></Field>
        <Field label="Audition/Tape Due Date"><input className={inputClass} value={completeForm.audition_deadline} onChange={(e) => setCompleteForm({ ...completeForm, audition_deadline: e.target.value })} /></Field>
        <Field label="Shoot/Performance Location"><input className={inputClass} value={completeForm.location} onChange={(e) => setCompleteForm({ ...completeForm, location: e.target.value })} /></Field>
        <Field label="Union Status"><input className={inputClass} value={completeForm.union} onChange={(e) => setCompleteForm({ ...completeForm, union: e.target.value })} /></Field>
      </div>}
      {action === "travel" && <div className="grid gap-3 md:grid-cols-2">
        <Field label="Audition Location"><input className={inputClass} value={travelForm.audition_location} onChange={(e) => setTravelForm({ ...travelForm, audition_location: e.target.value })} /></Field>
        <Field label="Manual Drive Time Override"><input className={inputClass} type="number" step="0.1" value={travelForm.audition_travel_hours} onChange={(e) => setTravelForm({ ...travelForm, audition_travel_hours: e.target.value })} /></Field>
      </div>}
      {action === "paste" && <Field label="Breakdown Text"><textarea className={inputClass} rows={8} value={pasteForm.raw_text} onChange={(e) => setPasteForm({ raw_text: e.target.value })} /></Field>}
      {action === "role" && <div className="grid gap-3 md:grid-cols-2">
        <Field label="Role Name"><input className={inputClass} value={roleForm.role_name} onChange={(e) => setRoleForm({ ...roleForm, role_name: e.target.value })} /></Field>
        <Field label="Role Requirements"><textarea className={inputClass} value={roleForm.requirements} onChange={(e) => setRoleForm({ ...roleForm, requirements: e.target.value })} /></Field>
        <div className="md:col-span-2"><Field label="Character Breakdown"><textarea className={inputClass} value={roleForm.character_description} onChange={(e) => setRoleForm({ ...roleForm, character_description: e.target.value })} /></Field></div>
      </div>}
      {error && <p role="alert" className="rounded bg-red-50 p-2 text-xs font-medium text-red-700">{error}</p>}
      <div className="flex flex-wrap gap-2"><Button type="submit" disabled={saving}>{saving ? "Saving..." : "Save"}</Button><Button type="button" variant="secondary" onClick={onCancel}>Cancel</Button></div>
    </form>
  );
}
