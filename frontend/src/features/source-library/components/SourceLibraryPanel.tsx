import { useMemo, useRef, useState, type FormEvent } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { Badge, Button, EmptyState, Field, Section, inputClass } from "../../../components/ui";
import { errorMessage } from "../../../services/api/errors";
import type { SourceResearchCategory, SourceResearchItem } from "../../../types/domain";
import {
  useActivateSourceResearchItem,
  useCreateSourceResearchItem,
  useDiscoverNewSources,
  useRejectSourceResearchItem,
  useSourceResearchItems,
  useUpdateSourceResearchItem
} from "../hooks/useSourceLibrary";
import { sourceClassificationOptions, sourceResearchCategories, sourceResearchStatuses, sourceUsefulnessOptions } from "../constants";
import type { DiscoveryMode, SourceEditFormState } from "../types";
import { formatSourceDateTime, isApprovedSource, isVisibleSource, sourceOpenUrl } from "../utils";

export function SourceLibraryPanel() {
  const sourceLibraryId = "source-library";
  const [formOpen, setFormOpen] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [hiddenSourceIds, setHiddenSourceIds] = useState<Set<string>>(new Set());
  const [editingSourceId, setEditingSourceId] = useState<string | null>(null);
  const editSourceFormRef = useRef<HTMLDivElement | null>(null);
  const [editForm, setEditForm] = useState<SourceEditFormState>({
    name: "",
    base_url: "",
    suggested_specific_url: "",
    approved_discovery_url: "",
    submitted_url: "",
    final_resolved_url: "",
    category: "Public casting site" as SourceResearchCategory,
    status: "Researching" as SourceResearchItem["status"],
    approved_by_user: false,
    source_classification: "Needs Review",
    source_usefulness: "Needs Review",
    organization_name: "",
    discovered_from_breakdown_id: "",
    discovery_reason: "",
    source_role_match_count: 0,
    notes: "",
    reliability_notes: "",
    verification_notes: "",
    rejection_reason: ""
  });
  const [form, setForm] = useState({
    name: "",
    base_url: "",
    suggested_specific_url: "",
    approved_discovery_url: "",
    category: "Public casting site" as SourceResearchCategory,
    notes: ""
  });
  const sourcesQuery = useSourceResearchItems();
  const createMutation = useCreateSourceResearchItem();
  const updateMutation = useUpdateSourceResearchItem();
  const activateMutation = useActivateSourceResearchItem();
  const rejectMutation = useRejectSourceResearchItem();
  const discoverMutation = useDiscoverNewSources();
  const sources = useMemo(() => sourcesQuery.data ?? [], [sourcesQuery.data]);
  const mutationError = createMutation.error ?? updateMutation.error ?? activateMutation.error ?? rejectMutation.error ?? discoverMutation.error;
  const mutationPending = createMutation.isPending || updateMutation.isPending || activateMutation.isPending || rejectMutation.isPending || discoverMutation.isPending;

  const visibleSources = useMemo(
    () => sources.filter((source) => isVisibleSource(source, hiddenSourceIds)),
    [hiddenSourceIds, sources]
  );

  const approvedSources = visibleSources.filter(isApprovedSource);
  const approvalSources = visibleSources.filter(
    (source) => ["Suggested", "Researching"].includes(source.status) && source.url_health_status === "Active" && !isApprovedSource(source)
  );

  async function createSource(event: FormEvent) {
    event.preventDefault();
    try {
      await createMutation.mutateAsync({
        ...form,
        source_url: form.base_url || null,
        base_url: form.base_url || null,
        suggested_specific_url: form.suggested_specific_url || null,
        approved_discovery_url: form.approved_discovery_url || null,
        notes: form.notes || null,
        status: "Researching",
        suggested_by_ai: false
      });
      setForm({ name: "", base_url: "", suggested_specific_url: "", approved_discovery_url: "", category: "Public casting site", notes: "" });
      setFormOpen(false);
      setMessage("Source saved.");
    } catch {
      // The mutation retains the standardized ApiError for presentation below.
    }
  }

  async function findNewSources(mode?: DiscoveryMode) {
    try {
      const found = await discoverMutation.mutateAsync(mode);
      const label = mode === "FilmTV" ? "Film/TV " : mode === "Theater" ? "theater " : "";
      setMessage(
        found.length
          ? `${found.length} new ${label}breakdown source${found.length === 1 ? "" : "s"} added for your approval.`
          : "No new source suggestions found. Rejected and duplicate sources were skipped."
      );
    } catch {
      // The mutation retains the standardized ApiError for presentation below.
    }
  }

  async function updateSource(source: SourceResearchItem, patch: Partial<SourceResearchItem>) {
    await updateMutation.mutateAsync({ sourceId: source.id, patch });
  }

  async function activateSource(source: SourceResearchItem) {
    try {
      const updated = await activateMutation.mutateAsync(source.id);
      setMessage(
        updated.status === "Active"
          ? `${source.name} is active. The system may check its approved URL for new breakdowns.`
          : `${source.name} was not activated. ${updated.health_reason || "Only active valid breakdown sources can be monitored."}`
      );
    } catch {
      // The mutation retains the standardized ApiError for presentation below.
    }
  }

  async function approveSource(source: SourceResearchItem) {
    try {
      const reviewed = await updateMutation.mutateAsync({ sourceId: source.id, patch: {
        approved_by_user: true,
        status: source.source_classification === "Valid Breakdown Source" ? source.status : "Approved",
        approved_discovery_url: source.approved_discovery_url || source.suggested_specific_url || source.base_url || source.source_url || null,
        last_researched_date: new Date().toISOString()
      } });
      if (reviewed.source_classification !== "Valid Breakdown Source") {
        setMessage(`${source.name} approved as ${reviewed.source_classification}. It will not be monitored for breakdown discovery.`);
        return;
      }
      const updated = await activateMutation.mutateAsync(source.id);
      setMessage(
        updated.status === "Active"
          ? `${source.name} approved and activated.`
          : `${source.name} is not a valid breakdown source. ${updated.health_reason || reviewed.health_reason || "It was kept for review instead of activated."}`
      );
    } catch {
      // The mutation retains the standardized ApiError for presentation below.
    }
  }

  async function addCorrectedUrl(source: SourceResearchItem) {
    startEditSource(source);
    setMessage("Add the corrected URL in the source form, then save.");
  }

  function searchSourceManually(source: SourceResearchItem) {
    const query = encodeURIComponent(`${source.organization_name || source.name} official casting auditions breakdowns`);
    window.open(`https://www.google.com/search?q=${query}`, "_blank", "noopener,noreferrer");
  }

  async function disableSource(source: SourceResearchItem) {
    try {
      await updateSource(source, { status: "Paused" });
      setMessage(`${source.name} paused. The system will not check it for new breakdowns.`);
    } catch {
      // The mutation retains the standardized ApiError for presentation below.
    }
  }

  async function rejectSource(source: SourceResearchItem) {
    setHiddenSourceIds((current) => new Set(current).add(source.id));
    try {
      await rejectMutation.mutateAsync({ sourceId: source.id, reason: source.rejection_reason || "Rejected by user." });
      setMessage("Source removed. It will no longer be suggested.");
    } catch (error) {
      setHiddenSourceIds((current) => {
        const next = new Set(current);
        next.delete(source.id);
        return next;
      });
      throw error;
    }
  }

  function startEditSource(source: SourceResearchItem) {
    setEditingSourceId(source.id);
    setEditForm({
      name: source.name,
      base_url: source.base_url || source.source_url || "",
      suggested_specific_url: source.suggested_specific_url || "",
      approved_discovery_url: source.approved_discovery_url || "",
      submitted_url: source.submitted_url || "",
      final_resolved_url: source.final_resolved_url || "",
      category: source.category,
      status: source.status,
      approved_by_user: source.approved_by_user,
      source_classification: source.source_classification || "Needs Review",
      source_usefulness: source.source_usefulness || "Needs Review",
      organization_name: source.organization_name || "",
      discovered_from_breakdown_id: source.discovered_from_breakdown_id || "",
      discovery_reason: source.discovery_reason || "",
      source_role_match_count: source.source_role_match_count || 0,
      notes: source.notes || "",
      reliability_notes: source.reliability_notes || "",
      verification_notes: source.verification_notes || "",
      rejection_reason: source.rejection_reason || ""
    });
    window.setTimeout(() => editSourceFormRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 0);
  }

  async function saveSourceEdit(event: FormEvent) {
    event.preventDefault();
    const source = visibleSources.find((item) => item.id === editingSourceId);
    if (!source) return;
    try {
      await updateSource(source, {
        name: editForm.name,
        source_url: editForm.base_url || null,
        base_url: editForm.base_url || null,
        suggested_specific_url: editForm.suggested_specific_url || null,
        approved_discovery_url: editForm.approved_discovery_url || null,
        submitted_url: editForm.submitted_url || editForm.base_url || null,
        final_resolved_url: editForm.final_resolved_url || null,
        category: editForm.category,
        status: editForm.status,
        approved_by_user: editForm.approved_by_user,
        source_classification: editForm.source_classification,
        suggested_classification: editForm.source_classification,
        source_usefulness: editForm.source_usefulness,
        organization_name: editForm.organization_name || null,
        notes: editForm.notes || null,
        reliability_notes: editForm.reliability_notes || null,
        verification_notes: editForm.verification_notes || null,
        rejection_reason: editForm.rejection_reason || null
      });
      setEditingSourceId(null);
      setMessage(`${editForm.name} updated.`);
    } catch {
      // Keep the edit draft open and show the standardized mutation error.
    }
  }

  const approvedSections = [
    {
      title: "Breakdown Sources",
      description: "Approved sources that can be activated for breakdown discovery.",
      sources: approvedSources.filter((source) => source.source_classification === "Valid Breakdown Source"),
      empty: "No approved breakdown sources yet."
    },
    {
      title: "Casting Offices",
      description: "Approved casting office research sources.",
      sources: approvedSources.filter((source) => source.source_classification === "Casting Office"),
      empty: "No approved casting office sources yet."
    },
    {
      title: "Production Companies",
      description: "Approved production company sources for watch lists and career context.",
      sources: approvedSources.filter((source) => source.source_classification === "Production Company"),
      empty: "No approved production company sources yet."
    },
    {
      title: "Regional Resources",
      description: "Approved film commissions, local boards, and regional resources.",
      sources: approvedSources.filter((source) => source.source_classification === "Regional Resource"),
      empty: "No approved regional resources yet."
    },
    {
      title: "Watch List Sources",
      description: "Approved sources that are useful for watch lists and relationship research.",
      sources: approvedSources.filter((source) => ["Watch List Source", "Relationship Source"].includes(source.source_classification)),
      empty: "No approved watch list sources yet."
    }
  ];

  const sourceQueues = [
    {
      title: "Breakdown Sources",
      description: "Sites that actually publish public acting breakdowns. These can be approved and activated for discovery.",
      sources: approvalSources.filter((source) => source.source_classification === "Valid Breakdown Source"),
      empty: "No active valid breakdown sources need approval."
    },
    {
      title: "Casting Offices",
      description: "Useful for relationship tracking, not daily breakdown scraping unless a public breakdown page is found.",
      sources: approvalSources.filter((source) => source.source_classification === "Casting Office"),
      empty: "No casting office research sources need review."
    },
    {
      title: "Production Companies",
      description: "Useful for watch lists and career intelligence, not automatic breakdown discovery.",
      sources: approvalSources.filter((source) => source.source_classification === "Production Company"),
      empty: "No production company sources need review."
    },
    {
      title: "Watch List Sources",
      description: "Useful for tracking target organizations, shows, and career context.",
      sources: approvalSources.filter((source) => ["Watch List Source", "Relationship Source"].includes(source.source_classification)),
      empty: "No watch-list sources need review."
    },
    {
      title: "Regional Resources",
      description: "Film commissions, regional production pages, and local resources that may help source research.",
      sources: approvalSources.filter((source) => source.source_classification === "Regional Resource"),
      empty: "No regional resources need review."
    },
    {
      title: "Needs Review",
      description: "Active websites that need a corrected category or URL before they can be useful.",
      sources: approvalSources.filter((source) => source.source_classification === "Needs Review" && source.source_usefulness !== "Not Useful"),
      empty: "No ambiguous active sources need review."
    }
  ];

  return (
    <Section
      title="Source Library"
      actions={(
        <>
          <Button variant="secondary" disabled={discoverMutation.isPending} onClick={() => void findNewSources()}>Find New Breakdown Sources</Button>
          <Button disabled={mutationPending} onClick={() => setFormOpen((current) => !current)}>{formOpen ? "Hide Form" : "Add Source"}</Button>
        </>
      )}
    >
      <p className="mb-3 text-sm text-slate-600">
        Manage casting source research here. The app only checks breakdown sources you approve and activate. Suggested, rejected, deleted, and paused sources are not checked.
      </p>
      {message && <p className="mb-3 rounded bg-green-50 p-2 text-sm text-green-800">{message}</p>}
      {sourcesQuery.isRefetching && !sourcesQuery.isLoading && <p className="mb-3 text-xs text-slate-500">Refreshing sources…</p>}
      {sourcesQuery.isLoading && <p className="mb-3 text-sm text-slate-600">Loading source library…</p>}
      {sourcesQuery.error && !sourcesQuery.data && (
        <p className="mb-3 rounded bg-red-50 p-2 text-sm text-red-800">{errorMessage(sourcesQuery.error, "Could not load Source Library.")}</p>
      )}
      {mutationPending && <p className="mb-3 text-xs text-slate-500">Saving source changes…</p>}
      {mutationError && (
        <p className="mb-3 rounded bg-red-50 p-2 text-sm text-red-800">{errorMessage(mutationError, "Could not update Source Library.")}</p>
      )}
      {formOpen && (
        <form className="mb-4 grid gap-3 rounded-md border border-slate-200 bg-slate-50 p-3 lg:grid-cols-4" onSubmit={createSource}>
          <Field label="Source Name"><input className={inputClass} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required /></Field>
          <Field label="Base URL"><input className={inputClass} type="url" value={form.base_url} onChange={(event) => setForm({ ...form, base_url: event.target.value })} placeholder="https://examplecastingoffice.com" /></Field>
          <Field label="Suggested Specific URL"><input className={inputClass} type="url" value={form.suggested_specific_url} onChange={(event) => setForm({ ...form, suggested_specific_url: event.target.value })} placeholder="https://examplecastingoffice.com/casting-calls" /></Field>
          <Field label="Approved Source URL"><input className={inputClass} type="url" value={form.approved_discovery_url} onChange={(event) => setForm({ ...form, approved_discovery_url: event.target.value })} placeholder="Optional until approved" /></Field>
          <Field label="Category">
            <select className={inputClass} value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value as SourceResearchCategory })}>
              {sourceResearchCategories.map((category) => <option key={category}>{category}</option>)}
            </select>
          </Field>
          <div className="lg:col-span-4"><Field label="Notes"><input className={inputClass} value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} /></Field></div>
          <div className="flex items-end"><Button type="submit" disabled={createMutation.isPending}>Save Source</Button></div>
        </form>
      )}

      {editingSourceId && (
        <div ref={editSourceFormRef}>
          <SourceEditForm
            form={editForm}
            onChange={setEditForm}
            onSubmit={saveSourceEdit}
            onCancel={() => setEditingSourceId(null)}
            onReject={() => {
              const source = visibleSources.find((item) => item.id === editingSourceId);
              if (source) void rejectSource({ ...source, rejection_reason: editForm.rejection_reason || source.rejection_reason });
              setEditingSourceId(null);
            }}
          />
        </div>
      )}

      {sourcesQuery.data && <div id={sourceLibraryId} className="grid gap-5">
        <div className="grid gap-3">
          {approvedSections.map((section) => (
            <SourceSection
              key={section.title}
              title={section.title}
              description={section.description}
              sources={section.sources}
              empty={section.empty}
              approved
              compactHeading
              onActivate={activateSource}
              onDisable={disableSource}
              onEdit={startEditSource}
              onDelete={rejectSource}
            />
          ))}
        </div>

        <div>
          <h3 className="mb-2 text-base font-semibold text-ink">Sources for Your Approval</h3>
          <div className="grid gap-4">
            {sourceQueues.map((queue) => (
              <SourceSection
                key={queue.title}
                title={queue.title}
                description={queue.description}
                sources={queue.sources}
                empty={queue.empty}
                onApprove={approveSource}
                onCorrectUrl={addCorrectedUrl}
                onSearchManually={searchSourceManually}
                onEdit={startEditSource}
                onReject={rejectSource}
              />
            ))}
          </div>
        </div>
      </div>}
    </Section>
  );
}

function SourceSection({
  title,
  description,
  sources,
  empty,
  approved = false,
  compactHeading = false,
  onActivate,
  onDisable,
  onDelete,
  onApprove,
  onCorrectUrl,
  onSearchManually,
  onEdit,
  onReject
}: {
  title: string;
  description: string;
  sources: SourceResearchItem[];
  empty: string;
  approved?: boolean;
  compactHeading?: boolean;
  onActivate?: (source: SourceResearchItem) => Promise<void>;
  onDisable?: (source: SourceResearchItem) => Promise<void>;
  onDelete?: (source: SourceResearchItem) => Promise<void>;
  onApprove?: (source: SourceResearchItem) => Promise<void>;
  onCorrectUrl?: (source: SourceResearchItem) => Promise<void>;
  onSearchManually?: (source: SourceResearchItem) => void;
  onEdit: (source: SourceResearchItem) => void;
  onReject?: (source: SourceResearchItem) => Promise<void>;
}) {
  const [expandedIds, setExpandedIds] = useState<Record<string, boolean>>({});
  return (
    <div>
      <h3 className={`${compactHeading ? "mb-1 text-sm" : "mb-1 text-base"} font-semibold text-ink`}>{title}</h3>
      <p className="mb-2 text-xs text-slate-600">{description}</p>
      <div className="grid gap-2">
        {sources.length === 0 ? (
          <EmptyState>{empty}</EmptyState>
        ) : sources.map((source) => (
          <SourceRow
            key={source.id}
            source={source}
            approved={approved}
            expanded={Boolean(expandedIds[source.id])}
            onToggleExpanded={() => setExpandedIds((current) => ({ ...current, [source.id]: !current[source.id] }))}
            onActivate={onActivate ? () => void onActivate(source) : undefined}
            onDisable={onDisable ? () => void onDisable(source) : undefined}
            onDelete={onDelete ? () => void onDelete(source) : undefined}
            onApprove={onApprove ? () => void onApprove(source) : undefined}
            onCorrectUrl={onCorrectUrl ? () => void onCorrectUrl(source) : undefined}
            onSearchManually={onSearchManually ? () => onSearchManually(source) : undefined}
            onEdit={() => onEdit(source)}
            onReject={onReject ? () => void onReject(source) : undefined}
          />
        ))}
      </div>
    </div>
  );
}

export function SourceEditForm({
  form,
  onChange,
  onSubmit,
  onCancel,
  onReject
}: {
  form: SourceEditFormState;
  onChange: (form: SourceEditFormState) => void;
  onSubmit: (event: FormEvent) => void;
  onCancel: () => void;
  onReject: () => void;
}) {
  return (
    <form className="mb-4 grid gap-3 rounded-md border border-blue-200 bg-blue-50 p-3 lg:grid-cols-4" onSubmit={onSubmit}>
      <div className="lg:col-span-4">
        <h3 className="font-semibold text-ink">Edit Source</h3>
        <p className="mt-1 text-xs text-slate-600">
          Update the exact URL, classification, approval status, and notes. Only active approved valid breakdown sources are used for breakdown discovery.
        </p>
      </div>
      <Field label="Source Name"><input name="edit_source_name" className={inputClass} value={form.name} onChange={(event) => onChange({ ...form, name: event.target.value })} required /></Field>
      <Field label="Source Category">
        <select name="edit_source_category" className={inputClass} value={form.category} onChange={(event) => onChange({ ...form, category: event.target.value as SourceResearchCategory })}>
          {sourceResearchCategories.map((category) => <option key={category}>{category}</option>)}
        </select>
      </Field>
      <Field label="Source Type">
        <select name="edit_source_classification" className={inputClass} value={form.source_classification} onChange={(event) => onChange({ ...form, source_classification: event.target.value as SourceResearchItem["source_classification"] })}>
          {sourceClassificationOptions.map((classification) => <option key={classification}>{classification}</option>)}
        </select>
      </Field>
      <Field label="Usefulness">
        <select name="edit_source_usefulness" className={inputClass} value={form.source_usefulness} onChange={(event) => onChange({ ...form, source_usefulness: event.target.value as SourceResearchItem["source_usefulness"] })}>
          {sourceUsefulnessOptions.map((usefulness) => <option key={usefulness}>{usefulness}</option>)}
        </select>
      </Field>
      <Field label="Base URL"><input name="edit_source_base_url" className={inputClass} type="url" value={form.base_url} onChange={(event) => onChange({ ...form, base_url: event.target.value })} /></Field>
      <Field label="Approved Discovery URL"><input name="edit_source_approved_url" className={inputClass} type="url" value={form.approved_discovery_url} onChange={(event) => onChange({ ...form, approved_discovery_url: event.target.value })} /></Field>
      <Field label="Submitted URL"><input name="edit_source_submitted_url" className={inputClass} type="url" value={form.submitted_url} onChange={(event) => onChange({ ...form, submitted_url: event.target.value })} /></Field>
      <Field label="Final Resolved URL"><input name="edit_source_final_url" className={inputClass} type="url" value={form.final_resolved_url} onChange={(event) => onChange({ ...form, final_resolved_url: event.target.value })} /></Field>
      <Field label="Suggested Specific URL"><input name="edit_source_suggested_url" className={inputClass} type="url" value={form.suggested_specific_url} onChange={(event) => onChange({ ...form, suggested_specific_url: event.target.value })} /></Field>
      <Field label="Organization Name"><input name="edit_source_organization" className={inputClass} value={form.organization_name} onChange={(event) => onChange({ ...form, organization_name: event.target.value })} /></Field>
      <Field label="Status">
        <select name="edit_source_status" className={inputClass} value={form.status} onChange={(event) => onChange({ ...form, status: event.target.value as SourceResearchItem["status"] })}>
          {sourceResearchStatuses.map((status) => <option key={status}>{status}</option>)}
        </select>
      </Field>
      <div className="rounded-md border border-blue-100 bg-white p-2 text-xs text-slate-700 lg:col-span-2">
        <p className="font-semibold text-ink">Matched Breakdown Source</p>
        <p className="mt-1">{form.discovery_reason || "No matched breakdown recorded yet."}</p>
        <p className="mt-1 text-slate-500">Matched role count: {form.source_role_match_count}</p>
      </div>
      <label className="flex items-center gap-2 text-xs font-semibold text-slate-700">
        <input
          name="edit_source_approved_by_user"
          type="checkbox"
          checked={form.approved_by_user}
          onChange={(event) => onChange({ ...form, approved_by_user: event.target.checked })}
        />
        Approved by user
      </label>
      <div className="lg:col-span-2"><Field label="Notes"><textarea name="edit_source_notes" className={inputClass} value={form.notes} onChange={(event) => onChange({ ...form, notes: event.target.value })} /></Field></div>
      <div className="lg:col-span-2"><Field label="Reliability Notes"><textarea name="edit_source_reliability_notes" className={inputClass} value={form.reliability_notes} onChange={(event) => onChange({ ...form, reliability_notes: event.target.value })} /></Field></div>
      <div className="lg:col-span-2"><Field label="Verification Notes"><textarea name="edit_source_verification_notes" className={inputClass} value={form.verification_notes} onChange={(event) => onChange({ ...form, verification_notes: event.target.value })} /></Field></div>
      <div className="lg:col-span-2"><Field label="Reject / Delete Reason"><textarea name="edit_source_rejection_reason" className={inputClass} value={form.rejection_reason} onChange={(event) => onChange({ ...form, rejection_reason: event.target.value })} /></Field></div>
      <div className="flex flex-wrap gap-2 lg:col-span-4">
        <Button type="submit">Save Source</Button>
        <Button type="button" variant="secondary" onClick={onCancel}>Cancel</Button>
        <Button type="button" variant="secondary" onClick={onReject}>Reject / Delete</Button>
      </div>
    </form>
  );
}

function SourceRow({
  source,
  approved = false,
  expanded = false,
  onToggleExpanded,
  onActivate,
  onDisable,
  onEdit,
  onDelete,
  onCorrectUrl,
  onSearchManually,
  onApprove,
  onReject
}: {
  source: SourceResearchItem;
  approved?: boolean;
  expanded?: boolean;
  onToggleExpanded?: () => void;
  onActivate?: () => void;
  onDisable?: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
  onCorrectUrl?: () => void;
  onSearchManually?: () => void;
  onApprove?: () => void;
  onReject?: () => void;
}) {
  const openUrl = sourceOpenUrl(source);
  const canApprove = source.url_health_status === "Active" && source.source_usefulness === "Useful Breakdown Source" && source.source_classification === "Valid Breakdown Source";
  const canApproveResearch = source.url_health_status === "Active" && source.source_usefulness !== "Not Useful" && !["Rejected", "Not Useful"].includes(source.source_classification);
  const recognizedButBadUrl = source.organization_legitimacy === "Recognized Organization" && !canApprove;
  const statusIsObvious = approved && ["Approved", "Active"].includes(source.status);
  const reason = source.notes || source.verification_notes || source.health_reason || source.reliability_notes || source.discovery_reason || "No notes yet.";
  const subheader = source.page_title && source.page_title !== source.name ? source.page_title : source.organization_name && source.organization_name !== source.name ? source.organization_name : "";
  return (
    <article className="rounded-md border border-slate-200 bg-white text-xs shadow-sm">
      <div className="flex flex-col gap-2 p-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <button type="button" className="rounded p-1 text-slate-500 hover:bg-slate-100" aria-label={expanded ? "Collapse source" : "Expand source"} onClick={onToggleExpanded}>
              {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            </button>
            <h4 className="font-semibold text-ink">
              {openUrl ? (
                <a className="text-accent hover:underline" href={openUrl} target="_blank" rel="noreferrer">
                  {source.name}
                </a>
              ) : (
                source.name
              )}
            </h4>
            <Badge>{source.category}</Badge>
            {!statusIsObvious && <Badge>{source.status === "Paused" ? "Paused / Disabled" : source.status}</Badge>}
          </div>
          {subheader && <p className="mt-1 text-xs font-medium text-slate-700">{subheader}</p>}
        </div>
        <div className="flex shrink-0 flex-wrap gap-2 text-xs font-semibold">
          {approved && canApprove && source.status === "Active" && <button type="button" className="text-amber-700 hover:underline" onClick={onDisable}>Disable</button>}
          {approved && canApprove && source.status !== "Active" && <button type="button" className="text-accent hover:underline" onClick={onActivate}>Activate</button>}
          {onEdit && <button type="button" className="text-slate-700 hover:underline" onClick={onEdit}>Edit</button>}
          {!approved && onCorrectUrl && <button type="button" className="text-slate-700 hover:underline" onClick={onCorrectUrl}>Add corrected URL</button>}
          {!approved && onSearchManually && <button type="button" className="text-slate-700 hover:underline" onClick={onSearchManually}>Search manually</button>}
          {approved && onDelete && <button type="button" className="text-red-700 hover:underline" onClick={onDelete}>Delete</button>}
          {!approved && canApproveResearch && onApprove && <button type="button" className="text-accent hover:underline" onClick={onApprove}>Approve</button>}
          {!approved && onReject && <button type="button" className="text-red-700 hover:underline" onClick={onReject}>Reject</button>}
        </div>
      </div>
      {expanded && (
        <div className="border-t border-slate-100 p-3">
          <p className="text-slate-600">{reason}</p>
          {recognizedButBadUrl && (
            <p className="mt-2 rounded border border-amber-200 bg-amber-50 p-2 font-medium text-amber-900">
              Recognized organization, but this URL is not a usable source.
            </p>
          )}
          {!canApprove && !approved && (
            <p className="mt-2 rounded bg-slate-50 p-2 text-slate-600">
              This is not classified as a valid breakdown source. It may be useful as a relationship, watch list, production, or regional research source, but it will not be monitored for breakdown discovery.
            </p>
          )}
          <div className="mt-3 grid gap-1 text-slate-600 md:grid-cols-2">
            {source.organization_name && <p><span className="font-semibold text-slate-800">Organization:</span> {source.organization_name}</p>}
            <p><span className="font-semibold text-slate-800">Source type:</span> {source.source_classification}</p>
            <p><span className="font-semibold text-slate-800">Usefulness:</span> {source.source_usefulness}</p>
            {source.last_checked_date && <p><span className="font-semibold text-slate-800">Last checked:</span> {formatSourceDateTime(source.last_checked_date)}</p>}
            {source.discovery_reason && <p className="md:col-span-2"><span className="font-semibold text-slate-800">Matched breakdown:</span> {source.discovery_reason}</p>}
          </div>
          {onEdit && <button type="button" className="mt-3 text-xs font-semibold text-accent hover:underline" onClick={onEdit}>Edit full source details</button>}
        </div>
      )}
    </article>
  );
}
