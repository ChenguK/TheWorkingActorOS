import { describe, expect, it } from "vitest";

const sources = import.meta.glob<string>(
  ["../../pages/{Calendar,Dashboard}Page.tsx", "../dashboard/components/DashboardPanel.tsx", "./{components,hooks}/**/*.{ts,tsx}"],
  { eager: true, import: "default", query: "?raw" }
);

describe("Chief of Staff command-center architecture", () => {
  it("exposes one public cache to Dashboard and Calendar", () => {
    expect(sources["../../pages/CalendarPage.tsx"]).toContain('from "@/features/chief-of-staff"');
    expect(sources["../dashboard/components/DashboardPanel.tsx"]).toContain('from "@/features/chief-of-staff"');
    expect(Object.values(sources).join("\n")).not.toMatch(/features\/chief-of-staff\/(api|hooks|components)/);
  });

  it("keeps command center out of global workflow state and broad refreshes", () => {
    const production = Object.entries(sources).filter(([path]) => path.includes("chief-of-staff") && !path.includes(".test.")).map(([, source]) => source).join("\n");
    expect(production).not.toContain("onChanged");
    expect(production).not.toContain("loadWorkflowData");
    expect(production).not.toMatch(/queryKey:\s*\[/);
  });
});
