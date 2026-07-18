import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithRouter } from "../../../test/testUtils";
import type { Opportunity } from "../types";
import { BreakdownViewer } from "./BreakdownViewer";

function opportunity(overrides: Partial<Opportunity> = {}): Opportunity {
  return {
    id: "opportunity-1",
    project: "Spring Forward",
    role: "Detective",
    description: "Production Spring Forward\nAudition Studio 8\nDetective solves the case.",
    source_type: "Manual Entry",
    project_type: "TV",
    category: "Television",
    role_type: "Guest Star",
    union: "SAG-AFTRA",
    rate: "$1,200/day",
    location: "New York",
    audition_location: "Studio 8",
    audition_type: "Self-Tape",
    audition_travel_hours: 1,
    travel_covered: true,
    housing_covered: false,
    archetypes: [],
    role_details: { submission_instructions: "Submit by Friday", preparation: "Prepare sides" },
    production_details: { project_title: "Spring Forward", audition_location_name: "Studio 8" },
    source_metadata: { platform: "Casting Source", submission_instructions: "Submit by Friday" },
    extracted_facts: { production_details: { project_title: "Spring Forward" } },
    ai_inference: { project_type: { value: "Television", confidence: 88 } },
    breakdown_sections: [
      { id: "section-production", section_type: "Production Details", raw_text: "Production Spring Forward", confidence_score: 82 },
      { id: "section-audition", section_type: "Audition Information", raw_text: "Audition Studio 8", confidence_score: 76 },
      { id: "section-preparation", section_type: "Preparation", raw_text: "Prepare sides", confidence_score: 65 },
      { id: "section-roles", section_type: "Roles", raw_text: "Detective solves the case", confidence_score: 91 },
      { id: "section-submission", section_type: "Submission Instructions", raw_text: "Submit by Friday", confidence_score: 72 },
      { id: "section-location", section_type: "Locations", raw_text: "Studio 8", confidence_score: 74 }
    ],
    breakdown_roles: [
      {
        id: "role-1",
        role_name: "Detective",
        role_type: "Guest Star",
        confidence_score: 91,
        fit_status: "Strong Fit",
        extracted_facts: {},
        ai_inference: {}
      }
    ],
    breakdown_parse_runs: [{ id: "parse-1", overall_confidence: 84, parse_mode: "Deep Parse", status: "completed", started_at: "2026-07-01T12:00:00Z" }],
    manual_review_required: false,
    demographic_match_status: "Match",
    watchlist_match_names: [],
    watchlist_match_count: 0,
    is_duplicate: false,
    from_agent: false,
    ...overrides
  } as unknown as Opportunity;
}

function renderViewer(item = opportunity(), callbacks = {
  onRunDeepParse: vi.fn(async () => undefined),
  onPasteText: vi.fn(),
  onManualAddRole: vi.fn()
}) {
  return {
    callbacks,
    view: renderWithRouter(<BreakdownViewer opportunity={item} {...callbacks} />)
  };
}

describe("BreakdownViewer characterization", () => {
  it("renders confidence, initial production facts, raw text, and a matching highlight", () => {
    const { view } = renderViewer();
    for (const label of ["Project Title", "Audition Info", "Preparation", "Role Extraction", "Location", "Overall"]) {
      expect(screen.getAllByText(label).length).toBeGreaterThan(0);
    }
    expect(screen.getByText("84%")).toBeInTheDocument();
    expect(screen.getByText("Parsed Structured Data")).toBeInTheDocument();
    expect(screen.getByText("Spring Forward", { selector: "dd" })).toBeInTheDocument();
    expect(view.container.querySelector("pre")).toHaveTextContent("Detective solves the case");
    expect(view.container.querySelector("mark")).toHaveTextContent("Production Spring Forward");
  });

  it("switches through every parsed section by accessible button name and keyboard", async () => {
    const { view } = renderViewer();
    const cases = [
      ["Audition Information", "Studio 8"],
      ["Preparation", "Prepare sides"],
      ["Role & Character Information", "Detective"],
      ["Submission Instructions", "Submit by Friday"],
      ["Travel / Location", "Travel Covered"],
      ["Source Metadata", "Casting Source"]
    ] as const;
    for (const [buttonName, expected] of cases) {
      const button = screen.getByRole("button", { name: new RegExp(buttonName) });
      button.focus();
      await view.user.keyboard("{Enter}");
      expect(screen.getAllByText(expected).length).toBeGreaterThan(0);
    }
  });

  it("renders sparse data safely and exposes all missing-role action callbacks", async () => {
    const callbacks = { onRunDeepParse: vi.fn(async () => undefined), onPasteText: vi.fn(), onManualAddRole: vi.fn() };
    const { view } = renderViewer(opportunity({
      description: "Unstructured source text",
      project: "",
      audition_type: "Unknown",
      location: undefined,
      audition_location: undefined,
      role_details: {},
      production_details: {},
      source_metadata: { malformed: ["still", "displayable"] },
      extracted_facts: {},
      ai_inference: {},
      breakdown_sections: [],
      breakdown_roles: [],
      breakdown_parse_runs: [],
      manual_review_required: true
    }), callbacks);
    expect(screen.getAllByText("0%").length).toBeGreaterThan(0);
    await view.user.click(screen.getByRole("button", { name: /Role & Character Information/ }));
    expect(screen.getByText("No individual roles are available yet.")).toBeInTheDocument();
    expect(view.container.querySelector("mark")).toBeNull();
    await view.user.click(screen.getByRole("button", { name: "Run deep parse" }));
    await view.user.click(screen.getByRole("button", { name: "Paste actual text" }));
    await view.user.click(screen.getByRole("button", { name: "Manually add role" }));
    expect(callbacks.onRunDeepParse).toHaveBeenCalledTimes(1);
    expect(callbacks.onPasteText).toHaveBeenCalledTimes(1);
    expect(callbacks.onManualAddRole).toHaveBeenCalledTimes(1);
  });

  it("disables only the deep-parse action while its manager-owned request is pending", () => {
    const item = opportunity({ breakdown_roles: [], breakdown_sections: [] });
    renderWithRouter(
      <BreakdownViewer
        opportunity={item}
        onRunDeepParse={vi.fn(async () => undefined)}
        onPasteText={vi.fn()}
        onManualAddRole={vi.fn()}
        deepParsePending
      />
    );
    expect(screen.getByRole("button", { name: "Run deep parse" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Paste actual text" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Manually add role" })).toBeEnabled();
  });

  it("renders a refreshed authoritative opportunity without copying server data", () => {
    const callbacks = { onRunDeepParse: vi.fn(async () => undefined), onPasteText: vi.fn(), onManualAddRole: vi.fn() };
    const rendered = renderWithRouter(<BreakdownViewer opportunity={opportunity()} {...callbacks} />);
    expect(rendered.container.querySelector("pre")).toHaveTextContent("Spring Forward");
    rendered.rerender(<BreakdownViewer opportunity={opportunity({ description: "Updated authoritative breakdown" })} {...callbacks} />);
    expect(rendered.container.querySelector("pre")).toHaveTextContent("Updated authoritative breakdown");
  });
});
