import { expect, test } from "@playwright/test";
import { createMockState, installMockApi } from "./support/mockApi";

function requestCounts(requests: string[]) {
  return requests.reduce<Record<string, number>>((counts, request) => {
    counts[request] = (counts[request] ?? 0) + 1;
    return counts;
  }, {});
}

test("deep parse uses its focused owner request graph", async ({ page }) => {
  const state = await installMockApi(page);
  await page.goto("/breakdowns");
  await page.getByRole("button", { name: "Expand breakdown" }).click();
  const start = state.requests.length;

  await page.getByRole("button", { name: "Run deep parse" }).first().click();
  await expect.poll(() => requestCounts(state.requests.slice(start))["GET /opportunities"] ?? 0).toBe(1);
  await expect(page.getByText("Spring Forward").first()).toBeVisible();

  const counts = requestCounts(state.requests.slice(start));
  expect(counts).toEqual({
    "POST /opportunities/opp-1/deep-parse": 1,
    "GET /opportunities": 1,
    "GET /automation/opportunities/hidden": 1,
    "GET /intelligence/readiness/opportunities": 1,
    "GET /opportunities/material-matches?include_hidden=false&min_score=15": 1
  });
  expect(Object.keys(counts).some((request) => /journal|calendar|self-tapes|intelligence\/dashboard/.test(request))).toBe(false);
});

test("visible deep parse reports local failure, prevents duplicates, restores focus, and retries", async ({ page }) => {
  const path = "/opportunities/opp-1/deep-parse";
  const state = createMockState({ failPath: path, delayPath: path, delayMs: 300 });
  await installMockApi(page, state);
  await page.goto("/breakdowns");
  await page.getByRole("button", { name: "Expand breakdown" }).click();
  await page.getByRole("button", { name: "Breakdown Viewer" }).click();
  const triggers = page.getByRole("button", { name: "Run deep parse" });
  await expect(triggers).toHaveCount(2);
  const first = triggers.first();
  const start = state.requests.length;

  await first.click();
  await expect(page.getByRole("status")).toHaveText("Deep parsing Spring Forward…");
  await expect(triggers.nth(0)).toBeDisabled();
  await expect(triggers.nth(1)).toBeDisabled();
  await expect(page.getByRole("alert")).toHaveText("Deterministic domain failure");
  await expect(first).toBeFocused();
  expect(state.requests.slice(start).filter((request) => request === `POST ${path}`)).toHaveLength(1);
  await expect(page.getByText("Detective · Spring Forward").first()).toBeVisible();

  state.failPath = undefined;
  await first.click();
  await expect(page.getByRole("alert")).not.toBeVisible();
  await expect(page.getByText("Deep parse completed")).toBeVisible();
  await expect(page.getByRole("button", { name: "Collapse breakdown" })).toBeFocused();

  const counts = requestCounts(state.requests.slice(start));
  expect(counts).toEqual({
    [`POST ${path}`]: 2,
    "GET /opportunities": 1,
    "GET /automation/opportunities/hidden": 1,
    "GET /intelligence/readiness/opportunities": 1,
    "GET /opportunities/material-matches?include_hidden=false&min_score=15": 1
  });
});
