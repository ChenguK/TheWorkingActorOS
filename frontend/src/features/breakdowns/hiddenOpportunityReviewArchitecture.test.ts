import { describe, expect, it } from "vitest";

const files = import.meta.glob<string>(["./index.ts", "./components/BreakdownDiscovery.tsx", "./components/HiddenOpportunityReview.tsx"], { eager: true, import: "default", query: "?raw" });
const read = (suffix: string) => Object.entries(files).find(([path]) => path.endsWith(suffix))?.[1] ?? "";

describe("hidden opportunity review architecture", () => {
  it("keeps the workspace route-private and parent composition narrow", () => {
    const barrel = read("index.ts");
    const parent = read("BreakdownDiscovery.tsx");
    const child = read("HiddenOpportunityReview.tsx");
    expect(barrel).not.toMatch(/HiddenOpportunityReview|HiddenOpportunityActionForm/);
    expect(parent).toContain("<HiddenOpportunityReview hiddenOpportunities={hiddenOpportunities} />");
    expect(parent).not.toMatch(/selectedHiddenOpportunity|hiddenAction|useDeleteBreakdown|useApproveBreakdown/);
    expect(child).not.toMatch(/useHiddenBreakdowns|api\.|fetch\(|queryClient|discoveryStatus|discoveryReport/);
    expect(child).toMatch(/selectedId/);
    expect(child).not.toMatch(/useState<Opportunity/);
  });
});
