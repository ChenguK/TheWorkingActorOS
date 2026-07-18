import { describe, expect, it } from "vitest";

const componentSource = import.meta.glob("./components/*.tsx", { eager: true, query: "?raw", import: "default" }) as Record<string, string>;
const hookSource = import.meta.glob("./hooks/*.ts", { eager: true, query: "?raw", import: "default" }) as Record<string, string>;

describe("Calendar form-only interaction architecture", () => {
  it("contains no drag, resize, or FullCalendar interaction plumbing", () => {
    const source = Object.entries(componentSource)
      .filter(([path]) => !path.endsWith(".test.tsx"))
      .map(([, contents]) => contents)
      .join("\n");
    expect(source).not.toContain("@fullcalendar/interaction");
    expect(source).not.toMatch(/eventDrop|eventResize|editable\s*=/);
    expect(source).toContain("Calendar editing is form-based");
  });

  it("keeps Calendar presentation off direct APIs and feature internals", () => {
    const source = Object.values(componentSource).join("\n");
    expect(source).not.toMatch(/services\/api(?:["'])/);
    expect(source).not.toMatch(/features\/(auditions|breakdowns|chief-of-staff)\/(components|hooks|api|utils)/);
    expect(source).not.toMatch(/\bfetch\s*\(/);
  });

  it("preserves the focused live query policy and exact invalidation", () => {
    const source = Object.entries(hookSource).find(([path]) => path.endsWith("useCalendarQueries.ts"))?.[1] ?? "";
    expect(source).toContain("staleTime: queryStaleTimes.live");
    expect(source).toContain('refetchOnMount: "always"');
    expect(source).toContain("invalidateInBackground(");
    expect(source).toContain("publicInvalidationKeys.analyticsOperations");
    expect(source).not.toMatch(/invalidateQueries\s*\(\s*\)/);
    expect(source).not.toMatch(/invalidateQueries\s*\(\s*\{\s*\}\s*\)/);
  });
});
