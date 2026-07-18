import { describe, expect, it } from "vitest";

const sources = import.meta.glob<string>(
  ["./JournalPage.tsx", "../features/journal/hooks/*.ts"],
  { eager: true, import: "default", query: "?raw" }
);

describe("Journal query migration boundary", () => {
  it("keeps JournalPage thin and independent of Journal WorkflowPageData", () => {
    const page = sources["./JournalPage.tsx"];
    expect(page).not.toContain("actorJournalEntries");
    expect(page).not.toContain("onChanged");
    expect(page).not.toContain("useQuery");
  });

  it("does not broadly reload WorkflowPageData after Journal mutations", () => {
    const hook = sources["../features/journal/hooks/useJournalEntries.ts"];
    expect(hook).not.toContain("loadWorkflowData");
    expect(hook).not.toContain("onChanged");
    expect(hook).not.toContain("new QueryClient");
    expect(hook).not.toContain("app/queryClient");
    expect(hook).toContain("queryKeys.journal.lists()");
    expect(hook).toContain("services/api/queryPolicy");
    expect(hook).toContain('from "../api"');
  });

});
