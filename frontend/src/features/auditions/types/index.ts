import type {
  ActorProfile,
  Asset,
  AuditionJournalEntry,
  CallbackEvent,
  Opportunity,
  SelfTapeWorkflow,
  Submission,
  SubmissionStatus
} from "../../../types/domain";

export type {
  ActorProfile,
  Asset,
  AuditionJournalEntry,
  CallbackEvent,
  Opportunity,
  SelfTapeWorkflow,
  Submission,
  SubmissionStatus
};

export type SubmissionFormState = {
  opportunity_id: string;
  asset_ids: string[];
  current_status: SubmissionStatus;
  notes: string;
  audition_text: string;
  tape_due_at: string;
  audition_date: string;
  audition_location: string;
  virtual_audition_link: string;
  self_tape_submission_link: string;
  preparation_instructions: string;
  submission_instructions: string;
  create_calendar: boolean;
  create_journal: boolean;
  create_self_tape: boolean;
  submission_fee: string;
  media_fee: string;
  travel_cost: string;
  housing_cost: string;
  parking_cost: string;
  other_cost: string;
};

export type SelfTapeTaskEditFormState = {
  status: string;
  tape_due_at: string;
  upload_link: string;
  slate_requirements: string;
  wardrobe_notes: string;
  reader_needed: boolean;
};

export type CallbackEventFormState = {
  submission_id: string;
  opportunity_id: string;
  event_name: string;
  event_type: string;
  event_datetime: string;
  location: string;
  is_virtual: boolean;
  preparation_notes: string;
  outcome: string;
  notes: string;
};

export type AuditionNoteFormState = {
  submission_id: string;
  opportunity_id: string;
  date: string;
  preparation_notes: string;
  performance_notes: string;
  casting_notes: string;
  wardrobe_notes: string;
  emotional_notes: string;
  follow_up_notes: string;
};
