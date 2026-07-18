import { expect, test, type Page } from "@playwright/test";
import { createMockState, installMockApi, opportunityFixture } from "./support/mockApi";

async function fillRequired(page: Page, role = "Neighbor") {
  await page.getByRole("textbox", { name: "Role", exact: true }).fill(role);
  await page.getByRole("textbox", { name: "Project", exact: true }).fill("Visible Pilot");
  await page.getByLabel("Shoot Location").fill("New York, NY");
  await page.getByLabel("Character Breakdown").fill("Comedy neighbor role");
}

async function openCreate(page: Page) {
  await expect(page.getByRole("heading", { name: "Add Breakdown" })).toBeVisible();
}

test("opportunity create succeeds with Step 52A owners and no broad refresh", async ({ page }) => {
  const state = createMockState(); await installMockApi(page, state); await page.goto("/breakdowns");
  await openCreate(page); await fillRequired(page);
  await page.getByLabel("Audition/Tape Due Date").fill("2026-08-01T18:00");
  const start = state.requests.length; await page.getByRole("button", { name: "Create Breakdown" }).click();
  await expect(page.getByText("Neighbor").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Add Breakdown" })).toHaveCount(0);
  expect(state.workflowTapes).toHaveLength(1); expect(state.calendarEvents).toHaveLength(1);
  expect(state.actorJournal).toHaveLength(1); expect(state.actorJournal[0].event_type).toBe("Accepted Breakdown");
  const requests = state.requests.slice(start);
  expect(requests.filter((item) => item === "POST /opportunities")).toHaveLength(1);
  expect(requests.some((item) => item === "GET /submissions" || item === "GET /dashboard/widgets" || item.includes("chief-of-staff/briefs"))).toBe(false);
});

test("opportunity create failure preserves the complete local draft", async ({ page }) => {
  const state = createMockState({ failPath: "/opportunities" }); await installMockApi(page, state); await page.goto("/breakdowns");
  await openCreate(page); await fillRequired(page, "Retained Neighbor");
  const start = state.requests.length; await page.getByRole("button", { name: "Create Breakdown" }).click();
  await expect(page.getByRole("alert")).toHaveText("Deterministic domain failure");
  await expect(page.getByRole("textbox", { name: "Role", exact: true })).toHaveValue("Retained Neighbor");
  await expect(page.getByLabel("Character Breakdown")).toHaveValue("Comedy neighbor role");
  expect(state.requests.slice(start)).toEqual(["POST /opportunities"]);
  expect(state.opportunities).toHaveLength(1);
  await expect(page.getByRole("button", { name: "All", exact: true })).toBeVisible();
});

test("opportunity edit succeeds by ID without persisted Calendar mutation", async ({ page }) => {
  const state = createMockState(); await installMockApi(page, state); await page.goto("/breakdowns");
  await page.getByRole("button", { name: "Expand breakdown" }).click(); await page.getByText("Edit").click();
  await expect(page.getByRole("textbox", { name: "Role", exact: true })).toHaveValue("DST Detective"); await page.getByRole("textbox", { name: "Role", exact: true }).fill("Lead Detective");
  const start = state.requests.length; await page.getByRole("button", { name: "Save Breakdown" }).click();
  await expect(page.getByText("Lead Detective").first()).toBeVisible();
  expect(state.calendarEvents).toHaveLength(0);
  expect(state.requests.slice(start).filter((item) => item === "PATCH /opportunities/opp-1")).toHaveLength(1);
});

test("opportunity edit failure retains target, draft and local error", async ({ page }) => {
  const state = createMockState({ opportunities: [opportunityFixture()], failPath: "/opportunities/opp-1" });
  await installMockApi(page, state); await page.goto("/breakdowns");
  await page.getByRole("button", { name: "Expand breakdown" }).click(); await page.getByText("Edit").click();
  await page.getByRole("textbox", { name: "Role", exact: true }).fill("Retained Edit"); await page.getByLabel("Notes").fill("Retained notes");
  const start = state.requests.length; await page.getByRole("button", { name: "Save Breakdown" }).click();
  await expect(page.getByRole("alert")).toHaveText("Deterministic domain failure");
  await expect(page.getByRole("heading", { name: "Edit Breakdown" })).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Role", exact: true })).toHaveValue("Retained Edit"); await expect(page.getByLabel("Notes")).toHaveValue("Retained notes");
  expect(state.requests.slice(start)).toEqual(["PATCH /opportunities/opp-1"]);
});
