import { expect, test } from "@playwright/test";
import { createMockState, installMockApi, opportunityFixture } from "./support/mockApi";

test("Breakdown Viewer inspects complete parsed details without another request", async ({ page }) => {
  const opportunity = {
    ...opportunityFixture(),
    description: "Production Spring Forward\nAudition Studio 8\nDetective solves the case.",
    extracted_facts: { production_details: { project_title: "Spring Forward" } },
    ai_inference: { project_type: { value: "Television", confidence: 88 } },
    breakdown_sections: [
      { id: "section-production", section_type: "Production Details", raw_text: "Production Spring Forward", confidence_score: 82 },
      { id: "section-audition", section_type: "Audition Information", raw_text: "Audition Studio 8", confidence_score: 76 },
      { id: "section-role", section_type: "Roles", raw_text: "Detective solves the case", confidence_score: 91 }
    ],
    breakdown_roles: [{ id: "role-1", role_name: "Detective", role_type: "Guest Star", confidence_score: 91, fit_status: "Strong Fit", extracted_facts: {}, ai_inference: {} }],
    breakdown_parse_runs: [{ id: "parse-1", overall_confidence: 84, parse_mode: "Deep Parse", status: "completed", started_at: "2026-07-01T12:00:00Z" }]
  };
  const state = await installMockApi(page, createMockState({ opportunities: [opportunity] }));
  await page.goto("/breakdowns");
  await page.getByRole("button", { name: "Expand breakdown" }).click();
  const beforeViewer = state.requests.length;
  const disclosure = page.getByRole("button", { name: "Breakdown Viewer" });
  await expect(disclosure).toHaveAttribute("aria-expanded", "false");
  await disclosure.click();
  await expect(disclosure).toHaveAttribute("aria-expanded", "true");
  await expect(page.getByRole("heading", { name: "Original Breakdown Text" })).toBeVisible();
  await expect(page.getByText("Parsed Structured Data")).toBeVisible();
  await page.getByRole("button", { name: /Role & Character Information/ }).click();
  await expect(page.getByText("Detective", { exact: true }).first()).toBeVisible();
  expect(state.requests.slice(beforeViewer)).toEqual([]);
});

test("Breakdown Viewer keeps sparse details stable without duplicate opportunity requests", async ({ page }) => {
  const sparse = {
    ...opportunityFixture(),
    project: "Sparse Project",
    description: "Unstructured source text",
    audition_type: "Unknown",
    location: null,
    shoot_location: null,
    role_details: {},
    production_details: {},
    source_metadata: { malformed: ["still", "displayable"] },
    extracted_facts: {},
    ai_inference: {},
    breakdown_sections: [],
    breakdown_roles: [],
    breakdown_parse_runs: [],
    manual_review_required: true
  };
  const state = await installMockApi(page, createMockState({ opportunities: [sparse] }));
  await page.goto("/breakdowns");
  await page.getByRole("button", { name: "Expand breakdown" }).click();
  const beforeViewer = state.requests.length;
  await page.getByRole("button", { name: "Breakdown Viewer" }).click();
  await expect(page.getByText("Unstructured source text").first()).toBeVisible();
  await expect(page.getByText("The parser could not confidently identify individual role sections.").first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Run deep parse" }).first()).toBeVisible();
  await expect(page.getByRole("button", { name: "All", exact: true })).toBeVisible();
  expect(state.requests.slice(beforeViewer)).toEqual([]);
  expect(state.requests.filter((request) => request === "GET /opportunities")).toHaveLength(1);
});
