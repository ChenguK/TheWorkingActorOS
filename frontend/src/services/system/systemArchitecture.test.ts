import { describe, expect, it } from "vitest";
const sources = import.meta.glob<string>(["./**/*.{ts,tsx}", "../../features/settings/{components,hooks}/**/*.{ts,tsx}"], { eager: true, import: "default", query: "?raw" });
describe("system capabilities architecture", () => {
  it("keeps capabilities infrastructure-owned and out of global workflow data", () => {
    expect(sources["./useSystemCapabilities.ts"]).toContain("queryStaleTimes.configuration");
    expect(sources["./useSystemCapabilities.ts"]).toContain("refetchOnMount: false");
    expect(sources["./useSystemCapabilities.ts"]).toContain("refetchOnReconnect: true");
  });
  it("keeps Settings presentation and hooks free of broad refreshes and base API access", () => {
    const production = Object.entries(sources).filter(([path]) => path.includes("features/settings") && !path.includes(".test.")).map(([, source]) => source).join("\n");
    expect(production).not.toContain("onChanged");
    expect(production).not.toContain("loadWorkflowData");
    expect(production).not.toMatch(/queryKey:\s*\[/);
    expect(production).not.toMatch(/fetch\(|services\/api["']/);
  });
});
