import { describe, expect, it } from "vitest";
import type { Opportunity } from "../types";
import { createEmptyOpportunityDraft, formDraftToOpportunityRequest, opportunityToFormDraft } from "./opportunityFormModel";

describe("opportunity form model", () => {
  it("creates a fully defined controlled draft", () => {
    const draft = createEmptyOpportunityDraft();
    expect(Object.values(draft).every((value) => value !== undefined && value !== null)).toBe(true);
    expect(draft).toMatchObject({ source_type: "Manual Entry", audition_type: "Self-Tape", union: "SAG-AFTRA", priority: "Medium", from_agent: false });
  });

  it("normalizes sparse authoritative records and nested fallbacks", () => {
    const draft = opportunityToFormDraft({
      id: "o1", source_type: "Manual Entry", role: "Reader", project: "Pilot", union: "Non-Union", location: "Remote",
      description: "Reader role", from_agent: false, audition_type: "Unknown", priority: "Low", archetypes: null,
      platform: null, representation_id: null, project_type: null, role_type: null, rate: null, shoot_location: null,
      audition_location: null, travel_covered: null, housing_covered: null, audition_travel_hours: null,
      original_post_url: null, audition_deadline: null, submission_deadline: null, callback_date: null,
      shoot_start_date: null, shoot_end_date: null, source_metadata: { casting_contact: "Morgan" },
      production_details: { production_company: "Studio" }, role_details: { preparation: "Prepare sides" }
    } as unknown as Opportunity);
    expect(draft).toMatchObject({ platform: "", representation_id: "", archetypes: "", audition_travel_hours: "", casting_contact: "Morgan", production_company: "Studio", preparation_instructions: "Prepare sides" });
  });

  it("maps optional values, arrays, dates, numbers, representation and nested metadata", () => {
    const request = formDraftToOpportunityRequest({
      ...createEmptyOpportunityDraft(), role: "Detective", project: "Pilot", location: "New York", description: "Lead role",
      source_type: "Agent Submission", representation_id: "rep-1", archetypes: "Authority, Detective",
      audition_travel_hours: "2.5", audition_deadline: "2026-08-01T18:00", callback_date: "2026-08-02T12:00",
      casting_contact: "Morgan", virtual_audition_link: "https://meet.example", travel_covered: true
    });
    expect(request).toMatchObject({
      representation_id: "rep-1", from_agent: true, archetypes: ["Authority", "Detective"], audition_travel_hours: 2.5,
      submission_deadline: "2026-08-01T18:00", audition_deadline: "2026-08-01T18:00", callback_date: "2026-08-02T12:00",
      source_metadata: { casting_contact: "Morgan", virtual_audition_link: "https://meet.example" },
      production_details: { travel_provided: true }, status: "open"
    });
  });
});
