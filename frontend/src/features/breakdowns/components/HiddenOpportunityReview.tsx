import { useEffect, useRef, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { Badge, ConfirmAction, DetailDisclosure } from "../../../components/ui";
import { errorMessage } from "../../../services/api/errors";
import { useApproveBreakdown, useDeepParseBreakdown, useDeleteBreakdown } from "../hooks/useBreakdownQueries";
import type { Opportunity } from "../types";
import {
  FactInferencePanel, KeyValueEntries, KeyValueGrid, OpportunityLink, TextAction,
  boolLabel, detailValue, externalBreakdownUrl, hiddenBreakdownReason, missingFields, productionFallback, roleFallback,
  type HiddenBreakdownAction
} from "./BreakdownDetails";
import { BreakdownViewer } from "./BreakdownViewer";
import { HiddenOpportunityActionForm } from "./HiddenOpportunityActionForm";

type ActionState = { type: HiddenBreakdownAction; opportunityId: string } | null;

export function HiddenOpportunityReview({ hiddenOpportunities }: { hiddenOpportunities: Opportunity[] }) {
  const [open, setOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [action, setAction] = useState<ActionState>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const disclosureRef = useRef<HTMLButtonElement>(null);
  const approve = useApproveBreakdown();
  const remove = useDeleteBreakdown();
  const deepParse = useDeepParseBreakdown();
  const selected = hiddenOpportunities.find((item) => item.id === selectedId) ?? null;
  const actionOpportunity = hiddenOpportunities.find((item) => item.id === action?.opportunityId) ?? null;

  useEffect(() => {
    if (selectedId && !selected) setSelectedId(null);
    if (action && !actionOpportunity) setAction(null);
  }, [action, actionOpportunity, selected, selectedId]);

  async function deleteOpportunity(opportunity: Opportunity) {
    if (remove.isPending) return;
    setDeleteError(null);
    try {
      await remove.mutateAsync(opportunity.id);
      if (selectedId === opportunity.id) setSelectedId(null);
      if (action?.opportunityId === opportunity.id) setAction(null);
      disclosureRef.current?.focus();
    } catch (caught) {
      setDeleteError(errorMessage(caught, "Could not delete this opportunity."));
    }
  }
  async function approveOpportunity(opportunity: Opportunity) {
    setActionError(null);
    try { await approve.mutateAsync(opportunity.id); }
    catch (caught) { setActionError(errorMessage(caught, "Could not approve this opportunity.")); }
  }
  async function deepParseOpportunity(opportunity: Opportunity) {
    setActionError(null);
    try { await deepParse.mutateAsync(opportunity.id); }
    catch (caught) { setActionError(errorMessage(caught, "Could not deep parse this opportunity.")); }
  }
  const chooseAction = (type: HiddenBreakdownAction, opportunity: Opportunity) => setAction({ type, opportunityId: opportunity.id });

  return <div className="rounded-md border border-slate-200 p-3">
    <button ref={disclosureRef} type="button" className="inline-flex items-center gap-2 font-semibold" onClick={() => setOpen((value) => !value)} aria-expanded={open} aria-controls="hidden-opportunity-review">
      {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />} Travel Exceptions / Needs Review
    </button>
    {open && <div id="hidden-opportunity-review">
      <p className="mt-1 text-sm text-slate-600">Travel exceptions and parser review items stay here. Hard demographic and role-type mismatches are discarded from normal actor views.</p>
      <div className="mt-3 grid gap-2">
        {deleteError && <p role="alert" tabIndex={-1} className="rounded bg-red-50 p-2 text-sm text-red-700">{deleteError}</p>}
        {actionError && <p role="alert" className="rounded bg-red-50 p-2 text-sm text-red-700">{actionError}</p>}
        {(approve.isPending || remove.isPending || deepParse.isPending) && <p role="status" className="text-sm text-slate-600">Updating hidden opportunity…</p>}
        {hiddenOpportunities.length === 0 ? <p className="text-sm text-slate-500">No travel exceptions or review-only breakdowns.</p> : hiddenOpportunities.map((opportunity) =>
          <div key={opportunity.id} aria-current={selectedId === opportunity.id ? "true" : undefined} className="rounded border border-amber-100 bg-amber-50 p-3 text-sm text-amber-950">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between"><div className="min-w-0">
              <p><OpportunityLink opportunity={opportunity} /></p><p className="mt-1 text-amber-900"><span className="font-medium">Project:</span> {opportunity.project}</p>
              <p className="text-amber-900"><span className="font-medium">Role:</span> {opportunity.role}</p><p className="mt-1 text-amber-900"><span className="font-medium">Reason:</span> {hiddenBreakdownReason(opportunity)}</p>
              {!externalBreakdownUrl(opportunity) && <p className="mt-1 text-amber-800">No source link available.</p>}
            </div><Badge>{opportunity.visibility_status === "travel_exception" ? "Travel Exception" : "Needs Review"}</Badge></div>
            {missingFields(opportunity).length > 0 && <p className="mt-1">Missing: {missingFields(opportunity).join(", ")}</p>}
            <div className="mt-2 flex flex-wrap gap-2">
              {externalBreakdownUrl(opportunity) ? <a className="text-sm font-semibold text-accent underline" href={externalBreakdownUrl(opportunity) ?? undefined} target="_blank" rel="noreferrer">Open Source</a> : <span className="text-sm text-amber-800">No source link available</span>}
              <TextAction onClick={() => setSelectedId(opportunity.id)}>View Details</TextAction>
              <TextAction onClick={() => chooseAction("travel", opportunity)}>Travel Info</TextAction><TextAction onClick={() => chooseAction("complete", opportunity)}>Complete</TextAction>
              <button type="button" className="text-sm font-semibold text-accent hover:underline disabled:opacity-60" disabled={approve.isPending} onClick={() => void approveOpportunity(opportunity)}>Approve</button>
              <ConfirmAction label="Delete" message={`Permanently delete ${opportunity.role}? Opportunities with linked submissions cannot be deleted; reject or archive them instead.`} onConfirm={() => deleteOpportunity(opportunity)} />
            </div>
            {action?.opportunityId === opportunity.id && selectedId !== opportunity.id && actionOpportunity && <HiddenOpportunityActionForm key={`${action.type}-${opportunity.id}`} action={action.type} opportunity={actionOpportunity} onCancel={() => setAction(null)} onSaved={() => setAction(null)} />}
          </div>)}
      </div>
      {selected && <HiddenOpportunityDetails opportunity={selected} onClose={() => setSelectedId(null)} onApprove={() => void approveOpportunity(selected)} onDelete={() => void deleteOpportunity(selected)} onRunDeepParse={() => deepParseOpportunity(selected)} onPasteText={() => chooseAction("paste", selected)} onManualAddRole={() => chooseAction("role", selected)} />}
      {action && selectedId === action.opportunityId && actionOpportunity && <HiddenOpportunityActionForm key={`${action.type}-${action.opportunityId}`} action={action.type} opportunity={actionOpportunity} onCancel={() => setAction(null)} onSaved={() => setAction(null)} />}
    </div>}
  </div>;
}

function HiddenOpportunityDetails({ opportunity, onClose, onApprove, onDelete, onRunDeepParse, onPasteText, onManualAddRole }: {
  opportunity: Opportunity; onClose: () => void; onApprove: () => void; onDelete: () => void;
  onRunDeepParse: () => Promise<unknown>; onPasteText: () => void; onManualAddRole: () => void;
}) {
  const sourceUrl = externalBreakdownUrl(opportunity);
  const travel = opportunity.source_metadata?.audition_travel && typeof opportunity.source_metadata.audition_travel === "object" && !Array.isArray(opportunity.source_metadata.audition_travel) ? opportunity.source_metadata.audition_travel as Record<string, unknown> : {};
  return <div className="mt-4 overflow-hidden rounded-md border border-amber-200 bg-white shadow-sm">
    <div className="flex flex-col gap-3 border-b border-amber-100 bg-amber-50 p-3 sm:flex-row sm:items-start sm:justify-between"><div className="min-w-0">
      <p className="text-xs font-semibold uppercase tracking-wide text-amber-700">{opportunity.visibility_status === "travel_exception" ? "Travel Exception Details" : "Needs Review Details"}</p>
      <h3 className="mt-1 break-words text-base font-semibold text-ink">{opportunity.project} · {opportunity.role}</h3><p className="mt-1 break-words text-sm text-amber-900">{hiddenBreakdownReason(opportunity)}</p>
      {sourceUrl ? <a className="mt-2 inline-flex text-sm font-semibold text-accent hover:underline" href={sourceUrl} target="_blank" rel="noreferrer">Open Source</a> : <p className="mt-2 text-sm text-amber-800">No source link available.</p>}
    </div><div className="flex shrink-0 flex-wrap gap-2 text-sm font-semibold"><button type="button" className="text-accent hover:underline" onClick={onApprove}>Approve anyway</button><ConfirmAction label="Delete" message={`Permanently delete ${opportunity.role}? Opportunities with linked submissions cannot be deleted; reject or archive them instead.`} onConfirm={onDelete} /><button type="button" className="text-slate-700 hover:underline" onClick={onClose}>Close</button></div></div>
    <div className="grid gap-3 p-3"><div className="grid gap-3 md:grid-cols-2">
      <div className="rounded border border-slate-200 bg-slate-50 p-3"><h4 className="font-semibold text-ink">Why It Was Flagged</h4><KeyValueEntries entries={Object.entries({ status: opportunity.visibility_status === "travel_exception" ? "Travel Exception" : "Needs Review", reason: hiddenBreakdownReason(opportunity), rule: opportunity.hidden_by_rule, rejection_reason: opportunity.rejection_reason, manual_review_required: boolLabel(opportunity.manual_review_required), demographic_status: opportunity.demographic_match_status, demographic_explanation: opportunity.demographic_match_explanation }).filter(([, value]) => detailValue(value))} /></div>
      <div className="rounded border border-slate-200 bg-slate-50 p-3"><h4 className="font-semibold text-ink">Audition Travel</h4><KeyValueEntries entries={Object.entries({ audition_type: opportunity.audition_type, audition_location: opportunity.audition_location || opportunity.production_details?.audition_location_name || opportunity.role_details?.audition_location_name, audition_address: opportunity.production_details?.audition_address || opportunity.role_details?.audition_address, audition_drive_time: opportunity.audition_drive_time ?? opportunity.audition_travel_hours, distance_miles: travel.distance_miles, estimate_basis: travel.basis, travel_provider: travel.provider, confidence: travel.confidence_score, shoot_or_performance_location: opportunity.shoot_location || opportunity.location, travel_covered: boolLabel(opportunity.travel_covered), housing_covered: boolLabel(opportunity.housing_covered) }).filter(([, value]) => detailValue(value))} /></div>
    </div>
    <DetailDisclosure label="Original Text" defaultOpen><pre className="max-h-72 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-3 text-xs leading-relaxed text-slate-700">{opportunity.description || "No original breakdown text was saved."}</pre></DetailDisclosure>
    <DetailDisclosure label="Parsed Facts" defaultOpen><FactInferencePanel facts={opportunity.extracted_facts} fallbackFacts={{ project: opportunity.project, role: opportunity.role, project_type: opportunity.project_type, role_type: opportunity.role_type, union: opportunity.union, rate: opportunity.rate, source_url: sourceUrl }} inference={opportunity.ai_inference} /></DetailDisclosure>
    <DetailDisclosure label="Production & Role Details"><div className="grid gap-3 md:grid-cols-2"><div><h4 className="mb-2 font-semibold text-ink">Production Details</h4><KeyValueGrid data={opportunity.production_details} fallback={productionFallback(opportunity)} /></div><div><h4 className="mb-2 font-semibold text-ink">Role Details</h4><KeyValueGrid data={opportunity.role_details} fallback={roleFallback(opportunity)} /></div></div></DetailDisclosure>
    <DetailDisclosure label="Breakdown Viewer"><BreakdownViewer opportunity={opportunity} onRunDeepParse={async () => { await onRunDeepParse(); }} onPasteText={onPasteText} onManualAddRole={onManualAddRole} /></DetailDisclosure>
    </div>
  </div>;
}
