import { expect, test } from "@playwright/test";
import { createMockState, installMockApi } from "./support/mockApi";

test("recommendation feedback avoids unchanged recommendation and inactive command-center refetches", async ({ page }) => {
  const state = await installMockApi(page, createMockState());
  await page.goto("/breakdowns");
  await page.getByRole("button", { name: "Expand breakdown" }).click();
  await page.getByRole("button", { name: "Generate strategy" }).click();
  await expect.poll(() => state.recommendations.length).toBe(1);
  await page.getByRole("button", { name: "Expand audition readiness" }).click();
  await expect(page.getByText("Optional feedback").first()).toBeVisible();
  const start = state.requests.length;

  await page.getByRole("button", { name: "Not My Type" }).first().click();
  await expect(page.getByText("Feedback saved. Future recommendations will learn from this.").first()).toBeVisible();
  await expect.poll(() => state.requests.slice(start)).toEqual([
    "POST /agents/recommendations/recommendation-1/feedback"
  ]);
});

test("recommendation feedback preserves its draft, prevents duplicates, restores focus, and retries", async ({ page }) => {
  const state = await installMockApi(page, createMockState());
  await page.goto("/breakdowns");
  await page.getByRole("button", { name: "Expand breakdown" }).click();
  await page.getByRole("button", { name: "Generate strategy" }).click();
  await expect.poll(() => state.recommendations.length).toBe(1);
  await page.getByRole("button", { name: "Expand audition readiness" }).click();
  await page.getByRole("button", { name: "This Fits Me" }).click();
  await page.getByRole("checkbox", { name: "Authority" }).check();
  const start = state.requests.length;
  state.delayPath = "/feedback";
  state.delayMs = 300;
  state.failPath = "/feedback";

  await page.getByRole("button", { name: "Save Feedback" }).evaluate((button) => {
    (button as HTMLButtonElement).click();
    (button as HTMLButtonElement).click();
  });
  await expect(page.getByText("Saving feedback…")).toHaveAttribute("role", "status");
  await expect(page.getByRole("button", { name: "Save Feedback" })).toBeDisabled();
  await expect(page.getByRole("alert")).toContainText("Deterministic domain failure");
  await expect(page.getByRole("checkbox", { name: "Authority" })).toBeChecked();
  await expect(page.getByRole("button", { name: "Save Feedback" })).toBeFocused();
  expect(state.requests.slice(start)).toEqual(["POST /agents/recommendations/recommendation-1/feedback"]);

  state.delayPath = undefined;
  state.failPath = undefined;
  await page.getByRole("button", { name: "Save Feedback" }).click();
  await expect(page.getByText("Feedback saved. Future recommendations will learn from this.")).toBeVisible();
  await expect(page.getByRole("button", { name: "This Fits Me" })).toBeFocused();
  await expect(page.getByRole("checkbox", { name: "Authority" })).toHaveCount(0);
  expect(state.requests.slice(start)).toEqual([
    "POST /agents/recommendations/recommendation-1/feedback",
    "POST /agents/recommendations/recommendation-1/feedback"
  ]);
});
