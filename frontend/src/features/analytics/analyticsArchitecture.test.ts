import { describe, expect, it } from "vitest";

const analyticsComponents = import.meta.glob<string>("./components/*.tsx", { eager: true, import: "default", query: "?raw" });
const consumers = import.meta.glob<string>(["../dashboard/components/*.tsx", "../career-intelligence/components/*.tsx"], { eager: true, import: "default", query: "?raw" });
const componentText = Object.values(analyticsComponents).join("\n");
const consumerText = Object.values(consumers).join("\n");

describe("Analytics architecture", () => {
  it("keeps Analytics presentation behind public query hooks", () => {
    expect(componentText).not.toContain("onChanged");
    expect(componentText).not.toContain("loadWorkflowData");
    expect(componentText).not.toMatch(/services\/api(?:["']|\/index)/);
    expect(componentText).not.toMatch(/queryKey:\s*\[/);
  });

  it("keeps Dashboard and Career on the public Analytics barrel", () => {
    expect(consumerText).not.toMatch(/features\/analytics\/(?:api|hooks|components)/);
    expect(consumerText).not.toMatch(/\.\.\/analytics\/(?:api|hooks|components)/);
  });
});
