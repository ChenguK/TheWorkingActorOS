import { expect, test } from "@playwright/test";
import { createMockState, installMockApi } from "./support/mockApi";

test("reject/archive refreshes only active exact owners", async ({ page }) => {
  const state = createMockState();
  await installMockApi(page, state);
  await page.goto("/breakdowns");
  await page.getByRole("button", { name: "Expand breakdown" }).click();
  await page.getByText("Delete / reject", { exact: true }).click();
  await page.getByLabel("Plain-English reason").fill("Actor archived this opportunity.");

  const start = state.requests.length;
  await page.getByRole("button", { name: "Delete / Reject", exact: true }).click();
  await expect(page.getByText("DST Detective")).toHaveCount(0);

  const requests = state.requests.slice(start);
  expect(requests.filter((item) => item === "POST /opportunities/opp-1/reject")).toHaveLength(1);
  expect(requests.filter((item) => item === "GET /opportunities")).toHaveLength(1);
  expect(requests.filter((item) => item === "GET /automation/opportunities/hidden")).toHaveLength(1);
  expect(requests.filter((item) => item === "GET /intelligence/readiness/opportunities")).toHaveLength(1);
  expect(requests.filter((item) => item.startsWith("GET /opportunities/material-matches"))).toHaveLength(1);
  expect(requests.some((item) => /journal|calendar|self-tapes|recommendations|dashboard|casting-patterns/.test(item))).toBe(false);
});
