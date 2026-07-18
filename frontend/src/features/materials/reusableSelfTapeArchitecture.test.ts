import { describe, expect, it } from "vitest";

const presentation = import.meta.glob<string>(["./components/*SelfTape*.tsx", "./hooks/useSelfTapeLibrary.ts", "./hooks/useReusableSelfTapes.ts"], { eager: true, import: "default", query: "?raw" });
const boundaries = import.meta.glob<string>(["./components/MaterialsPanel.tsx"], { eager: true, import: "default", query: "?raw" });
const reusable = import.meta.glob<string>(["./**/*.ts", "./**/*.tsx"], { eager: true, import: "default", query: "?raw" });
const workflow = import.meta.glob<string>(["../auditions/**/*.ts", "../auditions/**/*.tsx"], { eager: true, import: "default", query: "?raw" });

describe("reusable self-tape architecture", () => {
  it("keeps network ownership in the Materials API module", () => {
    const source = Object.entries(presentation).filter(([path]) => !path.includes(".test.")).map(([, text]) => text).join("\n");
    expect(source).not.toMatch(/services\/api["']|api\.(get|post|put|patch|delete)|\bfetch\s*\(|\/intelligence\/self-tapes/);
    expect(source).not.toMatch(/features\/auditions\/(api|hooks|components)/);
    expect(source).not.toContain("onChanged");
    expect(source).not.toContain("loadWorkflowData");
  });

  it("removes reusable server props and both global snapshots", () => {
    const panel = presentation["./components/SelfTapeLibraryPanel.tsx"];
    expect(panel).not.toMatch(/selfTapeLibrary\s*:/);
    expect(panel).not.toMatch(/selfTapeAnalytics\s*:/);
    const global = Object.values(boundaries).join("\n");
    expect(global).not.toMatch(/\bselfTapeLibrary\s*:/);
    expect(global).not.toMatch(/\bselfTapeAnalytics\s*:/);
  });

  it("keeps reusable and workflow self-tape internals separated", () => {
    expect(Object.values(reusable).join("\n")).not.toMatch(/features\/auditions\/(api|hooks|components)|\.\.\/auditions\/(api|hooks|components)/);
    expect(Object.values(workflow).join("\n")).not.toMatch(/features\/materials\/(api|hooks|components)|\.\.\/materials\/(api|hooks|components)/);
  });
});
