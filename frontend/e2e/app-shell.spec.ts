import { expect, test } from "@playwright/test";
import { createMockState, installMockApi } from "./support/mockApi";

test("app boots with navigation and no global workflow loader", async ({ page }) => {
  const state = await installMockApi(page);
  await page.goto("/materials");
  await expect(page.getByRole("navigation", { name: "Primary workflow navigation" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Materials", expanded: true })).toBeVisible();
  expect(state.requests.some((request) => /workflow/i.test(request))).toBe(false);
  expect(state.requests.filter((request) => request === "GET /system/capabilities")).toHaveLength(1);
});

test("hosted demo keeps Materials readable without upload requests", async ({ page }) => {
  const state = await installMockApi(page);
  await page.goto("/materials");

  await expect(page.getByText("E2E Headshot")).toBeVisible();
  await expect(page.getByRole("link", { name: "View" })).toBeVisible();
  await expect(page.getByText(/File uploads are disabled in the hosted demo/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Upload Material" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Delete" })).toHaveCount(0);
  expect(state.requests.filter((request) => request === "POST /assets")).toHaveLength(0);
});

test("local durable-storage capability preserves Materials upload controls", async ({ page }) => {
  const state = createMockState();
  const flags = state.capabilities.flags as Record<string, unknown>;
  flags.persistent_file_storage_available = true;
  await installMockApi(page, state);
  await page.goto("/materials");

  await expect(page.getByRole("button", { name: "Upload Material" })).toBeVisible();
  await expect(page.getByLabel("File")).toBeVisible();
  await expect(page.getByText(/File uploads are disabled/)).toHaveCount(0);
});

test("hosted demo keeps profile imports text-only", async ({ page }) => {
  const state = await installMockApi(page);
  await page.goto("/profile");

  await expect(page.getByLabel("Upload File")).toBeDisabled();
  await expect(page.getByText(/Paste profile text or guided form answers instead/)).toBeVisible();
  expect(
    state.requests.filter(
      (request) => request === "POST /platform-imports/profiles/import-upload"
    )
  ).toHaveLength(0);
});

test("a failed feature request stays owned by that route", async ({ page }) => {
  await installMockApi(page, createMockState({ failPath: "/intelligence/self-tapes/analytics" }));
  await page.goto("/materials");
  await expect(page.getByRole("alert").filter({ hasText: "Could not load self-tape analytics" })).toBeVisible();
  await expect(page.getByText("E2E Headshot")).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Primary workflow navigation" })).toBeVisible();
});

test("route navigation requests only required domains and retains cached content", async ({ page }) => {
  const state = await installMockApi(page);
  await page.goto("/materials");
  await expect(page.getByText("E2E Headshot")).toBeVisible();
  const before = state.requests.length;
  await page.getByRole("link", { name: "Journal" }).click();
  await expect(page.getByRole("button", { name: "Journal", expanded: true })).toBeVisible();
  await expect.poll(() => state.requests.slice(before).some((request) => request.includes("/journal"))).toBe(true);
  const navigationRequests = state.requests.slice(before);
  expect(navigationRequests.some((request) => request.includes("/dashboard/widgets"))).toBe(false);
  await page.getByRole("link", { name: "Materials" }).click();
  await expect(page.getByText("E2E Headshot")).toBeVisible();
});
