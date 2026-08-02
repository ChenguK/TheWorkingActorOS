import type {
  ActorProfile,
  AgentRecommendation,
  AuditionReadiness,
  Asset,
  AssetType,
  BreakdownSection,
  DiscoveryPlugin,
  MaterialOpportunityMatch,
  Opportunity,
  RecommendationFeedback,
  Representation,
  SourceResearchItem,
  SubmissionAutomationQueueItem,
  SystemCapabilities
} from "../../../types/domain";

export type {
  ActorProfile,
  AgentRecommendation,
  AuditionReadiness,
  Asset,
  AssetType,
  BreakdownSection,
  DiscoveryPlugin,
  MaterialOpportunityMatch,
  Opportunity,
  RecommendationFeedback,
  Representation,
  SourceResearchItem,
  SubmissionAutomationQueueItem,
  SystemCapabilities
};

export type BreakdownFilter = "Theater" | "FilmTV" | "All" | "TravelExceptions" | "NeedsReview";
export type DiscoveryMode = "Theater" | "FilmTV" | "All";
export type DiscoverySearchMode = "Match My Profile" | "Match My Archetypes" | "Find Stretch Roles" | "Search Specific Archetype";

export type DiscoveryCoverage = {
  approved_active_sources_checked: number;
  approved_active_source_names_checked: string[];
  eligible_sources_skipped: number;
  skipped_source_reasons: Array<{
    source: string;
    provider_key: string;
    reason: string;
    status?: string | null;
    source_research_item_id?: string | null;
    source_status?: SourceResearchItem["status"] | null;
    approved_by_user?: boolean | null;
    source_classification?: string | null;
    url_health_status?: string | null;
    source_usefulness?: string | null;
  }>;
  approved_mode_sources_available: number;
  approved_mode_sources_label: string;
  suggested_sources_awaiting_approval: number;
  coverage_level: "Very Limited" | "Limited" | "Good" | "Broad" | string;
  scope_note: string;
};

export type DiscoveryCandidateReport = {
  page_title?: string | null;
  url?: string | null;
  source?: string | null;
  provider_evidence?: {
    provider: string;
    canonical_url: string;
    title?: string;
    snippet?: string;
    published_date?: string;
  } | null;
  decision?: "Accepted" | "Rejected" | "Parsed" | string;
  rejection_reason?: string | null;
  parser_confidence?: number | null;
};

export type DiscoveryReport = {
  parallel_queries_run: number;
  candidate_pages_returned: number;
  candidate_pages_fetched: number;
  candidate_pages_parsed: number;
  accepted: number;
  rejected: number;
  top_rejection_reasons: Record<string, number>;
  average_parser_confidence?: number | null;
  approved_source_hits: number;
  public_web_hits: number;
  candidates: DiscoveryCandidateReport[];
};

export type DiscoveryRunRequest = {
  mode: DiscoveryMode;
  searchModes: DiscoverySearchMode[];
  specificArchetype?: string;
};

export type PublicWebDiscoverySummary = {
  provider: string;
  configured: boolean;
  run: boolean;
  reason?: string | null;
  search_queries?: string[];
  candidate_pages_found: number;
  candidate_pages_fetched?: number;
  candidate_pages_parsed?: number;
  candidates_rejected: number;
  eligible_breakdowns_added: number;
  sources_suggested_for_approval: number;
};

export type DiscoveryRunResult = {
  discovery_mode: DiscoveryMode;
  search_modes: DiscoverySearchMode[];
  specific_archetype?: string | null;
  opportunities_created: number;
  opportunities_hidden: number;
  opportunities_rejected: number;
  travel_exceptions?: number;
  total_found: number;
  total_rejected: number;
  total_hidden: number;
  total_travel_exceptions?: number;
  total_visible: number;
  target_visible?: number | null;
  limit_reached: boolean;
  rejection_reasons_summary: Record<string, number>;
  sources_run: number;
  coverage: DiscoveryCoverage;
  discovery_report?: DiscoveryReport;
  public_web_search?: PublicWebDiscoverySummary;
};
