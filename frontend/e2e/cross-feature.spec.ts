import { expect, test } from "@playwright/test";
import { createMockState, installMockApi } from "./support/mockApi";

test("breakdown creates an Auditions submission without a global reload", async ({ page }) => {
  const state = await installMockApi(page);
  await page.goto("/breakdowns");
  await expect(page.getByText("DST Detective").first()).toBeVisible();
  await page.goto("/auditions?breakdownId=opp-1");
  await expect(page.locator('select[name="breakdown"]').first()).toHaveValue("opp-1");
  const beforeMutation = state.requests.length;
  await page.getByRole("button", { name: "Submitted/Auditioned for this role" }).click();
  await expect.poll(() => state.submissions.length).toBe(1);
  await expect(page.getByLabel("Linked Submission").first().getByRole("option", { name: /DST Detective/ })).toHaveCount(1);
  expect(state.submissions).toHaveLength(1);
  expect(state.requests.filter((request) => request.startsWith("POST /submissions"))).toHaveLength(1);
  const mutationRequests = state.requests.slice(beforeMutation);
  expect(mutationRequests.some((request) => request === "GET /dashboard/widgets")).toBe(false);
  expect(mutationRequests.some((request) => request === "GET /representation")).toBe(false);
  expect(mutationRequests.filter((request) => request === "GET /assets")).toHaveLength(1);
});

test("audition deadline propagates to Calendar across the DST boundary", async ({ page }) => {
  const state = await installMockApi(page);
  await page.goto("/auditions?breakdownId=opp-1");
  await expect(page.locator('select[name="breakdown"]').first()).toHaveValue("opp-1");
  await page.getByLabel("Audition/Tape Due Date").fill("2026-03-08T01:30");
  await page.getByLabel("Create self-tape task if due date exists").check();
  await page.getByLabel("Add to calendar").check();
  const beforeMutation = state.requests.length;
  await page.getByRole("button", { name: "Submitted/Auditioned for this role" }).click();
  await expect.poll(() => state.calendarEvents.length).toBe(1);
  await expect.poll(() => state.workflowTapes.length).toBe(1);
  const requests = state.requests.slice(beforeMutation);
  expect(requests.filter((request) => request === "POST /submissions")).toHaveLength(1);
  expect(requests.filter((request) => request === "POST /command-center/self-tapes")).toHaveLength(1);
  expect(requests.filter((request) => request === "POST /operations/calendar/events")).toHaveLength(1);
  expect(requests.filter((request) => request === "POST /intelligence/audition-journal")).toHaveLength(1);
  await page.getByRole("link", { name: "Calendar" }).click();
  await expect(page.getByText("DST Detective · Spring Forward").filter({ visible: true }).first()).toBeVisible();
  expect(state.calendarEvents[0].start_datetime).toBe("2026-03-08T01:30");
  expect(state.workflowTapes).toHaveLength(1);
});

test("unchecked Add to calendar omits only the frontend Calendar request", async ({ page }) => {
  const state = await installMockApi(page);
  await page.goto("/auditions?breakdownId=opp-1");
  await expect(page.locator('select[name="breakdown"]').first()).toHaveValue("opp-1");
  await page.getByLabel("Audition/Tape Due Date").fill("2026-03-08T01:30");
  await page.getByLabel("Add to calendar").uncheck();
  const beforeMutation = state.requests.length;

  await page.getByRole("button", { name: "Submitted/Auditioned for this role" }).click();
  await expect.poll(() => state.submissions.length).toBe(1);
  await expect.poll(() => state.workflowTapes.length).toBe(1);

  const requests = state.requests.slice(beforeMutation);
  expect(requests.filter((request) => request === "POST /submissions")).toHaveLength(1);
  expect(requests.filter((request) => request === "POST /command-center/self-tapes")).toHaveLength(1);
  expect(requests.filter((request) => request === "POST /operations/calendar/events")).toHaveLength(0);
  expect(requests.filter((request) => request === "POST /intelligence/audition-journal")).toHaveLength(1);
  expect(state.calendarEvents).toHaveLength(0);
});

test("material edits propagate to Journal material options", async ({ page }) => {
  const state = await installMockApi(page);
  await page.goto("/materials");
  await page.getByRole("button", { name: "Edit" }).first().click();
  await page.getByLabel("Material Name").fill("E2E Updated Headshot");
  await page.getByRole("button", { name: "Save Material" }).click();
  await expect(page.getByText("E2E Updated Headshot")).toBeVisible();
  await page.getByRole("link", { name: "Journal" }).click();
  await expect(page.getByLabel("Material").getByRole("option", { name: "E2E Updated Headshot" })).toHaveCount(1);
  expect(state.assets[0].asset_name).toBe("E2E Updated Headshot");
});

test("representation updates flow through the public Profile boundary", async ({ page }) => {
  const state = await installMockApi(page);
  await page.goto("/profile");
  await page.getByRole("button", { name: "Add Representation" }).click();
  await page.getByLabel("Agency Name").fill("E2E Artists Agency");
  await page.getByLabel("Agent Name").fill("Jordan Agent");
  await page.getByRole("button", { name: "Add Representation" }).last().click();
  await expect(page.getByText("Represented by E2E Artists Agency")).toBeVisible();
  await page.getByRole("link", { name: "Breakdowns" }).click();
  await expect(page.getByLabel("Agent / Agency").getByRole("option", { name: /E2E Artists Agency/ })).toHaveCount(1);
  expect(state.representations).toHaveLength(1);
});

test("reusable and workflow self-tapes remain separate", async ({ page }) => {
  const state = await installMockApi(page);
  await page.goto("/materials");
  await page.getByLabel("Title").fill("Reusable Authority Take");
  await page.getByLabel("File Path").fill("/fixtures/reusable.mp4");
  await page.getByRole("button", { name: "Add Self-Tape" }).click();
  await expect(page.getByText("Reusable Authority Take")).toBeVisible();
  await page.getByRole("link", { name: "Auditions" }).click();
  await expect(page.getByText("Reusable Authority Take")).toHaveCount(0);
  expect(state.reusableTapes).toHaveLength(1);
  expect(state.workflowTapes).toHaveLength(0);
});

test("submission outcome refreshes actor Journal without a broad request burst", async ({ page }) => {
  const state = await installMockApi(page);
  await page.goto("/auditions?breakdownId=opp-1");
  await expect(page.locator('select[name="breakdown"]').first()).toHaveValue("opp-1");
  await page.getByRole("button", { name: "Submitted/Auditioned for this role" }).click();
  await expect.poll(() => state.submissions.length).toBe(1);

  await page.getByRole("link", { name: "Journal" }).click();
  await expect(page.getByRole("button", { name: "Journal", expanded: true })).toBeVisible();
  await page.getByRole("link", { name: "Analytics" }).click();
  await expect(page.getByText("Callback and Booking Rates")).toBeVisible();
  await page.getByRole("link", { name: "Auditions" }).click();

  await page.getByRole("button", { name: "Update Status" }).click();
  const beforeOutcome = state.requests.length;
  await page.getByRole("button", { name: "Booked", exact: true }).click();
  await expect.poll(() => state.submissions[0].current_status).toBe("Booked");
  await expect.poll(() => state.actorJournal.length).toBe(1);

  await page.getByRole("link", { name: "Journal" }).click();
  await expect(page.getByText("Booked: DST Detective in Spring Forward")).toBeVisible();
  await page.getByRole("link", { name: "Analytics" }).click();
  await expect(page.getByText("100%").last()).toBeVisible();
  const requests = state.requests.slice(beforeOutcome);
  expect(requests.filter((request) => request.startsWith("POST /submissions/") && request.endsWith("/status-history"))).toHaveLength(1);
  expect(requests.some((request) => request === "GET /dashboard/widgets")).toBe(false);
  expect(requests.some((request) => request === "GET /dashboard/focus-mode")).toBe(false);
  expect(requests.some((request) => request === "GET /agents/chief-of-staff/briefs")).toBe(false);
  expect(requests.filter((request) => request === "GET /intelligence/dashboard")).toHaveLength(1);
  expect(requests.filter((request) => request === "GET /intelligence/materials/performance")).toHaveLength(1);
});
