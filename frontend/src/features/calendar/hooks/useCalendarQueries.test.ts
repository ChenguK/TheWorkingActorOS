import { describe, expect, it } from "vitest";
import { queryKeys } from "../../../services/api/queryKeys";
import { availabilityListKey, calendarEventListKey } from "./useCalendarQueries";

describe("Calendar query keys", () => {
  it("uses deterministic resource keys for the backend's unfiltered lists", () => {
    expect(calendarEventListKey).toEqual(queryKeys.calendar.list({ resource: "events" }));
    expect(availabilityListKey).toEqual(queryKeys.calendar.list({ resource: "availability" }));
    expect(calendarEventListKey).not.toEqual(availabilityListKey);
  });
});
