import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { renderWithRouter, screen, waitFor } from "../../../test/testUtils";
import * as api from "../api";
import type { Opportunity } from "../types";
import { HiddenOpportunityReview } from "./HiddenOpportunityReview";

vi.mock("../api", () => ({
  updateBreakdown: vi.fn(async () => ({})), parseBreakdownText: vi.fn(async () => ({})), deepParseBreakdown: vi.fn(async () => ({})),
  approveActingBreakdown: vi.fn(async () => ({})), deleteBreakdown: vi.fn(async () => undefined)
}));

const hidden = (role = "Hidden Detective") => ({
  id: "hidden-1", role, project: "Spring Forward", description: "Original hidden text", visibility_status: "hidden",
  hidden_reason: "Needs manual review", hidden_by_rule: "needs_date_review", manual_review_required: true,
  source_type: "Manual Entry", project_type: "TV", role_type: "Guest Star", union: "SAG-AFTRA", location: "New York",
  audition_type: "Self-Tape", priority: "High", archetypes: [], role_details: {}, source_metadata: {}, production_details: {},
  extracted_facts: {}, ai_inference: {}, breakdown_roles: [], breakdown_sections: [], breakdown_parse_runs: [], watchlist_match_names: [],
  watchlist_match_count: 0, is_duplicate: false, from_agent: false
} as unknown as Opportunity);

describe("HiddenOpportunityReview", () => {
  it("owns disclosure, empty, list, selection, and derives selected details from current props", async () => {
    const view = renderWithRouter(<HiddenOpportunityReview hiddenOpportunities={[]} />);
    await view.user.click(screen.getByRole("button", { name: "Travel Exceptions / Needs Review" }));
    expect(screen.getByText("No travel exceptions or review-only breakdowns.")).toBeInTheDocument();
    view.rerender(<HiddenOpportunityReview hiddenOpportunities={[hidden()]} />);
    await view.user.click(screen.getByText("View Details"));
    expect(screen.getByRole("heading", { name: "Spring Forward · Hidden Detective" })).toBeInTheDocument();
    view.rerender(<HiddenOpportunityReview hiddenOpportunities={[hidden("Updated Detective")]} />);
    expect(screen.getByRole("heading", { name: "Spring Forward · Updated Detective" })).toBeInTheDocument();
    view.rerender(<HiddenOpportunityReview hiddenOpportunities={[]} />);
    await waitFor(() => expect(screen.queryByText("Needs Review Details")).not.toBeInTheDocument());
  });

  it("preserves selection and announces the protected-delete error", async () => {
    vi.mocked(api.deleteBreakdown).mockRejectedValueOnce(new Error("This opportunity cannot be permanently deleted because it has linked submissions."));
    const view = renderWithRouter(<HiddenOpportunityReview hiddenOpportunities={[hidden()]} />);
    await view.user.click(screen.getByRole("button", { name: "Travel Exceptions / Needs Review" }));
    await view.user.click(screen.getByText("View Details"));
    await view.user.click(screen.getAllByRole("button", { name: "Delete" })[1]);
    await view.user.click(screen.getByRole("button", { name: "Confirm" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("linked submissions");
    expect(screen.getByRole("heading", { name: "Spring Forward · Hidden Detective" })).toBeInTheDocument();
  });

  it("owns approve and deep-parse mutations", async () => {
    const view = renderWithRouter(<HiddenOpportunityReview hiddenOpportunities={[hidden()]} />);
    await view.user.click(screen.getByRole("button", { name: "Travel Exceptions / Needs Review" }));
    await view.user.click(screen.getByText("Approve"));
    const approveCalls = vi.mocked(api.approveActingBreakdown).mock.calls;
    expect(approveCalls[approveCalls.length - 1]?.[0]).toBe("hidden-1");
    await view.user.click(screen.getByText("View Details"));
    await view.user.click(screen.getByRole("button", { name: "Breakdown Viewer" }));
    await view.user.click(screen.getByRole("button", { name: "Run deep parse" }));
    const parseCalls = vi.mocked(api.deepParseBreakdown).mock.calls;
    expect(parseCalls[parseCalls.length - 1]?.[0]).toBe("hidden-1");
  });

  it("preserves paste drafts and surrounding UI after mutation failure", async () => {
    vi.mocked(api.parseBreakdownText).mockRejectedValueOnce(new Error("Parse unavailable"));
    const view = renderWithRouter(<HiddenOpportunityReview hiddenOpportunities={[hidden()]} />);
    await view.user.click(screen.getByRole("button", { name: "Travel Exceptions / Needs Review" }));
    await view.user.click(screen.getByText("View Details"));
    await view.user.click(screen.getByRole("button", { name: "Breakdown Viewer" }));
    await view.user.click(screen.getByRole("button", { name: "Paste actual text" }));
    const draft = screen.getByLabelText("Breakdown Text");
    await view.user.clear(draft); await view.user.type(draft, "Retained draft text"); await view.user.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Parse unavailable");
    expect(draft).toHaveValue("Retained draft text");
    expect(screen.getAllByText("Hidden Detective")[0]).toBeInTheDocument();
  });

  it("clears action state after a successful update", async () => {
    const view = renderWithRouter(<HiddenOpportunityReview hiddenOpportunities={[hidden()]} />);
    await view.user.click(screen.getByRole("button", { name: "Travel Exceptions / Needs Review" }));
    await view.user.click(screen.getByText("Travel Info"));
    await view.user.type(screen.getByLabelText("Audition Location"), "Studio 8");
    await view.user.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(screen.queryByRole("heading", { name: "Update Travel Info" })).not.toBeInTheDocument());
    expect(api.updateBreakdown).toHaveBeenCalled();
  });
});
