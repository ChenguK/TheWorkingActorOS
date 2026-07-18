import { describe, expect, it } from "vitest";
import { queryPolicyInventory } from "./queryPolicyInventory";
import { queryStaleTimes } from "./queryPolicy";

describe("query policy inventory", () => {
  it("documents every owner with explicit freshness and consequences", () => {
    const owners = new Set(queryPolicyInventory.map((entry) => entry.owner));
    for (const owner of ["system", "chief-of-staff", "calendar", "dashboard", "profile", "materials", "relationships", "analytics", "auditions", "breakdowns", "journal", "career-intelligence", "source-library", "script-finder"]) {
      expect(owners.has(owner)).toBe(true);
    }
    expect(queryPolicyInventory.every((entry) => entry.endpoints.length > 0 && entry.consumers.length > 0 && entry.staleConsequence && entry.requestConsequence)).toBe(true);
  });

  it("keeps live operational queries short and forced on route entry", () => {
    const command = queryPolicyInventory.find((entry) => entry.family === "chief.commandCenter");
    const calendar = queryPolicyInventory.find((entry) => entry.family === "calendar.events");
    expect(command).toMatchObject({ staleTime: queryStaleTimes.live, refetchOnMount: "always" });
    expect(calendar).toMatchObject({ staleTime: queryStaleTimes.live, refetchOnMount: "always" });
  });

  it("does not force fresh configuration and reference queries to refetch", () => {
    for (const family of ["dashboard.preferences", "analytics.industryTrends", "analytics.derived", "journal.entries", "scriptFinder.sources"]) {
      expect(queryPolicyInventory.find((entry) => entry.family === family)?.refetchOnMount).toBe("stale");
    }
  });

  it("retains forced freshness for external, asynchronous, and live families", () => {
    for (const family of ["chief.commandCenter", "calendar.events", "auditions.workflow", "breakdowns.workflow", "career.records", "sourceLibrary.records"]) {
      expect(queryPolicyInventory.find((entry) => entry.family === family)?.refetchOnMount).toBe("always");
    }
  });

  it("retains the global ten-minute garbage-collection budget", () => {
    expect(new Set(queryPolicyInventory.map((entry) => entry.gcTime))).toEqual(new Set([10 * 60_000]));
  });
});
