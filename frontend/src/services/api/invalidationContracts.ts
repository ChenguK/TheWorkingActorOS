import type { QueryClient } from "@tanstack/react-query";
import { queryKeys } from "./queryKeys";

export const publicInvalidationKeys = {
  submissions: queryKeys.auditions.list({ resource: "submissions" }),
  workflowSelfTapes: queryKeys.auditions.list({ resource: "selfTapes" }),
  callbacks: queryKeys.auditions.list({ resource: "callbacks" }),
  auditionPerformanceNotes: queryKeys.auditions.list({ resource: "auditionJournal" }),
  calendarEvents: queryKeys.calendar.list({ resource: "events" }),
  journalEntries: queryKeys.journal.lists(),
  careerTasks: queryKeys.career.list({ resource: "tasks" }),
  breakdownOpportunities: queryKeys.breakdowns.list({ resource: "opportunities" }),
  breakdownHidden: queryKeys.breakdowns.list({ resource: "hiddenOpportunities" }),
  breakdownRecommendations: queryKeys.breakdowns.list({ resource: "recommendations" }),
  breakdownQueue: queryKeys.breakdowns.list({ resource: "submissionQueue" }),
  breakdownReadiness: queryKeys.breakdowns.list({ resource: "readiness" }),
  breakdownMaterialMatches: queryKeys.breakdowns.list({ resource: "materialMatches" }),
  relationships: queryKeys.relationships.list({ resource: "relationships" }),
  relationshipAnalytics: queryKeys.relationships.list({ resource: "analytics" }),
  materials: queryKeys.materials.list(),
  reusableSelfTapes: queryKeys.materials.list({ resource: "reusableSelfTapes" }),
  analyticsOperations: queryKeys.analytics.list({ resource: "operationsDashboard" }),
  analyticsIntelligence: queryKeys.analytics.list({ resource: "intelligenceDashboard" }),
  analyticsIndustryTrends: queryKeys.analytics.list({ resource: "industryTrends" }),
  analyticsMaterialPerformance: queryKeys.analytics.list({ resource: "materialPerformance" }),
  commandCenter: queryKeys.chiefOfStaff.list({ resource: "commandCenter" }),
  profileActor: queryKeys.profile.list({ resource: "actor" }),
  profileCredits: queryKeys.profile.list({ resource: "actingCredits" }),
  profilePlatformProfiles: queryKeys.profile.list({ resource: "platformProfiles" }),
  profilePublicImports: queryKeys.profile.list({ resource: "publicProfileImports" }),
  profileMappings: queryKeys.profile.list({ resource: "platformMappings" })
} as const;

export type PublicInvalidationKey = keyof typeof publicInvalidationKeys;
export type InvalidationTiming = "synchronous" | "asynchronous" | "none";

export type InvalidationContract = {
  owner: "auditions" | "breakdowns" | "career" | "materials" | "settings" | "chief-of-staff" | "calendar" | "profile";
  operation: string;
  direct: readonly PublicInvalidationKey[];
  derived: readonly PublicInvalidationKey[];
  forbidden: readonly (PublicInvalidationKey | "dashboardPreferences" | "executiveBriefs" | "industryTrends")[];
  timing: InvalidationTiming;
  reason: string;
};

export const invalidationContracts = {
  actorProfileUpdate: {
    owner: "profile", operation: "actorProfile.update",
    direct: ["profileActor"],
    derived: ["breakdownOpportunities", "breakdownHidden", "breakdownReadiness", "breakdownMaterialMatches"],
    forbidden: [
      "profileCredits", "profilePlatformProfiles", "profilePublicImports", "profileMappings",
      "submissions", "workflowSelfTapes", "callbacks", "auditionPerformanceNotes", "calendarEvents",
      "journalEntries", "careerTasks", "breakdownRecommendations", "breakdownQueue", "relationships",
      "relationshipAnalytics", "materials", "reusableSelfTapes", "analyticsOperations",
      "analyticsIntelligence", "analyticsIndustryTrends", "analyticsMaterialPerformance",
      "commandCenter", "dashboardPreferences", "executiveBriefs"
    ],
    timing: "synchronous",
    reason: "ActorProfileService synchronously updates the actor and recomputes demographic eligibility and enriched state for every non-demo opportunity. Visible/hidden membership, readiness, and material-match inputs can therefore change; no other frontend-owned records are written."
  },
  actorLinkedPlatformProfileApprove: {
    owner: "profile", operation: "platformProfile.approve",
    direct: ["profilePlatformProfiles", "profileMappings", "profileActor", "profileCredits"],
    derived: [],
    forbidden: [
      "profilePublicImports", "submissions", "workflowSelfTapes", "callbacks", "auditionPerformanceNotes",
      "calendarEvents", "journalEntries", "careerTasks", "breakdownOpportunities", "breakdownHidden",
      "breakdownRecommendations", "breakdownQueue", "breakdownReadiness", "breakdownMaterialMatches",
      "relationships", "relationshipAnalytics", "materials", "reusableSelfTapes", "analyticsOperations",
      "analyticsIntelligence", "analyticsIndustryTrends", "analyticsMaterialPerformance",
      "commandCenter", "dashboardPreferences", "executiveBriefs"
    ],
    timing: "synchronous",
    reason: "PlatformImportService approval updates the platform profile, creates asset mappings and acting credits, and merges imported skills and accents into its linked actor. It does not invoke actor-profile opportunity refresh, so opportunity-derived owners are intentionally excluded."
  },
  opportunityCreate: {
    owner: "breakdowns", operation: "opportunity.create",
    direct: ["breakdownOpportunities", "breakdownHidden"],
    derived: ["breakdownReadiness", "breakdownMaterialMatches", "workflowSelfTapes", "calendarEvents", "journalEntries", "analyticsOperations", "analyticsIndustryTrends", "commandCenter"],
    forbidden: ["submissions", "callbacks", "auditionPerformanceNotes", "breakdownRecommendations", "breakdownQueue", "relationships", "relationshipAnalytics", "materials", "reusableSelfTapes", "analyticsIntelligence", "analyticsMaterialPerformance", "careerTasks", "dashboardPreferences", "executiveBriefs"],
    timing: "synchronous",
    reason: "OpportunityService synchronously persists the parsed/classified opportunity, roles and intelligence, always records Accepted Breakdown actor work, conditionally creates an Auditions-owned self-tape workflow, and conditionally creates persisted Calendar rows for dated audition/callback fields. Readiness, material matches, operational/industry Analytics, and command center are derived reads; the submission/outcome-backed Intelligence dashboard and material-performance Analytics are unchanged."
  },
  opportunityUpdate: {
    owner: "breakdowns", operation: "opportunity.update",
    direct: ["breakdownOpportunities", "breakdownHidden"],
    derived: ["breakdownReadiness", "breakdownMaterialMatches", "workflowSelfTapes", "analyticsOperations", "analyticsIntelligence", "analyticsIndustryTrends", "commandCenter"],
    forbidden: ["submissions", "callbacks", "auditionPerformanceNotes", "calendarEvents", "journalEntries", "breakdownRecommendations", "breakdownQueue", "relationships", "relationshipAnalytics", "materials", "reusableSelfTapes", "analyticsMaterialPerformance", "dashboardPreferences", "executiveBriefs"],
    timing: "synchronous",
    reason: "OpportunityService updates classification, deadlines, readiness inputs and aggregates, and conditionally creates or updates the Auditions-owned self-tape workflow; it does not write Journal or persisted Calendar rows."
  },
  opportunityManualParse: {
    owner: "breakdowns", operation: "opportunity.manualParse",
    direct: ["breakdownOpportunities", "breakdownHidden"],
    derived: ["breakdownReadiness", "breakdownMaterialMatches", "workflowSelfTapes", "analyticsOperations", "analyticsIntelligence", "analyticsIndustryTrends", "commandCenter"],
    forbidden: ["submissions", "callbacks", "auditionPerformanceNotes", "calendarEvents", "journalEntries", "breakdownRecommendations", "breakdownQueue", "relationships", "relationshipAnalytics", "materials", "reusableSelfTapes", "analyticsMaterialPerformance", "dashboardPreferences", "executiveBriefs"],
    timing: "synchronous",
    reason: "Manual paste replaces and reparses the opportunity and conditionally synchronizes its Auditions-owned self-tape workflow; it does not write Journal or persisted Calendar rows."
  },
  opportunityDeepParse: {
    owner: "breakdowns", operation: "opportunity.deepParse",
    direct: ["breakdownOpportunities", "breakdownHidden"],
    derived: ["breakdownReadiness", "breakdownMaterialMatches", "analyticsOperations", "analyticsIndustryTrends", "commandCenter"],
    forbidden: ["submissions", "workflowSelfTapes", "callbacks", "auditionPerformanceNotes", "calendarEvents", "journalEntries", "careerTasks", "breakdownRecommendations", "breakdownQueue", "relationships", "relationshipAnalytics", "materials", "reusableSelfTapes", "analyticsIntelligence", "analyticsMaterialPerformance", "dashboardPreferences", "executiveBriefs"],
    timing: "synchronous",
    reason: "Deep parse synchronously replaces parse, section, role, classification, deadline, intelligence, trust and eligibility state and can change both opportunity-list owners. Readiness, material matches, operational/industry Analytics and command center are derived reads; it does not write persisted Calendar or other forbidden records, and Intelligence and material-performance Analytics are unchanged."
  },
  opportunityReject: {
    owner: "breakdowns", operation: "opportunity.reject",
    direct: ["breakdownOpportunities", "breakdownHidden"],
    derived: ["breakdownReadiness", "breakdownMaterialMatches", "commandCenter"],
    forbidden: [
      "submissions", "workflowSelfTapes", "callbacks", "auditionPerformanceNotes", "calendarEvents", "journalEntries",
      "careerTasks", "breakdownRecommendations", "breakdownQueue", "relationships", "relationshipAnalytics", "materials",
      "reusableSelfTapes", "analyticsOperations", "analyticsIntelligence", "analyticsIndustryTrends",
      "analyticsMaterialPerformance", "dashboardPreferences", "executiveBriefs"
    ],
    timing: "synchronous",
    reason: "Reject/archive synchronously persists discarded and archived opportunity state plus user-rejection metadata and manual-override history. Both active opportunity owners can lose the record; readiness, material matches and command center are derived reads. It does not write submission, workflow, Journal, Calendar, recommendation, queue, relationship, material, Career, Analytics, preference, or brief records."
  },
  opportunityStrategyGenerate: {
    owner: "breakdowns", operation: "opportunity.strategyGenerate",
    direct: ["breakdownRecommendations", "breakdownOpportunities", "breakdownHidden"],
    derived: ["analyticsMaterialPerformance", "commandCenter"],
    forbidden: ["submissions", "workflowSelfTapes", "callbacks", "auditionPerformanceNotes", "calendarEvents", "journalEntries", "careerTasks", "breakdownQueue", "breakdownReadiness", "breakdownMaterialMatches", "relationships", "relationshipAnalytics", "materials", "reusableSelfTapes", "analyticsOperations", "analyticsIntelligence", "analyticsIndustryTrends", "dashboardPreferences", "executiveBriefs"],
    timing: "synchronous",
    reason: "StrategyAgent synchronously appends a recommendation and deadline validation can move its opportunity between visible and hidden owners. Recommendations drive material-performance Analytics and executive command-center priorities; strategy generation does not write submissions, workflow tapes, Journal, Calendar, queue, relationship, material, or unrelated Analytics records."
  },
  recommendationFeedbackCreate: {
    owner: "breakdowns", operation: "recommendation.feedbackCreate",
    direct: [],
    derived: ["commandCenter"],
    forbidden: [
      "submissions", "workflowSelfTapes", "callbacks", "auditionPerformanceNotes", "calendarEvents", "journalEntries",
      "careerTasks", "breakdownOpportunities", "breakdownHidden", "breakdownRecommendations", "breakdownQueue",
      "breakdownReadiness", "breakdownMaterialMatches", "relationships", "relationshipAnalytics", "materials",
      "reusableSelfTapes", "analyticsOperations", "analyticsIntelligence", "analyticsIndustryTrends",
      "analyticsMaterialPerformance", "dashboardPreferences", "executiveBriefs"
    ],
    timing: "synchronous",
    reason: "Recommendation feedback synchronously appends feedback and a learning insight in one transaction. The raw histories have no frontend query owner, recommendation rows remain unchanged, and only executive command-center priorities can derive a different current response from the latest learning insight."
  },
  opportunityDelete: {
    owner: "breakdowns", operation: "opportunity.delete",
    direct: ["breakdownOpportunities", "breakdownHidden"],
    derived: ["breakdownReadiness", "breakdownMaterialMatches", "breakdownRecommendations", "breakdownQueue", "workflowSelfTapes", "callbacks", "auditionPerformanceNotes", "calendarEvents", "journalEntries", "relationships", "relationshipAnalytics", "reusableSelfTapes", "analyticsOperations", "analyticsIntelligence", "analyticsIndustryTrends", "analyticsMaterialPerformance", "commandCenter"],
    forbidden: ["submissions", "materials", "careerTasks", "dashboardPreferences", "executiveBriefs"],
    timing: "synchronous",
    reason: "Successful hard delete is limited to opportunities without linked submissions and retains the proven unlinked-delete side effects. A linked submission produces a protected 409 before mutation, preserves every record, and runs no invalidation; submissions therefore remain forbidden."
  },
  submissionCreate: {
    owner: "auditions", operation: "submission.create", direct: ["submissions"],
    derived: ["calendarEvents", "journalEntries", "auditionPerformanceNotes", "breakdownOpportunities", "breakdownReadiness", "relationships", "relationshipAnalytics", "materials", "analyticsOperations", "analyticsIntelligence", "analyticsIndustryTrends", "analyticsMaterialPerformance", "commandCenter"],
    forbidden: ["dashboardPreferences", "executiveBriefs"], timing: "synchronous",
    reason: "SubmissionService synchronously connects Calendar, Journal, audition-note, opportunity, relationship, material-use, and aggregate records."
  },
  submissionUpdate: {
    owner: "auditions", operation: "submission.update", direct: ["submissions"],
    derived: ["analyticsOperations", "analyticsIntelligence", "analyticsMaterialPerformance", "breakdownReadiness", "commandCenter"],
    forbidden: ["journalEntries", "calendarEvents", "executiveBriefs", "dashboardPreferences", "industryTrends"], timing: "synchronous",
    reason: "Only cost, status, material, opportunity, and date fields affect derived reads; notes-only edits remain submission-local."
  },
  submissionStatus: {
    owner: "auditions", operation: "submission.status", direct: ["submissions"],
    derived: ["journalEntries", "breakdownOpportunities", "breakdownReadiness", "relationships", "relationshipAnalytics", "analyticsOperations", "analyticsIntelligence", "analyticsIndustryTrends", "analyticsMaterialPerformance", "commandCenter"],
    forbidden: ["calendarEvents", "auditionPerformanceNotes", "dashboardPreferences", "executiveBriefs"], timing: "synchronous",
    reason: "Status history updates outcome learning and selected statuses create actor Journal work events."
  },
  submissionDelete: {
    owner: "auditions", operation: "submission.delete", direct: ["submissions"],
    derived: ["calendarEvents", "breakdownReadiness", "relationships", "relationshipAnalytics", "analyticsOperations", "analyticsIntelligence", "analyticsIndustryTrends", "analyticsMaterialPerformance", "commandCenter"],
    forbidden: ["journalEntries", "dashboardPreferences", "executiveBriefs"], timing: "synchronous",
    reason: "Deleting the authoritative submission changes aggregates and linked-record projections but does not erase historical actor Journal entries."
  },
  callbackChange: {
    owner: "auditions", operation: "callback.change", direct: ["callbacks"],
    derived: ["submissions", "journalEntries", "analyticsIntelligence", "analyticsMaterialPerformance", "commandCenter"],
    forbidden: ["calendarEvents", "dashboardPreferences", "executiveBriefs", "industryTrends"], timing: "synchronous",
    reason: "Callback creation may update its linked submission and create an actor Journal entry; Calendar renders the callback owner cache directly."
  },
  workflowSelfTapeUpdate: {
    owner: "auditions", operation: "workflowSelfTape.update", direct: ["workflowSelfTapes"],
    derived: ["journalEntries", "commandCenter"], forbidden: ["calendarEvents", "dashboardPreferences", "executiveBriefs", "industryTrends"], timing: "synchronous",
    reason: "Completed self-tapes create actor Journal records; Calendar projects the Auditions cache without a persisted Calendar mutation."
  },
  queueExecution: {
    owner: "breakdowns", operation: "submissionQueue.execute", direct: [], derived: [],
    forbidden: ["submissions", "calendarEvents", "journalEntries", "analyticsOperations", "dashboardPreferences"], timing: "none",
    reason: "Queue execution records adapter execution state only; it does not create a local Submission."
  },
  careerTaskChange: {
    owner: "career", operation: "careerTask.change", direct: ["careerTasks"], derived: ["journalEntries", "commandCenter"],
    forbidden: ["analyticsOperations", "dashboardPreferences", "executiveBriefs", "industryTrends"], timing: "synchronous",
    reason: "Task completion creates an actor Journal record and command center reads active Career tasks."
  },
  reusableSelfTapeChange: {
    owner: "materials", operation: "reusableSelfTape.change", direct: [], derived: [],
    forbidden: ["workflowSelfTapes", "calendarEvents", "journalEntries", "commandCenter"], timing: "none",
    reason: "Reusable Materials tapes are separate from Auditions workflow self-tapes and have no cross-feature side effects."
  },
  providerChange: {
    owner: "settings", operation: "provider.change", direct: [], derived: [],
    forbidden: ["submissions", "analyticsOperations", "dashboardPreferences", "calendarEvents"], timing: "none",
    reason: "Provider mutations affect provider settings and system capabilities only."
  },
  platformCheckIn: {
    owner: "chief-of-staff", operation: "platformCheckIn.update", direct: ["commandCenter"], derived: ["journalEntries"],
    forbidden: ["calendarEvents", "analyticsOperations", "dashboardPreferences", "executiveBriefs"], timing: "synchronous",
    reason: "A completed platform check-in synchronously records actor work; Calendar projects command-center state directly."
  },
  calendarEventChange: {
    owner: "calendar", operation: "calendarEvent.change", direct: ["calendarEvents"], derived: ["analyticsOperations"],
    forbidden: ["submissions", "callbacks", "workflowSelfTapes", "dashboardPreferences", "executiveBriefs"], timing: "synchronous",
    reason: "The operations dashboard derives upcoming alerts from persisted Calendar rows."
  }
} as const satisfies Record<string, InvalidationContract>;

export function keysForContract(contract: InvalidationContract): readonly (readonly unknown[])[] {
  return [...contract.direct, ...contract.derived].map((name) => publicInvalidationKeys[name]);
}

export function invalidateInBackground(client: QueryClient, keys: readonly (readonly unknown[])[]): void {
  void Promise.allSettled(keys.map((queryKey) => client.invalidateQueries({ queryKey })));
}
