import type {
  ActorProfile,
  Asset,
  AssetType,
  AuditionJournalEntry,
  Opportunity,
  SelfTape,
  SelfTapeAnalytics,
  Submission,
  SystemCapabilities
} from "../../../types/domain";

export type MaterialOption = Pick<import("../../../types/domain").Asset, "id" | "asset_name" | "asset_type" | "archetype_names">;

export type {
  ActorProfile,
  Asset,
  AssetType,
  AuditionJournalEntry,
  Opportunity,
  SelfTape,
  SelfTapeAnalytics,
  Submission,
  SystemCapabilities
};

export type MaterialFormState = {
  asset_name: string;
  asset_type: AssetType;
  description: string;
  tags: string;
  archetype_names: string;
};

export type SelfTapeFormState = {
  title: string;
  role_type: string;
  archetypes: string;
  file_path: string;
  linked_opportunity_id: string;
  linked_submission_id: string;
  outcome: string;
  notes: string;
  date_created: string;
};
