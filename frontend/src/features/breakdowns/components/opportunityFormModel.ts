import { joinList, splitList } from "../../../utils/tags";
import type { Opportunity } from "../types";
import { formStringValue, toDateTimeLocal } from "./BreakdownDetails";

export type OpportunityFormDraft = {
  source_type: Opportunity["source_type"];
  platform: string; from_agent: boolean; representation_id: string; role: string; project: string;
  production_company: string; project_type: string; role_type: string; casting_office: string; casting_contact: string;
  archetypes: string; union: string; rate: string; location: string; audition_location: string;
  travel_covered: boolean; housing_covered: boolean; audition_type: string; audition_travel_hours: string;
  original_post_url: string; audition_deadline: string; callback_date: string; shoot_start_date: string; shoot_end_date: string;
  virtual_audition_link: string; self_tape_submission_link: string; preparation_instructions: string;
  submission_instructions: string; priority: string; notes: string; description: string;
};

export function createEmptyOpportunityDraft(): OpportunityFormDraft {
  return {
    source_type: "Manual Entry", platform: "", from_agent: false, representation_id: "", role: "", project: "",
    production_company: "", project_type: "", role_type: "", casting_office: "", casting_contact: "", archetypes: "",
    union: "SAG-AFTRA", rate: "", location: "", audition_location: "", travel_covered: false, housing_covered: false,
    audition_type: "Self-Tape", audition_travel_hours: "", original_post_url: "", audition_deadline: "", callback_date: "",
    shoot_start_date: "", shoot_end_date: "", virtual_audition_link: "", self_tape_submission_link: "",
    preparation_instructions: "", submission_instructions: "", priority: "Medium", notes: "", description: ""
  };
}

export function opportunityToFormDraft(opportunity: Opportunity): OpportunityFormDraft {
  return {
    source_type: opportunity.source_type ?? "Manual Entry",
    platform: opportunity.platform || formStringValue(opportunity.source_metadata?.platform),
    from_agent: Boolean(opportunity.from_agent), representation_id: opportunity.representation_id || "",
    role: opportunity.role || "", project: opportunity.project || "",
    production_company: formStringValue(opportunity.production_details?.production_company),
    project_type: opportunity.project_type || formStringValue(opportunity.production_details?.project_type),
    role_type: opportunity.role_type || formStringValue(opportunity.role_details?.role_type),
    casting_office: formStringValue(opportunity.production_details?.casting_office),
    casting_contact: formStringValue(opportunity.source_metadata?.casting_contact),
    archetypes: joinList(opportunity.archetypes ?? []), union: opportunity.union || "", rate: opportunity.rate || "",
    location: opportunity.shoot_location || opportunity.location || formStringValue(opportunity.production_details?.shoot_location) || formStringValue(opportunity.production_details?.performance_location),
    audition_location: opportunity.audition_location || formStringValue(opportunity.role_details?.audition_location_name) || formStringValue(opportunity.role_details?.audition_location),
    travel_covered: Boolean(opportunity.travel_covered), housing_covered: Boolean(opportunity.housing_covered),
    audition_type: opportunity.audition_type || "Unknown",
    audition_travel_hours: opportunity.audition_travel_hours == null ? "" : String(opportunity.audition_travel_hours),
    original_post_url: opportunity.original_post_url || "",
    audition_deadline: toDateTimeLocal(opportunity.audition_deadline || opportunity.submission_deadline || formStringValue(opportunity.role_details?.tape_due_date) || formStringValue(opportunity.role_details?.self_tape_due_date)),
    callback_date: toDateTimeLocal(opportunity.callback_date), shoot_start_date: opportunity.shoot_start_date || "", shoot_end_date: opportunity.shoot_end_date || "",
    virtual_audition_link: formStringValue(opportunity.source_metadata?.virtual_audition_link) || formStringValue(opportunity.role_details?.virtual_audition_link),
    self_tape_submission_link: formStringValue(opportunity.source_metadata?.self_tape_submission_link) || formStringValue(opportunity.role_details?.self_tape_submission_link),
    preparation_instructions: formStringValue(opportunity.role_details?.preparation_instructions) || formStringValue(opportunity.role_details?.preparation) || formStringValue(opportunity.production_details?.preparation),
    submission_instructions: formStringValue(opportunity.role_details?.submission_instructions) || formStringValue(opportunity.source_metadata?.submission_instructions),
    priority: opportunity.priority || "Medium", notes: formStringValue(opportunity.source_metadata?.notes) || formStringValue(opportunity.role_details?.notes),
    description: opportunity.description || ""
  };
}

export function formDraftToOpportunityRequest(form: OpportunityFormDraft) {
  return {
    ...form, platform: form.platform || null, representation_id: form.representation_id || null,
    from_agent: form.source_type === "Agent Submission" || form.from_agent,
    project_type: form.project_type || null, role_type: form.role_type || null, archetypes: splitList(form.archetypes),
    rate: form.rate || null, shoot_location: form.location || null, audition_location: form.audition_location || null,
    audition_travel_hours: form.audition_travel_hours ? Number(form.audition_travel_hours) : null,
    original_post_url: form.original_post_url || null, submission_deadline: form.audition_deadline || null,
    audition_deadline: form.audition_deadline || null, callback_date: form.callback_date || null,
    shoot_start_date: form.shoot_start_date || null, shoot_end_date: form.shoot_end_date || null,
    source_metadata: {
      platform: form.platform || null, casting_contact: form.casting_contact || null,
      virtual_audition_link: form.virtual_audition_link || null, self_tape_submission_link: form.self_tape_submission_link || null,
      submission_instructions: form.submission_instructions || null, notes: form.notes || null
    },
    production_details: {
      production_company: form.production_company || null, casting_office: form.casting_office || null,
      project_type: form.project_type || null, shoot_location: form.location || null, performance_location: form.location || null,
      travel_provided: form.travel_covered, housing_provided: form.housing_covered
    },
    role_details: {
      role_name: form.role || null, role_type: form.role_type || null, character_description: form.description || null,
      audition_type: form.audition_type, tape_due_date: form.audition_deadline || null,
      self_tape_due_date: form.audition_deadline || null, audition_date: form.audition_deadline || null,
      audition_location_name: form.audition_location || null, preparation: form.preparation_instructions || null,
      preparation_instructions: form.preparation_instructions || null, submission_instructions: form.submission_instructions || null,
      self_tape_submission_link: form.self_tape_submission_link || null, virtual_audition_link: form.virtual_audition_link || null,
      notes: form.notes || null
    },
    status: "open"
  };
}
