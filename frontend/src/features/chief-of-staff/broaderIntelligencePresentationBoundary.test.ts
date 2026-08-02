import { describe, expect, it } from "vitest";

const sources = import.meta.glob<string>(
  [
    "../../types/domain.ts",
    "../dashboard/components/DashboardPanel.tsx",
    "../breakdowns/api/index.ts",
    "../breakdowns/hooks/useBreakdownQueries.ts",
    "../breakdowns/components/BreakdownManager.tsx",
    "../breakdowns/components/BreakdownViewer.tsx",
    "../breakdowns/components/HiddenOpportunityReview.tsx",
    "../breakdowns/components/BreakdownReadiness.tsx",
    "../../pages/OpportunitiesPage.tsx",
    "../../pages/AuditionsPage.tsx",
    "../../pages/CalendarPage.tsx",
    "../../pages/MaterialsPage.tsx",
    "../../pages/JournalPage.tsx",
    "../../../e2e/request-graphs.spec.ts"
  ],
  { eager: true, import: "default", query: "?raw" }
);

const read = (path: string) => sources[path] ?? "";
const nonDashboardConsumers = Object.entries(sources)
  .filter(([path]) => !path.includes("DashboardPanel") && !path.endsWith("domain.ts"))
  .map(([, source]) => source)
  .join("\n");

describe("broader Opportunity Intelligence presentation boundary", () => {
  it("keeps the versioned summary owned by the Dashboard presentation", () => {
    const domain = read("../../types/domain.ts");
    const dashboard = read("../dashboard/components/DashboardPanel.tsx");

    expect(domain).toContain("export type OpportunityIntelligenceSummary");
    expect(dashboard).toContain("OpportunityIntelligenceSummary");
    expect(dashboard).toContain("OpportunityPriorityCard");
    expect(nonDashboardConsumers).not.toContain("OpportunityIntelligenceSummary");
    expect(nonDashboardConsumers).not.toMatch(/\.intelligence\??\.(?:version|overall_score)/);
  });

  it("does not add a command-center join to Breakdown or workflow consumers", () => {
    const breakdownSources = [
      read("../breakdowns/api/index.ts"),
      read("../breakdowns/hooks/useBreakdownQueries.ts"),
      read("../breakdowns/components/BreakdownManager.tsx"),
      read("../breakdowns/components/HiddenOpportunityReview.tsx")
    ].join("\n");

    expect(breakdownSources).not.toContain("useCommandCenter");
    expect(breakdownSources).not.toContain("commandCenterKey");
    expect(breakdownSources).not.toMatch(/command-center\/(?:intelligence|scores)/);
    expect(read("../../pages/AuditionsPage.tsx")).not.toContain("useCommandCenter");
    expect(read("../../pages/MaterialsPage.tsx")).not.toContain("useCommandCenter");
    expect(read("../../pages/JournalPage.tsx")).not.toContain("useCommandCenter");
  });

  it("preserves the current page request graph and Calendar-only operational reuse", () => {
    const requestGraphs = read("../../../e2e/request-graphs.spec.ts");
    const calendar = read("../../pages/CalendarPage.tsx");

    expect(requestGraphs).toContain('["GET /command-center"]).toBe(1)');
    expect(requestGraphs).not.toMatch(/command-center\/(?:intelligence|scores|history)/);
    expect(calendar).toContain("useCommandCenter");
    expect(calendar).not.toContain("OpportunityIntelligenceSummary");
    expect(calendar).not.toMatch(/\.intelligence\??\./);
  });
});
