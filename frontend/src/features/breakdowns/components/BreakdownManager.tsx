import { useRef, useState, type FormEvent } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { ActionCard, Badge, Button, DetailDisclosure, EmptyState, Field, Section, inputClass } from "../../../components/ui";
import { useDeepParseBreakdown, useGenerateBreakdownStrategy, useParseBreakdownText, useRefreshDemographicCheck, useRejectBreakdown, useUpdateBreakdown } from "../hooks/useBreakdownQueries";
import type { BreakdownFilter, Opportunity, Representation } from "../types";
import { sourceTypeLabel } from "../constants";
import { KeyValueGrid, OpportunityLink, TextAction, TrustVerificationPanel, breakdownFamily, detailValue, formatDateTime, missingFields, parseConfidence, preparationText, productionFallback, projectTypeLabel, roleFallback, roleFitLabel, withoutKeys, type BreakdownRejectFormState, type BreakdownRoleFormState } from "./BreakdownDetails";
import { RoleViewer } from "./BreakdownRoleDetails";
import { BreakdownViewer } from "./BreakdownViewer";
import { OpportunityFormWorkspace, type OpportunityFormMode } from "./OpportunityFormWorkspace";
import { errorMessage } from "../../../services/api/errors";

export function OpportunityManager({
  opportunities,
  hiddenOpportunities = [],
  representations
}: {
  opportunities: Opportunity[];
  hiddenOpportunities?: Opportunity[];
  representations: Representation[];
}) {
  const parseMutation = useParseBreakdownText(); const deepParseMutation = useDeepParseBreakdown();
  const strategyMutation = useGenerateBreakdownStrategy(); const demographicMutation = useRefreshDemographicCheck();
  const [formMode, setFormMode] = useState<OpportunityFormMode>(opportunities.length === 0 ? { kind: "create" } : { kind: "closed" });
  const [breakdownFilter, setBreakdownFilter] = useState<BreakdownFilter>("All");
  const [pasteOpenById, setPasteOpenById] = useState<Record<string, boolean>>({});
  const [pasteTextById, setPasteTextById] = useState<Record<string, string>>({});
  const [pastePendingById, setPastePendingById] = useState<Record<string, boolean>>({});
  const [pasteErrorById, setPasteErrorById] = useState<Record<string, string | null>>({});
  const pasteTriggerRefs = useRef<Record<string, HTMLButtonElement | null>>({});
  const pasteTextareaRefs = useRef<Record<string, HTMLTextAreaElement | null>>({});
  const [deepParsePendingById, setDeepParsePendingById] = useState<Record<string, boolean>>({});
  const [deepParseErrorById, setDeepParseErrorById] = useState<Record<string, string | null>>({});
  const deepParsePendingIds = useRef(new Set<string>());
  const expansionTriggerRefs = useRef<Record<string, HTMLButtonElement | null>>({});
  const [expandedBreakdowns, setExpandedBreakdowns] = useState<Record<string, boolean>>({});
  const [rejectingBreakdown, setRejectingBreakdown] = useState<Opportunity | null>(null);
  const [addingRoleForBreakdown, setAddingRoleForBreakdown] = useState<Opportunity | null>(null);
  async function parsePastedBreakdown(event: FormEvent, opportunity: Opportunity) {
    event.preventDefault();
    if (pastePendingById[opportunity.id]) return;
    const raw_text = pasteTextById[opportunity.id]?.trim();
    if (!raw_text) return;
    setPastePendingById((current) => ({ ...current, [opportunity.id]: true }));
    setPasteErrorById((current) => ({ ...current, [opportunity.id]: null }));
    try {
      await parseMutation.mutateAsync({ id: opportunity.id, text: raw_text });
      setPasteTextById((current) => ({ ...current, [opportunity.id]: "" }));
      setPasteOpenById((current) => ({ ...current, [opportunity.id]: false }));
      requestAnimationFrame(() => pasteTriggerRefs.current[opportunity.id]?.focus());
    } catch (caught) {
      setPasteErrorById((current) => ({
        ...current,
        [opportunity.id]: errorMessage(caught, "Could not parse this breakdown text.")
      }));
    } finally {
      setPastePendingById((current) => ({ ...current, [opportunity.id]: false }));
    }
  }

  async function runDeepParse(opportunity: Opportunity) {
    if (deepParsePendingIds.current.has(opportunity.id)) return;
    const invokingButton = document.activeElement instanceof HTMLButtonElement ? document.activeElement : null;
    deepParsePendingIds.current.add(opportunity.id);
    setDeepParsePendingById((current) => ({ ...current, [opportunity.id]: true }));
    setDeepParseErrorById((current) => ({ ...current, [opportunity.id]: null }));
    try {
      await deepParseMutation.mutateAsync(opportunity.id);
      requestAnimationFrame(() => expansionTriggerRefs.current[opportunity.id]?.focus());
    } catch (caught) {
      setDeepParseErrorById((current) => ({
        ...current,
        [opportunity.id]: errorMessage(caught, "Could not deep parse this opportunity.")
      }));
      requestAnimationFrame(() => {
        if (invokingButton?.isConnected) invokingButton.focus();
      });
    } finally {
      deepParsePendingIds.current.delete(opportunity.id);
      setDeepParsePendingById((current) => ({ ...current, [opportunity.id]: false }));
    }
  }

  const visibleBreakdowns = breakdownFilter === "TravelExceptions"
    ? hiddenOpportunities
    : opportunities.filter((opportunity) => {
      if (breakdownFilter === "All") return true;
      if (breakdownFilter === "NeedsReview") {
        return opportunity.manual_review_required || opportunity.breakdown_classification === "Unknown" || opportunity.demographic_match_status === "Needs Review";
      }
      return breakdownFamily(opportunity) === breakdownFilter;
    });

  return (
    <Section
      title="Breakdowns"
      actions={<Button onClick={() => setFormMode((current) => current.kind === "closed" ? { kind: "create" } : { kind: "closed" })}>{formMode.kind === "closed" ? "Add Breakdown" : "Hide Form"}</Button>}
    >
      <div className="mb-3 flex flex-wrap gap-2">
        {[
          ["Theater", "Theater"],
          ["FilmTV", "Film/TV"],
          ["All", "All"],
          ["TravelExceptions", "Travel Exceptions"],
          ["NeedsReview", "Needs Review"]
        ].map(([value, label]) => (
          <Button
            key={value}
            variant={breakdownFilter === value ? "primary" : "secondary"}
            onClick={() => setBreakdownFilter(value as BreakdownFilter)}
          >
            {label}
          </Button>
        ))}
      </div>
      <OpportunityFormWorkspace mode={formMode} onModeChange={setFormMode} opportunities={opportunities} representations={representations} />
      <div className="grid gap-2">
        {visibleBreakdowns.length === 0 ? (
          <EmptyState>New roles will appear here. Add a breakdown manually or discover public breakdowns from source pages.</EmptyState>
        ) : visibleBreakdowns.map((opportunity) => (
          <ActionCard
            key={opportunity.id}
            title={(
              <div className="flex min-w-0 items-center gap-2">
                <button ref={(node) => { expansionTriggerRefs.current[opportunity.id] = node; }} type="button" className="rounded p-1 text-slate-500 hover:bg-slate-100" aria-label={expandedBreakdowns[opportunity.id] ? "Collapse breakdown" : "Expand breakdown"} onClick={() => setExpandedBreakdowns((current) => ({ ...current, [opportunity.id]: !current[opportunity.id] }))}>
                  {expandedBreakdowns[opportunity.id] ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                </button>
                <OpportunityLink opportunity={opportunity} />
              </div>
            )}
            status={(
              <div className="flex flex-wrap gap-2">
                <Badge>{opportunity.role_type || opportunity.category || "Role"}</Badge>
                <Badge>{projectTypeLabel(opportunity)}</Badge>
              </div>
            )}
            meta={opportunity.project}
            details={expandedBreakdowns[opportunity.id] ? (
              <div className="grid gap-2">
                <div className="flex flex-wrap gap-2 rounded bg-slate-50 p-2">
                  <a className="text-sm font-semibold text-accent underline-offset-2 hover:underline" href={`/auditions?breakdownId=${opportunity.id}`}>Track audition</a>
                  <TextAction onClick={() => strategyMutation.mutateAsync(opportunity.id)}>Generate strategy</TextAction>
                  <TextAction tone="muted" onClick={() => setFormMode({ kind: "edit", opportunityId: opportunity.id })}>Edit</TextAction>
                  <TextAction tone="danger" onClick={() => setRejectingBreakdown(opportunity)}>Delete / reject</TextAction>
                  {opportunity.tracked_submission_id && <a className="text-sm font-semibold text-accent underline-offset-2 hover:underline" href="/auditions">View submission</a>}
                </div>
                {rejectingBreakdown?.id === opportunity.id && (
                  <BreakdownRejectForm
                    opportunity={opportunity}
                    selectedText={window.getSelection()?.toString().trim() || ""}
                    onCancel={() => setRejectingBreakdown(null)}
                    onSaved={async () => {
                      setRejectingBreakdown(null);
                    }}
                  />
                )}
                {addingRoleForBreakdown?.id === opportunity.id && (
                  <VisibleBreakdownRoleForm
                    opportunity={opportunity}
                    onCancel={() => setAddingRoleForBreakdown(null)}
                    onSaved={async () => {
                      setAddingRoleForBreakdown(null);
                    }}
                  />
                )}
                {opportunity.ai_summary && (
                  <p className="rounded bg-blue-50 p-2 text-sm font-medium text-blue-900">{opportunity.ai_summary}</p>
                )}
                <div className="flex flex-wrap gap-2 text-sm">
                  <Badge>{projectTypeLabel(opportunity)}</Badge>
                  <Badge>Mode: {String(opportunity.source_metadata?.discovery_mode ?? "Manual/Unknown")}</Badge>
                  <Badge>Role Fit: {roleFitLabel(opportunity)}</Badge>
                  <Badge>Match: {opportunity.demographic_match_status}</Badge>
                  <Badge>Parse: {parseConfidence(opportunity)}%</Badge>
                </div>
                {parseConfidence(opportunity) < 70 && (
                  <div className="rounded bg-amber-50 p-2 text-sm text-amber-900">
                    <p className="font-medium">Needs Review: parse confidence is below 70%.</p>
                    <p className="mt-1">The app already used the deep parser. Review the extracted facts, fill missing fields, or approve the breakdown if the details look right.</p>
                  </div>
                )}
                <TrustVerificationPanel opportunity={opportunity} />
                {(opportunity.manual_review_required || opportunity.breakdown_classification === "Unknown") && (
                  <p className="rounded bg-amber-50 p-2 text-sm text-amber-900">Needs Review: paste the actual breakdown text below to re-run parsing.</p>
                )}
                {deepParsePendingById[opportunity.id] && (
                  <p id={`deep-parse-feedback-${opportunity.id}`} role="status" className="rounded bg-blue-50 p-2 text-sm text-blue-900">
                    Deep parsing {opportunity.project}…
                  </p>
                )}
                {deepParseErrorById[opportunity.id] && (
                  <p id={`deep-parse-feedback-${opportunity.id}`} role="alert" className="rounded bg-red-50 p-2 text-sm text-red-700">
                    {deepParseErrorById[opportunity.id]}
                  </p>
                )}
                <div className="grid gap-3 rounded-md border border-slate-200 p-3 text-sm">
                  <h4 className="font-semibold text-ink">Production Details</h4>
                  <KeyValueGrid
                    data={opportunity.production_details}
                    fallback={productionFallback(opportunity)}
                  />
                </div>
                <div className="grid gap-3 rounded-md border border-slate-200 p-3 text-sm">
                  <h4 className="font-semibold text-ink">Role & Character Information</h4>
                  {opportunity.breakdown_roles.length === 0 ? (
                    <div className="grid gap-2 rounded bg-amber-50 p-3 text-amber-900">
                      <p className="font-medium">The parser could not confidently identify individual role sections.</p>
                      <div className="flex flex-wrap gap-2">
                        <TextAction
                          onClick={() => runDeepParse(opportunity)}
                          disabled={deepParsePendingById[opportunity.id]}
                          ariaDescribedBy={`deep-parse-feedback-${opportunity.id}`}
                        >Run deep parse</TextAction>
                        <TextAction onClick={() => setPasteOpenById((current) => ({ ...current, [opportunity.id]: true }))}>Paste actual text</TextAction>
                        <TextAction onClick={() => setAddingRoleForBreakdown(opportunity)}>Manually add role</TextAction>
                      </div>
                    </div>
                  ) : (
                    <RoleViewer roles={opportunity.breakdown_roles} />
                  )}
                </div>
                <div className="grid gap-3 rounded-md border border-slate-200 p-3 text-sm">
                  <h4 className="font-semibold text-ink">Role Details</h4>
                  <KeyValueGrid
                    data={withoutKeys(opportunity.role_details, ["available_roles"])}
                    fallback={{
                      role_name: opportunity.role,
                      role_type: opportunity.role_type,
                      archetypes: opportunity.archetypes,
                      audition_type: opportunity.audition_type,
                      audition_location: opportunity.audition_location,
                      character_description: opportunity.description
                    }}
                  />
                </div>
                <DetailDisclosure label="Breakdown Viewer" defaultOpen={false}>
                  <BreakdownViewer
                    opportunity={opportunity}
                    onRunDeepParse={() => runDeepParse(opportunity)}
                    onPasteText={() => setPasteOpenById((current) => ({ ...current, [opportunity.id]: true }))}
                    onManualAddRole={() => setAddingRoleForBreakdown(opportunity)}
                    deepParsePending={deepParsePendingById[opportunity.id]}
                  />
                </DetailDisclosure>
                <DetailDisclosure label="Submission Instructions">
                  <p>{detailValue(opportunity.role_details.submission_instructions) || detailValue(opportunity.source_metadata.submission_instructions) || "Needs Review"}</p>
                </DetailDisclosure>
                <DetailDisclosure label="Preparation">
                  <p>{preparationText(opportunity) || "Needs Review"}</p>
                </DetailDisclosure>
                <DetailDisclosure label="Detected Sections">
                  {opportunity.breakdown_sections.length === 0 ? (
                    <p>Needs Review</p>
                  ) : (
                    <div className="grid gap-2">
                      {opportunity.breakdown_sections.map((section) => (
                        <div key={section.id} className="rounded bg-slate-50 p-2">
                          <p className="font-medium">{section.section_type} · {section.confidence_score}%</p>
                          {section.heading && <p className="text-slate-600">{section.heading}</p>}
                          <p className="mt-1 line-clamp-3">{section.raw_text}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </DetailDisclosure>
                <DetailDisclosure label="Parse History">
                  {opportunity.breakdown_parse_runs.length === 0 ? (
                    <p>No parse history yet.</p>
                  ) : (
                    <div className="grid gap-2">
                      {opportunity.breakdown_parse_runs.slice(0, 5).map((run) => (
                        <div key={run.id} className="rounded bg-slate-50 p-2">
                          <p className="font-medium">{run.parse_mode} · {run.overall_confidence}% · {run.status}</p>
                          <p className="text-slate-600">{formatDateTime(run.started_at)}</p>
                          {run.error_message && <p className="text-red-700">{run.error_message}</p>}
                        </div>
                      ))}
                    </div>
                  )}
                </DetailDisclosure>
                <DetailDisclosure label="Travel / Audition Feasibility">
                  <p>Shoot location: {opportunity.location}</p>
                  <p>Audition location: {opportunity.audition_location || "Not listed"}</p>
                  <p>Audition travel: {opportunity.audition_travel_hours ?? "Unknown"} hours</p>
                  <p>Travel covered: {opportunity.travel_covered ? "Yes" : "No"} · Housing covered: {opportunity.housing_covered ? "Yes" : "No"}</p>
                  {opportunity.hidden_reason && <p className="mt-2 rounded bg-amber-50 p-2 text-amber-900">{opportunity.hidden_reason}</p>}
                </DetailDisclosure>
                <DetailDisclosure label="Submission Strategy Preview">
                  <p>{opportunity.quality_explanation || "Generate a strategy to see a recommended submission approach."}</p>
                  {opportunity.risk_explanation && <p className="mt-2">Risk: {opportunity.risk_explanation}</p>}
                  <p className="mt-2">Quality {opportunity.quality_score} · Urgency {opportunity.urgency_score} · {opportunity.risk_level} risk</p>
                </DetailDisclosure>
                {opportunity.demographic_match_status === "Not a Match" && (
                  <DetailDisclosure label="Why This Was Rejected or Marked Low Priority">
                    <p>{opportunity.demographic_match_explanation || "No individual role currently fits the saved actor profile."}</p>
                    {opportunity.breakdown_roles.length > 0 && (
                      <div className="mt-2 grid gap-2">
                        {opportunity.breakdown_roles.map((role) => (
                          <p key={`${role.id}-why`} className="rounded bg-red-50 p-2 text-red-800">
                            {role.role_name}: {role.fit_explanation || role.fit_status}
                          </p>
                        ))}
                      </div>
                    )}
                  </DetailDisclosure>
                )}
                <DetailDisclosure label="Source Metadata">
                  <KeyValueGrid
                    data={opportunity.source_metadata}
                    fallback={{
                      source_type: sourceTypeLabel(opportunity.source_type),
                      platform: opportunity.platform,
                      source_url: opportunity.original_post_url,
                      classification: opportunity.breakdown_classification,
                      rejection_reason: opportunity.rejection_reason
                    }}
                  />
                </DetailDisclosure>
                <DetailDisclosure label="Raw / Pasted Breakdown Text">
                  {opportunity.rejection_reason && (
                    <p className="mb-2 rounded bg-red-50 p-2 font-medium text-red-700">{opportunity.rejection_reason}</p>
                  )}
                  {opportunity.watchlist_notification && (
                    <p className="mb-2 rounded bg-amber-50 p-2 font-medium text-amber-800">{opportunity.watchlist_notification}</p>
                  )}
                  <p>{opportunity.description}</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <Badge>{opportunity.audition_type}</Badge>
                    {opportunity.from_agent && <Badge>Agent Submission</Badge>}
                    {opportunity.rate && <Badge>{opportunity.rate}</Badge>}
                    {opportunity.is_duplicate && <Badge>Duplicate</Badge>}
                  </div>
                  <div className="mt-3">
                    <button
                      ref={(element) => { pasteTriggerRefs.current[opportunity.id] = element; }}
                      type="button"
                      className="text-sm font-semibold text-accent underline-offset-2 hover:text-blue-700 hover:underline"
                      aria-expanded={Boolean(pasteOpenById[opportunity.id])}
                      onClick={() => {
                        const opening = !pasteOpenById[opportunity.id];
                        setPasteOpenById((current) => ({ ...current, [opportunity.id]: opening }));
                        setPasteErrorById((current) => ({ ...current, [opportunity.id]: null }));
                        if (opening) requestAnimationFrame(() => pasteTextareaRefs.current[opportunity.id]?.focus());
                      }}
                    >
                      {pasteOpenById[opportunity.id] ? "Hide Paste Box" : "Paste Actual Breakdown Text"}
                    </button>
                  </div>
                  {pasteOpenById[opportunity.id] && (
                    <form className="mt-3 grid gap-2" onSubmit={(event) => void parsePastedBreakdown(event, opportunity)}>
                      <Field label="Breakdown Text">
                        <textarea
                          ref={(element) => { pasteTextareaRefs.current[opportunity.id] = element; }}
                          className={inputClass}
                          rows={8}
                          value={pasteTextById[opportunity.id] ?? ""}
                          aria-describedby={pasteErrorById[opportunity.id] ? `paste-error-${opportunity.id}` : undefined}
                          onChange={(event) => {
                            setPasteTextById((current) => ({ ...current, [opportunity.id]: event.target.value }));
                            setPasteErrorById((current) => ({ ...current, [opportunity.id]: null }));
                          }}
                          placeholder="Paste the visible role breakdown text here, then re-run parsing."
                        />
                      </Field>
                      {pastePendingById[opportunity.id] && <p role="status" className="text-sm text-slate-600">Re-running breakdown parsing…</p>}
                      {pasteErrorById[opportunity.id] && <p id={`paste-error-${opportunity.id}`} role="alert" className="rounded bg-red-50 p-2 text-sm font-medium text-red-700">{pasteErrorById[opportunity.id]}</p>}
                      <div>
                        <Button type="submit" disabled={Boolean(pastePendingById[opportunity.id])}>{pastePendingById[opportunity.id] ? "Parsing…" : "Re-run Parsing"}</Button>
                      </div>
                    </form>
                  )}
                </DetailDisclosure>
                {opportunity.watchlist_match_count > 0 && (
                  <DetailDisclosure label="Watch Lists">
                    <div className="grid gap-2">
                      {opportunity.watchlist_match_names.map((match) => (
                        <div key={`${match.id}-${match.title}`} className="rounded bg-slate-50 p-2">
                          <p className="font-medium">{match.title} · {match.priority}</p>
                          <p>Matched: {match.matched_terms.join(", ")}</p>
                          <p className="text-slate-600">{match.category}</p>
                        </div>
                      ))}
                    </div>
                  </DetailDisclosure>
                )}
                <DetailDisclosure label="Demographics">
                  <p>{opportunity.demographic_match_explanation || "No demographic check has been run yet."}</p>
                  <div className="mt-2 grid gap-2">
                    {(opportunity.demographic_match_details?.checks ?? [])
                      .filter((check) => check.status !== "Not Specified")
                      .map((check) => (
                        <div key={`${check.label}-${check.status}`} className="rounded bg-slate-50 p-2">
                          <p className="font-medium">{check.label}: {check.status}</p>
                          {check.detected_requirements?.length ? (
                            <p>Breakdown says: {check.detected_requirements.join(", ")}</p>
                          ) : null}
                          {check.profile_values?.length ? (
                            <p>Your profile says: {check.profile_values.join(", ")}</p>
                          ) : null}
                          {check.explanation && <p className="text-slate-600">{check.explanation}</p>}
                        </div>
                      ))}
                  </div>
                  <div className="mt-3">
                    <TextAction onClick={() => demographicMutation.mutateAsync(opportunity.id)}>Refresh check</TextAction>
                  </div>
                </DetailDisclosure>
              </div>
            ) : null}
          />
        ))}
      </div>
    </Section>
  );
}

function BreakdownRejectForm({
  opportunity,
  selectedText,
  onCancel,
  onSaved
}: {
  opportunity: Opportunity;
  selectedText: string;
  onCancel: () => void;
  onSaved: () => Promise<void>;
}) {
  const rejectMutation = useRejectBreakdown();
  const [form, setForm] = useState<BreakdownRejectFormState>({
    highlighted_text_as_rejection_reason: selectedText,
    rejection_reason: selectedText || opportunity.rejection_reason || ""
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await rejectMutation.mutateAsync({ id: opportunity.id, payload: {
        highlighted_text_as_rejection_reason: form.highlighted_text_as_rejection_reason.trim() || null,
        rejection_reason: form.rejection_reason.trim() || null
      } });
      await onSaved();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not delete or reject this breakdown.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="grid gap-3 rounded-md border border-red-100 bg-red-50 p-3 text-sm text-red-950" onSubmit={submit}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <h4 className="font-semibold">Delete / Reject Breakdown</h4>
          <p className="mt-1 text-xs text-red-800">Save the text or reason that explains why this breakdown should disappear from your normal workflow.</p>
        </div>
        <button type="button" className="text-xs font-semibold text-red-800 hover:underline" onClick={onCancel}>Cancel</button>
      </div>
      <Field label="Highlighted text as rejection reason">
        <textarea className={inputClass} value={form.highlighted_text_as_rejection_reason} onChange={(event) => setForm({ ...form, highlighted_text_as_rejection_reason: event.target.value })} />
      </Field>
      <Field label="Plain-English reason">
        <textarea className={inputClass} value={form.rejection_reason} onChange={(event) => setForm({ ...form, rejection_reason: event.target.value })} />
      </Field>
      {error && <p className="rounded bg-white p-2 text-xs font-medium text-red-700">{error}</p>}
      <div className="flex flex-wrap gap-2">
        <Button type="submit" variant="danger" disabled={saving}>{saving ? "Saving..." : "Delete / Reject"}</Button>
        <Button type="button" variant="secondary" onClick={onCancel}>Cancel</Button>
      </div>
    </form>
  );
}

function VisibleBreakdownRoleForm({
  opportunity,
  onCancel,
  onSaved
}: {
  opportunity: Opportunity;
  onCancel: () => void;
  onSaved: () => Promise<void>;
}) {
  const updateMutation = useUpdateBreakdown();
  const [form, setForm] = useState<BreakdownRoleFormState>({ role_name: "", requirements: "", character_description: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!form.role_name.trim()) {
      setError("Role name is required.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const available_roles = [
        ...((opportunity.role_details?.available_roles as Array<Record<string, unknown>> | undefined) ?? []),
        {
          role_name: form.role_name.trim(),
          role_type: "Needs Review",
          character_description: form.character_description.trim() || form.requirements.trim() || null,
          role_requirement_text: form.requirements.trim() || form.character_description.trim() || form.role_name.trim(),
          confidence_score: 60
        }
      ];
      await updateMutation.mutateAsync({ id: opportunity.id, patch: {
        role_details: {
          ...(opportunity.role_details ?? {}),
          available_roles
        }
      } });
      await onSaved();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not add this role.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="grid gap-3 rounded-md border border-slate-200 bg-white p-3 text-sm" onSubmit={submit}>
      <div className="flex items-start justify-between gap-3">
        <h4 className="font-semibold text-ink">Manually Add Role</h4>
        <button type="button" className="text-xs font-semibold text-slate-600 hover:underline" onClick={onCancel}>Cancel</button>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        <Field label="Role Name"><input className={inputClass} value={form.role_name} onChange={(event) => setForm({ ...form, role_name: event.target.value })} /></Field>
        <Field label="Role Requirements"><textarea className={inputClass} value={form.requirements} onChange={(event) => setForm({ ...form, requirements: event.target.value })} /></Field>
        <div className="md:col-span-2">
          <Field label="Character Breakdown"><textarea className={inputClass} value={form.character_description} onChange={(event) => setForm({ ...form, character_description: event.target.value })} /></Field>
        </div>
      </div>
      {error && <p className="rounded bg-red-50 p-2 text-xs font-medium text-red-700">{error}</p>}
      <div className="flex flex-wrap gap-2">
        <Button type="submit" disabled={saving}>{saving ? "Saving..." : "Add Role"}</Button>
        <Button type="button" variant="secondary" onClick={onCancel}>Cancel</Button>
      </div>
    </form>
  );
}
