import { QueryClient } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import {
  invalidateInBackground,
  invalidationContracts,
  keysForContract,
  publicInvalidationKeys
} from "./invalidationContracts";

const productionHooks = import.meta.glob("../../features/**/hooks/*.{ts,tsx}", {
  eager: true,
  query: "?raw",
  import: "default"
}) as Record<string, string>;

describe("cross-feature invalidation contracts", () => {
  it("covers the review-critical mutation operations", () => {
    const operations = Object.values(invalidationContracts).map((contract) => contract.operation);
    expect(operations).toEqual(expect.arrayContaining([
      "submission.create", "submission.update", "submission.status", "submission.delete",
      "opportunity.create", "opportunity.update", "opportunity.manualParse", "opportunity.deepParse", "opportunity.strategyGenerate", "opportunity.reject", "opportunity.delete",
      "recommendation.feedbackCreate",
      "submissionQueue.execute", "callback.change", "workflowSelfTape.update", "careerTask.change",
      "reusableSelfTape.change", "provider.change", "platformCheckIn.update", "calendarEvent.change"
    ]));
  });

  it("maps every public invalidation key to a production query key", () => {
    const source = Object.values(productionHooks).join("\n");
    for (const key of Object.values(publicInvalidationKeys)) {
      const serialized = JSON.stringify(key);
      const resource = serialized.match(/"resource":"([^"]+)"/)?.[1];
      expect(resource ? source.includes(`resource: "${resource}"`) : source.includes(`${key[0]}.list`)).toBe(true);
    }
  });

  it("keeps direct and derived keys out of each contract's forbidden set", () => {
    for (const contract of Object.values(invalidationContracts)) {
      const affected = new Set([...contract.direct, ...contract.derived]);
      expect(contract.forbidden.filter((key) => affected.has(key as never))).toEqual([]);
      expect(new Set(keysForContract(contract).map((key) => JSON.stringify(key))).size).toBe(keysForContract(contract).length);
    }
  });

  it("documents queue execution as queue-only without pretending a Submission exists", () => {
    expect(invalidationContracts.queueExecution.timing).toBe("none");
    expect(invalidationContracts.queueExecution.forbidden).toContain("submissions");
  });

  it.each([
    ["create", invalidationContracts.opportunityCreate, ["breakdownOpportunities", "breakdownHidden", "workflowSelfTapes", "calendarEvents", "journalEntries", "breakdownReadiness", "breakdownMaterialMatches", "analyticsOperations", "analyticsIndustryTrends", "commandCenter"], ["submissions", "callbacks", "breakdownQueue", "relationships", "materials", "reusableSelfTapes", "analyticsIntelligence", "analyticsMaterialPerformance", "careerTasks"]],
    ["update", invalidationContracts.opportunityUpdate, ["breakdownOpportunities", "breakdownHidden", "workflowSelfTapes", "breakdownReadiness", "breakdownMaterialMatches"], ["calendarEvents", "journalEntries", "submissions", "reusableSelfTapes"]],
    ["manual parse", invalidationContracts.opportunityManualParse, ["breakdownOpportunities", "breakdownHidden", "workflowSelfTapes", "breakdownReadiness", "breakdownMaterialMatches"], ["calendarEvents", "journalEntries", "submissions", "reusableSelfTapes"]],
    ["strategy generation", invalidationContracts.opportunityStrategyGenerate, ["breakdownRecommendations", "breakdownOpportunities", "breakdownHidden", "analyticsMaterialPerformance", "commandCenter"], ["submissions", "workflowSelfTapes", "calendarEvents", "journalEntries", "breakdownQueue", "breakdownReadiness", "materials", "analyticsIntelligence"]],
    ["hard delete", invalidationContracts.opportunityDelete, ["breakdownOpportunities", "breakdownHidden", "workflowSelfTapes", "breakdownQueue", "breakdownRecommendations", "calendarEvents", "journalEntries", "reusableSelfTapes"], ["submissions", "materials", "careerTasks"]]
  ])("records exact %s side-effect and forbidden families", (_label, contract, required, forbidden) => {
    const affected = [...contract.direct, ...contract.derived];
    expect(affected).toEqual(expect.arrayContaining(required));
    expect(contract.forbidden).toEqual(expect.arrayContaining(forbidden));
  });

  it("records the exact deep-parse owner contract", () => {
    expect(invalidationContracts.opportunityDeepParse).toEqual({
      owner: "breakdowns",
      operation: "opportunity.deepParse",
      direct: ["breakdownOpportunities", "breakdownHidden"],
      derived: ["breakdownReadiness", "breakdownMaterialMatches", "analyticsOperations", "analyticsIndustryTrends", "commandCenter"],
      forbidden: [
        "submissions", "workflowSelfTapes", "callbacks", "auditionPerformanceNotes", "calendarEvents", "journalEntries",
        "careerTasks", "breakdownRecommendations", "breakdownQueue", "relationships", "relationshipAnalytics", "materials",
        "reusableSelfTapes", "analyticsIntelligence", "analyticsMaterialPerformance", "dashboardPreferences", "executiveBriefs"
      ],
      timing: "synchronous",
      reason: expect.any(String)
    });
    expect(keysForContract(invalidationContracts.opportunityDeepParse)).toEqual([
      publicInvalidationKeys.breakdownOpportunities,
      publicInvalidationKeys.breakdownHidden,
      publicInvalidationKeys.breakdownReadiness,
      publicInvalidationKeys.breakdownMaterialMatches,
      publicInvalidationKeys.analyticsOperations,
      publicInvalidationKeys.analyticsIndustryTrends,
      publicInvalidationKeys.commandCenter
    ]);
  });

  it("records the exact reject/archive owner contract", () => {
    expect(invalidationContracts.opportunityReject).toEqual({
      owner: "breakdowns",
      operation: "opportunity.reject",
      direct: ["breakdownOpportunities", "breakdownHidden"],
      derived: ["breakdownReadiness", "breakdownMaterialMatches", "commandCenter"],
      forbidden: [
        "submissions", "workflowSelfTapes", "callbacks", "auditionPerformanceNotes", "calendarEvents", "journalEntries",
        "careerTasks", "breakdownRecommendations", "breakdownQueue", "relationships", "relationshipAnalytics", "materials",
        "reusableSelfTapes", "analyticsOperations", "analyticsIntelligence", "analyticsIndustryTrends",
        "analyticsMaterialPerformance", "dashboardPreferences", "executiveBriefs"
      ],
      timing: "synchronous",
      reason: expect.any(String)
    });
    expect(keysForContract(invalidationContracts.opportunityReject)).toEqual([
      publicInvalidationKeys.breakdownOpportunities,
      publicInvalidationKeys.breakdownHidden,
      publicInvalidationKeys.breakdownReadiness,
      publicInvalidationKeys.breakdownMaterialMatches,
      publicInvalidationKeys.commandCenter
    ]);
  });

  it("records recommendation feedback as command-center-derived without refetching unchanged recommendations", () => {
    expect(invalidationContracts.recommendationFeedbackCreate).toEqual({
      owner: "breakdowns",
      operation: "recommendation.feedbackCreate",
      direct: [],
      derived: ["commandCenter"],
      forbidden: [
        "submissions", "workflowSelfTapes", "callbacks", "auditionPerformanceNotes", "calendarEvents", "journalEntries",
        "careerTasks", "breakdownOpportunities", "breakdownHidden", "breakdownRecommendations", "breakdownQueue",
        "breakdownReadiness", "breakdownMaterialMatches", "relationships", "relationshipAnalytics", "materials",
        "reusableSelfTapes", "analyticsOperations", "analyticsIntelligence", "analyticsIndustryTrends",
        "analyticsMaterialPerformance", "dashboardPreferences", "executiveBriefs"
      ],
      timing: "synchronous",
      reason: expect.any(String)
    });
    expect(keysForContract(invalidationContracts.recommendationFeedbackCreate)).toEqual([
      publicInvalidationKeys.commandCenter
    ]);
  });

  it("keeps create distinct from update because create writes Journal and Calendar records", () => {
    expect(invalidationContracts.opportunityCreate.derived).toContain("journalEntries");
    expect(invalidationContracts.opportunityCreate.derived).toContain("calendarEvents");
    expect(invalidationContracts.opportunityUpdate.forbidden).toContain("journalEntries");
    expect(invalidationContracts.opportunityUpdate.forbidden).toContain("calendarEvents");
  });

  it("does not turn a successful mutation into a failure when a derived refetch rejects", async () => {
    const client = new QueryClient();
    vi.spyOn(client, "invalidateQueries").mockRejectedValue(new Error("derived route unavailable"));
    expect(() => invalidateInBackground(client, [publicInvalidationKeys.analyticsOperations])).not.toThrow();
    await Promise.resolve();
  });
});
