export type ActorProfile = {
  id: string;
  name: string;
  sag_status: string;
  union_status: string;
  current_location: string;
  playable_age_min: number;
  playable_age_max: number;
  secondary_playable_age_min?: number | null;
  secondary_playable_age_max?: number | null;
  skills: string[];
  gender_identities: string[];
  gender_expression?: string | null;
  pronouns?: string | null;
  ethnicities: string[];
  racial_identities: string[];
  nationalities: string[];
  languages: string[];
  accents: string[];
  disability_identities: string[];
  included_role_types: string[];
  excluded_role_types: string[];
  accessibility_notes?: string | null;
  demographic_notes?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
};

export type TravelPreference = {
  id: string;
  actor_profile_id: string;
  max_local_drive_time: number;
  extended_drive_time: number;
  flight_allowed: boolean;
  housing_required: boolean;
  international_allowed: boolean;
  audition_max_drive_time: number;
  audition_virtual_allowed: boolean;
  audition_self_tape_allowed: boolean;
  working_as_local_drive_time: number;
  working_as_local_housing_self_provided: boolean;
  require_travel_housing_over_local_drive: boolean;
  audition_notes?: string | null;
  working_notes?: string | null;
  created_at: string;
  updated_at: string;
};

export type AssetType = "Headshot" | "Reel" | "Slate" | "Resume";

export type Asset = {
  id: string;
  actor_profile_id: string;
  asset_name: string;
  asset_type: AssetType;
  local_file_path: string;
  original_filename?: string | null;
  mime_type?: string | null;
  file_size_bytes?: number | null;
  description?: string | null;
  tags: string[];
  archetype_names: string[];
  ai_suggested_tags: string[];
  ai_suggested_archetypes: string[];
  analysis_status: string;
  analysis_explanation?: string | null;
  upload_date?: string | null;
  last_used_date?: string | null;
  last_updated_date?: string | null;
  expiration_warning_date?: string | null;
  freshness_status: "Current" | "Aging" | "Needs Review" | "Outdated";
  created_at: string;
  updated_at: string;
};

export type CapabilityState = {
  state: string;
  explanation: string;
  safe_fallback: string;
};

export type SystemCapabilities = {
  flags: {
    travel_provider_configured: boolean;
    ai_configured: boolean;
    scheduler_configured: boolean;
    notifications_configured: boolean;
    source_discovery_configured: boolean;
    public_profile_import_configured: boolean;
  };
  states: Record<string, CapabilityState>;
  integrations: Array<{
    id: string;
    name: string;
    status: string;
    configured: boolean;
    what_it_enables: string;
    fallback_behavior: string;
    setup_instructions: string;
    provider?: string | null;
  }>;
  labels: {
    not_configured: string;
    needs_info: string;
    manual_override: string;
    user_entered_estimate: string;
    add_data_first: string;
    insufficient_data: string;
    dashboard_alerts_only: string;
    manual_check_in: string;
    suggested_tags: string;
    deterministic_recommendation: string;
  };
};

export type CharacterProfile = {
  id: string;
  breakdown_id: string;
  breakdown_role_id: string;
  role_name: string;
  billing?: string | null;
  primary_archetypes: string[];
  secondary_archetypes: string[];
  archetype_confidence_scores: Array<{
    archetype: string;
    confidence: number;
    tier: "Primary" | "Secondary";
    evidence: string[];
  }>;
  personality_traits: string[];
  emotional_traits: string[];
  relationships: string[];
  motivations: string[];
  internal_conflict?: string | null;
  external_conflict?: string | null;
  emotional_arc?: string | null;
  genre?: string | null;
  comedic_level: number;
  dramatic_level: number;
  physical_requirements: string[];
  vocal_requirements: string[];
  movement_requirements: string[];
  casting_language: string[];
  recommended_materials: string[];
  ai_summary?: string | null;
  created_at: string;
  updated_at: string;
};

export type CastingLanguage = {
  id: string;
  breakdown_id: string;
  breakdown_role_id: string;
  original_text: string;
  billing?: string | null;
  age_range?: string | null;
  gender?: string | null;
  ethnicity?: string | null;
  union?: string | null;
  compensation?: string | null;
  special_notes: string[];
  created_at: string;
  updated_at: string;
};

export type BreakdownRole = {
  id: string;
  breakdown_id: string;
  role_name: string;
  role_type?: string | null;
  billing?: string | null;
  billing_or_role_type?: string | null;
  character_description?: string | null;
  gender_presentation?: string | null;
  ethnicity_or_cultural_background?: string | null;
  playable_age_min?: number | null;
  playable_age_max?: number | null;
  height_requirements?: string | null;
  vocal_requirements?: string | null;
  dance_requirements?: string | null;
  movement_requirements?: string | null;
  language_requirements?: string | null;
  special_skills?: string | null;
  preparation_notes?: string | null;
  union_status?: string | null;
  role_notes?: string | null;
  fit_status: "Strong Fit" | "Possible Fit" | "Stretch Fit" | "Not Fit" | "Needs Review";
  fit_score: number;
  fit_explanation?: string | null;
  confidence_score: number;
  extracted_facts: Record<string, unknown>;
  ai_inference: Record<string, unknown>;
  character_profile?: CharacterProfile | null;
  casting_language?: CastingLanguage | null;
  created_at: string;
  updated_at: string;
};

export type BreakdownSection = {
  id: string;
  breakdown_id: string;
  section_type: "Production Details" | "Audition Information" | "Preparation" | "Roles" | "Character Descriptions" | "Dates" | "Locations" | "Submission Instructions" | "Contact" | "Additional Notes";
  heading?: string | null;
  raw_text: string;
  parsed_json: Record<string, unknown>;
  confidence_score: number;
  display_order: number;
  created_at: string;
  updated_at: string;
};

export type BreakdownParseRun = {
  id: string;
  breakdown_id: string;
  parser_version: string;
  parse_mode: "Standard Parse" | "Deep Parse" | "Manual Paste Reparse";
  started_at: string;
  completed_at?: string | null;
  status: "running" | "succeeded" | "failed";
  overall_confidence: number;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
};

export type Opportunity = {
  id: string;
  opportunity_source_id?: string | null;
  casting_office_id?: string | null;
  representation_id?: string | null;
  casting_contact_id?: string | null;
  source_type: "Platform Discovery" | "Agent Submission" | "Direct Email" | "Social Media" | "Production Website" | "Manual Entry" | "Other";
  platform?: string | null;
  from_agent: boolean;
  role: string;
  project: string;
  project_type?: string | null;
  role_type?: string | null;
  archetypes: string[];
  union: string;
  rate?: string | null;
  location: string;
  shoot_location?: string | null;
  audition_location?: string | null;
  travel_covered?: boolean | null;
  housing_covered?: boolean | null;
  description: string;
  original_post_url?: string | null;
  status: "open" | "closed" | "archived";
  normalized_key?: string | null;
  category?: string | null;
  source_reliability_score: number;
  is_duplicate: boolean;
  is_demo_data: boolean;
  breakdown_classification: "Acting Role" | "Background Role" | "Voiceover Role" | "Theater Role" | "Commercial Role" | "Non-Acting Job" | "Crew Job" | "Unknown";
  rejection_reason?: string | null;
  highlighted_text_as_rejection_reason?: string | null;
  source_metadata: Record<string, unknown>;
  production_details: Record<string, unknown>;
  role_details: Record<string, unknown>;
  extracted_facts: Record<string, unknown>;
  ai_inference: Record<string, unknown>;
  ai_summary?: string | null;
  audition_type: "Self-Tape" | "Virtual" | "In-Person" | "Unknown";
  audition_travel_hours?: number | null;
  visibility_status: "visible" | "hidden" | "discarded" | "travel_exception";
  hidden_reason?: string | null;
  hidden_by_rule?: string | null;
  audition_drive_time?: number | null;
  manual_review_required: boolean;
  submission_deadline?: string | null;
  audition_deadline?: string | null;
  callback_date?: string | null;
  shoot_start_date?: string | null;
  shoot_end_date?: string | null;
  priority: "Low" | "Medium" | "High" | "Urgent";
  urgency_score: number;
  quality_score: number;
  quality_explanation?: string | null;
  confidence_level: "Low" | "Medium" | "High";
  risk_level: "Low" | "Medium" | "High";
  risk_explanation?: string | null;
  demographic_match_status: "Match" | "Needs Review" | "Not a Match";
  demographic_match_explanation?: string | null;
  demographic_match_details: {
    checks?: Array<{
      label: string;
      status: string;
      compatibility_label?: string;
      compatibility_score?: number;
      detected_requirements?: string[];
      profile_values?: string[];
      explanation?: string;
    }>;
    detected_requirements?: unknown[];
    profile_source?: string;
  };
  watchlist_match_names: Array<{
    id: string;
    title: string;
    category: string;
    priority: "Low" | "Medium" | "High";
    matched_terms: string[];
  }>;
  watchlist_match_count: number;
  watchlist_notification?: string | null;
  already_tracked: boolean;
  tracked_submission_id?: string | null;
  breakdown_roles: BreakdownRole[];
  breakdown_sections: BreakdownSection[];
  breakdown_parse_runs: BreakdownParseRun[];
  created_at: string;
  updated_at: string;
};

export type MaterialMatchAsset = {
  asset_id: string;
  asset_name: string;
  asset_type: AssetType;
  matched_terms: string[];
  reason: string;
};

export type MaterialOpportunityMatch = {
  opportunity: Opportunity;
  score: number;
  match_type: "Strong Material Match" | "Good Material Match" | "Possible Material Match";
  matched_assets: MaterialMatchAsset[];
  matched_terms: string[];
  missing_material_types: AssetType[];
  explanation: string;
};

export type Representation = {
  id: string;
  actor_profile_id: string;
  agency_name: string;
  agent_name?: string | null;
  agent_email?: string | null;
  agent_phone?: string | null;
  agency_website?: string | null;
  representation_type: "Theatrical" | "Commercial" | "Voiceover" | "Print" | "Manager" | "Other";
  market: string[];
  notes?: string | null;
  active: boolean;
  start_date?: string | null;
  end_date?: string | null;
  created_at: string;
  updated_at: string;
};

export type ActingCreditCategory =
  | "Television"
  | "Film"
  | "Commercial"
  | "Theater"
  | "New Media"
  | "Voiceover"
  | "Industrial"
  | "Print"
  | "Training"
  | "Special Skills"
  | "Other";

export type ActingCredit = {
  id: string;
  actor_profile_id: string;
  category: ActingCreditCategory;
  section_enabled: boolean;
  section_order: number;
  display_order: number;
  highlighted: boolean;
  project_title?: string | null;
  role_or_character?: string | null;
  role_type?: string | null;
  production_company?: string | null;
  network_or_distributor?: string | null;
  director?: string | null;
  episode_title?: string | null;
  season_episode?: string | null;
  year?: string | null;
  union_status?: string | null;
  class_or_program?: string | null;
  instructor?: string | null;
  institution?: string | null;
  skill_name?: string | null;
  skill_category?: string | null;
  proficiency?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
};

export type SubmissionStatus =
  | "Submitted"
  | "Requested"
  | "Self-Tape Callback"
  | "In-Person Callback"
  | "Pinned"
  | "Booked"
  | "Passed"
  | "No Response";

export type SubmissionStatusHistory = {
  id: string;
  status: SubmissionStatus;
  notes?: string | null;
  occurred_at: string;
};

export type Submission = {
  id: string;
  actor_profile_id: string;
  opportunity_id: string;
  current_status: SubmissionStatus;
  notes?: string | null;
  submitted_at?: string | null;
  submission_fee: number;
  media_fee: number;
  travel_cost: number;
  housing_cost: number;
  parking_cost: number;
  other_cost: number;
  total_cost: number;
  opportunity?: Opportunity | null;
  assets: Asset[];
  status_history: SubmissionStatusHistory[];
  created_at: string;
  updated_at: string;
};

export type AgentRecommendation = {
  id: string;
  opportunity_id: string;
  actor_profile_id: string;
  agent_version: string;
  score: number;
  match_type: "Strong Match" | "Growth Match" | "High-Risk / High-Reward";
  display_opportunity: boolean;
  explanation: string;
  score_breakdown: Record<string, number>;
  audition_type: "Self-Tape" | "Virtual" | "In-Person" | "Unknown";
  audition_travel_hours?: number | null;
  audition_decision: string;
  audition_explanation: string;
  travel_explanation: string;
  archetype_explanation: string;
  asset_explanation: string;
  submission_strategy_explanation: string;
  confidence_level: "Low" | "Medium" | "High";
  risk_level: "Low" | "Medium" | "High";
  risk_explanation?: string | null;
  recommended_headshot_id?: string | null;
  recommended_reel_id?: string | null;
  recommended_resume_id?: string | null;
  recommended_slate_id?: string | null;
  recommended_note: string;
  created_at: string;
  updated_at: string;
};

export type LearningInsight = {
  id: string;
  actor_profile_id: string;
  trends: Record<string, unknown>;
  recommendation_weights: Record<string, unknown>;
  explanation: string;
  created_at: string;
  updated_at: string;
};

export type RecommendationFeedback = {
  id: string;
  actor_profile_id: string;
  opportunity_id: string;
  recommendation_id?: string | null;
  feedback_type: "This Fits Me" | "Not My Type" | "Interesting Stretch" | "Save For Later";
  fit_reasons: string[];
  notes?: string | null;
  created_at: string;
  updated_at: string;
};

export type CareerMemory = {
  id: string;
  actor_profile_id?: string | null;
  current_career_goals: string[];
  current_focus?: string | null;
  stretch_archetypes: string[];
  preferred_project_types: string[];
  preferred_markets: string[];
  unavailable_dates: string[];
  career_notes?: string | null;
  executive_notes?: string | null;
  created_at: string;
  updated_at: string;
};

export type ExecutiveBrief = {
  id: string;
  actor_profile_id?: string | null;
  period_start: string;
  period_end: string;
  brief_type: string;
  new_matching_breakdowns: unknown[];
  submissions_completed: unknown[];
  callbacks_received: unknown[];
  bookings: unknown[];
  materials_used: unknown[];
  career_progress: unknown[];
  recommended_priorities: unknown[];
  summary: string;
  created_at: string;
  updated_at: string;
};

export type AvailabilityBlock = {
  id: string;
  actor_profile_id?: string | null;
  start_date: string;
  end_date: string;
  block_type: string;
  title: string;
  notes?: string | null;
  created_at: string;
  updated_at: string;
};

export type ProfessionalEquipmentProfile = {
  id: string;
  actor_profile_id?: string | null;
  cameras: string[];
  lighting: string[];
  audio_equipment: string[];
  backdrops: string[];
  editing_software: string[];
  teleprompter: boolean;
  reader_availability?: string | null;
  internet_upload_speed?: string | null;
  home_audition_space?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
};

export type CallbackEvent = {
  id: string;
  submission_id?: string | null;
  opportunity_id?: string | null;
  event_name: string;
  event_type: string;
  event_datetime?: string | null;
  location?: string | null;
  is_virtual: boolean;
  preparation_notes?: string | null;
  outcome?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
};

export type CommunicationLog = {
  id: string;
  representation_id?: string | null;
  opportunity_id?: string | null;
  submission_id?: string | null;
  date: string;
  topic: string;
  notes?: string | null;
  follow_up_needed: boolean;
  follow_up_date?: string | null;
  created_at: string;
  updated_at: string;
};

export type MaterialPerformance = {
  asset_id: string;
  asset_name: string;
  asset_type: AssetType;
  times_recommended: number;
  times_selected: number;
  submissions: number;
  callbacks: number;
  bookings: number;
  callback_rate: number;
  booking_rate: number;
};

export type CareerRecommendation = {
  id: string;
  actor_profile_id: string;
  strengths: unknown[];
  growth_opportunities: unknown[];
  archetypes_to_expand: unknown[];
  recommended_headshots: unknown[];
  recommended_role_types: unknown[];
  strong_match_roles: unknown[];
  growth_match_roles: unknown[];
  stretch_roles: Array<Record<string, unknown>>;
  explanation: string;
  created_at: string;
  updated_at: string;
};

export type CareerSwotAnalysis = {
  id: string;
  actor_profile_id: string;
  strengths: string[];
  weaknesses: string[];
  opportunities: string[];
  threats: string[];
  explanation: string;
  created_at: string;
  updated_at: string;
};

export type CareerTask = {
  id: string;
  career_recommendation_id?: string | null;
  title: string;
  description: string;
  priority: string;
  estimated_impact: string;
  related_archetype: string;
  target_roles: string[];
  status: string;
  created_at: string;
  updated_at: string;
};

export type CareerDevelopmentTask = {
  id: string;
  title: string;
  description: string;
  priority: "Low" | "Medium" | "High";
  status: "Not Started" | "In Progress" | "Completed";
  related_archetype?: string | null;
  target_role_types: string[];
  estimated_impact: "Low" | "Medium" | "High";
  reason?: string | null;
  supported_archetypes: string[];
  created_by_agent: boolean;
  created_at: string;
  updated_at: string;
  completed_at?: string | null;
  archetype_id?: string | null;
  asset_id?: string | null;
  career_recommendation_id?: string | null;
};

export type DiscoveryPlugin = {
  name: string;
  priority_rank: number;
  source_type: string;
  implementation_key: string;
  reliability_score: number;
  category: string;
  tier: number;
  enabled: boolean;
};

export type DiscoveryProviderSettings = {
  id: string;
  provider_key: string;
  display_name: string;
  tier: number;
  category: string;
  source_type: string;
  enabled: boolean;
  poll_frequency_minutes: number;
  priority: number;
  authentication_method: string;
  supported_authentication_methods: string[];
  reliability_score: number;
  notes?: string | null;
  provider_metadata: Record<string, unknown>;
  health_status: string;
  health_message?: string | null;
  last_health_check_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type SubmissionAutomationQueueItem = {
  id: string;
  submission_id?: string | null;
  opportunity_id: string;
  recommendation_id?: string | null;
  adapter_key: string;
  submission_mode: string;
  approval_status: string;
  automation_status: string;
  retry_count: number;
  max_retries: number;
  error_message?: string | null;
  prepared_payload: Record<string, unknown>;
  execution_log: Array<Record<string, unknown>>;
  approved_at?: string | null;
  executed_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type AuditionCalendarEventType =
  | "Submission Due"
  | "Self-Tape Due"
  | "Virtual Callback"
  | "In-Person Callback"
  | "Fitting"
  | "Shoot"
  | "Meeting"
  | "Other";

export type AuditionCalendarEvent = {
  id: string;
  title: string;
  event_type: AuditionCalendarEventType;
  opportunity_id?: string | null;
  submission_id?: string | null;
  start_datetime: string;
  end_datetime?: string | null;
  location?: string | null;
  is_virtual: boolean;
  notes?: string | null;
  created_at: string;
  updated_at: string;
};

export type ActorJournalEntry = {
  id: string;
  date: string;
  event_type: string;
  title: string;
  description?: string | null;
  linked_breakdown_id?: string | null;
  linked_audition_id?: string | null;
  linked_material_id?: string | null;
  linked_career_task_id?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
};

export type OperationsAlert = {
  alert_type: string;
  severity: string;
  title: string;
  message: string;
  related_id?: string | null;
};

export type CostDashboard = {
  total_spent: number;
  cost_per_callback: number;
  cost_per_booking: number;
  costs_by_platform: Record<string, number>;
  costs_by_archetype: Record<string, number>;
  subscriptions: Record<string, number>;
  subscription_monthly_total: number;
  subscription_annual_total: number;
  estimated_monthly_subscription_spend: number;
  submission_fees_total: number;
  media_fees_total: number;
  travel_housing_total: number;
  other_costs_total: number;
};

export type FreshnessWarning = {
  asset_id: string;
  asset_name: string;
  asset_type: string;
  freshness_status: string;
  message: string;
};

export type OperationsDashboard = {
  alerts: OperationsAlert[];
  upcoming_events: AuditionCalendarEvent[];
  cost_dashboard: CostDashboard;
  freshness_warnings: FreshnessWarning[];
};

export type AssetPerformance = {
  asset_id: string;
  asset_name: string;
  asset_type: AssetType | string;
  submissions: number;
  positive_outcomes: number;
  callback_rate: number;
};

export type CommandCenterCard = Record<string, string | number | null | undefined>;

export type ExecutivePriority = {
  rank: number;
  title: string;
  reason: string;
  category: string;
  action_label: string;
  target_path: string;
  urgency: number;
};

export type CastingPlatformSubscription = {
  id: string;
  platform_name: string;
  has_subscription: boolean;
  subscription_level?: string | null;
  monthly_cost?: number | null;
  annual_cost?: number | null;
  renewal_date?: string | null;
  notes?: string | null;
  active: boolean;
  created_at: string;
  updated_at: string;
};

export type DailyPlatformCheckIn = {
  id: string;
  platform_subscription_id: string;
  platform_name: string;
  has_subscription: boolean;
  subscription_level?: string | null;
  active: boolean;
  check_date: string;
  timezone: string;
  checked_today: boolean;
  checked_at?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
};

export type ActorCommandCenter = {
  today_opportunities: CommandCenterCard[];
  executive_priorities: ExecutivePriority[];
  chief_of_staff_priorities?: ExecutivePriority[];
  since_last_visit?: CommandCenterCard[];
  upcoming_attention?: CommandCenterCard[];
  today_career_recommendation?: CommandCenterCard | null;
  platform_check_ins?: DailyPlatformCheckIn[];
  queued_submissions: CommandCenterCard[];
  upcoming_deadlines: CommandCenterCard[];
  outcome_nudges: CommandCenterCard[];
  career_tasks: CommandCenterCard[];
  material_gaps: CommandCenterCard[];
  asset_performance: AssetPerformance[];
};

export type SelfTapeWorkflow = {
  id: string;
  opportunity_id: string;
  submission_id?: string | null;
  status: "Not Started" | "In Progress" | "Completed" | string;
  sides_file_path?: string | null;
  reader_needed: boolean;
  tape_due_at?: string | null;
  slate_requirements?: string | null;
  wardrobe_notes?: string | null;
  upload_link?: string | null;
  final_file_path?: string | null;
  created_at: string;
  updated_at: string;
};

export type ArchetypePerformance = {
  archetype: string;
  submissions: number;
  requested: number;
  self_tape_callbacks: number;
  in_person_callbacks: number;
  pinned: number;
  booked: number;
  passed: number;
  no_response: number;
  callback_rate: number;
  booking_rate: number;
};

export type ArchetypePerformanceDashboard = {
  metrics: ArchetypePerformance[];
  best_performing_archetypes: string[];
  underused_archetypes: string[];
  overused_archetypes: string[];
  high_potential_stretch_archetypes: string[];
};

export type CastingOffice = {
  id: string;
  name: string;
  source_platform?: string | null;
  project_history: unknown[];
  submission_history: unknown[];
  callback_history: unknown[];
  booking_history: unknown[];
  notes?: string | null;
  created_at: string;
  updated_at: string;
};

export type CastingOfficeAnalytics = {
  casting_office_id?: string | null;
  casting_office: string;
  submissions: number;
  callbacks: number;
  bookings: number;
  callback_rate: number;
  booking_rate: number;
  best_materials: string[];
  stretch_response_signal: string;
};

export type RoleSimilarity = {
  source_role: string;
  similar_roles: Array<Record<string, string>>;
  explanation: string;
};

export type AuditionPreparationBrief = {
  id: string;
  opportunity_id: string;
  submission_id?: string | null;
  brief: Record<string, unknown>;
  explanation: string;
  created_at: string;
  updated_at: string;
};

export type MaterialCreationPlan = {
  id: string;
  career_task_id?: string | null;
  missing_asset: string;
  target_archetype?: string | null;
  plan_status: "Pending Review" | "Approved" | "Denied" | string;
  plan: Record<string, unknown>;
  explanation: string;
  created_at: string;
  updated_at: string;
};

export type ScriptSource = {
  id: string;
  name: string;
  url?: string | null;
  source_type: string;
  rights_status: "Public Domain" | "Royalty-Free" | "Original / User-Owned" | "Licensed" | "Permission Required" | "Unknown" | string;
  notes?: string | null;
  approved: boolean;
  created_at: string;
  updated_at: string;
};

export type SceneCandidate = {
  id: string;
  script_source_id?: string | null;
  career_task_id?: string | null;
  title: string;
  result_type: "Specific Scene" | "Specific Monologue" | "Script Library" | "Resource Guide" | "Music / Sound Library" | "Dead / Fetch Failed" | "Rights Unknown" | "Not Useful" | string;
  rights_status: string;
  source_url?: string | null;
  logline: string;
  scene_brief: Record<string, unknown>;
  action_status: "Candidate" | "Saved" | "Permission Requested" | "Original Brief" | string;
  notes?: string | null;
  created_at: string;
  updated_at: string;
};

export type CareerPathSimulation = {
  id: string;
  actor_profile_id: string;
  goal: string;
  result: Record<string, unknown>;
  explanation: string;
  created_at: string;
  updated_at: string;
};

export type IntelligenceDashboard = {
  archetype_performance: ArchetypePerformanceDashboard;
  casting_office_analytics: CastingOfficeAnalytics[];
  role_similarity: RoleSimilarity[];
};

export type RelationshipRole =
  | "Casting Director"
  | "Casting Office"
  | "Producer"
  | "Director"
  | "Writer"
  | "Agent"
  | "Manager"
  | "Coach";

export type RelationshipStrength = "Cold" | "Warm" | "Strong" | "Champion";

export type ActorRelationship = {
  id: string;
  name: string;
  role_title: RelationshipRole;
  company_office?: string | null;
  projects: string[];
  notes?: string | null;
  last_contact_date?: string | null;
  relationship_strength: RelationshipStrength;
  linked_outcomes: string[];
  linked_opportunity_ids: string[];
  linked_submission_ids: string[];
  created_at: string;
  updated_at: string;
};

export type RelationshipAnalytics = {
  rows: Array<{
    relationship_id: string;
    name: string;
    role_title: string;
    company_office?: string | null;
    relationship_strength: string;
    submissions: number;
    callbacks: number;
    pins: number;
    bookings: number;
    repeat_opportunities: number;
    callback_rate: number;
    booking_rate: number;
    correlation_signal: string;
  }>;
  strongest_relationships: string[];
  relationship_agent_explanation: string;
};

export type SelfTape = {
  id: string;
  title: string;
  role_type?: string | null;
  archetypes: string[];
  file_path: string;
  linked_opportunity_id?: string | null;
  linked_submission_id?: string | null;
  outcome?: string | null;
  notes?: string | null;
  date_created: string;
  created_at: string;
  updated_at: string;
};

export type SelfTapeAnalytics = {
  by_archetype: Array<Record<string, unknown>>;
  by_outcome: Array<Record<string, unknown>>;
  best_performing_tapes: SelfTape[];
  underused_tapes: SelfTape[];
};

export type AuditionJournalEntry = {
  id: string;
  submission_id?: string | null;
  opportunity_id?: string | null;
  date: string;
  preparation_notes?: string | null;
  performance_notes?: string | null;
  casting_notes?: string | null;
  wardrobe_notes?: string | null;
  emotional_notes?: string | null;
  follow_up_notes?: string | null;
  created_at: string;
  updated_at: string;
};

export type AuditionReadiness = {
  opportunity_id: string;
  opportunity_label: string;
  readiness_label: "Ready" | "Mostly Ready" | "Needs Materials" | "Stretch" | "Not Recommended" | string;
  readiness_percentage: number;
  score_breakdown: Record<string, number>;
  missing_materials: string[];
  character_archetypes: string[];
  character_parsing_confidence: number;
  character_parsing_status: string;
  debug_score_available: boolean;
  explanation: string;
};

export type IndustryTrendInsight = {
  trend_type: string;
  label: string;
  count: number;
  insight: string;
  recommended_action?: string | null;
};

export type IndustryTrendDashboard = {
  role_type: IndustryTrendInsight[];
  archetype: IndustryTrendInsight[];
  project_type: IndustryTrendInsight[];
  union_status: IndustryTrendInsight[];
  location: IndustryTrendInsight[];
  audition_type: IndustryTrendInsight[];
  submission_source: IndustryTrendInsight[];
  submitted_project_type: IndustryTrendInsight[];
  callback_archetype: IndustryTrendInsight[];
  booking_archetype: IndustryTrendInsight[];
  insights: string[];
  pattern_stage: string;
  stage: string;
  tracked_breakdowns_or_auditions: number;
  submission_count: number;
  outcome_count: number;
  unlock_message: string;
};

export type QuarterlyCareerReview = {
  id: string;
  actor_profile_id: string;
  year: number;
  quarter: number;
  report: Record<string, unknown>;
  explanation: string;
  created_at: string;
  updated_at: string;
};

export type DreamTargetType = "Role" | "Show" | "Genre" | "Casting Office" | "Studio" | "Archetype";

export type DreamRoleTarget = {
  id: string;
  actor_profile_id: string;
  target_type: DreamTargetType;
  name: string;
  description?: string | null;
  target_archetypes: string[];
  target_genres: string[];
  target_offices: string[];
  notes?: string | null;
  created_at: string;
  updated_at: string;
};

export type DreamRoleReadiness = {
  target: DreamRoleTarget;
  current_readiness_score: number;
  missing_materials: string[];
  recommended_actions: string[];
  related_career_development_tasks: Array<Record<string, unknown>>;
  explanation: string;
};

export type PlatformName = "Actors Access" | "Casting Networks" | "Casting Frontier" | "Other";
export type PlatformImportMethod =
  | "Manual Copy/Paste"
  | "Uploaded PDF"
  | "Uploaded Screenshot"
  | "Uploaded CSV"
  | "User-Provided Text"
  | "Manual Guided Form";

export type PlatformProfile = {
  id: string;
  actor_profile_id?: string | null;
  platform_name: PlatformName;
  profile_url?: string | null;
  imported_at: string;
  import_method: PlatformImportMethod;
  raw_import_text: string;
  import_status: "Draft" | "Needs Review" | "Approved" | "Rejected";
  user_approved: boolean;
  parsed_profile: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type PlatformAssetMapping = {
  id: string;
  platform_name: PlatformName;
  platform_asset_name: string;
  asset_type: AssetType | "Other";
  local_asset_id?: string | null;
  tags: string[];
  archetypes: string[];
  notes?: string | null;
  created_at: string;
  updated_at: string;
};

export type PublicProfileImport = {
  id: string;
  platform_name: PlatformName;
  profile_url: string;
  import_method: "Public/shareable profile URL";
  imported_at: string;
  raw_visible_text: string;
  parsed_data_json: Record<string, unknown>;
  import_status: "Draft" | "Needs Review" | "Approved" | "Rejected" | "Blocked";
  user_approved: boolean;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
};

export type SupervisedBreakdownImport = {
  id: string;
  actor_profile_id?: string | null;
  approved_opportunity_id?: string | null;
  platform_name: "Actors Access" | "Casting Networks" | "Casting Frontier";
  source_url?: string | null;
  imported_at: string;
  raw_visible_text: string;
  parsed_data_json: Record<string, unknown>;
  import_status: "Draft" | "Approved" | "Rejected" | "Needs Review" | "Blocked";
  user_approved: boolean;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
};

export type SourceResearchCategory =
  | "Public casting site"
  | "Casting office"
  | "Film commission"
  | "Social media account"
  | "Production company"
  | "Theater company"
  | "Talent platform"
  | "Other";

export type SourceResearchStatus =
  | "Suggested"
  | "Researching"
  | "Approved"
  | "Rejected"
  | "Active"
  | "Paused"
  | "Deleted";

export type SourceResearchItem = {
  id: string;
  name: string;
  source_url?: string | null;
  base_url?: string | null;
  suggested_specific_url?: string | null;
  approved_discovery_url?: string | null;
  category: SourceResearchCategory;
  status: SourceResearchStatus;
  reliability_notes?: string | null;
  user_rating?: number | null;
  last_researched_date?: string | null;
  last_checked_date?: string | null;
  notes?: string | null;
  suggested_by_ai: boolean;
  approved_by_user: boolean;
  deleted: boolean;
  deleted_at?: string | null;
  rejection_reason?: string | null;
  rejected_by_user: boolean;
  previous_status?: string | null;
  provider_key?: string | null;
  added_to_discovery_at?: string | null;
  source_health: "Unchecked" | "Active" | "Dead / Unavailable Domain" | "Placeholder Website" | "No Meaningful Content" | "Blocked" | "Needs Review";
  suggested_classification: "Valid Breakdown Source" | "Casting Office" | "Production Company" | "Regional Resource" | "Watch List Source" | "Rejected" | "Not Useful" | "Relationship Source" | "Needs Review";
  health_reason?: string | null;
  http_status?: number | null;
  page_title?: string | null;
  redirect_target?: string | null;
  visible_text_excerpt?: string | null;
  organization_name?: string | null;
  submitted_url?: string | null;
  final_resolved_url?: string | null;
  url_health_status: "Unchecked" | "Active" | "Dead / Unavailable Domain" | "Placeholder Website" | "No Meaningful Content" | "Blocked" | "Needs Review";
  organization_legitimacy: "Recognized Organization" | "Unverified Organization" | string;
  source_usefulness: "Useful Breakdown Source" | "Useful Non-Breakdown Source" | "Not Useful" | "Needs Review" | string;
  source_classification: "Valid Breakdown Source" | "Casting Office" | "Production Company" | "Regional Resource" | "Watch List Source" | "Rejected" | "Not Useful" | "Relationship Source" | "Needs Review";
  verification_notes?: string | null;
  discovered_from_breakdown_id?: string | null;
  discovery_reason?: string | null;
  source_role_match_count: number;
  created_at: string;
  updated_at: string;
};

export type SupervisedBrowserStatus = {
  active: boolean;
  platform_name?: string | null;
  current_url?: string | null;
  message: string;
};

export type DashboardWidgetSize = "small" | "medium" | "large";

export type DashboardWidget = {
  id: string;
  actor_profile_id?: string | null;
  widget_id: string;
  display_name: string;
  enabled: boolean;
  sort_order: number;
  size: DashboardWidgetSize;
  created_at: string;
  updated_at: string;
};

export type FocusModeName =
  | "Audition Mode"
  | "Career Building Mode"
  | "Casting Goals Mode"
  | "Relationship Mode"
  | "Analytics Mode";

export type FocusModePreference = {
  id: string;
  actor_profile_id?: string | null;
  active_mode: FocusModeName;
  created_at: string;
  updated_at: string;
};

export type CastingGoalType =
  | "TV"
  | "Film"
  | "Streaming"
  | "Guest Star"
  | "Recurring"
  | "Lead"
  | "Supporting"
  | "Commercial"
  | "Voiceover"
  | "Theater"
  | "Other";

export type CastingGoalStatus = "Active" | "Paused" | "Completed" | "Archived";

export type CastingGoal = {
  id: string;
  actor_profile_id?: string | null;
  title: string;
  goal_type: CastingGoalType;
  target_archetypes: string[];
  target_role_types: string[];
  target_project_types: string[];
  target_markets: string[];
  target_casting_offices: string[];
  target_deadline?: string | null;
  priority: "Low" | "Medium" | "High";
  status: CastingGoalStatus;
  notes?: string | null;
  created_at: string;
  updated_at: string;
};

export type WatchListCategory =
  | "Studios"
  | "Networks"
  | "Streaming Platforms"
  | "Shows"
  | "Genres"
  | "Project Types"
  | "Casting Offices"
  | "Casting Directors"
  | "Production Companies"
  | "Archetypes"
  | "Role Types"
  | "Markets"
  | "Cities"
  | "States"
  | "Countries"
  | "Keywords";

export type WatchList = {
  id: string;
  actor_profile_id?: string | null;
  title: string;
  category: WatchListCategory;
  terms: string[];
  enabled: boolean;
  priority: "Low" | "Medium" | "High";
  notes?: string | null;
  match_count: number;
  last_matched_at?: string | null;
  created_at: string;
  updated_at: string;
};
