import { useId, useMemo, useRef, useState, type FormEvent, type ReactNode } from "react";
import { ChevronDown, ChevronRight, Gauge, Sparkles, Star } from "lucide-react";
import { ActionCard, Badge, Button, ConfirmAction, DetailDisclosure, EmptyState, Field, Section, inputClass } from "../../../components/ui";
import { useRecommendationFeedback } from "../hooks/useBreakdownQueries";
import { joinList, splitList } from "../../../utils/tags";
import { errorMessage } from "../../../services/api/errors";
import type {
  ActorProfile,
  AgentRecommendation,
  AuditionReadiness,
  Asset,
  AssetType,
  DiscoveryPlugin,
  MaterialOpportunityMatch,
  Opportunity,
  RecommendationFeedback,
  Representation,
  SourceResearchItem,
  SubmissionAutomationQueueItem,
  SystemCapabilities,
  BreakdownFilter,
  DiscoveryCoverage,
  DiscoveryMode,
  DiscoveryReport,
  DiscoverySearchMode
} from "../types";
import { discoverySearchModes, sourceTypes } from "../constants";

const recommendationFeedbackTypes: RecommendationFeedback["feedback_type"][] = [
  "This Fits Me",
  "Not My Type",
  "Interesting Stretch",
  "Save For Later"
];
const fitReasonOptions = [
  "Archetype",
  "Personality",
  "Comedy",
  "Drama",
  "Mom",
  "Authority",
  "Detective",
  "Executive",
  "Age Stretch",
  "Emotional Range",
  "Personal Connection",
  "Other"
];

export function formatDateTime(value: unknown) {
  if (!value) return "Not scheduled";
  const date = new Date(String(value));
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
}


export function OpportunityLink({
  opportunity,
  className = "font-semibold"
}: {
  opportunity: Opportunity;
  className?: string;
}) {
  const label = `${opportunity.role} · ${opportunity.project}`;
  const sourceUrl = externalBreakdownUrl(opportunity);
  if (!sourceUrl) return <span className={`${className} break-words`}>{label}</span>;
  return (
    <a className={`${className} break-words text-accent hover:underline`} href={sourceUrl} target="_blank" rel="noreferrer">
      {label}
    </a>
  );
}

export function externalBreakdownUrl(opportunity: Opportunity): string | null {
  const metadataUrl = opportunity.source_metadata?.source_url ?? opportunity.source_metadata?.url ?? opportunity.source_metadata?.original_post_url;
  const sourceUrl = opportunity.original_post_url || (typeof metadataUrl === "string" ? metadataUrl : "");
  return sourceUrl.trim() || null;
}

export function TrustVerificationPanel({ opportunity }: { opportunity: Opportunity }) {
  const verification = opportunity.source_metadata?.trust_verification;
  if (!verification || typeof verification !== "object" || Array.isArray(verification)) return null;
  const record = verification as Record<string, unknown>;
  const reasons = Array.isArray(record.plain_language_reasons)
    ? record.plain_language_reasons.map(String).filter(Boolean)
    : [];
  const status = String(record.status ?? "Verified");
  if (status === "Verified" && reasons.length === 0) return null;
  return (
    <div className="rounded border border-amber-200 bg-amber-50 p-2 text-xs text-amber-950">
      <p className="font-semibold">Trust check: {status}</p>
      {reasons.length > 0 && (
        <ul className="mt-1 grid gap-1">
          {reasons.slice(0, 5).map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function hiddenBreakdownReason(opportunity: Opportunity): string {
  return (
    opportunity.hidden_reason ||
    opportunity.rejection_reason ||
    opportunity.demographic_match_explanation ||
    (opportunity.visibility_status === "travel_exception"
      ? "This otherwise relevant breakdown is outside your audition travel preference."
      : "This breakdown needs review before it returns to the main list.")
  );
}

export function TextAction({
  children,
  onClick,
  tone = "default",
  disabled = false,
  ariaDescribedBy
}: {
  children: ReactNode;
  onClick: () => void;
  tone?: "default" | "danger" | "muted";
  disabled?: boolean;
  ariaDescribedBy?: string;
}) {
  const tones = {
    default: "text-accent hover:text-blue-700",
    danger: "text-red-700 hover:text-red-800",
    muted: "text-slate-600 hover:text-ink"
  };
  return (
    <button
      type="button"
      className={`text-sm font-semibold underline-offset-2 hover:underline disabled:cursor-not-allowed disabled:opacity-60 ${tones[tone]}`}
      disabled={disabled}
      aria-describedby={ariaDescribedBy}
      onClick={onClick}
    >
      {children}
    </button>
  );
}

export type HiddenBreakdownAction = "complete" | "travel" | "paste" | "role";

export type CompleteBreakdownFormState = {
  project_type: string;
  role_type: string;
  audition_type: string;
  audition_location: string;
  audition_travel_hours: string;
  audition_deadline: string;
  location: string;
  union: string;
};

export type TravelInfoFormState = {
  audition_location: string;
  audition_travel_hours: string;
};

export type PasteBreakdownTextFormState = {
  raw_text: string;
};

export type BreakdownRoleFormState = {
  role_name: string;
  requirements: string;
  character_description: string;
};

export type BreakdownRejectFormState = {
  highlighted_text_as_rejection_reason: string;
  rejection_reason: string;
};

export function completeBreakdownInitialState(opportunity: Opportunity): CompleteBreakdownFormState {
  return {
    project_type: opportunity.project_type ?? "",
    role_type: opportunity.role_type ?? "",
    audition_type: opportunity.audition_type ?? "",
    audition_location: opportunity.audition_location ?? "",
    audition_travel_hours: opportunity.audition_travel_hours ? String(opportunity.audition_travel_hours) : "",
    audition_deadline: opportunity.audition_deadline ?? opportunity.submission_deadline ?? "",
    location: opportunity.location ?? "",
    union: opportunity.union ?? ""
  };
}

export function travelInfoInitialState(opportunity: Opportunity): TravelInfoFormState {
  return {
    audition_location: opportunity.audition_location ?? "",
    audition_travel_hours: opportunity.audition_travel_hours ? String(opportunity.audition_travel_hours) : ""
  };
}

export function parseManualHours(value: string) {
  if (!value.trim()) return null;
  const manualHours = Number(value);
  return Number.isFinite(manualHours) ? manualHours : Number.NaN;
}


export function FactInferencePanel({
  facts,
  inference,
  fallbackFacts = {}
}: {
  facts?: Record<string, unknown> | null;
  inference?: Record<string, unknown> | null;
  fallbackFacts?: Record<string, unknown>;
}) {
  const factEntries = Object.entries({ ...fallbackFacts, ...(facts ?? {}) }).filter(([, value]) => detailValue(value));
  const inferenceEntries = Object.entries(inference ?? {}).filter(([, value]) => detailValue(value));
  return (
    <div className="grid gap-3">
      <div className="rounded border border-emerald-100 bg-emerald-50 p-3">
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <h5 className="font-semibold text-emerald-950">From Breakdown</h5>
          <Badge>Extracted Facts</Badge>
        </div>
        {factEntries.length === 0 ? <NeedsReviewLabel /> : <KeyValueEntries entries={factEntries} />}
      </div>
      <div className="rounded border border-blue-100 bg-blue-50 p-3">
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <h5 className="font-semibold text-blue-950">AI Inference</h5>
          <Badge>Inferred</Badge>
        </div>
        {inferenceEntries.length === 0 ? (
          <p className="text-sm text-blue-800">No inference has been generated for this section yet.</p>
        ) : (
          <div className="grid gap-2">
            {inferenceEntries.map(([key, value]) => (
              <InferenceItem key={key} name={key} value={value} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export function KeyValueEntries({ entries }: { entries: Array<[string, unknown]> }) {
  return (
    <dl className="grid gap-2">
      {entries.map(([key, value]) => (
        <div key={key} className="grid min-w-0 gap-1 rounded bg-white/80 p-2">
          <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{humanizeKey(key)}</dt>
          <dd className="break-words text-xs text-slate-800">{detailValue(value)}</dd>
        </div>
      ))}
    </dl>
  );
}

function InferenceItem({ name, value }: { name: string; value: unknown }) {
  const structured = value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : null;
  const displayValue = structured ? structured.value : value;
  const confidence = structured?.confidence;
  const explanation = structured?.explanation || "Inferred from role description.";
  return (
    <div className="min-w-0 rounded bg-white/80 p-2">
      <div className="flex flex-wrap items-center gap-2">
        <p className="break-words font-medium text-slate-800">{humanizeKey(name)}</p>
        {confidence !== undefined && <Badge>Confidence {String(confidence)}%</Badge>}
      </div>
      <p className="mt-1 break-words text-slate-800">{detailValue(displayValue) || "Needs Review"}</p>
      <p className="mt-1 break-words text-xs text-blue-800">{String(explanation)}</p>
    </div>
  );
}

function NeedsReviewLabel() {
  return <p className="rounded bg-amber-50 p-2 text-sm font-medium text-amber-900">Needs Review</p>;
}

export function missingFields(opportunity: Opportunity): string[] {
  const value = opportunity.source_metadata?.missing_fields;
  return Array.isArray(value) ? value.map(String).filter(Boolean) : [];
}

export function KeyValueGrid({ data, fallback = {} }: { data?: Record<string, unknown> | null; fallback?: Record<string, unknown> }) {
  const merged = { ...fallback, ...(data ?? {}) };
  const entries = Object.entries(merged).filter(([, value]) => detailValue(value));
  if (entries.length === 0) {
    return <p className="text-slate-500">Needs Review</p>;
  }
  return (
    <dl className="grid gap-2">
      {entries.map(([key, value]) => (
        <div key={key} className="grid gap-1 rounded bg-slate-50 p-2">
          <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{humanizeKey(key)}</dt>
          <dd className="text-xs text-slate-800">{detailValue(value)}</dd>
        </div>
      ))}
    </dl>
  );
}

export function withoutKeys(data: Record<string, unknown> | null | undefined, keys: string[]): Record<string, unknown> {
  return Object.fromEntries(Object.entries(data ?? {}).filter(([key]) => !keys.includes(key)));
}

export function breakdownFamily(opportunity: Opportunity): "Theater" | "FilmTV" | "All" {
  const text = [
    opportunity.project_type,
    opportunity.category,
    opportunity.production_details?.project_type,
    opportunity.description,
    opportunity.project
  ].join(" ").toLowerCase();
  const hasTheater = /\b(theater|theatre|musical theater|musical theatre|stage|play|reading|workshop|broadway|off-broadway|off-off-broadway|epa|ecc)\b/.test(text);
  const hasFilmTv = /\b(film|television|tv|streaming|episodic|series|feature film|short film|tv movie|web series)\b/.test(text);
  if (hasTheater && !hasFilmTv) return "Theater";
  if (hasFilmTv && !hasTheater) return "FilmTV";
  return "All";
}

export function projectTypeLabel(opportunity: Opportunity): string {
  return String(opportunity.production_details?.project_type || opportunity.project_type || opportunity.category || breakdownFamily(opportunity));
}

export function isTheaterBreakdown(opportunity: Opportunity): boolean {
  return /\b(theatre|theater|musical|stage|play|epa|equity principal audition)\b/i.test(
    [
      opportunity.project_type,
      opportunity.category,
      opportunity.production_details?.project_type,
      opportunity.role_details?.audition_subtype,
      opportunity.description
    ].join(" ")
  );
}

export function productionFallback(opportunity: Opportunity): Record<string, unknown> {
  const base = {
    project_title: opportunity.project,
    project_type: opportunity.project_type || opportunity.category,
    union_status: opportunity.union,
    rate: opportunity.rate,
    travel_provided: boolLabel(opportunity.travel_covered),
    housing_provided: boolLabel(opportunity.housing_covered)
  };
  if (isTheaterBreakdown(opportunity)) {
    return {
      ...base,
      performance_location: opportunity.production_details?.performance_location,
      audition_location: opportunity.audition_location || opportunity.production_details?.audition_location_name,
      rehearsal_location: opportunity.production_details?.rehearsal_location,
      audition_date: opportunity.production_details?.audition_date || opportunity.role_details?.audition_date,
      audition_time: opportunity.production_details?.audition_time || opportunity.role_details?.audition_time,
      preparation: preparationText(opportunity)
    };
  }
  return {
    ...base,
    shoot_location: opportunity.shoot_location || opportunity.location
  };
}

export function roleFallback(opportunity: Opportunity): Record<string, unknown> {
  return {
    role_name: opportunity.role,
    role_billing: opportunity.role_type,
    audition_type: opportunity.audition_type,
    character_description: opportunity.role_details?.character_description || opportunity.description,
    preparation: preparationText(opportunity),
    submission_instructions: detailValue(opportunity.role_details?.submission_instructions) || detailValue(opportunity.source_metadata?.submission_instructions)
  };
}

export function roleFitLabel(opportunity: Opportunity): string {
  if (opportunity.breakdown_roles?.length) {
    const fitting = opportunity.breakdown_roles.filter((role) => ["Strong Fit", "Possible Fit", "Stretch Fit"].includes(role.fit_status));
    if (fitting.length) return `${fitting.length} fitting role${fitting.length === 1 ? "" : "s"}`;
    if (opportunity.breakdown_roles.every((role) => role.fit_status === "Not Fit")) return "No fitting roles";
    return "Needs Review";
  }
  return opportunity.demographic_match_status;
}

export function parseConfidence(opportunity: Opportunity): number {
  const latest = opportunity.breakdown_parse_runs?.[0]?.overall_confidence;
  if (typeof latest === "number") return latest;
  const metadataValue = opportunity.source_metadata?.breakdown_parse_confidence;
  if (typeof metadataValue === "number") return metadataValue;
  if (typeof metadataValue === "string") {
    const parsed = Number(metadataValue);
    if (!Number.isNaN(parsed)) return parsed;
  }
  return opportunity.manual_review_required ? 50 : 80;
}

export function preparationText(opportunity: Opportunity): string {
  const direct = detailValue(opportunity.role_details?.preparation) || detailValue(opportunity.production_details?.preparation);
  if (direct) return direct;
  const section = opportunity.breakdown_sections?.find((item) => item.section_type === "Preparation");
  return section?.raw_text ?? "";
}

export function stringValue(value: unknown): string {
  return detailValue(value);
}

export function formStringValue(value: unknown): string {
  if (value === null || value === undefined || value === "" || value === false) return "";
  if (Array.isArray(value)) return value.filter(Boolean).join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export function toDateTimeLocal(value?: string | null): string {
  if (!value) return "";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value.includes("T") ? value.slice(0, 16) : "";
  }
  const pad = (item: number) => String(item).padStart(2, "0");
  return `${parsed.getFullYear()}-${pad(parsed.getMonth() + 1)}-${pad(parsed.getDate())}T${pad(parsed.getHours())}:${pad(parsed.getMinutes())}`;
}

export function detailValue(value: unknown): string {
  if (value === null || value === undefined || value === "" || value === false) return "";
  if (Array.isArray(value)) return value.filter(Boolean).join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  const text = String(value);
  if (/^https?:\/\//i.test(text)) return "Link saved";
  return text.replace(/https?:\/\/\S+/gi, "Link saved");
}

export function boolLabel(value?: boolean | null) {
  if (value === null || value === undefined) return "";
  return value ? "Yes" : "No";
}

export function humanizeKey(value: string) {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function RecommendationPanel({
  recommendations,
  opportunities,
  assets
}: {
  recommendations: AgentRecommendation[];
  opportunities: Opportunity[];
  assets: Asset[];
}) {
  const feedbackMutation = useRecommendationFeedback();
  const [selected, setSelected] = useState<AgentRecommendation | null>(null);
  const [feedbackOpenFor, setFeedbackOpenFor] = useState<string | null>(null);
  const [feedbackReasons, setFeedbackReasons] = useState<Record<string, string[]>>({});
  const [feedbackPendingById, setFeedbackPendingById] = useState<Record<string, boolean>>({});
  const [feedbackErrorById, setFeedbackErrorById] = useState<Record<string, string>>({});
  const [feedbackSuccessById, setFeedbackSuccessById] = useState<Record<string, string>>({});
  const feedbackPendingIds = useRef(new Set<string>());
  const opportunityById = useMemo(() => Object.fromEntries(opportunities.map((item) => [item.id, item])), [opportunities]);
  const assetById = useMemo(() => Object.fromEntries(assets.map((item) => [item.id, item])), [assets]);
  const selectedOpportunity = selected ? opportunityById[selected.opportunity_id] : null;

  async function submitFeedback(
    recommendation: AgentRecommendation,
    feedbackType: RecommendationFeedback["feedback_type"],
    reasons: string[] = [],
    initiatingControl?: HTMLButtonElement | null,
    successFocusTarget?: HTMLButtonElement | null
  ) {
    if (feedbackPendingIds.current.has(recommendation.id)) return;
    feedbackPendingIds.current.add(recommendation.id);
    setFeedbackPendingById((current) => ({ ...current, [recommendation.id]: true }));
    setFeedbackErrorById((current) => ({ ...current, [recommendation.id]: "" }));
    setFeedbackSuccessById((current) => ({ ...current, [recommendation.id]: "" }));
    try {
      await feedbackMutation.mutateAsync({ id: recommendation.id, payload: {
        feedback_type: feedbackType,
        fit_reasons: reasons
      } });
      setFeedbackOpenFor((current) => current === recommendation.id ? null : current);
      setFeedbackReasons((current) => ({ ...current, [recommendation.id]: [] }));
      setFeedbackSuccessById((current) => ({ ...current, [recommendation.id]: "Feedback saved. Future recommendations will learn from this." }));
      window.setTimeout(() => successFocusTarget?.isConnected && successFocusTarget.focus(), 0);
    } catch (caught) {
      setFeedbackErrorById((current) => ({ ...current, [recommendation.id]: errorMessage(caught, "Could not save recommendation feedback.") }));
      window.setTimeout(() => initiatingControl?.isConnected && initiatingControl.focus(), 0);
    } finally {
      feedbackPendingIds.current.delete(recommendation.id);
      setFeedbackPendingById((current) => ({ ...current, [recommendation.id]: false }));
    }
  }

  function clearFeedbackResult(recommendationId: string) {
    setFeedbackErrorById((current) => ({ ...current, [recommendationId]: "" }));
    setFeedbackSuccessById((current) => ({ ...current, [recommendationId]: "" }));
  }

  function toggleFeedbackReason(recommendationId: string, reason: string) {
    clearFeedbackResult(recommendationId);
    setFeedbackReasons((current) => {
      const existing = current[recommendationId] ?? [];
      const next = existing.includes(reason) ? existing.filter((item) => item !== reason) : [...existing, reason];
      return { ...current, [recommendationId]: next };
    });
  }

  return (
    <Section title="Recommended Strategy" actions={<Sparkles className="h-5 w-5 text-slate-500" />}>
      <div className="grid gap-3 lg:grid-cols-3">
        {recommendations.length === 0 ? <EmptyState>Generate a strategy for a breakdown to see recommendation, materials, and a submission note.</EmptyState> : recommendations.map((recommendation) => {
          const opportunity = opportunityById[recommendation.opportunity_id];
          return (
            <ActionCard
              key={recommendation.id}
              title={opportunity ? <OpportunityLink opportunity={opportunity} /> : "Breakdown"}
              status={<Badge>{actorRecommendationLabel(recommendation)}</Badge>}
              meta={`${recommendation.audition_type} · ${recommendation.audition_decision}`}
              primaryAction={<Button variant="secondary" onClick={() => setSelected(recommendation)}>Why?</Button>}
              details={(
                <div className="grid gap-2">
                  <div className="flex flex-wrap gap-2">
                    <Badge>{recommendation.confidence_level} Confidence</Badge>
                    <Badge>{recommendation.risk_level} Risk</Badge>
                  </div>
                  {!recommendation.display_opportunity && <p className="rounded bg-red-50 p-2 text-sm text-red-700">Hidden from the main list because the audition travel rule says it is not eligible.</p>}
                  <DetailDisclosure label="Recommended Materials">
                    <RecommendedMaterialsList recommendation={recommendation} assetById={assetById} opportunity={opportunity} />
                  </DetailDisclosure>
                  <RecommendationFeedbackControls
                    recommendation={recommendation}
                    open={feedbackOpenFor === recommendation.id}
                    selectedReasons={feedbackReasons[recommendation.id] ?? []}
                    pending={Boolean(feedbackPendingById[recommendation.id])}
                    error={feedbackErrorById[recommendation.id]}
                    successMessage={feedbackSuccessById[recommendation.id]}
                    onToggleOpen={() => { clearFeedbackResult(recommendation.id); setFeedbackOpenFor((current) => current === recommendation.id ? null : recommendation.id); }}
                    onToggleReason={(reason) => toggleFeedbackReason(recommendation.id, reason)}
                    onSubmit={(feedbackType, reasons, initiatingControl, successFocusTarget) => void submitFeedback(recommendation, feedbackType, reasons, initiatingControl, successFocusTarget)}
                  />
                </div>
              )}
            />
          );
        })}
      </div>
      {selected && (
        <div className="mt-4 rounded-md border border-blue-200 bg-blue-50 p-4">
          <div className="flex items-start justify-between gap-3">
            <h3 className="font-semibold">Why This Was Recommended</h3>
            <Button variant="secondary" onClick={() => setSelected(null)}>Close</Button>
          </div>
          <div className="mt-3 grid gap-2 text-sm">
            <div className="rounded bg-white/80 p-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Overall Recommendation</p>
              <p className="mt-1 text-base font-semibold text-ink">{actorRecommendationLabel(selected)}</p>
            </div>
            <div className="rounded bg-white/80 p-3">
              <h4 className="font-semibold text-ink">Why This Role Fits</h4>
              <div className="mt-2 grid gap-1">
                {recommendationFitItems(selected, selectedOpportunity).map((item) => (
                  <p key={`${item.kind}-${item.label}`} className={item.kind === "warning" ? "text-amber-800" : "text-emerald-800"}>
                    <span className="font-semibold">{item.kind === "warning" ? "△" : "✓"}</span> {item.label}
                  </p>
                ))}
              </div>
            </div>
            <div className="rounded bg-white/80 p-3">
              <h4 className="font-semibold text-ink">Missing Materials</h4>
              <div className="mt-2 grid gap-1">
                {missingRecommendationMaterials(selected).length === 0 ? (
                  <p className="text-emerald-800">✓ Full submission material package available</p>
                ) : missingRecommendationMaterials(selected).map((item) => (
                  <p key={item}>• {item}</p>
                ))}
              </div>
            </div>
            <div className="rounded bg-white/80 p-3">
              <h4 className="font-semibold text-ink">Recommended Materials</h4>
              <RecommendedMaterialsList recommendation={selected} assetById={assetById} opportunity={selectedOpportunity} detailed />
            </div>
            <DetailDisclosure label="Strategy" defaultOpen>
              <p>{selected.submission_strategy_explanation}</p>
              {selected.recommended_note && <p className="mt-2"><strong>Suggested note:</strong> {selected.recommended_note}</p>}
            </DetailDisclosure>
            <DetailDisclosure label="Audition">
              <p>{selected.audition_type}, {selected.audition_travel_hours ?? "unknown"} hours, {selected.audition_decision}</p>
              <p className="mt-2">{selected.audition_explanation}</p>
            </DetailDisclosure>
            <DetailDisclosure label="Travel">{selected.travel_explanation}</DetailDisclosure>
            <DetailDisclosure label="Archetype">{selected.archetype_explanation}</DetailDisclosure>
            <DetailDisclosure label="Materials">{selected.asset_explanation}</DetailDisclosure>
            <DetailDisclosure label="Risk">
              <p>{selected.risk_level}. {selected.risk_explanation}</p>
            </DetailDisclosure>
            <DetailDisclosure label="Debug: Internal Scores">
              <p>Internal score: {selected.score}</p>
              {Object.entries(selected.score_breakdown).map(([key, value]) => <p key={key}>{humanizeKey(key)}: {value}</p>)}
            </DetailDisclosure>
            <RecommendationFeedbackControls
              recommendation={selected}
              open={feedbackOpenFor === selected.id}
              selectedReasons={feedbackReasons[selected.id] ?? []}
              pending={Boolean(feedbackPendingById[selected.id])}
              error={feedbackErrorById[selected.id]}
              successMessage={feedbackSuccessById[selected.id]}
              onToggleOpen={() => { clearFeedbackResult(selected.id); setFeedbackOpenFor((current) => current === selected.id ? null : selected.id); }}
              onToggleReason={(reason) => toggleFeedbackReason(selected.id, reason)}
              onSubmit={(feedbackType, reasons, initiatingControl, successFocusTarget) => void submitFeedback(selected, feedbackType, reasons, initiatingControl, successFocusTarget)}
            />
          </div>
        </div>
      )}
    </Section>
  );
}

export function actorRecommendationLabel(recommendation: AgentRecommendation): string {
  if (recommendation.match_type === "High-Risk / High-Reward" && !recommendation.display_opportunity) {
    return "Not Recommended";
  }
  if (recommendation.score >= 85) return "Excellent Match";
  if (recommendation.match_type === "Strong Match") return "Strong Match";
  if (recommendation.match_type === "Growth Match") return recommendation.score >= 60 ? "Good Match" : "Comfortable Stretch";
  return "Stretch";
}

export function recommendationFitItems(recommendation: AgentRecommendation, opportunity?: Opportunity | null): Array<{ kind: "positive" | "warning"; label: string }> {
  const items: Array<{ kind: "positive" | "warning"; label: string }> = [];
  const checks = opportunity?.demographic_match_details?.checks ?? [];
  for (const check of checks) {
    if (check.status === "Not Specified") continue;
    const decision = check.compatibility_label || check.status;
    const label = check.label === "Race / Ethnicity / Nationality" ? ethnicityFitLabel(check) : String(decision);
    items.push({ kind: decision === "Comfortable Stretch" || decision === "Stretch" ? "warning" : "positive", label });
  }
  if (recommendation.audition_type === "Self-Tape" || recommendation.audition_type === "Virtual") {
    items.push({ kind: "positive", label: recommendation.audition_type });
  }
  if (opportunity?.travel_covered) items.push({ kind: "positive", label: "Travel Covered" });
  if (opportunity?.housing_covered) items.push({ kind: "positive", label: "Housing Covered" });
  const profile = opportunity?.breakdown_roles.find((role) => ["Strong Fit", "Possible Fit", "Stretch Fit"].includes(role.fit_status))?.character_profile;
  for (const archetype of [...(profile?.primary_archetypes ?? []), ...(profile?.secondary_archetypes ?? [])].slice(0, 4)) {
    items.push({ kind: archetype.includes("Stretch") ? "warning" : "positive", label: archetype });
  }
  if (items.length === 0) {
    items.push({ kind: "positive", label: recommendation.archetype_explanation });
  }
  return items;
}

function ethnicityFitLabel(check: { detected_requirements?: string[]; compatibility_label?: string; status: string }): string {
  const detected = (check.detected_requirements ?? []).join(" ").toLowerCase();
  if (detected.includes("open") || detected.includes("any")) return "Open Ethnicity";
  return check.compatibility_label || check.status;
}

export function missingRecommendationMaterials(recommendation: AgentRecommendation): string[] {
  return [
    ["Headshot", recommendation.recommended_headshot_id],
    ["Reel", recommendation.recommended_reel_id],
    ["Resume", recommendation.recommended_resume_id],
    ["Slate", recommendation.recommended_slate_id]
  ].filter(([, id]) => !id).map(([label]) => String(label));
}

export function mergedReadinessStatus(readiness?: AuditionReadiness, recommendation?: AgentRecommendation): string {
  if (readiness?.readiness_label) return readiness.readiness_label;
  if (!recommendation) return "Needs Materials";
  const label = actorRecommendationLabel(recommendation);
  if (label === "Excellent Match" || label === "Strong Match") return "Ready";
  if (label === "Good Match") return "Mostly Ready";
  if (label === "Comfortable Stretch" || label === "Stretch") return "Stretch";
  if (label === "Not Recommended") return "Not Recommended";
  return "Needs Materials";
}

export function recommendedAssetId(recommendation: AgentRecommendation | undefined, assetType: AssetType): string | undefined | null {
  if (!recommendation) return "";
  if (assetType === "Headshot") return recommendation.recommended_headshot_id;
  if (assetType === "Reel") return recommendation.recommended_reel_id;
  if (assetType === "Resume") return recommendation.recommended_resume_id;
  return recommendation.recommended_slate_id;
}

export function mergedMissingMaterials(readiness?: AuditionReadiness, recommendation?: AgentRecommendation): string[] {
  return Array.from(new Set([
    ...(readiness?.missing_materials ?? []),
    ...(recommendation ? missingRecommendationMaterials(recommendation) : [])
  ])).filter(Boolean);
}

export function stretchExplanation(readinessStatus: string, recommendation: AgentRecommendation | undefined, opportunity: Opportunity): string {
  if (recommendation?.risk_explanation) return recommendation.risk_explanation;
  if (readinessStatus === "Stretch") {
    return "This may be worth considering, but at least one fit, materials, travel, or history signal is not fully aligned yet.";
  }
  if (readinessStatus === "Not Recommended") {
    return opportunity.demographic_match_explanation || "This role is not recommended based on the current breakdown and saved profile.";
  }
  return "No major stretch concerns are currently flagged. Review the breakdown details before deciding.";
}

export function RecommendedMaterialSelect({
  assetType,
  assets,
  recommendedAssetId,
  selectedAssetId,
  onChange
}: {
  assetType: AssetType;
  assets: Asset[];
  recommendedAssetId?: string | null;
  selectedAssetId: string;
  onChange: (assetId: string) => void;
}) {
  return (
    <Field label={assetType}>
      <select className={inputClass} value={selectedAssetId} onChange={(event) => onChange(event.target.value)}>
        <option value="">No {assetType.toLowerCase()} selected</option>
        {assets.map((asset) => (
          <option key={asset.id} value={asset.id}>
            {asset.asset_name}{asset.id === recommendedAssetId ? " *recommended" : ""}
          </option>
        ))}
      </select>
    </Field>
  );
}

export function RecommendedMaterialsList({
  recommendation,
  assetById,
  opportunity,
  detailed = false
}: {
  recommendation: AgentRecommendation;
  assetById: Record<string, Asset>;
  opportunity?: Opportunity | null;
  detailed?: boolean;
}) {
  const rows: Array<[string, string | null | undefined]> = [
    ["Headshot", recommendation.recommended_headshot_id],
    ["Reel", recommendation.recommended_reel_id],
    ["Resume", recommendation.recommended_resume_id],
    ["Slate", recommendation.recommended_slate_id],
  ];
  return (
    <div className="grid gap-2">
      {rows.map(([label, id]) => {
        const asset = assetById[id ?? ""];
        return (
          <div key={label} className="rounded bg-white/80 p-2">
            <p><strong>{label}:</strong> {asset?.asset_name ?? "Missing"}</p>
            {detailed && (
              <p className="mt-1 text-slate-600">
                {asset ? materialReason(label, asset, recommendation, opportunity) : `${label} is missing from the recommended package.`}
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}

function materialReason(label: string, asset: Asset, recommendation: AgentRecommendation, opportunity?: Opportunity | null): string {
  const archetypes = asset.archetype_names.length ? asset.archetype_names.join(", ") : "the role's casting lane";
  if (label === "Headshot") return `Selected because it visually supports ${archetypes} for ${opportunity?.role ?? "this role"}.`;
  if (label === "Reel") return `Selected because its tags and archetypes reinforce the character tone and role fit.`;
  if (label === "Resume") return `Selected so casting sees the most relevant credits and professional context.`;
  if (label === "Slate") return `Selected to keep the submission package complete and current.`;
  return recommendation.asset_explanation;
}

export function RecommendationFeedbackControls({
  recommendation,
  open,
  selectedReasons,
  pending,
  error,
  successMessage,
  onToggleOpen,
  onToggleReason,
  onSubmit
}: {
  recommendation: AgentRecommendation;
  open: boolean;
  selectedReasons: string[];
  pending: boolean;
  error?: string;
  successMessage?: string;
  onToggleOpen: () => void;
  onToggleReason: (reason: string) => void;
  onSubmit: (feedbackType: RecommendationFeedback["feedback_type"], reasons: string[], initiatingControl: HTMLButtonElement, successFocusTarget: HTMLButtonElement) => void;
}) {
  const instanceId = useId();
  const feedbackId = `recommendation-feedback-${recommendation.id}-${instanceId.replace(/:/g, "")}`;
  const statusId = `${feedbackId}-status`;
  const fitTriggerRef = useRef<HTMLButtonElement>(null);
  const describedBy = pending || error || successMessage ? statusId : undefined;
  return (
    <div className="rounded border border-slate-200 bg-white/80 p-3" aria-busy={pending || undefined}>
      <p className="text-sm font-semibold text-ink">Optional feedback</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {recommendationFeedbackTypes.map((type) => (
          <button
            key={type}
            ref={type === "This Fits Me" ? fitTriggerRef : undefined}
            type="button"
            disabled={pending}
            aria-describedby={describedBy}
            className="text-sm font-semibold text-accent hover:underline"
            onClick={(event) => type === "This Fits Me" ? onToggleOpen() : onSubmit(type, [], event.currentTarget, event.currentTarget)}
          >
            {type}
          </button>
        ))}
      </div>
      {pending && <p id={statusId} role="status" className="mt-2 text-sm text-slate-600">Saving feedback…</p>}
      {!pending && error && <p id={statusId} role="alert" className="mt-2 rounded bg-red-50 p-2 text-sm text-red-700">{error}</p>}
      {!pending && !error && successMessage && <p id={statusId} role="status" className="mt-2 rounded bg-emerald-50 p-2 text-sm text-emerald-800">{successMessage}</p>}
      {open && (
        <form
          aria-label="Recommendation feedback"
          aria-describedby={describedBy}
          className="mt-3 grid gap-3 rounded bg-slate-50 p-3"
          onSubmit={(event) => {
            event.preventDefault();
            const submitter = event.nativeEvent.submitter;
            if (submitter instanceof HTMLButtonElement && fitTriggerRef.current) {
              onSubmit("This Fits Me", selectedReasons, submitter, fitTriggerRef.current);
            }
          }}
        >
          <fieldset disabled={pending} className="grid gap-3">
          <legend className="text-sm font-medium text-slate-700">What makes this role a good fit?</legend>
          <div className="grid gap-2 sm:grid-cols-2">
            {fitReasonOptions.map((reason) => (
              <label key={reason} className="flex items-center gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={selectedReasons.includes(reason)}
                  onChange={() => onToggleReason(reason)}
                />
                {reason}
              </label>
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            <Button type="submit" variant="secondary" disabled={pending}>
              Save Feedback
            </Button>
            <Button variant="secondary" disabled={pending} onClick={onToggleOpen}>
              Cancel
            </Button>
          </div>
          </fieldset>
        </form>
      )}
    </div>
  );
}

export function formatScoreLabel(value: string) {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
