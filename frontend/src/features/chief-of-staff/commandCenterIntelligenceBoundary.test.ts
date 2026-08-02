import { describe, expect, it } from "vitest";

const sources = import.meta.glob<string>(
  [
    "../../types/domain.ts",
    "./api/index.ts",
    "./hooks/useCommandCenter.ts",
    "../dashboard/components/DashboardPanel.tsx",
    "../../../e2e/support/mockApi.ts",
    "../../../e2e/request-graphs.spec.ts"
  ],
  { eager: true, import: "default", query: "?raw" }
);

const intelligenceNames = [
  "intelligence_version",
  "overall_score",
  "suggested_action",
  "action_reason_code",
  "positive_contributors",
  "negative_contributors",
  "hard_override_reason",
  "ranking_position",
  "scoring_context"
];

describe("command-center intelligence API boundary", () => {
  it("keeps current frontend production types and consumers intelligence-free", () => {
    const domain = sources["../../types/domain.ts"];
    const api = sources["./api/index.ts"];
    const hook = sources["./hooks/useCommandCenter.ts"];
    const dashboard = sources["../dashboard/components/DashboardPanel.tsx"];

    expect(domain).toContain("export type CommandCenterCard = Record<string, string | number | null | undefined>");
    expect(domain).toContain("today_opportunities: CommandCenterCard[]");
    expect(api).toContain('api.get<ActorCommandCenter>("/command-center")');
    expect(api).not.toMatch(/command-center.*intelligence|intelligence.*command-center/i);
    expect(hook).toContain("queryFn: getCommandCenter");
    expect(dashboard).toContain('`${item.role ?? "Role"} · ${item.project ?? "Project"}`');
    for (const field of intelligenceNames) {
      expect(`${domain}\n${api}\n${hook}\n${dashboard}`).not.toContain(field);
    }
  });

  it("keeps strict Playwright request and response fixtures on the current contract", () => {
    const mockApi = sources["../../../e2e/support/mockApi.ts"];
    const requestGraphs = sources["../../../e2e/request-graphs.spec.ts"];

    expect(mockApi).toContain('"GET /command-center"');
    expect(mockApi).toContain('path === "/command-center" && method === "GET"');
    expect(mockApi).toContain("today_opportunities: []");
    expect(requestGraphs).toContain('["GET /command-center"]).toBe(1)');
    expect(`${mockApi}\n${requestGraphs}`).not.toMatch(
      /command-center\/(?:intelligence|scores|history)/
    );
    for (const field of intelligenceNames) {
      expect(mockApi).not.toContain(field);
    }
  });

  it("documents runtime additive-field tolerance without requiring it in current types", () => {
    const oldCard = { role: "Detective", project: "Fictional Procedural" };
    const additiveCard = {
      ...oldCard,
      intelligence: { version: 1, overall_score: 87 }
    };
    const currentLabel = (item: Record<string, unknown>) =>
      `${item.role ?? "Role"} · ${item.project ?? "Project"}`;

    expect(currentLabel(additiveCard)).toBe(currentLabel(oldCard));
    expect(Object.keys(oldCard)).not.toContain("intelligence");
  });
});
