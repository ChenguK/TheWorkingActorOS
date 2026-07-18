import type { ActorJournalEntry, CareerDevelopmentTask, Submission } from "../../../types/domain";
import type { OpportunityOption } from "../../breakdowns";
import type { MaterialOption } from "../../materials";

export type JournalEntry = ActorJournalEntry;

export type JournalCreatePayload = {
  date: string;
  event_type: string;
  title: string;
  description: string | null;
  linked_breakdown_id: string | null;
  linked_audition_id: string | null;
  linked_material_id: string | null;
  linked_career_task_id: string | null;
  notes: string | null;
};

export type JournalUpdatePayload = {
  notes: string | null;
};

export type JournalDateGroup = [date: string, entries: ActorJournalEntry[]];

export type JournalLinkedEntity = {
  key: string;
  href: string;
  label: string;
};

export type JournalFormState = {
  date: string;
  event_type: string;
  title: string;
  description: string;
  linked_breakdown_id: string;
  linked_audition_id: string;
  linked_material_id: string;
  linked_career_task_id: string;
  notes: string;
};

export type JournalPanelData = {
  opportunities: OpportunityOption[];
  submissions: Submission[];
  assets: MaterialOption[];
  careerTasks: CareerDevelopmentTask[];
};
