import { expect, test } from "@playwright/test";
import { createMockState, installMockApi } from "./support/mockApi";


test("configured discovery preserves the strict request graph and renders decisions with evidence", async ({ page }) => {
  const state = createMockState({
    capabilities: {
      flags: {
        source_discovery_configured: true,
        ai_configured: false,
        supervised_browser_available: false,
        persistent_file_storage_available: false,
        portfolio_demo: false
      },
      states: {},
      integrations: [],
      labels: {}
    }
  });
  await installMockApi(page, state);
  await page.goto("/breakdowns");
  await expect(page.getByRole("button", { name: "Find Film/TV Breakdowns" })).toBeVisible();
  const beforeRun = state.requests.length;

  await page.getByRole("button", { name: "Find Film/TV Breakdowns" }).click();
  await page.getByRole("button", { name: "View Discovery Report" }).click();

  const runRequest = "POST /automation/discovery/run?mode=FilmTV&search_modes=Match+My+Profile&search_modes=Match+My+Archetypes";
  expect(state.requests.filter((request) => request === runRequest)).toHaveLength(1);
  expect(state.requests.some((request) => request.includes("/automation/discovery/report"))).toBe(false);
  expect(state.requests.slice(beforeRun).filter((request) => request.startsWith("POST /automation/discovery/run"))).toHaveLength(1);
  await expect(page.getByText("Accepted", { exact: true }).last()).toBeVisible();
  await expect(page.getByText("Needs Review", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Rejected", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("In-person audition travel cannot be verified yet.")).toBeVisible();
  await expect(page.getByRole("link", { name: "River City — Maya" })).toHaveAttribute(
    "href",
    "https://casting.example.test/river-city"
  );
  await expect(page.getByText(/Search-result context:.*Fictional search-result context/)).toBeVisible();
  await expect(page.getByText("Provider publication date: 2026-08-01")).toBeVisible();
  await expect(page.getByText("Decision code: direct_eligible_notice")).toBeVisible();

  const afterEvidence = state.requests.length;
  await page.waitForTimeout(100);
  expect(state.requests).toHaveLength(afterEvidence);
  await page.getByRole("link", { name: "Settings" }).click();
  await expect(page).toHaveURL(/\/settings$/);
  await page.getByRole("link", { name: "Breakdowns" }).click();
  await expect(page).toHaveURL(/\/breakdowns$/);
  expect(state.requests.filter((request) => request.startsWith("POST /automation/discovery/run"))).toHaveLength(1);
});
