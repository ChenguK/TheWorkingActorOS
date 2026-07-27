import { expect, test } from "@playwright/test";
import { assertHandledApiRequest, installMockApi } from "./support/mockApi";

test("recognized API requests return their fixture and remain recorded", async ({ page }) => {
  const state = await installMockApi(page);

  const response = await page.evaluate(async () => {
    const result = await fetch("http://127.0.0.1:4173/api/v1/system/capabilities");
    return { ok: result.ok, body: await result.json() };
  });

  expect(response.ok).toBe(true);
  expect(response.body).toMatchObject({ flags: { ai_configured: false } });
  expect(state.requests).toEqual(["GET /system/capabilities"]);
});

test("unknown paths, wrong methods, and unexpected queries are rejected with context", () => {
  expect(() => assertHandledApiRequest("GET", new URL("http://example.test/api/v1/unknown")))
    .toThrow("Unhandled mock API request: GET /unknown");
  expect(() => assertHandledApiRequest("DELETE", new URL("http://example.test/api/v1/system/capabilities")))
    .toThrow("Unhandled mock API request: DELETE /system/capabilities");
  expect(() => assertHandledApiRequest("GET", new URL("http://example.test/api/v1/opportunities/material-matches?min_score=15")))
    .toThrow("Unhandled mock API request: GET /opportunities/material-matches?min_score=15");
});

test("the API interceptor does not reject non-API requests", async ({ page }) => {
  const state = await installMockApi(page);

  const response = await page.goto("/");

  expect(response?.ok()).toBe(true);
  expect(state.requests.every((request) => request.includes(" /"))).toBe(true);
});
