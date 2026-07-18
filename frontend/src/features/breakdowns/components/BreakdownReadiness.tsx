import { useMemo, useRef, useState } from "react";
import { ChevronDown, ChevronRight, Gauge } from "lucide-react";
import { Badge, Button, DetailDisclosure, EmptyState, Field, Section, inputClass } from "../../../components/ui";
import { useGenerateBreakdownStrategy, useMaterialMatches, useRecommendationFeedback } from "../hooks/useBreakdownQueries";
import type { ActorProfile, AgentRecommendation, Asset, AssetType, AuditionReadiness, MaterialOpportunityMatch, Opportunity, RecommendationFeedback } from "../types";
import { errorMessage } from "../../../services/api/errors";
import {
  OpportunityLink,
  RecommendedMaterialSelect,
  RecommendedMaterialsList,
  RecommendationFeedbackControls,
  TextAction,
  formatScoreLabel,
  humanizeKey,
  mergedMissingMaterials,
  mergedReadinessStatus,
  projectTypeLabel,
  recommendationFitItems,
  recommendedAssetId,
  stretchExplanation
} from "./BreakdownDetails";

export function MergedAuditionReadinessPanel({
  actor,
  opportunities,
  recommendations,
  assets,
  readiness
}: {
  actor: ActorProfile | null;
  opportunities: Opportunity[];
  recommendations: AgentRecommendation[];
  assets: Asset[];
  readiness: AuditionReadiness[];
}) {
  const [expandedIds, setExpandedIds] = useState<Record<string, boolean>>({});
  const [selectedAssetIds, setSelectedAssetIds] = useState<Record<string, Record<AssetType, string>>>({});
  const materialMatches = useMaterialMatches();
  const matches = useMemo(() => materialMatches.data ?? [], [materialMatches.data]);
  const strategyMutation = useGenerateBreakdownStrategy(); const feedbackMutation = useRecommendationFeedback();
  const [feedbackOpenFor, setFeedbackOpenFor] = useState<string | null>(null);
  const [feedbackReasons, setFeedbackReasons] = useState<Record<string, string[]>>({});
  const [feedbackPendingById, setFeedbackPendingById] = useState<Record<string, boolean>>({});
  const [feedbackErrorById, setFeedbackErrorById] = useState<Record<string, string>>({});
  const [feedbackSuccessById, setFeedbackSuccessById] = useState<Record<string, string>>({});
  const feedbackPendingIds = useRef(new Set<string>());

  const opportunityById = useMemo(() => Object.fromEntries(opportunities.map((item) => [item.id, item])), [opportunities]);
  const recommendationByOpportunityId = useMemo(() => Object.fromEntries(recommendations.map((item) => [item.opportunity_id, item])), [recommendations]);
  const readinessByOpportunityId = useMemo(() => Object.fromEntries(readiness.map((item) => [item.opportunity_id, item])), [readiness]);
  const materialMatchByOpportunityId = useMemo(() => Object.fromEntries(matches.map((item) => [item.opportunity.id, item])), [matches]);
  const assetById = useMemo(() => Object.fromEntries(assets.map((item) => [item.id, item])), [assets]);
  const rows = useMemo(() => {
    const ids = new Set<string>();
    const items: Opportunity[] = [];
    for (const opportunity of opportunities) {
      if (!ids.has(opportunity.id)) {
        ids.add(opportunity.id);
        items.push(opportunity);
      }
    }
    for (const item of readiness) {
      const opportunity = opportunityById[item.opportunity_id];
      if (opportunity && !ids.has(opportunity.id)) {
        ids.add(opportunity.id);
        items.push(opportunity);
      }
    }
    return items;
  }, [opportunities, opportunityById, readiness]);

  async function refreshMaterialMatches() {
    if (!actor || assets.length === 0) return;
    await materialMatches.refetch();
  }

  async function generateStrategy(opportunityId: string) {
    await strategyMutation.mutateAsync(opportunityId);
  }

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

  function selectMaterial(opportunityId: string, assetType: AssetType, assetId: string) {
    setSelectedAssetIds((current) => ({
      ...current,
      [opportunityId]: {
        ...(current[opportunityId] ?? {}),
        [assetType]: assetId
      }
    }));
  }

  return (
    <Section
      title="Audition Readiness"
      actions={<Button variant="secondary" disabled={!actor || assets.length === 0 || materialMatches.isFetching} onClick={() => void refreshMaterialMatches()}>{materialMatches.isFetching ? "Refreshing..." : "Refresh Material Matches"}</Button>}
    >
      {materialMatches.error && <p className="mb-3 rounded border border-red-200 bg-red-50 p-2 text-xs text-red-700">{materialMatches.error.message}</p>}
      <div className="grid gap-2">
        {rows.length === 0 ? (
          <EmptyState>Add or discover a breakdown to see readiness, materials, and strategy in one place.</EmptyState>
        ) : rows.map((opportunity) => {
          const recommendation = recommendationByOpportunityId[opportunity.id];
          const readinessItem = readinessByOpportunityId[opportunity.id];
          const materialMatch = materialMatchByOpportunityId[opportunity.id];
          const readinessStatus = mergedReadinessStatus(readinessItem, recommendation);
          const expanded = Boolean(expandedIds[opportunity.id]);
          return (
            <article key={opportunity.id} className="rounded-md border border-slate-200 bg-white text-xs shadow-sm">
              <div className="flex flex-col gap-2 p-3 lg:flex-row lg:items-center lg:justify-between">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      className="rounded p-1 text-slate-500 hover:bg-slate-100"
                      aria-label={expanded ? "Collapse audition readiness" : "Expand audition readiness"}
                      onClick={() => setExpandedIds((current) => ({ ...current, [opportunity.id]: !current[opportunity.id] }))}
                    >
                      {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                    </button>
                    <div className="min-w-0">
                      <h3 className="truncate font-semibold text-ink">{opportunity.role || "Role TBD"}</h3>
                      <p className="truncate text-slate-600">{opportunity.project || "Project TBD"}</p>
                    </div>
                  </div>
                </div>
                <div className="flex shrink-0 flex-wrap items-center gap-2">
                  <Badge>{opportunity.role_type || opportunity.category || "Role"}</Badge>
                  <Badge>{readinessStatus}</Badge>
                </div>
              </div>
              {expanded && (
                <div className="grid gap-3 border-t border-slate-100 p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-ink">{opportunity.role || "Role"} · {opportunity.project || "Project"}</p>
                      <p className="mt-1 text-slate-600">{opportunity.role_type || opportunity.category || "Role type not listed"} · {projectTypeLabel(opportunity)}</p>
                    </div>
                    <Badge>{readinessStatus}</Badge>
                  </div>
                  {!recommendation && (
                    <div className="rounded bg-slate-50 p-2">
                      <p className="text-slate-600">Generate a strategy to select materials, write a submission approach, and explain fit.</p>
                      <div className="mt-2">
                        <TextAction onClick={() => void generateStrategy(opportunity.id)}>Generate strategy</TextAction>
                      </div>
                    </div>
                  )}
                  {readinessItem?.explanation && <p className="rounded bg-blue-50 p-2 text-blue-950">{readinessItem.explanation}</p>}
                  <DetailDisclosure label="Recommended Materials" defaultOpen>
                    <div className="grid gap-2 md:grid-cols-2">
                      {(["Headshot", "Reel", "Resume", "Slate"] as AssetType[]).map((assetType) => (
                        <RecommendedMaterialSelect
                          key={`${opportunity.id}-${assetType}`}
                          assetType={assetType}
                          assets={assets.filter((asset) => asset.asset_type === assetType)}
                          recommendedAssetId={recommendedAssetId(recommendation, assetType)}
                          selectedAssetId={selectedAssetIds[opportunity.id]?.[assetType] ?? recommendedAssetId(recommendation, assetType) ?? ""}
                          onChange={(assetId) => selectMaterial(opportunity.id, assetType, assetId)}
                        />
                      ))}
                    </div>
                    {recommendation && (
                      <div className="mt-3 rounded bg-white p-2">
                        <RecommendedMaterialsList recommendation={recommendation} assetById={assetById} opportunity={opportunity} detailed />
                      </div>
                    )}
                  </DetailDisclosure>
                  <DetailDisclosure label="Missing Materials" defaultOpen={Boolean(readinessItem?.missing_materials.length || recommendation)}>
                    <div className="grid gap-1">
                      {mergedMissingMaterials(readinessItem, recommendation).length === 0 ? (
                        <p className="text-emerald-800">No major material gaps found.</p>
                      ) : mergedMissingMaterials(readinessItem, recommendation).map((item) => (
                        <p key={item}>• {item}</p>
                      ))}
                    </div>
                  </DetailDisclosure>
                  <DetailDisclosure label="Why This Role Fits" defaultOpen={Boolean(recommendation)}>
                    {recommendation ? (
                      <div className="grid gap-1">
                        {recommendationFitItems(recommendation, opportunity).map((item) => (
                          <p key={`${item.kind}-${item.label}`} className={item.kind === "warning" ? "text-amber-800" : "text-emerald-800"}>
                            <span className="font-semibold">{item.kind === "warning" ? "△" : "✓"}</span> {item.label}
                          </p>
                        ))}
                      </div>
                    ) : (
                      <p>{opportunity.demographic_match_explanation || "Generate a strategy to see fit details."}</p>
                    )}
                  </DetailDisclosure>
                  <DetailDisclosure label="Why This Role May Be a Stretch">
                    <p>{stretchExplanation(readinessStatus, recommendation, opportunity)}</p>
                  </DetailDisclosure>
                  <DetailDisclosure label="Strategy" defaultOpen={Boolean(recommendation)}>
                    <p>{recommendation?.submission_strategy_explanation || opportunity.quality_explanation || "Generate a strategy to see a recommended submission approach."}</p>
                    {recommendation?.recommended_note && <p className="mt-2"><strong>Suggested note:</strong> {recommendation.recommended_note}</p>}
                  </DetailDisclosure>
                  {materialMatch && (
                    <DetailDisclosure label="Material Match">
                      <p>{materialMatch.explanation}</p>
                      <div className="mt-2 grid gap-2">
                        {materialMatch.matched_assets.map((asset) => (
                          <div key={asset.asset_id} className="rounded bg-slate-50 p-2">
                            <p className="font-semibold">{asset.asset_name} · {asset.asset_type}</p>
                            <p>{asset.reason}</p>
                          </div>
                        ))}
                      </div>
                    </DetailDisclosure>
                  )}
                  {recommendation && (
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
                  )}
                  <DetailDisclosure label="Technical Details">
                    {readinessItem ? (
                      <div className="grid gap-1">
                        <p>Internal score: {readinessItem.readiness_percentage}%</p>
                        <p>Character parsing: {readinessItem.character_parsing_status} ({readinessItem.character_parsing_confidence}% confidence)</p>
                        {Object.entries(readinessItem.score_breakdown).map(([label, value]) => (
                          <p key={label}>{formatScoreLabel(label)}: {value}</p>
                        ))}
                      </div>
                    ) : recommendation ? (
                      <div className="grid gap-1">
                        <p>Internal strategy score: {recommendation.score}</p>
                        {Object.entries(recommendation.score_breakdown).map(([label, value]) => (
                          <p key={label}>{humanizeKey(label)}: {value}</p>
                        ))}
                      </div>
                    ) : (
                      <p>No technical scoring available yet.</p>
                    )}
                  </DetailDisclosure>
                </div>
              )}
            </article>
          );
        })}
      </div>
    </Section>
  );
}
