import { describe, expect, it } from "vitest";

const componentModules = import.meta.glob<string>("./components/*.tsx", { eager: true, import: "default", query: "?raw" });
const pageModules = import.meta.glob<string>("../../pages/Profile*.tsx", { eager: true, import: "default", query: "?raw" });
const production = [...Object.values(componentModules), ...Object.values(pageModules)].join("\n");

describe("Profile architecture", () => {
  it("does not accept global reload or removed workflow snapshots", () => {
    expect(production).not.toContain("onChanged");
    expect(production).not.toContain("onSaved");
    expect(production).not.toContain("loadWorkflowData");
    expect(production).not.toMatch(/<Profile(?:Setup)?Panel\s+data=/);
  });

  it("uses only the public Materials boundary", () => {
    expect(production).not.toMatch(/features\/materials\/(?:components|hooks|api)/);
    expect(production).not.toMatch(/\.\.\/\.\.\/materials\/(?:components|hooks|api)/);
    expect(production).not.toMatch(/queryKey:\s*\[\s*["']materials/);
  });
});
