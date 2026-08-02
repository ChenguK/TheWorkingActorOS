import type { Page, Request } from "@playwright/test";

const now = "2026-03-07T15:00:00-05:00";

export type MockState = {
  requests: string[];
  actor: Record<string, unknown> | null;
  representations: Array<Record<string, unknown>>;
  opportunities: Array<Record<string, unknown>>;
  hiddenOpportunities: Array<Record<string, unknown>>;
  recommendations: Array<Record<string, unknown>>;
  submissions: Array<Record<string, unknown>>;
  workflowTapes: Array<Record<string, unknown>>;
  reusableTapes: Array<Record<string, unknown>>;
  calendarEvents: Array<Record<string, unknown>>;
  actorJournal: Array<Record<string, unknown>>;
  assets: Array<Record<string, unknown>>;
  capabilities: Record<string, unknown>;
  discoveryResult: Record<string, unknown>;
  focusMode: string;
  failPath?: string;
  delayPath?: string;
  delayMs?: number;
};

export function createMockState(overrides: Partial<MockState> = {}): MockState {
  return {
    requests: [],
    actor: actorFixture(),
    representations: [],
    opportunities: [opportunityFixture()],
    hiddenOpportunities: [],
    recommendations: [],
    submissions: [],
    workflowTapes: [],
    reusableTapes: [],
    calendarEvents: [],
    actorJournal: [],
    assets: [assetFixture()],
    capabilities: capabilitiesFixture(),
    discoveryResult: discoveryResultFixture(),
    focusMode: "Audition Mode",
    ...overrides
  };
}

export async function installMockApi(page: Page, state = createMockState()) {
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = `${url.pathname.replace("/api/v1", "")}${url.search}`;
    state.requests.push(`${request.method()} ${path}`);
    assertHandledApiRequest(request.method(), url);
    if (state.delayPath && url.pathname.endsWith(state.delayPath)) {
      await new Promise((resolve) => setTimeout(resolve, state.delayMs ?? 250));
    }
    if (state.failPath && url.pathname.endsWith(state.failPath)) {
      await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Deterministic domain failure" }) });
      return;
    }
    const response = await handle(request, url.pathname.replace("/api/v1", ""), state);
    await route.fulfill({ status: response.status ?? 200, contentType: "application/json", body: response.status === 204 ? "" : JSON.stringify(response.body) });
  });
  return state;
}

const exactRoutes = new Set([
  "GET /system/capabilities",
  "GET /actor-profile",
  "PUT /actor-profile",
  "GET /representation",
  "POST /representation",
  "GET /representation/acting-credits/list",
  "GET /opportunities",
  "POST /opportunities",
  "GET /automation/opportunities/hidden",
  "GET /automation/source-research",
  "GET /automation/discovery/plugins",
  "GET /automation/discovery/providers",
  "POST /automation/discovery/run",
  "GET /automation/submission-queue",
  "GET /agents/recommendations",
  "GET /agents/chief-of-staff/briefs",
  "GET /agents/career/swot",
  "GET /agents/casting-goals",
  "GET /agents/watch-lists",
  "GET /agents/career-memory",
  "GET /submissions",
  "POST /submissions",
  "GET /command-center",
  "GET /command-center/self-tapes",
  "POST /command-center/self-tapes",
  "GET /intelligence/self-tapes",
  "POST /intelligence/self-tapes",
  "GET /intelligence/self-tapes/analytics",
  "GET /intelligence/audition-journal",
  "POST /intelligence/audition-journal",
  "GET /intelligence/callback-events",
  "GET /intelligence/readiness/opportunities",
  "GET /intelligence/dashboard",
  "GET /intelligence/casting-patterns",
  "GET /intelligence/materials/performance",
  "GET /intelligence/relationships",
  "GET /intelligence/relationships/analytics",
  "GET /intelligence/scripts/sources",
  "GET /intelligence/casting-offices",
  "GET /intelligence/career/quarterly-reviews",
  "GET /intelligence/dream-targets/readiness",
  "GET /operations/calendar/events",
  "POST /operations/calendar/events",
  "GET /operations/availability",
  "GET /operations/platform-subscriptions",
  "GET /operations/equipment-profile",
  "GET /operations/dashboard",
  "GET /journal",
  "GET /assets",
  "POST /assets",
  "GET /dashboard/focus-mode",
  "PUT /dashboard/focus-mode",
  "GET /dashboard/widgets",
  "GET /career-development/tasks",
  "GET /platform-imports/profiles",
  "GET /platform-imports/public-profiles",
  "GET /platform-imports/asset-mappings"
]);

const dynamicRoutes = [
  /^POST \/agents\/recommendations\/[^/]+\/feedback$/,
  /^POST \/opportunities\/[^/]+\/recommend$/,
  /^POST \/opportunities\/[^/]+\/reject$/,
  /^DELETE \/opportunities\/[^/]+$/,
  /^PATCH \/opportunities\/[^/]+$/,
  /^POST \/opportunities\/[^/]+\/parse-breakdown-text$/,
  /^POST \/opportunities\/[^/]+\/deep-parse$/,
  /^POST \/submissions\/[^/]+\/status-history$/,
  /^PATCH \/operations\/calendar\/events\/[^/]+$/,
  /^PATCH \/assets\/[^/]+$/,
  /^GET \/travel-preferences\/[^/]+$/
];

export function assertHandledApiRequest(method: string, url: URL) {
  const path = url.pathname.replace("/api/v1", "");
  const methodPath = `${method} ${path}`;
  const queryIsExpected = methodPath === "GET /opportunities/material-matches"
    && url.search === "?include_hidden=false&min_score=15";
  const discoveryQueryIsExpected = methodPath === "POST /automation/discovery/run"
    && url.search === "?mode=FilmTV&search_modes=Match+My+Profile&search_modes=Match+My+Archetypes";
  const hasUnexpectedQuery = url.search !== "" && !queryIsExpected && !discoveryQueryIsExpected;
  const handled = !hasUnexpectedQuery && (
    exactRoutes.has(methodPath)
    || dynamicRoutes.some((pattern) => pattern.test(methodPath))
    || queryIsExpected
    || discoveryQueryIsExpected
  );
  if (!handled) {
    throw new Error(`Unhandled mock API request: ${method} ${path}${url.search}`);
  }
}

async function handle(request: Request, path: string, state: MockState): Promise<{ body?: unknown; status?: number }> {
  const method = request.method();
  const json = async () => {
    try { return request.postDataJSON(); } catch { return {}; }
  };
  if (path === "/system/capabilities" && method === "GET") return { body: state.capabilities };
  if (path === "/actor-profile") {
    if (method === "PUT") state.actor = { ...state.actor, ...(await json()) };
    return { body: state.actor };
  }
  if (path === "/representation") {
    if (method === "POST") state.representations.push({ id: `rep-${state.representations.length + 1}`, ...(await json()), active: true, created_at: now, updated_at: now });
    return { body: method === "GET" ? state.representations : state.representations.at(-1) };
  }
  if (path === "/opportunities") {
    if (method === "POST") {
      const payload = await json() as Record<string, unknown>;
      const opportunity = { ...opportunityFixture(`opp-${state.opportunities.length + 1}`), ...payload };
      state.opportunities.push(opportunity);
      state.actorJournal.push({ id: `journal-${state.actorJournal.length + 1}`, event_type: "Accepted Breakdown", title: `Accepted ${opportunity.role} in ${opportunity.project}`, linked_breakdown_id: opportunity.id, created_at: now, updated_at: now });
      if (opportunity.audition_type === "Self-Tape") state.workflowTapes.push(workflowTapeFixture(opportunity, { tape_due_at: opportunity.audition_deadline }));
      if (opportunity.audition_deadline) state.calendarEvents.push(calendarFixture(opportunity, { tape_due_at: opportunity.audition_deadline }));
    }
    return { body: method === "GET" ? state.opportunities : state.opportunities.at(-1), status: method === "POST" ? 201 : 200 };
  }
  if (path === "/automation/opportunities/hidden" && method === "GET") return { body: state.hiddenOpportunities };
  if (path === "/agents/recommendations" && method === "GET") return { body: state.recommendations };
  if (path.startsWith("/agents/recommendations/") && path.endsWith("/feedback") && method === "POST") {
    const recommendationId = path.split("/")[3];
    const payload = await json() as Record<string, unknown>;
    const recommendation = state.recommendations.find((item) => item.id === recommendationId);
    return {
      status: 201,
      body: {
        id: `feedback-${recommendationId}`,
        actor_profile_id: recommendation?.actor_profile_id ?? "actor-1",
        opportunity_id: recommendation?.opportunity_id ?? "opp-1",
        recommendation_id: recommendationId,
        ...payload,
        created_at: now,
        updated_at: now
      }
    };
  }
  if (path.startsWith("/opportunities/") && path.endsWith("/recommend") && method === "POST") {
    const opportunityId = path.split("/")[2];
    const recommendation = {
      id: `recommendation-${state.recommendations.length + 1}`,
      opportunity_id: opportunityId,
      actor_profile_id: "actor-1",
      score: 80,
      match_type: "Strong Match",
      display_opportunity: true,
      explanation: "Strong role fit.",
      score_breakdown: {},
      audition_type: "Self-Tape",
      audition_travel_hours: 0,
      audition_decision: "Recommended",
      audition_explanation: "Self-tape is feasible.",
      travel_explanation: "No travel required.",
      archetype_explanation: "Authority fit.",
      asset_explanation: "Current materials align.",
      submission_strategy_explanation: "Submit current materials.",
      confidence_level: "High",
      risk_level: "Low",
      risk_explanation: null,
      recommended_headshot_id: "asset-1",
      recommended_reel_id: null,
      recommended_resume_id: null,
      recommended_slate_id: null,
      recommended_note: "Available on request.",
      created_at: now,
      updated_at: now
    };
    state.recommendations.unshift(recommendation);
    return { body: recommendation };
  }
  if (path.startsWith("/opportunities/") && path.endsWith("/reject") && method === "POST") {
    const opportunityId = path.split("/")[2];
    const opportunity = [...state.opportunities, ...state.hiddenOpportunities].find((item) => item.id === opportunityId);
    const payload = await json() as Record<string, unknown>;
    Object.assign(opportunity ?? {}, {
      ...payload,
      visibility_status: "discarded",
      status: "archived",
      hidden_by_rule: "user_rejected"
    });
    state.opportunities = state.opportunities.filter((item) => item.id !== opportunityId);
    state.hiddenOpportunities = state.hiddenOpportunities.filter((item) => item.id !== opportunityId);
    return { body: opportunity };
  }
  if (path.startsWith("/opportunities/") && method === "DELETE") {
    const opportunityId = path.split("/")[2];
    if (state.submissions.some((item) => item.opportunity_id === opportunityId)) {
      return {
        status: 409,
        body: {
          detail: {
            code: "opportunity_has_submissions",
            message: "This opportunity cannot be permanently deleted because it has linked submissions. Reject or archive it instead."
          }
        }
      };
    }
    state.opportunities = state.opportunities.filter((item) => item.id !== opportunityId);
    state.hiddenOpportunities = state.hiddenOpportunities.filter((item) => item.id !== opportunityId);
    return { status: 204 };
  }
  if (path.startsWith("/opportunities/") && method === "PATCH") {
    const opportunityId = path.split("/")[2];
    const opportunity = [...state.opportunities, ...state.hiddenOpportunities].find((item) => item.id === opportunityId);
    Object.assign(opportunity ?? {}, await json());
    if (opportunity && !state.workflowTapes.some((item) => item.opportunity_id === opportunityId)) state.workflowTapes.push(workflowTapeFixture(opportunity, {}));
    return { body: opportunity };
  }
  if (path.startsWith("/opportunities/") && path.endsWith("/parse-breakdown-text") && method === "POST") {
    const opportunityId = path.split("/")[2];
    const opportunity = [...state.opportunities, ...state.hiddenOpportunities].find((item) => item.id === opportunityId);
    Object.assign(opportunity ?? {}, { description: (await json() as Record<string, unknown>).raw_text });
    if (opportunity && !state.workflowTapes.some((item) => item.opportunity_id === opportunityId)) state.workflowTapes.push(workflowTapeFixture(opportunity, {}));
    return { body: opportunity };
  }
  if (path.startsWith("/opportunities/") && path.endsWith("/deep-parse") && method === "POST") {
    const opportunityId = path.split("/")[2];
    const opportunity = [...state.opportunities, ...state.hiddenOpportunities].find((item) => item.id === opportunityId);
    Object.assign(opportunity ?? {}, { ai_summary: "Deep parse completed", updated_at: now });
    return { body: opportunity };
  }
  if (path === "/submissions") {
    if (method === "POST") {
      const payload = await json() as Record<string, unknown>;
      const opportunity = state.opportunities.find((item) => item.id === payload.opportunity_id) ?? state.opportunities[0];
      state.submissions.push(submissionFixture(`submission-${state.submissions.length + 1}`, opportunity, payload));
    }
    return { body: method === "GET" ? state.submissions : state.submissions.at(-1) };
  }
  if (path.startsWith("/submissions/") && path.endsWith("/status-history") && method === "POST") {
    const submission = state.submissions.find((item) => item.id === path.split("/")[2]);
    const payload = await json() as Record<string, unknown>;
    if (submission) submission.current_status = payload.status;
    if (["Self-Tape Callback", "In-Person Callback", "Pinned", "Booked", "Passed", "No Response"].includes(String(payload.status))) {
      state.actorJournal.push({
        id: `journal-${state.actorJournal.length + 1}`,
        date: "2026-03-10",
        event_type: payload.status === "Booked" ? "Booking Recorded" : "Callback Received",
        title: `${payload.status}: DST Detective in Spring Forward`,
        description: null,
        linked_audition_id: submission?.id ?? null,
        created_at: now,
        updated_at: now
      });
    }
    return { body: submission };
  }
  if (path === "/command-center/self-tapes") {
    if (method === "POST") state.workflowTapes.push({ id: `workflow-${state.workflowTapes.length + 1}`, ...(await json()), created_at: now, updated_at: now });
    return { body: method === "GET" ? state.workflowTapes : state.workflowTapes.at(-1) };
  }
  if (path === "/intelligence/self-tapes") {
    if (method === "POST") state.reusableTapes.push({ id: `reusable-${state.reusableTapes.length + 1}`, ...(await json()), created_at: now, updated_at: now });
    return { body: method === "GET" ? state.reusableTapes : state.reusableTapes.at(-1) };
  }
  if (path === "/intelligence/self-tapes/analytics" && method === "GET") return { body: { by_archetype: [], by_outcome: [], best_performing_tapes: [], underused_tapes: [] } };
  if (path === "/operations/calendar/events") {
    if (method === "POST") state.calendarEvents.push({ id: `calendar-${state.calendarEvents.length + 1}`, ...(await json()), created_at: now, updated_at: now });
    return { body: method === "GET" ? state.calendarEvents : state.calendarEvents.at(-1) };
  }
  if (path === "/journal" && method === "GET") return { body: state.actorJournal };
  if (path === "/intelligence/audition-journal" && method === "GET") return { body: [] };
  if (path === "/intelligence/audition-journal" && method === "POST") return { body: { id: "note-1", ...(await json()), created_at: now, updated_at: now } };
  if (path.startsWith("/operations/calendar/events/") && method === "PATCH") {
    const event = state.calendarEvents.find((item) => item.id === path.split("/").at(-1)); Object.assign(event ?? {}, await json()); return { body: event };
  }
  if (path === "/assets") {
    if (method === "POST") state.assets.push(assetFixture(`asset-${state.assets.length + 1}`, "E2E Updated Headshot"));
    return { body: method === "GET" ? state.assets : state.assets.at(-1) };
  }
  if (path.startsWith("/assets/") && method === "PATCH") {
    const asset = state.assets.find((item) => item.id === path.split("/").at(-1)); Object.assign(asset ?? {}, await json()); return { body: asset };
  }
  if (path === "/dashboard/focus-mode") {
    if (method === "PUT") state.focusMode = String((await json() as Record<string, unknown>).active_mode);
    return { body: { id: "focus-1", active_mode: state.focusMode, created_at: now, updated_at: now } };
  }
  if (path === "/dashboard/widgets" && method === "GET") return { body: dashboardWidgets() };
  if (path === "/command-center" && method === "GET") return { body: { today_opportunities: [], executive_priorities: [], chief_of_staff_priorities: [], since_last_visit: [], queued_submissions: [], upcoming_deadlines: [], outcome_nudges: [], career_tasks: [], material_gaps: [], asset_performance: [], platform_check_ins: [] } };
  if (path === "/operations/equipment-profile" && method === "GET") return { body: null };
  if (/^\/travel-preferences\/[^/]+$/.test(path) && method === "GET") return { body: null };
  if (path === "/operations/dashboard" && method === "GET") return { body: null };
  if (path === "/intelligence/dashboard" && method === "GET") return { body: null };
  if (path === "/intelligence/relationships/analytics" && method === "GET") return { body: null };
  if (path === "/intelligence/casting-patterns" && method === "GET") return { body: null };
  if (path === "/intelligence/materials/performance" && method === "GET") return { body: null };
  if (path === "/opportunities/material-matches" && method === "GET") return { body: [] };
  if (path === "/automation/source-research" && method === "GET") return { body: [] };
  if (path === "/automation/discovery/plugins" && method === "GET") return { body: [] };
  if (path === "/automation/discovery/providers" && method === "GET") return { body: [] };
  if (path === "/automation/discovery/run" && method === "POST") return { body: state.discoveryResult };
  if (path === "/automation/submission-queue" && method === "GET") return { body: [] };
  if (path === "/intelligence/readiness/opportunities" && method === "GET") return { body: [] };
  if (path === "/operations/availability" && method === "GET") return { body: [] };
  if (path === "/intelligence/callback-events" && method === "GET") return { body: [] };
  if (path === "/career-development/tasks" && method === "GET") return { body: [] };
  if (path === "/representation/acting-credits/list" && method === "GET") return { body: [] };
  if (path === "/operations/platform-subscriptions" && method === "GET") return { body: [] };
  if (path === "/platform-imports/profiles" && method === "GET") return { body: [] };
  if (path === "/platform-imports/public-profiles" && method === "GET") return { body: [] };
  if (path === "/platform-imports/asset-mappings" && method === "GET") return { body: [] };
  if (path === "/intelligence/relationships" && method === "GET") return { body: [] };
  if (path === "/agents/career/swot" && method === "GET") return { body: null };
  if (path === "/intelligence/career/quarterly-reviews" && method === "GET") return { body: [] };
  if (path === "/agents/casting-goals" && method === "GET") return { body: [] };
  if (path === "/intelligence/scripts/sources" && method === "GET") return { body: [] };
  if (path === "/agents/chief-of-staff/briefs" && method === "GET") return { body: [] };
  if (path === "/intelligence/casting-offices" && method === "GET") return { body: [] };
  if (path === "/intelligence/dream-targets/readiness" && method === "GET") return { body: [] };
  if (path === "/agents/watch-lists" && method === "GET") return { body: [] };
  if (path === "/agents/career-memory" && method === "GET") return { body: [] };
  throw new Error(`Mock route was recognized but has no response: ${method} ${path}`);
}

export const opportunityFixture = (id = "opp-1") => ({ id, role: "DST Detective", project: "Spring Forward", description: "Lead investigator", source_type: "Manual Entry", source_status: "Approved", visibility_status: "Visible", platform: "E2E", project_type: "TV", role_type: "Guest Star", category: "Film/TV", union: "SAG-AFTRA", location: "New York, NY", shoot_location: "New York, NY", audition_type: "Self-Tape", audition_deadline: "2026-03-08T01:30:00-05:00", submission_deadline: "2026-03-08T01:30:00-05:00", priority: "High", archetypes: ["Authority"], role_details: {}, source_metadata: {}, production_details: {}, extracted_facts: {}, ai_inference: {}, breakdown_roles: [], breakdown_sections: [], breakdown_parse_runs: [], watchlist_match_names: [], watchlist_match_count: 0, manual_review_required: false, is_duplicate: false, from_agent: false, travel_covered: false, housing_covered: false, created_at: now, updated_at: now });
export const hiddenOpportunityFixture = (id = "opp-hidden") => ({ ...opportunityFixture(id), role: "Hidden Detective", visibility_status: "hidden", hidden_reason: "Needs manual review", hidden_by_rule: "needs_date_review", manual_review_required: true });
export const linkedSubmissionFixture = (opportunity: Record<string, unknown>) => submissionFixture("submission-linked", opportunity, { current_status: "Submitted" });
export const assetFixture = (id = "asset-1", name = "E2E Headshot") => ({ id, actor_profile_id: "actor-1", asset_name: name, asset_type: "Headshot", file_path: "/tmp/headshot.jpg", description: "Current theatrical headshot", tags: ["theatrical"], archetype_names: ["Authority"], ai_suggested_tags: [], ai_suggested_archetypes: [], freshness_status: "Current", is_active: true, last_updated_date: "2026-03-01", last_used_date: null, expiration_warning_date: null, created_at: now, updated_at: now });
const actorFixture = () => ({ id: "actor-1", name: "Avery Stone", sag_status: "SAG-AFTRA", union_status: "SAG-AFTRA", current_location: "New York, NY", playable_age_min: 30, playable_age_max: 45, secondary_playable_age_min: null, secondary_playable_age_max: null, skills: [], gender_identities: ["Woman"], gender_expression: null, pronouns: "she/her", ethnicities: ["Black"], racial_identities: ["Black"], nationalities: [], languages: ["English"], accents: [], disability_identities: [], accessibility_notes: null, demographic_notes: null, included_role_types: [], excluded_role_types: [], notes: null, created_at: now, updated_at: now });
const submissionFixture = (id: string, opportunity: Record<string, unknown>, payload: Record<string, unknown>) => ({ id, opportunity_id: opportunity.id, actor_profile_id: "actor-1", opportunity, current_status: payload.current_status ?? "Submitted", assets: [], status_history: [], total_cost: 0, submission_fee: 0, media_fee: 0, travel_cost: 0, housing_cost: 0, parking_cost: 0, other_cost: 0, tape_due_at: payload.tape_due_at ?? null, audition_date: payload.audition_date ?? null, created_at: now, updated_at: now });
const workflowTapeFixture = (opportunity: Record<string, unknown>, payload: Record<string, unknown>) => ({ id: `workflow-${Date.now()}`, opportunity_id: opportunity.id, submission_id: null, title: `${opportunity.role} Self-Tape`, project: opportunity.project, role: opportunity.role, tape_due_at: payload.tape_due_at, status: "Not Started", created_at: now, updated_at: now });
const calendarFixture = (opportunity: Record<string, unknown>, payload: Record<string, unknown>) => ({ id: `calendar-${Date.now()}`, title: `${opportunity.role} Audition`, event_type: "Self-Tape Due", start_datetime: payload.tape_due_at, end_datetime: null, opportunity_id: opportunity.id, submission_id: null, is_virtual: true, created_at: now, updated_at: now });
const capabilitiesFixture = () => ({ flags: { ai_configured: false, supervised_browser_available: false, persistent_file_storage_available: false, portfolio_demo: true }, states: { industry_trend_analysis: { state: "available" }, career_agent_recommendations: { state: "available" }, archetype_performance: { state: "available" } }, integrations: [], labels: {} });
const discoveryResultFixture = () => ({
  discovery_mode: "FilmTV",
  search_modes: ["Match My Profile", "Match My Archetypes"],
  opportunities_created: 2,
  opportunities_hidden: 2,
  opportunities_rejected: 1,
  total_found: 4,
  total_rejected: 1,
  total_hidden: 2,
  total_visible: 1,
  total_travel_exceptions: 1,
  limit_reached: false,
  rejection_reasons_summary: { crew_or_staff_listing: 1 },
  sources_run: 1,
  coverage: {
    approved_active_sources_checked: 0,
    approved_active_source_names_checked: [],
    eligible_sources_skipped: 0,
    skipped_source_reasons: [],
    approved_mode_sources_available: 0,
    approved_mode_sources_label: "Film/TV sources",
    suggested_sources_awaiting_approval: 1,
    coverage_level: "Limited",
    scope_note: "Configured mocked public search only."
  },
  public_web_search: {
    configured: true,
    run: true,
    candidate_pages_found: 4,
    candidates_rejected: 1,
    eligible_breakdowns_added: 1,
    sources_suggested_for_approval: 1
  },
  discovery_report: {
    parallel_queries_run: 6,
    candidate_pages_returned: 4,
    candidate_pages_fetched: 4,
    candidate_pages_parsed: 4,
    accepted: 1,
    reviewed: 2,
    rejected: 1,
    top_rejection_reasons: { crew_or_staff_listing: 1 },
    average_parser_confidence: 79,
    approved_source_hits: 0,
    public_web_hits: 4,
    candidates: [
      {
        page_title: "River City — Maya",
        url: "https://casting.example.test/river-city",
        decision: "Accepted",
        outcome: "accept_visible",
        reason_code: "direct_eligible_notice",
        explanation: "Direct actionable acting notice passed current eligibility and trust checks.",
        provider_evidence: {
          provider: "Parallel",
          canonical_url: "https://casting.example.test/river-city",
          title: "River City — Maya",
          snippet: "Fictional search-result context.",
          published_date: "2026-08-01"
        }
      },
      {
        page_title: "Harbor City — Jordan",
        decision: "Needs Review",
        outcome: "review_hidden",
        reason_code: "missing_deadline",
        explanation: "No submission deadline was identified for the candidate."
      },
      {
        page_title: "Lake City — Rina",
        decision: "Needs Review",
        outcome: "review_hidden",
        reason_code: "travel_uncertain",
        explanation: "In-person audition travel cannot be verified yet."
      },
      {
        page_title: "Production Coordinator",
        decision: "Rejected",
        outcome: "reject_discarded",
        reason_code: "crew_or_staff_listing",
        explanation: "The candidate is not an actor-facing role notice."
      }
    ]
  }
});
const dashboardWidgets = () => [{ id: "widget-1", widget_id: "quick_actions", display_name: "Quick Actions", enabled: true, sort_order: 0, size: "medium", created_at: now, updated_at: now }];
