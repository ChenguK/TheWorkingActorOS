import type { SourceResearchCategory, SourceResearchItem } from "../../../types/domain";

export type SourceCategory = SourceResearchCategory;
export type SourceStatus = SourceResearchItem["status"];
export type SourceHealth = SourceResearchItem["source_health"] | SourceResearchItem["url_health_status"];
export type SourceUsefulness = SourceResearchItem["source_usefulness"];
export type SourceClassification = SourceResearchItem["source_classification"];
export type SourceApprovalState = "approved" | "approval-required" | "hidden";

export type SourceEditPayload = {
  name: string;
  source_url: string | null;
  base_url: string | null;
  suggested_specific_url: string | null;
  approved_discovery_url: string | null;
  submitted_url: string | null;
  final_resolved_url: string | null;
  category: SourceResearchCategory;
  status: SourceResearchItem["status"];
  approved_by_user: boolean;
  source_classification: SourceResearchItem["source_classification"];
  suggested_classification: SourceResearchItem["source_classification"];
  source_usefulness: SourceResearchItem["source_usefulness"];
  organization_name: string | null;
  notes: string | null;
  reliability_notes: string | null;
  verification_notes: string | null;
  rejection_reason: string | null;
};

export type DiscoveryMode = "Theater" | "FilmTV" | "All";

export type SourceEditFormState = {
  name: string;
  base_url: string;
  suggested_specific_url: string;
  approved_discovery_url: string;
  submitted_url: string;
  final_resolved_url: string;
  category: SourceResearchCategory;
  status: SourceResearchItem["status"];
  approved_by_user: boolean;
  source_classification: SourceResearchItem["source_classification"];
  source_usefulness: SourceResearchItem["source_usefulness"];
  organization_name: string;
  discovered_from_breakdown_id: string;
  discovery_reason: string;
  source_role_match_count: number;
  notes: string;
  reliability_notes: string;
  verification_notes: string;
  rejection_reason: string;
};

