import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Opportunity } from "../types";
import { RoleViewer } from "./BreakdownRoleDetails";

type BreakdownRole = Opportunity["breakdown_roles"][number];

function role(overrides: Partial<BreakdownRole> = {}): BreakdownRole {
  return {
    id: "role-1",
    role_name: "Detective Mara",
    role_type: "Guest Star",
    billing: "Guest Star",
    confidence_score: 91,
    fit_status: "Strong Fit",
    character_description: "A patient investigator with a guarded sense of humor.",
    role_notes: "Must be comfortable with procedural dialogue.",
    playable_age_min: 35,
    playable_age_max: 45,
    special_skills: ["Stage combat"],
    casting_language: {
      original_text: "DETECTIVE MARA, 35-45, Guest Star",
      billing: "Guest Star",
      age_range: "35-45",
      gender: null,
      ethnicity: null,
      union: "SAG-AFTRA",
      compensation: "$1,200/day",
      special_notes: ["Local hire"]
    },
    character_profile: {
      ai_summary: "Grounded authority with dry warmth.",
      primary_archetypes: ["Detective"],
      secondary_archetypes: ["Mentor"],
      archetype_confidence_scores: [
        { archetype: "Detective", confidence: 88, tier: "PRIMARY", evidence: ["procedural dialogue", "authority"] }
      ],
      personality_traits: ["Patient"],
      emotional_traits: ["Guarded"],
      relationships: ["Partner"],
      motivations: ["Solve the case"],
      internal_conflict: "Trust",
      external_conflict: "Time pressure",
      emotional_arc: "Isolation to partnership",
      genre: "Drama",
      comedic_level: 20,
      dramatic_level: 80,
      recommended_materials: ["Procedural reel"]
    },
    extracted_facts: { source_note: "Series regular option" },
    ai_inference: { compatibility: { value: "Priority Match", confidence: 93 } },
    fit_explanation: "Strong overlap with authority archetypes.",
    ...overrides
  } as unknown as BreakdownRole;
}

describe("RoleViewer characterization", () => {
  it("renders complete role, character, casting, compatibility, and archetype data", () => {
    render(<RoleViewer roles={[role()]} />);

    expect(screen.getAllByText("Detective Mara").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Guest Star").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Priority Match").length).toBeGreaterThan(0);
    expect(screen.getByText("Confidence 91%")).toBeInTheDocument();
    expect(screen.getByText("Role Information")).toBeInTheDocument();
    expect(screen.getByText("Character Information")).toBeInTheDocument();
    expect(screen.getByText("Grounded authority with dry warmth.")).toBeInTheDocument();
    expect(screen.getByText(/Detective \(88% primary: procedural dialogue, authority\)/)).toBeInTheDocument();
    expect(screen.getByText("Strong overlap with authority archetypes.")).toBeInTheDocument();
    expect(screen.getByText("Series regular option")).toBeInTheDocument();
  });

  it("preserves role input order and compatibility fallback labels", () => {
    const { container } = render(<RoleViewer roles={[
      role({ id: "first", role_name: "First Role", fit_status: "Possible Fit", ai_inference: {} }),
      role({ id: "second", role_name: "Second Role", fit_status: "Stretch Fit", ai_inference: {} })
    ]} />);

    const names = Array.from(container.querySelectorAll("p.break-words.font-semibold"));
    expect(names.map((item) => item.textContent)).toEqual(["First Role", "Second Role"]);
    expect(screen.getAllByText("Good Match").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Stretch").length).toBeGreaterThan(0);
  });

  it("renders empty and sparse role data without inventing character interpretation", () => {
    const { rerender } = render(<RoleViewer roles={[]} />);
    expect(screen.getByText("No individual roles are available yet.")).toBeInTheDocument();

    rerender(<RoleViewer roles={[role({
      role_name: "Sparse Role",
      billing: undefined,
      role_type: undefined,
      billing_or_role_type: undefined,
      character_description: undefined,
      role_notes: undefined,
      casting_language: undefined,
      character_profile: undefined,
      extracted_facts: {},
      ai_inference: { compatibility: { malformed: true } } as BreakdownRole["ai_inference"],
      fit_status: "Needs Review",
      fit_explanation: undefined
    })]} />);

    expect(screen.getAllByText("Sparse Role").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Low Fit").length).toBeGreaterThan(0);
    expect(screen.getByText("No AI character interpretation has been generated yet.")).toBeInTheDocument();
  });
});
