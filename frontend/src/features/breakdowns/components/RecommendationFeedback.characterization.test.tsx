import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, renderWithRouter, screen, waitFor } from "../../../test/testUtils";
import type { AgentRecommendation, Opportunity } from "../types";
import { RecommendationPanel } from "./BreakdownDetails";
import { MergedAuditionReadinessPanel } from "./BreakdownReadiness";

const hooks = vi.hoisted(() => ({
  feedback: { mutateAsync: vi.fn() },
  strategy: { mutateAsync: vi.fn() },
  matches: { data: [], error: null, isFetching: false, refetch: vi.fn() }
}));

vi.mock("../hooks/useBreakdownQueries", () => ({
  useRecommendationFeedback: () => hooks.feedback,
  useGenerateBreakdownStrategy: () => hooks.strategy,
  useMaterialMatches: () => hooks.matches
}));

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
}

const opportunity = {
  id: "opp-1", role: "Detective", project: "Feedback Pilot", project_type: "TV", role_type: "Guest Star",
  category: "Film/TV", status: "open", visibility_status: "visible", source_type: "Manual Entry",
  platform: null, from_agent: false, archetypes: [], union: "SAG-AFTRA", location: "New York, NY",
  description: "Detective role", source_metadata: {}, production_details: {}, role_details: {}, extracted_facts: {},
  ai_inference: {}, breakdown_roles: [], breakdown_sections: [], breakdown_parse_runs: [], watchlist_match_names: [],
  watchlist_match_count: 0, manual_review_required: false, is_duplicate: false, already_tracked: false,
  created_at: "2026-07-01T00:00:00Z", updated_at: "2026-07-01T00:00:00Z"
} as unknown as Opportunity;

const recommendation = {
  id: "rec-1", opportunity_id: opportunity.id, actor_profile_id: "actor-1", score: 80,
  match_type: "Strong Match", display_opportunity: true, explanation: "Good fit", score_breakdown: {},
  audition_type: "Self-Tape", audition_travel_hours: 0, audition_decision: "Recommended",
  audition_explanation: "Feasible", travel_explanation: "Local", archetype_explanation: "Authority",
  asset_explanation: "Current materials", submission_strategy_explanation: "Submit", confidence_level: "High",
  risk_level: "Low", risk_explanation: null, recommended_headshot_id: null, recommended_reel_id: null,
  recommended_resume_id: null, recommended_slate_id: null, recommended_note: "Available",
  created_at: "2026-07-01T00:00:00Z", updated_at: "2026-07-01T00:00:00Z"
} as AgentRecommendation;

beforeEach(() => {
  hooks.feedback.mutateAsync.mockReset();
  hooks.strategy.mutateAsync.mockReset();
  hooks.matches.refetch.mockReset();
});

describe.each([
  ["recommendation panel", () => renderWithRouter(<RecommendationPanel recommendations={[recommendation]} opportunities={[opportunity]} assets={[]} />), null],
  ["readiness panel", () => renderWithRouter(<MergedAuditionReadinessPanel actor={null} opportunities={[opportunity]} recommendations={[recommendation]} assets={[]} readiness={[]} />), "Expand audition readiness"]
] as const)("%s feedback characterization", (_label, renderOwner, expandLabel) => {
  it("announces pending, blocks same-ID duplicates, preserves a failed draft, and retries to target-only success", async () => {
    const first = deferred<Record<string, never>>();
    const second = deferred<Record<string, never>>();
    hooks.feedback.mutateAsync.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
    const { user } = renderOwner();
    if (expandLabel) await user.click(screen.getByRole("button", { name: expandLabel }));
    const fitTrigger = screen.getByRole("button", { name: "This Fits Me" });
    await user.click(fitTrigger);
    await user.click(screen.getByRole("checkbox", { name: "Authority" }));
    const submit = screen.getByRole("button", { name: "Save Feedback" });

    fireEvent.click(submit);
    fireEvent.click(submit);
    expect(hooks.feedback.mutateAsync).toHaveBeenCalledTimes(1);
    expect(hooks.feedback.mutateAsync).toHaveBeenCalledWith({
      id: recommendation.id,
      payload: { feedback_type: "This Fits Me", fit_reasons: ["Authority"] }
    });
    expect(screen.getByRole("status")).toHaveTextContent(/saving feedback/i);
    expect(submit).toBeDisabled();

    await act(async () => { first.reject(new Error("Learning service unavailable")); await Promise.resolve(); });
    expect(await screen.findByRole("alert")).toHaveTextContent("Learning service unavailable");
    expect(screen.getByRole("checkbox", { name: "Authority" })).toBeChecked();
    await waitFor(() => expect(submit).toHaveFocus());

    await act(async () => { (screen.getByRole("form", { name: "Recommendation feedback" }) as HTMLFormElement).requestSubmit(submit); });
    expect(hooks.feedback.mutateAsync).toHaveBeenCalledTimes(2);
    await waitFor(() => expect(screen.queryByRole("alert")).not.toBeInTheDocument());
    await act(async () => { second.resolve({}); await second.promise; });
    expect(await screen.findByText("Feedback saved. Future recommendations will learn from this.")).toHaveAttribute("role", "status");
    expect(screen.queryByRole("checkbox", { name: "Authority" })).not.toBeInTheDocument();
    await waitFor(() => expect(fitTrigger).toHaveFocus());
  });
});
