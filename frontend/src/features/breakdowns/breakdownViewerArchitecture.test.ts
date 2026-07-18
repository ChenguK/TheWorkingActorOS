import { describe, expect, it } from "vitest";

const modules = import.meta.glob<string>(
  ["./components/*.{ts,tsx}", "./index.ts"],
  { eager: true, import: "default", query: "?raw" }
);

describe("BreakdownViewer route-private boundary", () => {
  it("keeps the approved exact contract and local display ownership", () => {
    const viewer = modules["./components/BreakdownViewer.tsx"];
    expect(viewer).toContain("opportunity: Opportunity");
    expect(viewer).toContain("onRunDeepParse: () => Promise<void>");
    expect(viewer).toContain("onPasteText: () => void");
    expect(viewer).toContain("onManualAddRole: () => void | Promise<void>");
    expect(viewer).toContain("useState<BreakdownViewerSectionId>");
    expect(viewer).not.toMatch(/use(?:Breakdowns|Breakdown|Mutation|Query|QueryClient)\s*\(/);
    expect(viewer).not.toMatch(/services\/api|queryKey|QueryClient|\bfetch\s*\(|\bapi\./);
  });

  it("is route-private with one-way dependencies and direct callers", () => {
    const publicBarrel = modules["./index.ts"];
    const details = modules["./components/BreakdownDetails.tsx"];
    const manager = modules["./components/BreakdownManager.tsx"];
    const hiddenReview = modules["./components/HiddenOpportunityReview.tsx"];
    expect(publicBarrel).not.toContain("BreakdownViewer");
    expect(details).not.toContain('from "./BreakdownViewer"');
    expect(manager).toContain('from "./BreakdownViewer"');
    expect(hiddenReview).toContain('from "./BreakdownViewer"');
    expect(manager).not.toContain("export function BreakdownViewer");
    expect(hiddenReview).not.toContain("export function BreakdownViewer");
  });
});
