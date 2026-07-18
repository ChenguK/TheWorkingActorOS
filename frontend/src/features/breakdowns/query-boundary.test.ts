import { describe, expect, it } from "vitest";

const sources = import.meta.glob<string>(
  ["./**/*.ts", "./**/*.tsx", "../../pages/*.tsx"],
  { eager: true, import: "default", query: "?raw" }
);

describe("Breakdowns Query boundaries", () => {
  it("has no broad reload or base-client access in Breakdowns presentation and hooks", () => {
    const production = Object.entries(sources).filter(([path]) => path.startsWith("./") && !path.includes(".test.") && !path.includes("/api/")).map(([, text]) => text).join("\n");
    expect(production).not.toContain("onChanged");
    expect(production).not.toContain("loadWorkflowData");
    expect(production).not.toContain('from "../../../services/api"');
    expect(production).not.toMatch(/\bfetch\(/);
  });

  it("outside consumers use only the public Breakdowns barrel", () => {
    const consumers = Object.entries(sources).filter(([path]) => path.startsWith("../../pages/")).map(([, text]) => text).join("\n");
    expect(consumers).not.toMatch(/features\/breakdowns\/(api|hooks|components)/);
    for (const hook of ["useBreakdowns", "useOpportunityOptions"]) expect(consumers).toContain(hook);
  });

  it("keeps deep parse on its typed contract without ad-hoc or manual refetch", () => {
    const hooks = sources["./hooks/useBreakdownQueries.ts"];
    const implementation = hooks.match(/export function useDeepParseBreakdown\(\)[^\n]+/)?.[0] ?? "";
    expect(implementation).toContain("keysForContract(invalidationContracts.opportunityDeepParse)");
    expect(implementation).not.toMatch(/classificationKeys|opportunityAggregateKeys|refetchQueries|invalidateQueries/);
  });

  it("keeps reject/archive on its typed contract without a new archive query", () => {
    const hooks = sources["./hooks/useBreakdownQueries.ts"];
    const implementation = hooks.match(/export function useRejectBreakdown\(\)[^\n]+/)?.[0] ?? "";
    expect(implementation).toContain("keysForContract(invalidationContracts.opportunityReject)");
    expect(implementation).not.toMatch(/classificationKeys|opportunityAggregateKeys|refetchQueries|invalidateQueries/);
    expect(hooks).not.toMatch(/resource: ["'](?:rejected|archive|archivedOpportunities)["']/);
  });

  it("keeps visible deep-parse feedback in the manager without duplicate hook ownership", () => {
    const manager = sources["./components/BreakdownManager.tsx"];
    const viewer = sources["./components/BreakdownViewer.tsx"];
    expect(manager.match(/useDeepParseBreakdown\(\)/g)).toHaveLength(1);
    expect(manager).toContain("deepParsePendingById");
    expect(manager).toContain("deepParseErrorById");
    expect(viewer).not.toContain("useDeepParseBreakdown");
    expect(viewer).not.toMatch(/QueryClient|queryKey|useQuery/);
  });

  it("keeps recommendation feedback local to its two approved owners without changing query ownership", () => {
    const details = sources["./components/BreakdownDetails.tsx"];
    const readiness = sources["./components/BreakdownReadiness.tsx"];
    const hooks = sources["./hooks/useBreakdownQueries.ts"];
    expect(details.match(/useRecommendationFeedback\(\)/g)).toHaveLength(1);
    expect(readiness.match(/useRecommendationFeedback\(\)/g)).toHaveLength(1);
    expect(`${details}\n${readiness}`).not.toMatch(/QueryClient|invalidateQueries|refetchQueries|feedbackController|useMutationFeedback/);
    expect(hooks.match(/export function useRecommendationFeedback\(\)[^\n]+/)?.[0]).toContain(
      "keysForContract(invalidationContracts.recommendationFeedbackCreate)"
    );
  });
});
