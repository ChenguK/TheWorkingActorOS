import { expect, test, type Page } from "@playwright/test";
import { installMockApi, type MockState } from "./support/mockApi";

const routes = [
  ["Dashboard", "/"],
  ["Breakdowns", "/breakdowns"],
  ["Auditions", "/auditions"],
  ["Calendar", "/calendar"],
  ["Journal", "/journal"],
  ["Materials", "/materials"],
  ["Profile", "/profile"],
  ["Career Intelligence", "/career"],
  ["Analytics", "/analytics"],
  ["Settings", "/settings"]
] as const;

test.describe.configure({ mode: "serial" });

async function waitForRoute(page: Page, path: string, startedAt = Date.now()) {
  await expect(page).toHaveURL(new RegExp(`${path === "/" ? "/?$" : `${path}(?:\\?.*)?$`}`));
  await expect(page.getByRole("navigation", { name: "Primary workflow navigation" })).toBeVisible();
  const primaryContentMs = Date.now() - startedAt;
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(100);
  return { primaryContentMs, settledMs: Date.now() - startedAt };
}

function endpointCounts(state: MockState, start = 0) {
  return state.requests.slice(start).reduce<Record<string, number>>((counts, request) => {
    counts[request] = (counts[request] ?? 0) + 1;
    return counts;
  }, {});
}

test("major route request graph stays focused", async ({ browser }) => {
  for (const [label, path] of routes) {
    const context = await browser.newContext({ timezoneId: "America/New_York" });
    const page = await context.newPage();
    const state = await installMockApi(page);
    const startedAt = Date.now();
    await page.goto(path);
    const timing = await waitForRoute(page, path, startedAt);
    const counts = endpointCounts(state);
    console.info(`cold-route ${label}: ${JSON.stringify({ timing, requests: counts })}`);
    expect(counts["GET /system/capabilities"]).toBe(1);
    expect(Object.keys(counts).some((request) => /workflow/i.test(request))).toBe(false);
    expect(Object.values(counts).every((count) => count <= 1)).toBe(true);
    expect(timing.primaryContentMs).toBeLessThan(2_000);
    expect(timing.settledMs).toBeLessThan(4_000);
    await context.close();
  }
});

test("fresh configuration and reference queries do not refetch on immediate return", async ({ page }) => {
  const state = await installMockApi(page);
  await page.goto("/");
  await waitForRoute(page, "/");
  await page.getByRole("link", { name: "Settings" }).click();
  await waitForRoute(page, "/settings");
  const dashboardReturnStart = state.requests.length;
  await page.getByRole("link", { name: "Dashboard" }).click();
  await waitForRoute(page, "/");
  const dashboardReturn = endpointCounts(state, dashboardReturnStart);
  console.info(`immediate-return Dashboard: ${JSON.stringify(dashboardReturn)}`);
  expect(dashboardReturn["GET /dashboard/widgets"] ?? 0).toBe(0);
  expect(dashboardReturn["GET /dashboard/focus-mode"] ?? 0).toBe(0);

  await page.getByRole("link", { name: "Profile" }).click();
  await waitForRoute(page, "/profile");
  await page.getByRole("link", { name: "Settings" }).click();
  await waitForRoute(page, "/settings");
  const profileReturnStart = state.requests.length;
  await page.getByRole("link", { name: "Profile" }).click();
  await waitForRoute(page, "/profile");
  const profileReturn = endpointCounts(state, profileReturnStart);
  console.info(`immediate-return Profile: ${JSON.stringify(profileReturn)}`);
  expect(profileReturn["GET /actor-profile"] ?? 0).toBe(0);
  expect(profileReturn["GET /representation"] ?? 0).toBe(0);
});

test("live route queries still refetch on immediate return", async ({ page }) => {
  const state = await installMockApi(page);
  await page.goto("/calendar");
  await waitForRoute(page, "/calendar");
  await page.getByRole("link", { name: "Settings" }).click();
  await waitForRoute(page, "/settings");
  const start = state.requests.length;
  await page.getByRole("link", { name: "Calendar" }).click();
  await waitForRoute(page, "/calendar");
  const counts = endpointCounts(state, start);
  expect(counts["GET /operations/calendar/events"]).toBe(1);

  await page.getByRole("link", { name: "Dashboard" }).click();
  await waitForRoute(page, "/");
  await page.getByRole("link", { name: "Settings" }).click();
  await waitForRoute(page, "/settings");
  const commandStart = state.requests.length;
  await page.getByRole("link", { name: "Dashboard" }).click();
  await waitForRoute(page, "/");
  expect(endpointCounts(state, commandStart)["GET /command-center"]).toBe(1);
});

test.describe.serial("immediate-return request graphs", () => {
  test(
    "fresh Category B aggregates and Journal history skip immediate-return requests",
    async ({ page }) => {
      const state = await installMockApi(page);

      await page.goto("/analytics");
      await waitForRoute(page, "/analytics");

      await page.getByRole("link", { name: "Settings" }).click();
      await waitForRoute(page, "/settings");

      const analyticsStart = state.requests.length;

      await page.getByRole("link", { name: "Analytics" }).click();
      await waitForRoute(page, "/analytics");

      const analytics = endpointCounts(state, analyticsStart);

      expect(analytics["GET /intelligence/dashboard"] ?? 0).toBe(0);
      expect(analytics["GET /intelligence/materials/performance"] ?? 0).toBe(0);
      expect(analytics["GET /operations/dashboard"]).toBe(1);

      await page.getByRole("link", { name: "Journal" }).click();
      await waitForRoute(page, "/journal");

      await page.getByRole("link", { name: "Settings" }).click();
      await waitForRoute(page, "/settings");

      const journalStart = state.requests.length;

      await page.getByRole("link", { name: "Journal" }).click();
      await waitForRoute(page, "/journal");

      const journal = endpointCounts(state, journalStart);

      expect(journal["GET /journal"] ?? 0).toBe(0);

      await page.getByRole("link", { name: "Career Intelligence" }).click();
      await waitForRoute(page, "/career");

      await page.getByRole("link", { name: "Materials" }).click();
      await waitForRoute(page, "/materials");

      const careerStart = state.requests.length;

      await page.getByRole("link", { name: "Career Intelligence" }).click();
      await waitForRoute(page, "/career");

      const career = endpointCounts(state, careerStart);

      expect(
        career["GET /career-development/tasks"] ?? 0
      ).toBeLessThanOrEqual(1);
    }
  );
});
