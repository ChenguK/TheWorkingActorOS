import { describe, expect, it } from "vitest";

const sourceLibraryModules = import.meta.glob<string>("./components/*.tsx", { eager: true, import: "default", query: "?raw" });
const breakdownModules = import.meta.glob<string>("../breakdowns/components/BreakdownsPanel.tsx", { eager: true, import: "default", query: "?raw" });
const panel = sourceLibraryModules["./components/SourceLibraryPanel.tsx"] ?? "";
const breakdownsPanel = breakdownModules["../breakdowns/components/BreakdownsPanel.tsx"] ?? "";

describe("Source Library architecture", () => {
  it("keeps production presentation behind query hooks", () => {
    expect(panel).not.toMatch(/from ["']\.\.\/api["']/);
    expect(panel).not.toMatch(/services\/api(?:["']|\/index)/);
    expect(panel).not.toContain("sourceResearchItems");
    expect(panel).not.toContain("onChanged");
    expect(panel).not.toContain("loadWorkflowData");
    expect(panel).not.toMatch(/\bfetch\s*\(/);
    expect(panel).not.toContain("/automation/source-research");
  });

  it("renders Source Library without workflow snapshot props", () => {
    expect(breakdownsPanel).toContain("<SourceLibraryPanel />");
    expect(breakdownsPanel).not.toMatch(/<SourceLibraryPanel[^>]+sourceResearchItems/);
    expect(breakdownsPanel).not.toMatch(/<SourceLibraryPanel[^>]+onChanged/);
  });
});
