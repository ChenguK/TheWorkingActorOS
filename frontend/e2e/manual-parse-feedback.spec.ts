import { expect, test } from "@playwright/test";
import { createMockState, installMockApi } from "./support/mockApi";

test("visible manual parse reports local failure, preserves its draft, and retries without a broad refresh", async ({ page }) => {
  const path = "/opportunities/opp-1/parse-breakdown-text";
  const state = createMockState({ failPath: path, delayPath: path, delayMs: 300 });
  await installMockApi(page, state);
  await page.goto("/breakdowns");
  await page.getByRole("button", { name: "Expand breakdown" }).click();
  await page.getByRole("button", { name: "Raw / Pasted Breakdown Text" }).click();
  const trigger = page.getByRole("button", { name: "Paste Actual Breakdown Text" });
  await trigger.click();
  const textarea = page.getByLabel("Breakdown Text");
  await expect(textarea).toBeFocused();
  await textarea.fill("Visible retained browser draft");
  const start = state.requests.length;

  await page.getByRole("button", { name: "Re-run Parsing" }).click();
  await expect(page.getByRole("status")).toHaveText("Re-running breakdown parsing…");
  await expect(page.getByRole("button", { name: "Parsing…" })).toBeDisabled();
  await expect(page.getByRole("alert")).toHaveText("Deterministic domain failure");
  await expect(textarea).toHaveValue("Visible retained browser draft");
  await expect(page.getByText("Detective · Spring Forward").first()).toBeVisible();

  state.failPath = undefined;
  await page.getByRole("button", { name: "Re-run Parsing" }).click();
  await expect(page.getByLabel("Breakdown Text")).not.toBeVisible();
  await expect(page.getByRole("button", { name: "Paste Actual Breakdown Text" })).toBeFocused();
  await expect(page.getByText("Visible retained browser draft").first()).toBeVisible();

  const requests = state.requests.slice(start);
  expect(requests.filter((request) => request === `POST ${path}`)).toHaveLength(2);
  for (const request of [
    "GET /opportunities",
    "GET /automation/opportunities/hidden",
    "GET /intelligence/readiness/opportunities",
    "GET /opportunities/material-matches?include_hidden=false&min_score=15"
  ]) {
    expect(requests.filter((item) => item === request)).toHaveLength(1);
  }
  expect(requests).not.toEqual(expect.arrayContaining([
    "GET /journal",
    "GET /operations/calendar/events",
    "GET /submissions",
    "GET /dashboard/widgets"
  ]));
});
