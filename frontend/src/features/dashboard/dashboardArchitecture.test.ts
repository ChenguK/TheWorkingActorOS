import { describe, expect, it } from "vitest";

const sources = import.meta.glob<string>(
  ["./{components,hooks}/**/*.{ts,tsx}"],
  { eager: true, import: "default", query: "?raw" }
);

describe("Dashboard query architecture", () => {
  it("contains no broad Dashboard refresh or presentation API access", () => {
    const production = Object.entries(sources).filter(([path]) => path.includes("/dashboard/") && !path.includes(".test.")).map(([, source]) => source).join("\n");
    expect(production).not.toContain("onChanged");
    expect(production).not.toContain("loadWorkflowData");
    expect(production).not.toMatch(/queryKey:\s*\[/);
    expect(production).not.toMatch(/fetch\(|services\/api["']/);
    expect(production).not.toContain('"/command-center"');
  });
});
