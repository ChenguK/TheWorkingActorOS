import type {
  ActorRelationship,
  CommunicationLog,
  Opportunity,
  RelationshipAnalytics,
  RelationshipRole,
  RelationshipStrength,
  Representation,
  Submission
} from "../../../types/domain";

export type {
  ActorRelationship,
  CommunicationLog,
  Opportunity,
  RelationshipAnalytics,
  RelationshipRole,
  RelationshipStrength,
  Representation,
  Submission
};

export type RelationshipFormState = {
  name: string;
  role_title: RelationshipRole;
  company_office: string;
  projects: string;
  notes: string;
  last_contact_date: string;
  relationship_strength: RelationshipStrength;
  linked_outcomes: string;
  linked_opportunity_ids: string[];
  linked_submission_ids: string[];
};

export type CommunicationLogFormState = {
  representation_id: string;
  opportunity_id: string;
  submission_id: string;
  date: string;
  topic: string;
  notes: string;
  follow_up_needed: boolean;
  follow_up_date: string;
};
