import { useMemo, useState, type FormEvent } from "react";
import { Sparkles } from "lucide-react";
import { Badge, Button, Field, Section, inputClass } from "../../../components/ui";
import { SourceEditForm, SourceLibraryPanel, type SourceEditFormState, useActivateSourceResearchItem, useDiscoverNewSources, useRejectSourceResearchItem, useUpdateSourceResearchItem } from "../../source-library";
import { useDiscoveryReport } from "../hooks/useBreakdownQueries";
import type { AgentRecommendation, DiscoveryCoverage, DiscoveryMode, DiscoveryPlugin, DiscoveryReport, DiscoverySearchMode, Opportunity, SourceResearchItem, SubmissionAutomationQueueItem, SystemCapabilities } from "../types";
import { discoverySearchModes } from "../constants";
import { useBreakdownDiscovery } from "../hooks/useBreakdownDiscovery";
import { TextAction, humanizeKey } from "./BreakdownDetails";
import { SubmissionQueuePanel } from "./SubmissionQueuePanel";
import { HiddenOpportunityReview } from "./HiddenOpportunityReview";

export const BreakdownSources = SourceLibraryPanel;

function DiscoveryReportPanel({ report }: { report: DiscoveryReport }) {
  const reasons = Object.entries(report.top_rejection_reasons ?? {}).sort((a, b) => b[1] - a[1]);
  return (
    <div className="mt-2 grid gap-3 rounded-md border border-slate-200 bg-white p-3 text-xs text-slate-700">
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        <ReportMetric label="Parallel queries run" value={report.parallel_queries_run} />
        <ReportMetric label="Candidate pages returned" value={report.candidate_pages_returned} />
        <ReportMetric label="Candidate pages fetched" value={report.candidate_pages_fetched} />
        <ReportMetric label="Candidate pages parsed" value={report.candidate_pages_parsed} />
        <ReportMetric label="Accepted" value={report.accepted} />
        <ReportMetric label="Rejected" value={report.rejected} />
        <ReportMetric label="Approved source hits" value={report.approved_source_hits} />
        <ReportMetric label="Public web hits" value={report.public_web_hits} />
      </div>
      <p>
        <span className="font-semibold text-slate-900">Average parser confidence:</span>{" "}
        {report.average_parser_confidence == null ? "Not enough parsed candidates yet" : `${report.average_parser_confidence}%`}
      </p>
      <div>
        <p className="font-semibold text-slate-900">Top rejection reasons</p>
        {reasons.length === 0 ? (
          <p className="mt-1 text-slate-500">No rejected candidates in this run.</p>
        ) : (
          <div className="mt-1 flex flex-wrap gap-2">
            {reasons.slice(0, 8).map(([reason, count]) => <Badge key={reason}>{reason}: {count}</Badge>)}
          </div>
        )}
      </div>
      <div>
        <p className="font-semibold text-slate-900">Candidate pages</p>
        <div className="mt-2 grid gap-2">
          {report.candidates.length === 0 ? (
            <p className="text-slate-500">No candidate pages were returned for this run.</p>
          ) : report.candidates.slice(0, 30).map((candidate, index) => (
            <div key={`${candidate.url || candidate.page_title || "candidate"}-${index}`} className="rounded border border-slate-200 bg-slate-50 p-2">
              <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0">
                  <p className="font-semibold text-slate-900">
                    {candidate.url ? (
                      <a className="break-words text-accent hover:underline" href={candidate.url} target="_blank" rel="noreferrer">
                        {candidate.page_title || candidate.url}
                      </a>
                    ) : candidate.page_title || "Candidate page"}
                  </p>
                  <p className="text-slate-500">{candidate.source || "Unknown source"}</p>
                </div>
                <Badge>{candidate.decision || "Unknown"}</Badge>
              </div>
              <p className="mt-1">
                <span className="font-semibold">Reason:</span> {candidate.rejection_reason || "Accepted"}
              </p>
              {candidate.parser_confidence != null && (
                <p className="mt-1 text-slate-500">Parser confidence: {candidate.parser_confidence}%</p>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ReportMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded bg-slate-50 p-2">
      <p className="text-lg font-bold text-ink">{value}</p>
      <p className="text-slate-500">{label}</p>
    </div>
  );
}

export function AutomationDashboard({
  plugins,
  hiddenOpportunities,
  recommendations,
  queueItems,
  opportunities,
  sourceResearchItems,
  capabilities
}: {
  plugins: DiscoveryPlugin[];
  hiddenOpportunities: Opportunity[];
  recommendations: AgentRecommendation[];
  queueItems: SubmissionAutomationQueueItem[];
  opportunities: Opportunity[];
  sourceResearchItems: SourceResearchItem[];
  capabilities?: SystemCapabilities | null;
}) {
  const [discoveryStatus, setDiscoveryStatus] = useState<string | null>(null);
  const [discoveryCoverage, setDiscoveryCoverage] = useState<DiscoveryCoverage | null>(null);
  const [discoveryReport, setDiscoveryReport] = useState<DiscoveryReport | null>(null);
  const savedDiscoveryReport = useDiscoveryReport();
  const visibleDiscoveryReport = discoveryReport ?? savedDiscoveryReport.data ?? null;
  const [discoveryReportOpen, setDiscoveryReportOpen] = useState(false);
  const [publicWebScopeNote, setPublicWebScopeNote] = useState<string | null>(null);
  const [lastDiscoveryResult, setLastDiscoveryResult] = useState<{ mode: DiscoveryMode; total_visible: number } | null>(null);
  const [sourceExpansionMessage, setSourceExpansionMessage] = useState<string | null>(null);
  const discovery = useBreakdownDiscovery();
  const discoverSources = useDiscoverNewSources(); const activateSource = useActivateSourceResearchItem();
  const updateSource = useUpdateSourceResearchItem(); const rejectSource = useRejectSourceResearchItem();
  const [editingSkippedSourceId, setEditingSkippedSourceId] = useState<string | null>(null);
  const [skippedSourceMessage, setSkippedSourceMessage] = useState<string | null>(null);
  const [skippedSourceEditForm, setSkippedSourceEditForm] = useState<SourceEditFormState | null>(null);
  const [searchModes, setSearchModes] = useState<DiscoverySearchMode[]>(["Match My Profile", "Match My Archetypes"]);
  const [specificArchetype, setSpecificArchetype] = useState("");
  const sourceDiscoveryConfigured = capabilities?.flags.source_discovery_configured ?? false;
  const sourceById = useMemo(
    () => Object.fromEntries(sourceResearchItems.map((item) => [item.id, item])),
    [sourceResearchItems]
  );
  async function runDiscovery(mode: DiscoveryMode) {
    if (!sourceDiscoveryConfigured) {
      setDiscoveryStatus("Not Configured: approve and activate at least one breakdown source, configure Parallel public web search, or add a breakdown manually.");
      return;
    }
    discovery.clearError();
    setDiscoveryStatus(null);
    setDiscoveryCoverage(null);
    setDiscoveryReport(null);
    setDiscoveryReportOpen(false);
    setPublicWebScopeNote(null);
    setLastDiscoveryResult(null);
    setSourceExpansionMessage(null);
    const selectedModes = searchModes.length > 0 ? searchModes : ["Match My Profile", "Match My Archetypes"] as DiscoverySearchMode[];
    const result = await discovery.run({ mode, searchModes: selectedModes, specificArchetype });
    if (result) {
      const label = mode === "FilmTV" ? "Film/TV" : mode;
      const intentLabel = (result.search_modes ?? selectedModes).join(" + ");
      const reasons = Object.entries(result.rejection_reasons_summary ?? {})
        .filter(([, count]) => count > 0)
        .map(([reason, count]) => `${humanizeKey(reason)}: ${count}`)
        .join("; ");
      const coverage = result.coverage;
      setDiscoveryCoverage(coverage ?? null);
      setDiscoveryReport(result.discovery_report ?? null);
      setLastDiscoveryResult({ mode, total_visible: result.total_visible });
      const publicWeb = result.public_web_search;
      const publicWebText = publicWeb?.run
        ? ` Parallel public web search run: yes. Candidate pages found ${publicWeb.candidate_pages_found}, candidates rejected ${publicWeb.candidates_rejected}, eligible breakdowns added ${publicWeb.eligible_breakdowns_added}, sources suggested for approval ${publicWeb.sources_suggested_for_approval}.`
        : ` Parallel public web search run: no. ${publicWeb?.reason || "Public web search is not configured. Only approved active sources were searched."}`;
      setPublicWebScopeNote(
        publicWeb?.run
          ? "Public web search ran through Parallel. Results depend on Parallel's indexed results and your query settings."
          : (publicWeb?.reason || "Public web search is not configured. Only approved sources were searched.")
      );
      setDiscoveryStatus(
        `Checked ${coverage?.approved_active_sources_checked ?? result.sources_run} approved active ${label} breakdown source(s) using ${intentLabel}. Coverage is ${coverage?.coverage_level ?? "Unknown"}.${publicWebText} Found ${result.total_found}, visible eligible ${result.total_visible}${result.target_visible ? `/${result.target_visible}` : ""}, added ${result.opportunities_created}, travel exceptions ${result.total_travel_exceptions ?? 0}, needs review ${result.total_hidden}, discarded ${result.total_rejected}.${reasons ? ` Reasons: ${reasons}.` : ""}`
      );
    }
  }
  async function findNewBreakdownSources(mode?: DiscoveryMode) {
    setSourceExpansionMessage(null);
    const found = await discoverSources.mutateAsync(mode);
    const label = mode === "FilmTV" ? "Film/TV " : mode === "Theater" ? "theater " : "";
    setSourceExpansionMessage(
      found.length
        ? `${found.length} new ${label}source${found.length === 1 ? "" : "s"} added for approval. Approve useful sources before running discovery again.`
        : `No new ${label || ""}source suggestions were added. Deleted, duplicate, and invalid sources were skipped.`
    );
  }
  async function activateSkippedSource(source: SourceResearchItem) {
    const updated = await activateSource.mutateAsync(source.id);
    setSkippedSourceMessage(
      updated.status === "Active"
        ? `${source.name} activated.`
        : `${source.name} was not activated. ${updated.health_reason || "Only valid breakdown sources can be monitored."}`
    );
  }
  async function approveSkippedSource(source: SourceResearchItem) {
    const reviewed = await updateSource.mutateAsync({ sourceId: source.id, patch: {
      approved_by_user: true,
      status: source.source_classification === "Valid Breakdown Source" ? source.status : "Approved",
      approved_discovery_url: source.approved_discovery_url || source.suggested_specific_url || source.base_url || source.source_url || null,
      last_researched_date: new Date().toISOString()
    } });
    if (reviewed.source_classification === "Valid Breakdown Source") {
      await activateSkippedSource(reviewed);
    } else {
      setSkippedSourceMessage(`${source.name} approved as ${reviewed.source_classification}. It will not be monitored for breakdown discovery.`);
    }
  }
  async function rejectSkippedSource(source: SourceResearchItem) {
    await rejectSource.mutateAsync({ sourceId: source.id, reason: source.rejection_reason || "Rejected from skipped source list." });
    setSkippedSourceMessage("Source removed. It will no longer be suggested.");
  }
  function startSkippedSourceEdit(source: SourceResearchItem) {
    setEditingSkippedSourceId(source.id);
    setSkippedSourceEditForm({
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
  }
  async function saveSkippedSourceEdit(event: FormEvent) {
    event.preventDefault();
    if (!editingSkippedSourceId || !skippedSourceEditForm) return;
    await updateSource.mutateAsync({ sourceId: editingSkippedSourceId, patch: {
      name: skippedSourceEditForm.name,
      source_url: skippedSourceEditForm.base_url || null,
      base_url: skippedSourceEditForm.base_url || null,
      suggested_specific_url: skippedSourceEditForm.suggested_specific_url || null,
      approved_discovery_url: skippedSourceEditForm.approved_discovery_url || null,
      submitted_url: skippedSourceEditForm.submitted_url || skippedSourceEditForm.base_url || null,
      final_resolved_url: skippedSourceEditForm.final_resolved_url || null,
      category: skippedSourceEditForm.category,
      status: skippedSourceEditForm.status,
      approved_by_user: skippedSourceEditForm.approved_by_user,
      source_classification: skippedSourceEditForm.source_classification,
      suggested_classification: skippedSourceEditForm.source_classification,
      source_usefulness: skippedSourceEditForm.source_usefulness,
      organization_name: skippedSourceEditForm.organization_name || null,
      notes: skippedSourceEditForm.notes || null,
      reliability_notes: skippedSourceEditForm.reliability_notes || null,
      verification_notes: skippedSourceEditForm.verification_notes || null,
      rejection_reason: skippedSourceEditForm.rejection_reason || null
    } });
    setSkippedSourceMessage(`${skippedSourceEditForm.name} updated.`);
    setEditingSkippedSourceId(null);
    setSkippedSourceEditForm(null);
  }
  function toggleSearchMode(mode: DiscoverySearchMode) {
    setSearchModes((current) => {
      const next = current.includes(mode) ? current.filter((item) => item !== mode) : [...current, mode];
      return next.length > 0 ? next : ["Match My Profile", "Match My Archetypes"];
    });
  }
  return (
    <Section title="Find & Submit Breakdowns" actions={<Sparkles className="h-5 w-5 text-slate-500" />}>
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-md border border-slate-200 p-3">
          <h3 className="font-semibold">Find Breakdowns</h3>
          <p className="mt-1 text-sm text-slate-600">Runs only against active approved breakdown sources. Protected casting-platform pages are not scraped.</p>
          {!sourceDiscoveryConfigured && (
            <p className="mt-2 rounded-md border border-amber-200 bg-amber-50 p-2 text-xs font-medium text-amber-900">
              Not Configured: approve and activate a breakdown source before public discovery can run. Manual breakdown entry still works.
            </p>
          )}
          <div className="mt-3 rounded-md bg-slate-50 p-3">
            <p className="text-sm font-semibold text-ink">Search Intent</p>
            <p className="mt-1 text-xs text-slate-600">
              Default searches prioritize your profile and current archetypes. Stretch roles are searched only when you select that mode.
            </p>
            <div className="mt-2 grid gap-2">
              {discoverySearchModes.map((mode) => (
                <label key={mode} className="flex items-center gap-2 text-sm text-slate-700">
                  <input
                    name={`discovery_search_mode_${mode.replace(/\W+/g, "_").toLowerCase()}`}
                    type="checkbox"
                    checked={searchModes.includes(mode)}
                    onChange={() => toggleSearchMode(mode)}
                  />
                  {mode}
                </label>
              ))}
            </div>
            {searchModes.includes("Search Specific Archetype") && (
              <Field label="Specific Archetype">
                <input
                  className={inputClass}
                  value={specificArchetype}
                  onChange={(event) => setSpecificArchetype(event.target.value)}
                  placeholder="Attorney, Detective, Executive..."
                />
              </Field>
            )}
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <Button disabled={discovery.discovering || !sourceDiscoveryConfigured} onClick={() => void runDiscovery("Theater")}>
              {discovery.discovering ? "Finding..." : "Find Theater Breakdowns"}
            </Button>
            <Button disabled={discovery.discovering || !sourceDiscoveryConfigured} variant="secondary" onClick={() => void runDiscovery("FilmTV")}>
              Find Film/TV Breakdowns
            </Button>
            <Button disabled={discovery.discovering || !sourceDiscoveryConfigured} variant="secondary" onClick={() => void runDiscovery("All")}>
              Find All
            </Button>
          </div>
          {(discoveryStatus || discovery.error) && (
            <div className="mt-2 rounded bg-slate-50 p-2 text-sm text-slate-700">
              <p>{discoveryStatus || discovery.error}</p>
              {discoveryCoverage && (
                <div className="mt-2 grid gap-1 text-xs text-slate-600">
                  <p>
                    <span className="font-medium text-slate-800">Approved active sources checked:</span>{" "}
                    {discoveryCoverage.approved_active_sources_checked}
                  </p>
                  <p>
                    <span className="font-medium text-slate-800">Available coverage:</span>{" "}
                    {discoveryCoverage.approved_mode_sources_available} {discoveryCoverage.approved_mode_sources_label}; {discoveryCoverage.coverage_level}
                  </p>
                  <p>
                    <span className="font-medium text-slate-800">Sources awaiting approval:</span>{" "}
                    {discoveryCoverage.suggested_sources_awaiting_approval}
                  </p>
                  <p>{publicWebScopeNote || discoveryCoverage.scope_note}</p>
                  {visibleDiscoveryReport && (
                    <div className="mt-2">
                      <TextAction onClick={() => setDiscoveryReportOpen((current) => !current)}>
                        {discoveryReportOpen ? "Hide Discovery Report" : "View Discovery Report"}
                      </TextAction>
                      {discoveryReportOpen && <DiscoveryReportPanel report={visibleDiscoveryReport} />}
                    </div>
                  )}
                  {skippedSourceMessage && <p className="rounded bg-green-50 p-2 text-green-800">{skippedSourceMessage}</p>}
                  {editingSkippedSourceId && skippedSourceEditForm && (
                    <SourceEditForm
                      form={skippedSourceEditForm}
                      onChange={setSkippedSourceEditForm}
                      onSubmit={saveSkippedSourceEdit}
                      onCancel={() => {
                        setEditingSkippedSourceId(null);
                        setSkippedSourceEditForm(null);
                      }}
                      onReject={() => {
                        const source = editingSkippedSourceId ? sourceById[editingSkippedSourceId] : null;
                        if (source) void rejectSkippedSource({ ...source, rejection_reason: skippedSourceEditForm.rejection_reason || source.rejection_reason });
                        setEditingSkippedSourceId(null);
                        setSkippedSourceEditForm(null);
                      }}
                    />
                  )}
                  {discoveryCoverage.skipped_source_reasons.length > 0 && (
                    <details>
                      <summary className="cursor-pointer font-medium text-slate-800">Skipped sources</summary>
                      <ul className="mt-2 grid gap-2">
                        {discoveryCoverage.skipped_source_reasons.slice(0, 8).map((item) => {
                          const source = item.source_research_item_id ? sourceById[item.source_research_item_id] : null;
                          const isValid = source?.source_classification === "Valid Breakdown Source" && source.url_health_status === "Active" && source.source_usefulness === "Useful Breakdown Source";
                          return (
                            <li key={`${item.provider_key}-${item.reason}`} className="rounded border border-slate-200 bg-white p-2">
                              <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
                                <div>
                                  <p className="font-semibold text-slate-900">{item.source}</p>
                                  <p className="text-slate-600">{item.reason}</p>
                                  <p className="text-slate-500">Status: {source?.status || item.source_status || item.status || "Unknown"}</p>
                                </div>
                                {source ? (
                                  <div className="flex flex-wrap gap-2 font-semibold">
                                    {source.status !== "Active" && isValid && <TextAction onClick={() => void activateSkippedSource(source)}>Activate</TextAction>}
                                    {!source.approved_by_user && isValid && <TextAction onClick={() => void approveSkippedSource(source)}>Approve</TextAction>}
                                    <TextAction tone="muted" onClick={() => startSkippedSourceEdit(source)}>Edit</TextAction>
                                    {!isValid && <TextAction tone="danger" onClick={() => void rejectSkippedSource(source)}>Delete / Reject</TextAction>}
                                  </div>
                                ) : (
                                  <a className="text-accent hover:underline" href="#source-library">Manage in Source Library</a>
                                )}
                              </div>
                            </li>
                          );
                        })}
                      </ul>
                    </details>
                  )}
                  {lastDiscoveryResult?.mode === "FilmTV" && lastDiscoveryResult.total_visible === 0 && discoveryCoverage.approved_mode_sources_available < 6 && (
                    <div className="mt-2 rounded border border-amber-200 bg-amber-50 p-2 text-amber-950">
                      <p>
                        No eligible Film/TV breakdowns found from your currently approved sources? Your coverage is limited.
                        Find more sources for approval to expand future searches.
                      </p>
                      <TextAction onClick={() => void findNewBreakdownSources("FilmTV")}>Find New Film/TV Sources</TextAction>
                    </div>
                  )}
                </div>
              )}
              {sourceExpansionMessage && <p className="mt-2 rounded bg-green-50 p-2 text-xs text-green-800">{sourceExpansionMessage}</p>}
            </div>
          )}
          <p className="mt-3 text-xs text-slate-500">
            <a className="font-semibold text-accent hover:underline" href="#source-library">Manage in Source Library</a>
          </p>
        </div>

        <HiddenOpportunityReview hiddenOpportunities={hiddenOpportunities} />

        <SubmissionQueuePanel
          recommendations={recommendations}
          queueItems={queueItems}
          opportunities={opportunities}
          hiddenOpportunities={hiddenOpportunities}
        />
      </div>
    </Section>
  );
}
