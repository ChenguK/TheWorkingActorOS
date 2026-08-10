import { expect, test } from "@playwright/test";
import {
  createMockState,
  installMockApi,
  sanitizedPortfolioCommandCenterFixture
} from "./support/mockApi";

test("sanitized portfolio Dashboard preserves the backend-defined command-center contract", async ({ page }) => {
  const state = createMockState({
    actor: {
      id: "c83b75d4-5585-5b5c-9a99-63363f5bc14d",
      name: "Mara Ellison — Fictional Portfolio Performer",
      current_location: "Atlanta, GA"
    },
    commandCenter: sanitizedPortfolioCommandCenterFixture()
  });
  await installMockApi(page, state);
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "The Working Actor OS" })).toBeVisible({ timeout: 30_000 });

  const cards = page.getByLabel(/Opportunity intelligence:/);
  await expect(cards).toHaveCount(3);
  await expect(page.getByText("Forensic Analyst")).toBeVisible();
  await expect(page.getByText("Signal at Dawn")).toBeVisible();
  await expect(page.getByText("Score 86 of 100 · Low confidence")).toBeVisible();
  await expect(page.getByText("Community Organizer")).toBeVisible();
  await expect(page.getByText("Score 81 of 100 · Medium confidence")).toBeVisible();
  await expect(page.getByText("Crisis Negotiator")).toBeVisible();
  const visibleRoles = await page.locator("p.font-medium.text-ink").allTextContents();
  expect(visibleRoles).toEqual(expect.arrayContaining([
    "Forensic Analyst",
    "Community Organizer",
    "Crisis Negotiator"
  ]));
  expect(visibleRoles.indexOf("Forensic Analyst")).toBeLessThan(
    visibleRoles.indexOf("Community Organizer")
  );
  expect(visibleRoles.indexOf("Community Organizer")).toBeLessThan(
    visibleRoles.indexOf("Crisis Negotiator")
  );

  const disclosure = page.getByText("Why this score").first();
  await disclosure.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByText(/Positive: The audition can be completed remotely/).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Quick Actions" })).toBeVisible();

  expect(state.requests.filter((request) => request === "GET /command-center")).toHaveLength(1);
  expect(state.requests.some((request) => request.includes("command-center/intelligence"))).toBe(false);

  await page.getByRole("link", { name: "Materials" }).click();
  await page.getByRole("link", { name: "Dashboard" }).click();
  await expect(page.getByText("Forensic Analyst")).toBeVisible();
  expect(state.requests.some((request) => request.includes("command-center/intelligence"))).toBe(false);

  const rendered = await page.locator("body").innerText();
  for (const prohibited of ["/Users/", "/tmp/", "example.com", "private-user", "portfolio_seed"]) {
    expect(rendered.toLowerCase()).not.toContain(prohibited.toLowerCase());
  }
});
