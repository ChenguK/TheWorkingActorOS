import { describe, expect, it, vi } from "vitest";
import { MergedAuditionReadinessPanel } from "./BreakdownReadiness";
import { renderWithRouter, screen } from "../../../test/testUtils";
import type { AuditionReadiness, Opportunity } from "../types";

function opportunityFixture(): Opportunity {
  return {
    id: "breakdown-1",
    source_type: "Manual Entry",
    platform: null,
    from_agent: false,
    role: "Viv",
    project: "I'm Sorry, Matt 06",
    project_type: "Film/TV",
    role_type: "Co-Star",
    archetypes: ["Mom", "Comedy"],
    union: "SAG-AFTRA",
    location: "Philadelphia, PA",
    description: "Protective mother with warm comedy.",
    status: "open",
    source_reliability_score: 90,
    is_duplicate: false,
    is_demo_data: false,
    breakdown_classification: "Acting Role",
    source_metadata: {},
    production_details: {},
    role_details: {},
    extracted_facts: {},
    ai_inference: {},
    audition_type: "Self-Tape",
    visibility_status: "visible",
    manual_review_required: false,
    priority: "High",
    urgency_score: 80,
    quality_score: 85,
    confidence_level: "High",
    risk_level: "Low",
    demographic_match_status: "Match",
    demographic_match_details: {},
    watchlist_match_names: [],
    watchlist_match_count: 0,
    already_tracked: false,
    breakdown_roles: [],
    breakdown_sections: [],
    breakdown_parse_runs: [],
    created_at: "2026-07-01T00:00:00Z",
    updated_at: "2026-07-01T00:00:00Z"
  };
}

function readinessFixture(): AuditionReadiness {
  return {
    opportunity_id: "breakdown-1",
    opportunity_label: "Viv · I'm Sorry, Matt 06",
    readiness_label: "Mostly Ready",
    readiness_percentage: 82,
    score_breakdown: { materials: 20 },
    missing_materials: ["Slate"],
    character_archetypes: ["Mom", "PTA Mom", "Comedy"],
    character_parsing_confidence: 88,
    character_parsing_status: "Parsed",
    debug_score_available: true,
    explanation: "You have strong maternal comedy materials, but a slate is missing."
  };
}

describe("MergedAuditionReadinessPanel", () => {
  it("shows compact readiness, expands details, and hides technical JSON by default", async () => {
    const { user, container } = renderWithRouter(
      <MergedAuditionReadinessPanel
        actor={null}
        opportunities={[opportunityFixture()]}
        recommendations={[]}
        assets={[]}
        readiness={[readinessFixture()]}
      />
    );

    expect(screen.getByText("Viv")).toBeInTheDocument();
    expect(screen.getByText("Mostly Ready")).toBeInTheDocument();
    expect(container.textContent).not.toContain("score_breakdown");

    await user.click(screen.getByRole("button", { name: "Expand audition readiness" }));

    expect(screen.getByText(/You have strong maternal comedy materials/i)).toBeInTheDocument();
    expect(screen.getByText("Recommended Materials")).toBeInTheDocument();
    expect(screen.queryByText("Internal score: 82%")).not.toBeInTheDocument();
  });
});
