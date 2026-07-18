import { describe, expect, it } from "vitest";

const presentationModules = import.meta.glob<string>(
  ["./components/**/*.{ts,tsx}", "./hooks/**/*.{ts,tsx}"],
  { eager: true, import: "default", query: "?raw" }
);
const presentationSources = Object.entries(presentationModules)
  .filter(([filename]) => !/\.(?:test|spec)\.(?:ts|tsx)$/.test(filename));

describe("Breakdowns presentation network boundary", () => {
  it("does not import the base API client or make raw requests", () => {
    for (const [filename, source] of presentationSources) {
      expect(source, filename).not.toMatch(/from\s+["'][^"']*services\/api(?:\/client)?["']/);
      expect(source, filename).not.toMatch(/\bapi\.(?:get|post|put|patch|delete)\s*\(/);
      expect(source, filename).not.toMatch(/\bfetch\s*\(/);
    }
  });

  it("does not embed backend request paths", () => {
    for (const [filename, source] of presentationSources) {
      expect(source, filename).not.toMatch(/["'`]\/(?:agents|automation|opportunities)(?:\/|[?"'`])/);
    }
  });

  it("keeps Track audition as navigation into the Auditions workflow", () => {
    const manager = presentationModules["./components/BreakdownManager.tsx"];
    expect(manager).toContain("/auditions?breakdownId=${opportunity.id}");
    expect(manager).toMatch(/>Track audition<\/a>/);
  });

  it("keeps the route-only submission queue presentation out of the public barrel", () => {
    const publicBarrel = import.meta.glob<string>("./index.ts", { eager: true, import: "default", query: "?raw" })["./index.ts"];
    expect(publicBarrel).not.toContain("SubmissionQueuePanel");
  });

  it("keeps the opportunity form route-private with narrow ownership", () => {
    const publicBarrel = import.meta.glob<string>("./index.ts", { eager: true, import: "default", query: "?raw" })["./index.ts"];
    const workspace = presentationModules["./components/OpportunityFormWorkspace.tsx"];
    const manager = presentationModules["./components/BreakdownManager.tsx"];
    expect(publicBarrel).not.toContain("OpportunityFormWorkspace");
    expect(workspace).toContain("mode: OpportunityFormMode");
    expect(workspace).toContain("opportunities: Opportunity[]");
    expect(workspace).toContain("representations: Representation[]");
    expect(workspace).not.toMatch(/use(?:Breakdowns|Representations)\s*\(/);
    expect(workspace).not.toMatch(/QueryClient|queryKey/);
    expect(manager).not.toContain("useCreateBreakdown");
    expect(manager).not.toMatch(/blankBreakdownForm|breakdownPayload|setEditingBreakdownId/);
  });
});
