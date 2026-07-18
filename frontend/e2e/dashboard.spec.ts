import { expect, test } from "@playwright/test";
import { createMockState, installMockApi } from "./support/mockApi";

test("Dashboard composes public reads and persists focus mode", async ({ page }) => {
  const state = await installMockApi(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "The Working Actor OS" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Add Audition" }).first()).toBeVisible();
  const focus = page.locator('select[name="active_focus_mode"]');
  await focus.selectOption("Career Building Mode");
  await page.getByRole("link", { name: "Materials" }).click();
  await page.getByRole("link", { name: "Dashboard" }).click();
  await expect(focus).toHaveValue("Career Building Mode");
  expect(state.focusMode).toBe("Career Building Mode");
});

test("widget preferences stay independent from feature mutations", async ({ page }) => {
  const state = await installMockApi(page, createMockState());
  await page.goto("/");
  await page.getByRole("button", { name: "Widgets" }).click();
  await expect(page.getByRole("heading", { name: "Quick Actions" })).toBeVisible();
  const widgetRequestsBefore = state.requests.filter((request) => request.includes("/dashboard/widgets")).length;
  await page.getByRole("link", { name: "Materials" }).click();
  await page.getByLabel("Title").fill("Independent Reusable Tape");
  await page.getByLabel("File Path").fill("/fixtures/independent.mp4");
  await page.getByRole("button", { name: "Add Self-Tape" }).click();
  expect(state.requests.filter((request) => request.includes("/dashboard/widgets"))).toHaveLength(widgetRequestsBefore);
});
