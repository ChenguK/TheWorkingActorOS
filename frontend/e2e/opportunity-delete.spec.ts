import { expect, test } from "@playwright/test";
import { createMockState, hiddenOpportunityFixture, installMockApi, linkedSubmissionFixture } from "./support/mockApi";

test("protected opportunity delete preserves linked history and shows the contract error", async ({ page }) => {
  const hidden = hiddenOpportunityFixture();
  const state = createMockState({ hiddenOpportunities: [hidden], submissions: [linkedSubmissionFixture(hidden)] });
  await installMockApi(page, state);
  await page.goto("/breakdowns");
  await page.getByRole("button", { name: "Travel Exceptions / Needs Review" }).click();
  await expect(page.getByText("Hidden Detective").first()).toBeVisible();
  await page.getByRole("button", { name: "Delete", exact: true }).click();
  await expect(page.getByText(/Opportunities with linked submissions cannot be deleted/)).toBeVisible();
  const beforeDelete = state.requests.length;
  await page.getByRole("button", { name: "Confirm" }).click();
  await expect(page.getByRole("alert")).toHaveText("This opportunity cannot be permanently deleted because it has linked submissions. Reject or archive it instead.");
  await expect(page.getByText("Hidden Detective").first()).toBeVisible();
  expect(state.hiddenOpportunities).toHaveLength(1);
  expect(state.submissions).toHaveLength(1);
  expect(state.requests.slice(beforeDelete)).toEqual(["DELETE /opportunities/opp-hidden"]);
});

test("unlinked opportunity delete still succeeds with focused refreshes", async ({ page }) => {
  const hidden = hiddenOpportunityFixture("opp-unlinked");
  const state = createMockState({ hiddenOpportunities: [hidden] });
  await installMockApi(page, state);
  await page.goto("/breakdowns");
  await page.getByRole("button", { name: "Travel Exceptions / Needs Review" }).click();
  await page.getByRole("button", { name: "Delete", exact: true }).click();
  await page.getByRole("button", { name: "Confirm" }).click();
  await expect(page.getByText("Hidden Detective")).toHaveCount(0);
  expect(state.hiddenOpportunities).toHaveLength(0);
  expect(state.requests.filter((request) => request === "GET /dashboard/widgets")).toHaveLength(0);
});

test("hidden update refreshes its owners without persisted Calendar or broad requests", async ({ page }) => {
  const hidden = hiddenOpportunityFixture();
  const state = createMockState({ hiddenOpportunities: [hidden] });
  await installMockApi(page, state);
  await page.goto("/breakdowns");
  await page.getByRole("button", { name: "Travel Exceptions / Needs Review" }).click();
  await page.getByText("Complete").click();
  await page.getByLabel("Role Billing").fill("Series Regular");
  const start = state.requests.length;
  await page.getByRole("button", { name: "Save" }).click();
  await expect.poll(() => state.hiddenOpportunities[0].role_type).toBe("Series Regular");
  expect(state.workflowTapes).toHaveLength(1);
  expect(state.calendarEvents).toHaveLength(0);
  const requests = state.requests.slice(start);
  expect(requests.some((request) => request === "GET /dashboard/widgets")).toBe(false);
  expect(requests.some((request) => request === "GET /system/capabilities")).toBe(false);
});

test("hidden parse failure preserves its draft and surrounding workspace", async ({ page }) => {
  const hidden = hiddenOpportunityFixture();
  const state = createMockState({ hiddenOpportunities: [hidden], failPath: "/opportunities/opp-hidden/parse-breakdown-text" });
  await installMockApi(page, state);
  await page.goto("/breakdowns");
  await page.getByRole("button", { name: "Travel Exceptions / Needs Review" }).click();
  await page.getByText("View Details").click();
  await page.getByRole("button", { name: "Breakdown Viewer" }).click();
  await page.getByRole("button", { name: "Paste actual text" }).click();
  await page.getByLabel("Breakdown Text").fill("Retained browser draft");
  await page.getByRole("button", { name: "Save" }).click();
  await expect(page.getByRole("alert")).toHaveText("Deterministic domain failure");
  await expect(page.getByLabel("Breakdown Text")).toHaveValue("Retained browser draft");
  await expect(page.getByText("Hidden Detective").first()).toBeVisible();
});
