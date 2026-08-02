import { expect, test } from "@playwright/test";
import { createMockState, installMockApi, opportunityFixture } from "./support/mockApi";

function upcomingNewYorkDate(daysAhead = 1) {
  const future = new Date(Date.now() + daysAhead * 24 * 60 * 60 * 1000);
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    year: "numeric",
    month: "2-digit",
    day: "2-digit"
  }).formatToParts(future);
  const value = (type: "year" | "month" | "day") => parts.find((part) => part.type === type)?.value;
  return `${value("year")}-${value("month")}-${value("day")}`;
}

test("Calendar is form-only and a Calendar-owned DST event persists", async ({ page }) => {
  const opportunity = { ...opportunityFixture(), audition_deadline: `${upcomingNewYorkDate()}T10:30:00` };
  const state = await installMockApi(page, createMockState({ opportunities: [opportunity] }));
  await page.goto("/calendar");
  await expect(page.getByText(/Calendar editing is form-based/)).toBeVisible();
  const projectedEvents = page.locator(".fc-event");
  await expect(projectedEvents.first()).toHaveAttribute("data-calendar-interaction", "form-only");
  expect(await projectedEvents.evaluateAll((items) => items.every((item) => !item.hasAttribute("draggable")))).toBe(true);
  await expect(page.locator(".fc-event-resizer")).toHaveCount(0);

  await page.getByLabel("Event Title").fill("Fall-back rehearsal");
  await page.getByLabel("Starts").fill("2030-11-03T01:30");
  await page.getByLabel("Ends").fill("2030-11-03T02:30");
  await page.getByRole("button", { name: "Create Calendar Event" }).click();
  await expect.poll(() => state.calendarEvents.length).toBe(1);
  expect(state.calendarEvents[0]).toMatchObject({ start_datetime: "2030-11-03T01:30", end_datetime: "2030-11-03T02:30" });
  const item = page.locator("article", { hasText: "Fall-back rehearsal" });
  await expect(item.getByText(/Calendar-owned/)).toBeVisible();
  await item.getByRole("button", { name: "Edit Calendar Event" }).click();
  await item.getByLabel("Event Title").fill("Fall-back rehearsal updated");
  const beforeSave = state.requests.length;
  await item.getByRole("button", { name: "Save" }).click();
  await expect.poll(() => String(state.calendarEvents[0].title)).toBe("Fall-back rehearsal updated");
  const saveRequests = state.requests.slice(beforeSave);
  expect(saveRequests.filter((request) => request.startsWith("PATCH /operations/calendar/events/"))).toHaveLength(1);
  expect(saveRequests.some((request) => request.includes("/workflow"))).toBe(false);
  expect(saveRequests.some((request) => request.includes("/submissions"))).toBe(false);

  await page.getByRole("link", { name: "Materials" }).click();
  await page.getByRole("link", { name: "Calendar" }).click();
  await expect(page.getByText("Fall-back rehearsal updated").first()).toBeVisible();
});

test("linked workflow Calendar rows and derived deadlines are read-only", async ({ page }) => {
  const upcomingDate = upcomingNewYorkDate();
  const linked = {
    id: "calendar-linked", title: "Linked workflow deadline", event_type: "Self-Tape Due",
    start_datetime: `${upcomingDate}T09:00:00`, end_datetime: null, opportunity_id: "opp-1",
    submission_id: null, is_virtual: true, created_at: "2026-03-01", updated_at: "2026-03-01"
  };
  const opportunity = { ...opportunityFixture(), audition_deadline: `${upcomingDate}T10:30:00` };
  const state = await installMockApi(page, createMockState({ calendarEvents: [linked], opportunities: [opportunity] }));
  await page.goto("/calendar");
  const item = page.locator("article", { hasText: "Linked workflow deadline" });
  await expect(item.getByText(/Read-only linked workflow event/)).toBeVisible();
  await expect(item.getByRole("button", { name: /Edit Calendar Event/ })).toHaveCount(0);
  await expect(item.getByRole("button", { name: /Delete Calendar Event/ })).toHaveCount(0);
  await expect(page.getByLabel(/Tape due: DST Detective/)).toContainText("");
  const mutationCount = state.requests.filter((request) => /^(PATCH|DELETE) \/operations\/calendar\/events/.test(request)).length;
  expect(mutationCount).toBe(0);
});
