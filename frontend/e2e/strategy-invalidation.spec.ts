import { expect, test } from "@playwright/test";
import { createMockState, installMockApi } from "./support/mockApi";

test("strategy generation refreshes exact active owners without a broad request burst", async ({ page }) => {
  const state = await installMockApi(page, createMockState());
  await page.goto("/breakdowns");
  await page.getByRole("button", { name: "Expand breakdown" }).click();
  const start = state.requests.length;

  await page.getByRole("button", { name: "Generate strategy" }).click();
  await expect.poll(() => state.requests.filter((request) => request === "GET /agents/recommendations").length).toBe(2);

  const requests = state.requests.slice(start);
  expect(requests).toEqual(expect.arrayContaining([
    "POST /opportunities/opp-1/recommend",
    "GET /agents/recommendations",
    "GET /opportunities",
    "GET /automation/opportunities/hidden"
  ]));
  expect(requests).not.toEqual(expect.arrayContaining([
    "GET /journal",
    "GET /operations/calendar/events",
    "GET /submissions",
    "GET /command-center/self-tapes",
    "GET /automation/submission-queue"
  ]));
});
