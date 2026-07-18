import { describe, expect, it } from "vitest";
import { queryKeys } from "./queryKeys";

describe("queryKeys", () => {
  it("creates deterministic feature list and detail keys", () => {
    expect(queryKeys.materials.all).toEqual(["materials"]);
    expect(queryKeys.materials.detail("asset-1")).toEqual(["materials", "detail", "asset-1"]);
    expect(queryKeys.journal.list({ date: "2026-07-16", type: "Audition" })).toEqual([
      "journal",
      "list",
      { date: "2026-07-16", type: "Audition" }
    ]);
    expect(queryKeys.journal.list({ date: "2026-07-16", type: "Audition" })).toEqual(
      queryKeys.journal.list({ date: "2026-07-16", type: "Audition" })
    );
  });

  it("provides factories for every planned feature boundary", () => {
    expect(Object.keys(queryKeys)).toEqual([
      "system",
      "journal",
      "calendar",
      "materials",
      "relationships",
      "auditions",
      "sourceLibrary",
      "scriptFinder",
      "breakdowns",
      "analytics",
      "career",
      "dashboard",
      "chiefOfStaff",
      "profile",
      "settings"
    ]);
  });

  it("keeps feature list and detail keys distinct", () => {
    expect(queryKeys.journal.list()).not.toEqual(queryKeys.journal.detail("journal-1"));
    expect(queryKeys.journal.list()).not.toEqual(queryKeys.calendar.list());
    expect(queryKeys.materials.detail("shared-id")).not.toEqual(queryKeys.profile.detail("shared-id"));
  });
});
