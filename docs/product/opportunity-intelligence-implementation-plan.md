# Opportunity Intelligence Phase 1 Implementation Plan

This plan implements the deterministic design in small, reviewable commits. It does not change discovery, persistence, APIs, frontend behavior, deployment, or dependencies.

## Task 1 — Characterize existing intelligence boundaries

Add focused tests that lock current `OpportunityIntelligenceService.enrich`, existing `Opportunity.urgency_score`/`quality_score`, and Strategy Agent behavior. Add test builders for fixed actors, opportunities, context, UUIDs, and timezone-aware `as_of` values.

Acceptance criteria:

- Existing mutable enrichment behavior is unchanged.
- Tests prove the new scorer will not overwrite existing score fields.
- No production change beyond test-enabling typing, if strictly necessary.

Suggested commit: `test(intelligence): characterize opportunity scoring boundaries`

## Task 2 — Add the pure versioned score contract

Add immutable `ScoreFactor`, `CategoryScore`, `OpportunityScore`, and a small explicit scoring-context type. Add constants for version, baseline, category caps, critical fields, and fixed ordering. Expose a read-only `OpportunityIntelligenceService.score(..., as_of=...)` skeleton with normalization and hard overrides.

Acceptance criteria:

- Score is bounded 0–100.
- Every factor has ID, category, points, explanation, and priority.
- `as_of` is required and timezone-aware.
- Scoring mutates no ORM object and performs no transaction or network work.

Suggested commit: `feat(intelligence): add deterministic scoring contract`

## Task 3 — Implement fit and career-value factors

Implement mutually exclusive role fit, demographic, role-type, language, and explicit union compatibility factors. Add best-only active goal, dream target, strategic stretch, and watch-list career factors using normalized structured data.

Acceptance criteria:

- Missing data is neutral unless documented otherwise.
- No identity or preference is inferred.
- Repeated goals/roles/terms cannot inflate totals.
- Perfect-match, stretch, dream-project, and conflicting-factor tests assert exact results.

Suggested commit: `feat(intelligence): score opportunity fit and career value`

## Task 4 — Implement practicality, confidence, and interest factors

Add deadline, audition mode, travel, housing, compensation, parse, trust, source, completeness, submission, and feedback factors. Build deterministic confidence text from fixed templates.

Acceptance criteria:

- Fixed-time deadline tests cover tomorrow, seven-day boundaries, missing dates, and expiration.
- Hard eligibility remains authoritative.
- Travel exception and travel dealbreaker remain distinct.
- Low-confidence and incomplete-data output is fully explained.

Suggested commit: `feat(intelligence): score practicality confidence and interest`

## Task 5 — Add actions, contributor ordering, and ranking

Implement first-match-wins action selection, contributor ordering, and the complete equal-score tie-break chain. Add a pure ranking helper that consumes already-produced scores.

Acceptance criteria:

- Only the six documented action labels can be returned.
- Duplicate and already-tracked opportunities cannot prompt a duplicate application.
- Repeated runs return equal serialized results.
- Equal scores are stable regardless of database return order.

Suggested commit: `feat(intelligence): rank scored opportunities deterministically`

## Task 6 — Integrate one read-only consumer

Only after the score contract is reviewed, select one existing backend read path and assemble its scoring context explicitly. Keep this separate from discovery and from the mutating `enrich()` path. Do not expose a new API in the same commit; API and frontend work require their own approved contracts.

The command-center queue is the first read-only consumer. Its public snapshot path intentionally refreshes persisted signals and records a dashboard visit, so the command center exposes separate internal boundaries: `refresh_signals()` owns enrichment, alert/nudge creation, and its commit; `record_visit()` owns visit persistence and its commit; and `read_snapshot()` reads only persisted state. `read_opportunity_candidates()` supplies at most 100 visible, non-demo acting-breakdown candidates with parsed roles and submissions eagerly loaded. The reader scores the full bounded set with one shared aware `as_of`, ranks it once using the version-1 projection, and only then selects the existing eight cards. Context uses loaded actor role, language, union, and demographic facts; parsed-role fit; persisted watch-list matches; deterministic latest submission status; one batched latest actor/Opportunity feedback record; and the saved audition-travel threshold. Career-goal, dream-target, and strategic-stretch matches remain neutral because no stable Opportunity association exists and this consumer does not invent semantic matching. Empty snapshots remain at 24 SELECTs; non-empty snapshots use 28 SELECTs for 1–100 candidates, including two fixed context queries, without candidate-count growth. The public schema, non-Opportunity sections, “since your last visit” behavior, score persistence, and score/action exposure are unchanged. When no actor profile exists, the bounded candidates retain the legacy urgency/quality ordering rather than fabricating actor context.

Acceptance criteria:

- Query count is characterized and bounded.
- Existing responses and persisted records are unchanged.
- No discovery request, provider call, write, flush, or commit occurs.
- Full backend and contract-smoke suites remain green.

Suggested commit: `feat(intelligence): integrate read-only opportunity ranking`

## Task 7B — Characterize the command-center API boundary

### Current boundary and absence guarantee

`GET /api/v1/command-center` is owned by `backend/app/api/v1/routes/command_center.py::get_command_center`, which calls `CommandCenterService.snapshot()` and validates the result with `ActorCommandCenterRead`. The response is a Pydantic model, but `today_opportunities` is intentionally a `list[dict]`; each entry is the manual `_opportunity_card()` projection rather than ORM serialization. A current card contains exactly `id`, `role`, `project`, `original_post_url`, `priority`, `urgency_score`, `quality_score`, `confidence_level`, and `risk_level`. `original_post_url` is the only nullable card field in ordinary output. The response contains no intelligence version, deterministic overall score, suggested action or reason, category/factor details, contributors, intelligence confidence, hard-override details, ranking projection or position, `as_of`, or scoring context. Intelligence affects only which existing card identities appear and their order.

The frontend receives this through `getCommandCenter()` and `useCommandCenter()` under the existing live TanStack Query key. `ActorCommandCenter.today_opportunities` is `CommandCenterCard[]`, where `CommandCenterCard` is a loose scalar-valued record. The Dashboard reads only `role` and `project`, presents loading with `role="status"`, presents failure with `role="alert"`, and uses an empty-state message when no priority breakdown exists. The generic request client performs no runtime response parsing. Current TypeScript fixtures and the strict Playwright mock contain no intelligence data; Playwright permits exactly the existing `GET /command-center` request and no score/history request. No existing response-size test existed before this characterization. Current OpenAPI exposes `today_opportunities.items` as an object with arbitrary properties, and current contract tests depend on route behavior and selected fields rather than a generated client with a typed card schema.

### Recommended additive owner and versioned summary

Future exposure should be one optional nested `intelligence` projection on each existing Opportunity card. The score belongs to that actor-specific, time-relative ranked card; nesting avoids collisions with legacy `quality_score`, `urgency_score`, and Strategy Agent score fields, adds no request or parallel ID map, and remains ergonomic for card rendering. A new endpoint would split ordering from its explanation, while a parallel response map would duplicate identity bookkeeping. The eventual schema must replace the loose proposal with an explicit typed nested model, but retain backward-compatible omission.

The proposed contract is:

```json
{
  "intelligence": {
    "version": 1,
    "overall_score": 87,
    "action": "apply_now",
    "action_label": "Apply Now",
    "action_reason_code": "high_priority_actionable",
    "confidence": {
      "level": "High",
      "summary": "High confidence: 4 bounded confidence factors contribute +15 points."
    },
    "hard_override": false,
    "hard_override_reason": null,
    "top_positive_contributors": [
      {
        "id": "match.role_fit.strong",
        "points": 18,
        "explanation": "Strong Fit is the best parsed role fit (+18)."
      }
    ],
    "top_negative_contributors": []
  }
}
```

`version` is a distinct command-center intelligence contract version, not the discovery-evidence version. It begins at integer `1`. `overall_score` is 0–100. `action` uses the existing six serialized `SuggestedAction` values and `action_label` carries the matching bounded display label. `action_reason_code` and hard-override reasons use bounded public codes. Confidence preserves the current `High`, `Medium`, `Low`, or `Not Scored` domain values. Contributor arrays are capped at three positive and three negative entries. Contributor `explanation` is optional and appears only for an approved public-safe template. Unknown versions must be treated as absent by the frontend. Adding or omitting the nested projection requires no data migration and no persisted score.

### Absent, neutral, override, duplicate, and tracked states

An omitted field is valid for old responses. A new server may use `intelligence: null` when evaluation is unavailable because no actor exists, the consumer intentionally skipped scoring, or a bounded internal evaluation failed while the legacy card remains usable. Evaluated neutral intelligence is a populated version-1 projection, normally with score 50, empty contributors, and its deterministic confidence/action fields. It must never be represented as `null` or `{}`.

Hard user rejection, expiration, discarded state, proven demographic incompatibility, excluded role type, and hard travel failure may expose score `0`, action `ignore`, `action_reason_code: hard_override`, and the stable bounded `hard_override_reason`. Raw rejection text and internal rule payloads remain excluded. Retained duplicates expose only deterministic `ignore / duplicate_opportunity`. Submitted, requested, callback, pinned, booked, passed, and no-response states expose only `save_for_later / already_tracked`; workflow notes and the private status history are not part of this projection.

### Payload-size evidence

Measurements use compact, key-sorted UTF-8 JSON, the complete current command-center envelope, deterministic fictional cards, the actual version-1 score serializer, and no production data.

| Fixture | Bytes | Increase over corresponding current envelope |
| --- | ---: | ---: |
| One current card | 571 | baseline |
| Eight current cards | 2,363 | baseline |
| One card with summary | 1,193 | 108.9% |
| Eight cards with summaries | 7,339 | 210.6% |
| One card with full maximum-factor score | 4,927 | 762.9% |
| Eight cards with full maximum-factor scores | 37,211 | 1,474.7% |
| One hard-override full score | 1,589 | 178.3% |
| One neutral full score | 1,632 | 185.8% |

The maximum-factor full score is 4,927 bytes. The largest growth is the repeated five-category structure, factor objects, contributor duplication, and explanation prose. The summary removes category totals, complete factor arrays, score explanation, action explanation, baseline, and Opportunity ID duplication. Full `OpportunityScore.as_dict()` remains an internal/debug comparison and should not be exposed by the command center.

### Privacy and factor-explanation safety

The future API must never include ActorProfile demographics, private notes, raw career goals, dream-target or watch-list notes, recommendation-feedback notes, raw trust/source metadata, provider evidence, fetched content, scoring context, ranking/canonical keys, database IDs beyond the existing card ID, `as_of`, stack traces, or validation errors.

Current operational templates are safe for actor-facing exposure because they contain no source values: parsed-role fit; remote/local/travel/housing/compensation/deadline facts; parser/trust/source/completeness bands; and generic watch-list priority. Demographic, preferred-role, union, and language factor IDs/templates are safe only under an explicitly actor-facing privacy policy because they reveal the existence or result of sensitive matching even though they do not reveal the underlying profile value. The current `career.goal.active_match`, `career.dream_target.match`, and `career.stretch.strategic` explanations interpolate user-controlled labels and must be redacted, replaced by approved generic prose, or omitted. Feedback factor explanations encode a private actor choice and should likewise omit prose or use a generic actor-authorized explanation. Public contributor serialization therefore requires an explicit factor allowlist; deterministic prose alone is not sufficient evidence of safety.

### Frontend, accessibility, and compatibility requirements

The eventual card should communicate numeric score and a text action label without relying on color. Contributor disclosure must be keyboard operable, must not be tooltip-only, and must expose descriptive screen-reader text such as “Opportunity intelligence score 87 of 100; Apply Now.” Hard overrides need a text reason and may not appear as a generic failure. Absent intelligence renders the existing card unchanged; neutral intelligence states that evaluation completed but no strong contributors were found. Unsupported versions degrade to the absent presentation. Mobile cards must preserve role/project and action before optional contributor details. Loading remains owned by the existing command-center request; no second spinner or request is introduced. Partial intelligence absence must not suppress or reorder an otherwise usable card.

Backward compatibility requires old responses to keep rendering, new optional projections to be ignored by old frontend code, missing/`null` projections to preserve ranked order, unsupported versions to degrade safely, strict mocks to remain valid until deliberately updated, and an OpenAPI diff containing only additive nested definitions/fields. No route or existing field may be removed.

### Required implementation test matrix

Backend contract tests must cover evaluated summary, absent and explicit-null intelligence, neutral baseline, each hard override, retained duplicate, every tracked status, maximum contributors, version serialization, unknown-version documentation, privacy sentinels, payload bounds, unchanged card fields, and an additive-only OpenAPI diff. Backend unit tests must verify public factor allowlisting/redaction and prove serialization does not mutate scores or ORM records.

Frontend unit tests must cover all six actions, score bounds, contributor disclosure, hard override, absent and neutral fallback, unsupported version, color-independent and screen-reader labels, keyboard disclosure, mobile-safe content order, and old fixtures against updated optional types. Playwright must use the same single `GET /command-center` request to cover a populated projection, absent-field compatibility, retained backend order, and strict unknown-request rejection. Compatibility tests must run the old frontend fixture against the new optional backend schema, the old response fixture against updated TypeScript types, and assert that OpenAPI changes are additive only.

## Task 8 — Expose bounded command-center intelligence summaries

The existing `GET /api/v1/command-center` route now adds only `today_opportunities[].intelligence`. The field is nullable and uses an explicit version-1 Pydantic schema. Existing card fields, route orchestration, ranking order, the 100-candidate ceiling, the eight-card display ceiling, and the 24/28 SELECT boundaries remain unchanged.

The request-local ranking path retains both `Opportunity UUID → Opportunity` and `Opportunity UUID → completed OpportunityScore`. It ranks the completed entries, selects eight, and passes the exact retained score to `_opportunity_card()`. Serialization never calls the scorer, queries the database, mutates an ORM record, or persists the score.

The version-1 summary contains `version`, `overall_score`, `action`, `action_label`, `action_reason_code`, generic confidence level/summary, bounded hard-override state, and at most three positive and three negative contributors. A maximum-factor fixture serializes to 558 compact UTF-8 JSON bytes and eight copies serialize to 4,473 bytes; neutral and hard-override fixtures serialize to 364 and 353 bytes. Each summary is capped at 2,048 bytes, materially below the characterized 4,927-byte full-score payload. Full categories, factor collections, priorities, caps, ranking keys, evaluation time, context, and internal explanations remain private.

Contributor serialization is allowlist-first. Operational role-fit, modality, deadline, compensation, travel-support, parser, trust, source, and completeness factors receive fixed generic prose. Sensitive demographic, language, union, role-preference, goal, dream-target, watch-list, feedback, and travel-threshold values never pass through; their bounded factor ID and points may remain without an explanation when already present in the completed top-three contributors. The serializer does not refill contributor positions after filtering. Demographic and excluded-role hard overrides map to `profile_incompatibility`; internal text and profile values remain private.

No actor produces `intelligence: null`; an evaluated neutral score produces a populated score-50 projection. The frontend renders absent and explicit-null values as the unchanged legacy card, and treats unsupported versions the same way without another request. Version 1 preserves role and project first, then shows visible action, numeric score, confidence, an assistive action/score label, and a semantic `details/summary` contributor disclosure. Hard overrides show only a bounded generic reason. The strict browser contract remains one `GET /command-center` request.

## Task 9 — Characterize the broader presentation boundary

### Executive decision

**Defer broader exposure and keep Opportunity Intelligence Dashboard-only for the portfolio deployment.** The current eight-card priority widget already owns the distinct daily decision—what deserves attention now—and visibly demonstrates deterministic scoring, ranking, privacy-safe explanation, versioned API design, accessibility, and bounded performance. No inspected secondary consumer satisfies all nine implementation criteria. Adding the same score elsewhere would currently be repetition, unsafe top-eight reuse, or a new scoring/API boundary rather than a distinct product decision.

### Consumers, decisions, and current data flows

| Consumer | Actor decision | Current route → service/schema | Frontend owner and ordering | Intelligence need and finding |
| --- | --- | --- | --- | --- |
| Dashboard priorities | “What should I review or act on today?” | `GET /command-center` → `CommandCenterService.snapshot/read_snapshot` → `ActorCommandCenterRead` | `getCommandCenter` → `useCommandCenter` → `DashboardPanel/OpportunityPriorityCard`; deterministic score rank, top 8, widget shows 3 | Confirmed owner. Action, score, confidence and contributors directly support prioritization. |
| Breakdowns list | “Which persisted breakdown should I inspect, edit, parse, track, or reject?” | `GET /opportunities` → `OpportunityService.list`/`OpportunityRepository.search` → `OpportunityRead` | `listBreakdowns` → `useBreakdowns` → `BreakdownsPanel/OpportunityManager`; created-at descending, client filters Film/TV, theater, needs-review and travel | Score could help full-list prioritization, but chronology/filter semantics, 100-row coverage, payload and repeated scoring are unresolved. Not justified before deployment. |
| Expanded breakdown/detail | “Are the source, parsed role, eligibility, deadline and instructions accurate enough to act on?” | The UI selects from the list query through `useBreakdown`; `GET /opportunities/{id}` exists but has no active detail hook | `OpportunityManager`, `BreakdownViewer`, `BreakdownDetails`; no distinct detail request | A future public-safe “why” view is the strongest candidate, but there is no existing detail composition boundary with actor/context data. Adding one now requires a new request or broad list scoring. |
| Hidden review | “Can missing/uncertain facts be completed, or should this item be approved/deleted?” | `GET /automation/opportunities/hidden` → route-owned filtered `select(Opportunity)` → `OpportunityRead` | `useHiddenBreakdowns` → `HiddenOpportunityReview`; created-at descending | Existing flag reason, missing fields, trust, travel, parse and demographic evidence explain review ownership. A score/action could conflict with discovery routing and imply eligibility before uncertainty is resolved. |
| Material matches | “Which saved material fits this role?” | `GET /opportunities/material-matches` → `MaterialMatchService.find_matches` → `MaterialOpportunityMatch` | `useMaterialMatches` → readiness/material panels; material score ordering | Opportunity score would compete with a purpose-specific material-fit score and answer a different question. Reject exposure here. |
| Audition readiness | “Am I prepared to audition for this role?” | `GET /intelligence/readiness/opportunities` → `IntelligenceService.audition_readiness_for_all` → `AuditionReadinessRead` | `useAuditionReadiness` → `MergedAuditionReadinessPanel` | Readiness percentage, character/material/travel state already own preparation. Opportunity priority would duplicate inputs and blur selection versus preparation. |
| Similar breakdowns | “What historical work resembles this breakdown?” | `GET /opportunities/{id}/similar` → `ExecutiveIntelligenceService.breakdown_similarity`; no frontend consumer | No current hook/component | Similarity is comparative history, not present-tense prioritization. No presentation owner exists. |
| Auditions/submissions | “What is the current workflow state and next audition task?” | `/submissions`, `/command-center/self-tapes`, callback/journal routes | `AuditionsPage/AuditionsPanel`; workflow/date ordering | Tracked items intentionally receive `save_for_later/already_tracked`; showing that beside active workflow would be redundant and could imply completed work remains a candidate. |
| Journal | “What happened and what should be recorded?” | `/journal` plus existing option lists | `JournalPage/JournalPanel`; historical ordering | Historical record ownership conflicts with a volatile request-time priority score. |
| Calendar | “What is due or scheduled when?” | Calendar events, Opportunities, submissions, self-tapes, callbacks, plus existing command-center request for platform check-ins | `CalendarPage/ActorCalendar`; chronological | It already loads command center, but consumes platform check-ins only. UUID joining top-eight scores would be accidental coupling and score is redundant with deadline/event ownership. |
| Materials library | “Which reusable asset should I maintain or use?” | `/assets`, reusable self-tapes/analytics, Opportunities and submissions | `MaterialsPage/MaterialsPanel` | Opportunity scoring would distract from asset freshness/performance and material ownership. |

### Current request, query, identity, and invalidation boundaries

All relevant Opportunity-family responses carry the stable Opportunity UUID. That makes a join technically possible, not architecturally safe. `GET /opportunities` is bounded to 100 in `OpportunityRepository.search`, ordered by `created_at DESC`, and has no frontend pagination. Its clean repository read begins with one SELECT, but `OpportunityService.list` is not a pure fixed-query boundary: it conditionally repairs deadlines, trust, parsed details, roles and character profiles and may commit; response serialization also traverses role/section/parse/submission relationships. `GET /opportunities/{id}` begins with `Session.get`, may verify trust and commit, and likewise serializes nested relationships. A single universal list/detail query-count promise therefore does not exist today and must be established before scoring is attached to either path.

The hidden-review route starts with one unbounded filtered Opportunity SELECT and then serializes the same nested `OpportunityRead`; it has no explicit pagination or scoring context. Material matching and readiness already perform separate actor/material/travel/history work. The command-center is the only proven constant scoring boundary: 24 SELECTs for an empty snapshot and 28 SELECTs for 1–100 candidates, independent of candidate count, with one shared `as_of`, a 100-candidate ceiling and an eight-card response.

The frontend Breakdown query family refetches on mount and is invalidated by parsing, classification, approval, rejection and discovery workflows. The command-center query is a separate chief-of-staff owner with its own invalidation contracts. Although relevant Opportunity mutations often invalidate both, the timing and coverage are not identical. A cross-feature join can therefore show a newer Opportunity beside an older score or omit a valid item outside the top eight. No inspected non-Dashboard component currently imports the summary type, reads `Opportunity.intelligence`, or requests a score endpoint.

### UUID-join and consistency assessment

Reusing command-center summaries by UUID is rejected. Summaries cover only the ranked top eight of at most 100 candidates; presenting them in a complete list would create unexplained partial coverage. Breakdowns, Auditions, Materials and Journal do not load command center. Calendar does, but only for operational platform check-ins. Adding `useCommandCenter` to those feature owners would reverse the current dependency, inherit chief-of-staff refresh/visit behavior, add a request on most routes, and couple unrelated invalidation policies.

Independent scoring is also rejected for now. The command center assembles actor, latest feedback, goals, dream targets, watch lists, submissions and travel context in bounded batches and evaluates all candidates with one shared `as_of`. List/detail services do not have that context or shared timestamp. Calling the scorer there could produce a second score for the same UUID in one session, increase queries, and disagree with Dashboard ordering. Any future consumer requires one request-local authoritative score owner, the same context assembler and `as_of`, and an additive response that returns the score with the data being acted on—never a client join to top-eight data.

### Presentation options

| Option | Benefit | Cost/risk | Decision |
| --- | --- | --- | --- |
| A. Dashboard only | Clear daily prioritization; one evaluation; compact API; strongest explainability demonstration | Scores unavailable for non-top-eight detail review | **Approve for deployment.** |
| B. Detail only | Could support a distinct “why should I act?” decision without list clutter | Current UI has no detail request/composition boundary; would require a new request or scoring broad list data; richer explanations need a separate safe design | Best future candidate, but prerequisites are unmet; defer. |
| C. List summaries | Full-list prioritization and visible comparison | Up to 100 evaluations, ordering conflict, dense mobile UI, conditional list writes, roughly 55.8 KB maximum added summaries, repeated scoring | Reject before deployment. |
| D. Command-center UUID join | No backend contract change | Only eight summaries, stale/missing rows, cross-feature dependency, extra command-center request and visit/refresh semantics | Reject. |
| E. No additional pre-deployment presentation | Preserves proven architecture and leaves time for demo/deployment polish | Does not show per-detail intelligence | **Recommended.** Equivalent to A for current release scope. |

### Payload, performance, privacy, and accessibility

The deterministic fictional `OpportunityRead` fixture is 1,766 compact bytes; eight copies are 14,137 bytes and 100 are 176,701 bytes. Adding the characterized maximum 558-byte summary to 100 list rows would add up to approximately 55,800 bytes before envelope effects, while also requiring scoring context and computation for every row. A detail projection would add at most the existing 2,048-byte enforced summary bound, but has no safe computation owner today. Request-scoped computation remains viable; caching is neither required nor justified until a real broader boundary exists.

The Task 8 serializer is sufficient for any future compact summary. None of the inspected consumers justifies categories, full factors, raw eligibility, profile values, demographic/language/union values, goals, feedback, watch-list labels, trust internals, ranking keys or `as_of`. A future detail experience that genuinely needs richer explanations must define a separate bounded public-safe projection rather than expose `OpportunityScore.as_dict()`.

List repetition would create mobile density and visual noise beside filters, badges and primary actions. Hidden review already has dense corrective controls and reason disclosures. Auditions, Calendar and Journal require workflow or chronological hierarchy. If detail exposure is later approved, role/project and the primary workflow action must precede intelligence; action, score and confidence must remain visible text; contributor disclosure must be keyboard-operable with expanded state; positive/negative meaning must be textual; and absent, null, neutral, hard-override and unsupported-version behavior must match Task 8 without color-only meaning.

### Compatibility conclusions and portfolio value

Absent, explicit-null and unsupported summaries remain legacy presentation states; neutral is evaluated score 50; hard overrides use bounded public reasons; duplicates and tracked records keep deterministic non-application actions. No ActorProfile or internal fallback yields unavailable intelligence, not a fabricated baseline. Items outside the top eight have no command-center summary. Stale summaries and differing invalidation timing make cross-feature reuse unsafe.

The Dashboard already proves the valuable engineering story: deterministic factor scoring, bounded batch context, stable ranking, single evaluation, privacy-aware serialization, schema versioning, additive compatibility, accessible explainability, constant queries and strict request graphs. Repeating score badges on the Breakdowns list would demonstrate no distinct capability. Portfolio effort has higher value in deployment/demo data, Chief of Staff clarity, Career Agent integration, manual import reliability and concise architecture documentation.

### Prerequisites for any future broader implementation

A future Opportunity-detail integration may be reconsidered only after: (1) a real routed detail consumer owns a distinct apply/review decision; (2) its existing response can carry the projection without a second request; (3) one authoritative request-local score/context assembler is shared without calling the scorer twice; (4) clean and repair-path query counts are characterized and bounded; (5) mutation invalidation aligns with command center; (6) the compact Task 8 serializer remains sufficient or a separate safe detail projection is designed; (7) mobile/accessibility behavior is tested; and (8) measured user or portfolio value exceeds deployment cost. Until then, no broader implementation plan is approved.

## Deferred phases

- Define any richer detail API response only after a distinct detail consumer is selected.
- Add frontend score explanations and action labels in a separate vertical slice.
- Measure query and calculation cost before adding request-scoped caching.
- Consider durable history only with a concrete audit or trend requirement and a separate migration design.
- Consider learned signals only after deterministic outcomes are measured; never silently blend them into version 1.
