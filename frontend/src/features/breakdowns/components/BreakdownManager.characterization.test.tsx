import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, screen, waitFor } from "@testing-library/react";
import { renderWithRouter } from "../../../test/testUtils";
import * as api from "../api";
import type { Opportunity, Representation } from "../types";
import { OpportunityManager } from "./BreakdownManager";

vi.mock("../api", () => ({
  createBreakdown: vi.fn(async (payload) => ({ id: "created", ...payload })),
  updateBreakdown: vi.fn(async (_id, payload) => ({ id: "opp-1", ...payload })),
  parseBreakdownText: vi.fn(async () => ({})), deepParseBreakdown: vi.fn(async () => ({})),
  generateBreakdownStrategy: vi.fn(async () => ({})), refreshDemographicCheck: vi.fn(async () => ({})),
  rejectBreakdown: vi.fn(async () => ({}))
}));

const opportunity = (overrides: Partial<Opportunity> = {}) => ({
  id: "opp-1", role: "Detective", project: "Spring Forward", description: "Original description",
  source_type: "Agent Submission", platform: null, from_agent: true, representation_id: "rep-1",
  project_type: null, role_type: null, union: "SAG-AFTRA", rate: null, location: "New York",
  shoot_location: null, audition_location: null, travel_covered: null, housing_covered: null,
  audition_type: "Self-Tape", audition_travel_hours: null, original_post_url: null,
  audition_deadline: null, submission_deadline: null, callback_date: null, shoot_start_date: null, shoot_end_date: null,
  priority: "Medium", archetypes: [], role_details: {}, source_metadata: {}, production_details: {},
  extracted_facts: {}, ai_inference: {}, breakdown_roles: [], breakdown_sections: [], breakdown_parse_runs: [],
  watchlist_match_names: [], watchlist_match_count: 0, is_duplicate: false, manual_review_required: false,
  demographic_match_status: "Needs Review", quality_score: 50, urgency_score: 20, risk_level: "Medium",
  ...overrides
} as unknown as Opportunity);

const representation = {
  id: "rep-1", actor_profile_id: "actor-1", agency_name: "Contract Artists", agent_name: null,
  representation_type: "Theatrical", market: ["New York"], active: true, created_at: "2026-01-01", updated_at: "2026-01-01"
} as Representation;

describe("embedded opportunity form characterization", () => {
  beforeEach(() => vi.clearAllMocks());

  it("opens a clean controlled create form for an empty list and normalizes its payload", async () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const view = renderWithRouter(<OpportunityManager opportunities={[]} representations={[representation]} />);
    expect(screen.getByRole("heading", { name: "Add Breakdown" })).toBeInTheDocument();
    expect(screen.getByLabelText("Platform")).toHaveValue("");
    expect(screen.getByLabelText("Agent / Agency")).toHaveValue("");
    expect(screen.getByLabelText("Audition Travel Hours")).toHaveValue(null);
    await view.user.type(screen.getByLabelText("Role"), "Neighbor");
    await view.user.type(screen.getByLabelText("Project"), "Visible Pilot");
    await view.user.type(screen.getByLabelText("Shoot Location"), "New York");
    await view.user.type(screen.getByLabelText("Character Breakdown"), "Comedy neighbor role");
    await view.user.selectOptions(screen.getByLabelText("Agent / Agency"), "rep-1");
    await view.user.type(screen.getByLabelText("Archetypes"), "Comedy, Parent");
    await view.user.click(screen.getByRole("button", { name: "Create Breakdown" }));
    await waitFor(() => expect(api.createBreakdown).toHaveBeenCalled());
    const createCalls = vi.mocked(api.createBreakdown).mock.calls;
    expect(createCalls[createCalls.length - 1]?.[0]).toMatchObject({
      role: "Neighbor", representation_id: "rep-1", platform: null, project_type: null,
      archetypes: ["Comedy", "Parent"], audition_travel_hours: null,
      submission_deadline: null, audition_deadline: null, status: "open"
    });
    expect(screen.queryByRole("heading", { name: "Add Breakdown" })).not.toBeInTheDocument();
    expect(consoleError).not.toHaveBeenCalledWith(expect.stringContaining("uncontrolled"));
    consoleError.mockRestore();
  });

  it("initializes edit by current record ID and submits the normalized update", async () => {
    const view = renderWithRouter(<OpportunityManager opportunities={[opportunity()]} representations={[representation]} />);
    await view.user.click(screen.getByRole("button", { name: "Expand breakdown" }));
    await view.user.click(screen.getByText("Edit"));
    expect(screen.getByRole("heading", { name: "Edit Breakdown" })).toBeInTheDocument();
    expect(screen.getByLabelText("Role")).toHaveValue("Detective");
    expect(screen.getByLabelText("Agent / Agency")).toHaveValue("rep-1");
    await view.user.clear(screen.getByLabelText("Role"));
    await view.user.type(screen.getByLabelText("Role"), "Lead Detective");
    await view.user.click(screen.getByRole("button", { name: "Save Breakdown" }));
    await waitFor(() => expect(api.updateBreakdown).toHaveBeenCalledWith("opp-1", expect.objectContaining({ role: "Lead Detective" })));
    expect(screen.queryByRole("heading", { name: "Edit Breakdown" })).not.toBeInTheDocument();
  });

  it("cancel discards the edit draft and reopening derives current props", async () => {
    const view = renderWithRouter(<OpportunityManager opportunities={[opportunity()]} representations={[representation]} />);
    await view.user.click(screen.getByRole("button", { name: "Expand breakdown" }));
    await view.user.click(screen.getByText("Edit"));
    await view.user.clear(screen.getByLabelText("Role")); await view.user.type(screen.getByLabelText("Role"), "Dirty Draft");
    await view.user.click(screen.getByRole("button", { name: "Cancel Edit" }));
    await view.user.click(screen.getByText("Edit"));
    expect(screen.getByLabelText("Role")).toHaveValue("Detective");
  });

  it("manual parse submits the complete per-opportunity draft and resets only after success", async () => {
    vi.mocked(api.parseBreakdownText).mockResolvedValueOnce({} as Opportunity);
    const view = renderWithRouter(<OpportunityManager opportunities={[opportunity()]} representations={[representation]} />);
    await view.user.click(screen.getByRole("button", { name: "Expand breakdown" }));
    await view.user.click(screen.getByRole("button", { name: "Raw / Pasted Breakdown Text" }));
    await view.user.click(screen.getByRole("button", { name: "Paste Actual Breakdown Text" }));
    const textarea = screen.getByPlaceholderText("Paste the visible role breakdown text here, then re-run parsing.");
    await view.user.type(textarea, "Complete pasted breakdown text");
    await view.user.click(screen.getByRole("button", { name: "Re-run Parsing" }));
    await waitFor(() => expect(api.parseBreakdownText).toHaveBeenLastCalledWith("opp-1", "Complete pasted breakdown text"));
    await waitFor(() => expect(screen.queryByPlaceholderText("Paste the visible role breakdown text here, then re-run parsing.")).not.toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Paste Actual Breakdown Text" })).toHaveFocus();
  });

  it("manual parse presents pending state and prevents a duplicate submit", async () => {
    let resolveParse!: (value: Opportunity) => void;
    vi.mocked(api.parseBreakdownText).mockImplementationOnce(() => new Promise((resolve) => { resolveParse = resolve; }));
    const view = renderWithRouter(<OpportunityManager opportunities={[opportunity()]} representations={[representation]} />);
    await view.user.click(screen.getByRole("button", { name: "Expand breakdown" }));
    await view.user.click(screen.getByRole("button", { name: "Raw / Pasted Breakdown Text" }));
    await view.user.click(screen.getByRole("button", { name: "Paste Actual Breakdown Text" }));
    await view.user.type(screen.getByLabelText("Breakdown Text"), "Pending parse text");
    await view.user.click(screen.getByRole("button", { name: "Re-run Parsing" }));
    expect(screen.getByRole("status")).toHaveTextContent("Re-running breakdown parsing");
    expect(screen.getByRole("button", { name: "Parsing…" })).toBeDisabled();
    expect(api.parseBreakdownText).toHaveBeenCalledTimes(1);
    await act(async () => resolveParse({} as Opportunity));
    await waitFor(() => expect(screen.queryByRole("status")).not.toBeInTheDocument());
  });

  it("manual parse keeps its target, draft, and details after failure, then retries successfully", async () => {
    vi.mocked(api.parseBreakdownText).mockRejectedValueOnce(new Error("Parser unavailable"));
    const view = renderWithRouter(<OpportunityManager opportunities={[opportunity()]} representations={[representation]} />);
    await view.user.click(screen.getByRole("button", { name: "Expand breakdown" }));
    await view.user.click(screen.getByRole("button", { name: "Raw / Pasted Breakdown Text" }));
    await view.user.click(screen.getByRole("button", { name: "Paste Actual Breakdown Text" }));
    const textarea = screen.getByPlaceholderText("Paste the visible role breakdown text here, then re-run parsing.");
    await view.user.type(textarea, "Draft survives parser failure");
    await view.user.click(screen.getByRole("button", { name: "Re-run Parsing" }));
    await waitFor(() => expect(api.parseBreakdownText).toHaveBeenLastCalledWith("opp-1", "Draft survives parser failure"));
    expect(textarea).toHaveValue("Draft survives parser failure");
    expect(screen.getAllByText("Original description").length).toBeGreaterThan(0);
    expect(screen.getByRole("alert")).toHaveTextContent("Parser unavailable");
    expect(textarea).toHaveAccessibleDescription("Parser unavailable");
    vi.mocked(api.parseBreakdownText).mockResolvedValueOnce({} as Opportunity);
    await view.user.click(screen.getByRole("button", { name: "Re-run Parsing" }));
    await waitFor(() => expect(api.parseBreakdownText).toHaveBeenLastCalledWith("opp-1", "Draft survives parser failure"));
    await waitFor(() => expect(screen.queryByLabelText("Breakdown Text")).not.toBeInTheDocument());
  });

  it("deep parse announces local pending state and prevents duplicate clicks across both triggers", async () => {
    let resolveParse!: (value: Opportunity) => void;
    vi.mocked(api.deepParseBreakdown).mockImplementationOnce(() => new Promise((resolve) => { resolveParse = resolve; }));
    const view = renderWithRouter(<OpportunityManager opportunities={[opportunity()]} representations={[representation]} />);
    await view.user.click(screen.getByRole("button", { name: "Expand breakdown" }));
    await view.user.click(screen.getByRole("button", { name: "Breakdown Viewer" }));
    const triggers = screen.getAllByRole("button", { name: "Run deep parse" });
    expect(triggers).toHaveLength(2);
    await view.user.click(triggers[0]);
    expect(screen.getByRole("status")).toHaveTextContent("Deep parsing Spring Forward");
    expect(triggers[0]).toBeDisabled();
    expect(triggers[1]).toBeDisabled();
    await view.user.click(triggers[1]);
    expect(api.deepParseBreakdown).toHaveBeenCalledTimes(1);
    await act(async () => resolveParse({} as Opportunity));
    await waitFor(() => expect(screen.queryByRole("status")).not.toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Collapse breakdown" })).toHaveFocus();
  });

  it("deep parse keeps surrounding details, reports a local error, restores focus, and retries", async () => {
    vi.mocked(api.deepParseBreakdown).mockRejectedValueOnce(new Error("Deep parser unavailable"));
    const view = renderWithRouter(<OpportunityManager opportunities={[opportunity()]} representations={[representation]} />);
    await view.user.click(screen.getByRole("button", { name: "Expand breakdown" }));
    const trigger = screen.getByRole("button", { name: "Run deep parse" });
    await view.user.click(trigger);
    expect(await screen.findByRole("alert")).toHaveTextContent("Deep parser unavailable");
    expect(screen.getAllByText("Original description").length).toBeGreaterThan(0);
    expect(trigger).toHaveFocus();
    vi.mocked(api.deepParseBreakdown).mockResolvedValueOnce({} as Opportunity);
    await view.user.click(trigger);
    await waitFor(() => expect(screen.queryByRole("alert")).not.toBeInTheDocument());
    expect(api.deepParseBreakdown).toHaveBeenCalledTimes(2);
    expect(screen.getByRole("button", { name: "Collapse breakdown" })).toHaveFocus();
  });
});
