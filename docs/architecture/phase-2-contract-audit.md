# Phase 2 Cross-Stack Boundary and API-Contract Audit

**Branch:** `release/portfolio-readiness`  
**Audit date:** 2026-07-26  
**Scope:** React feature APIs/query hooks/domain types/invalidation contracts/Playwright mocks and FastAPI routes/schemas/service results/errors/filtering/side effects/contract smoke.  
**Constraint:** Audit only. No production code was changed.

## Executive summary

The cross-stack contract is functional but manually duplicated. TypeScript types, Pydantic schemas, mock fixtures, invalidation descriptions, and contract-smoke assertions independently describe the same resources. The strongest part of the contract is mutation side-effect characterization: opportunity, submission, recommendation-feedback, discovery, and source-exclusion behavior has unusually specific backend and frontend tests.

The highest-risk confirmed defects are:

1. the frontend queries `GET /automation/discovery/report`, but the backend does not register that endpoint;
2. the Playwright catch-all mock turns that missing route, and many other unsupported routes, into successful empty data;
3. submission creation can create persisted Calendar events on the backend regardless of the frontend’s “Add to calendar” choice, after which the frontend may POST a second event;
4. actor-profile and platform-import mutations do not invalidate all frontend data owners affected by backend side effects;
5. list endpoints silently truncate selected resources to 100 items without pagination metadata or frontend pagination.

No numeric-versus-string ID mismatch was found in the primary resource contracts: backend UUIDs serialize as strings and frontend IDs are consistently `string`. The more important ID issue is semantic: one unused frontend travel PATCH helper labels the path argument as an actor ID while the backend expects a preference ID.

## Audit approach and contract sources

- Frontend requests were inventoried from every `frontend/src/features/*/api` module plus `frontend/src/services/system/api.ts` and shared URL helpers.
- Backend endpoints were inventoried from `backend/app/api/v1/router.py` and all `backend/app/api/v1/routes/*.py`.
- Primary TypeScript resource types in `frontend/src/types/domain.ts` and feature-local request/view types were compared with Pydantic schemas under `backend/app/schemas`.
- Query hooks were compared with backend service side effects and `frontend/src/services/api/invalidationContracts.ts`.
- `frontend/e2e/support/mockApi.ts` was compared with real route status codes, response shapes, filtering, and side effects.
- Backend contract-smoke and cross-module tests were used as the strongest evidence for persisted behavior.

## 1. Confirmed frontend/backend contract mismatches

### C-01 — The frontend calls a backend route that does not exist

- **Severity:** high
- **Confidence:** confirmed
- **Frontend:** `frontend/src/features/breakdowns/api/index.ts:getDiscoveryReport`; `frontend/src/features/breakdowns/hooks/useBreakdownQueries.ts:useDiscoveryReport`; `BreakdownManager`.
- **Backend:** no matching decorator in `backend/app/api/v1/routes/automation.py`; `DiscoveryAutomationService._discovery_report` only returns a report inside `run_all`.
- **Mismatch:** the frontend issues `GET /automation/discovery/report`, but the FastAPI router exposes discovery run endpoints only. A real request returns 404.
- **Why it matters:** the Breakdowns workspace owns an always-enabled query whose production contract is absent. Unit tests verify only that the frontend calls the string.
- **Smallest safe cleanup:** decide whether the report is run-result-only or a persisted/latest resource. Either remove the standalone query or add a typed backend endpoint with a defined empty state.
- **Protection/gap:** `frontend/src/features/breakdowns/api/index.test.ts` preserves the nonexistent URL; no backend contract test covers it.

### C-02 — The Playwright catch-all masks missing and malformed endpoints

- **Severity:** high
- **Confidence:** confirmed
- **Frontend mock:** `frontend/e2e/support/mockApi.ts:installMockApi`, `handle`, and `defaultResponse`.
- **Real contract:** `backend/app/api/v1/routes/*`.
- **Mismatch:** any unhandled `/api/v1/**` request receives 200 with `[]`, `null`, or another default. This is why `/automation/discovery/report` succeeds in browser tests. Many POST/PATCH routes also receive 200/default data instead of a real 201, typed object, 204, 404, or 422.
- **Why it matters:** E2E tests can pass when an endpoint is absent, misspelled, called with the wrong method, or returning a wrong shape.
- **Smallest safe cleanup:** make unhandled mock routes fail with an explicit 501/test error. Add handlers only for routes intentionally exercised.
- **Protection/gap:** request-graph tests assert selected request strings, but do not require every request to have an explicit mock handler.

### C-03 — Submission Calendar ownership conflicts with the frontend opt-in

- **Severity:** high
- **Confidence:** confirmed
- **Frontend:** `frontend/src/features/auditions/hooks/useSubmissionTracker.ts:submit` and `createAuditionLinkedRecords`; `SubmissionFormState.create_calendar`; `frontend/e2e/cross-feature.spec.ts` (“audition deadline propagates to Calendar”).
- **Backend:** `backend/app/services/submission_service.py:SubmissionService.create`; `backend/app/services/workflow_connector_service.py:after_submission_created`, `_ensure_calendar_events`, `_calendar_candidates`; `backend/app/services/operations_service.py:create_event`.
- **Mock:** `frontend/e2e/support/mockApi.ts` creates Calendar data from the explicit frontend Calendar POST; its submission handler does not reproduce the backend’s unconditional workflow-connector Calendar creation for the actual submitted payload.
- **Mismatch:** a submission with dates on its linked opportunity can create Calendar rows inside `SubmissionService.create` whether the frontend checkbox is checked or not. When checked, the frontend then calls `POST /operations/calendar/events`, whose service does no deduplication, so a second semantically equivalent event can be created.
- **Why it matters:** users cannot reliably opt out and may see duplicates. The E2E test proves the UI orchestration, not the real combined side effect.
- **Smallest safe cleanup:** establish one owner. Prefer passing an explicit Calendar intent in a typed submission use case or relying exclusively on backend policy; add a real contract test for checked and unchecked behavior before changing it.
- **Protection/gap:** `backend/tests/test_cross_module_workflows.py` protects automatic submission-linked Calendar creation; Playwright protects explicit creation. No test combines both real behaviors.

### C-04 — Actor-profile mutation invalidation omits backend-derived opportunity owners

- **Severity:** high
- **Confidence:** confirmed
- **Frontend:** `frontend/src/features/profile/hooks/useProfileQueries.ts:useUpdateActorProfile` invalidates only `profileKeys.actor`.
- **Backend:** `backend/app/services/actor_profile_service.py:create_or_replace`, `update`, `_refresh_breakdown_eligibility`; `backend/app/services/workflow_connector_service.py:profile_changed`.
- **Mismatch:** changing age, identity, location, skills, or role preferences refreshes eligibility across non-demo opportunities and adds rescore metadata, but the frontend leaves Breakdowns, hidden opportunities, readiness, material matches, command center, and related analytics caches live.
- **Why it matters:** a successful profile save can immediately show stale fit/visibility data elsewhere.
- **Smallest safe cleanup:** define an actor-profile invalidation contract from the proven backend effects and invalidate only affected public owners.
- **Protection/gap:** actor-profile and eligibility backend tests protect recomputation; profile hook tests currently assert only the profile key.

### C-05 — Platform-profile approval invalidation omits the mutated actor and derived reads

- **Severity:** high
- **Confidence:** confirmed
- **Frontend:** `frontend/src/features/profile/hooks/useProfileQueries.ts:useInvalidateImports`, `usePlatformImportAction`; invalidates platform profiles, public imports, mappings, and credits.
- **Backend:** `backend/app/services/platform_import_service.py:approve_profile`, `_create_credits_from_parsed`, `_apply_skills_to_actor`.
- **Mismatch:** approval can mutate actor skills and acting credits, but `profileKeys.actor` is not invalidated. Derived readiness/material matching owners that read actor skills also remain cached.
- **Why it matters:** the import UI can report approval while the visible profile and opportunity-fit data retain pre-import skills.
- **Smallest safe cleanup:** distinguish public-import approval (mappings only) from actor-linked platform-profile approval; add actor and proven derived keys only to the latter.
- **Protection/gap:** platform/profile component tests mock mutations; no cross-stack test verifies actor skills are visible after approval without reload.

### C-06 — Selected list endpoints silently cap results at 100

- **Severity:** medium
- **Confidence:** confirmed
- **Frontend:** `listBreakdowns` in `frontend/src/features/breakdowns/api/index.ts`; `listMaterials` in `frontend/src/features/materials/api/index.ts`; components treat returned arrays as complete.
- **Backend:** `backend/app/repositories/base.py:BaseRepository.list`; `backend/app/repositories/opportunity.py:OpportunityRepository.search`; `backend/app/repositories/asset.py:list_by_actor`; routes expose no offset/limit parameters or total metadata.
- **Mismatch:** opportunity and asset results are limited to 100 internally, but the API response is a plain list and gives the frontend no indication of truncation.
- **Why it matters:** dropdowns, material matching choices, and visible breakdown lists silently become incomplete as portfolio data grows.
- **Smallest safe cleanup:** either remove the internal cap for the current single-user deployment with measured bounds, or expose explicit pagination and migrate consumers intentionally.
- **Protection/gap:** existing tests use small datasets and cannot detect truncation.

### C-07 — Mock resource fixtures drift from Pydantic response contracts

- **Severity:** medium
- **Confidence:** confirmed
- **Frontend mock:** `frontend/e2e/support/mockApi.ts:opportunityFixture`, `assetFixture`, `submissionFixture`, `workflowTapeFixture`, `calendarFixture`.
- **Backend schemas:** `backend/app/schemas/opportunity.py:OpportunityRead`; `asset.py:AssetRead`; `submission.py:SubmissionRead`; `agent.py:SelfTapeWorkflowRead`; `operations.py:AuditionCalendarEventRead`.
- **Examples:**
  - the mock opportunity uses `visibility_status: "Visible"` while the backend and TypeScript use lowercase `"visible"`;
  - the mock asset provides `file_path` instead of required `local_file_path`, omits required frontend `analysis_status`, and adds `is_active`, which `AssetRead` does not expose;
  - mock submission objects add `tape_due_at` and `audition_date`, which `SubmissionRead` does not define;
  - mock workflow tapes add `title`, `project`, and `role`, which `SelfTapeWorkflowRead` does not define.
- **Why it matters:** UI code can accidentally depend on mock-only fields or fail to exercise real required fields.
- **Smallest safe cleanup:** type mock fixture builders with the actual frontend domain types and maintain a contract-smoke JSON fixture for representative responses.
- **Protection/gap:** TypeScript cannot check these fixtures because most are `Record<string, unknown>`.

### C-08 — Travel PATCH helper uses the wrong semantic ID

- **Severity:** medium
- **Confidence:** confirmed, currently dormant
- **Frontend:** `frontend/src/features/profile/api/index.ts:updateTravelPreferences(actorProfileId, patch)` sends `PATCH /travel-preferences/${actorProfileId}`.
- **Backend:** `backend/app/api/v1/routes/travel_preferences.py:update_travel_preference(preference_id, ...)` loads `TravelPreferenceRepository.get(preference_id)`.
- **Mismatch:** the helper names and expects an actor-profile ID while the endpoint expects the travel-preference record ID.
- **Why it matters:** activating this helper would return 404 for normal data unless IDs accidentally matched.
- **Smallest safe cleanup:** remove the unused helper or rename its argument to `preferenceId`; keep the current PUT upsert path for actor-owned saves.
- **Protection/gap:** current hooks use `saveTravelPreferences` PUT instead, so no test exercises the bad helper.

### C-09 — Structured backend error information is flattened inconsistently

- **Severity:** medium
- **Confidence:** confirmed
- **Frontend:** `frontend/src/services/api/request.ts:parseApiError`; `frontend/src/services/api/errors.ts`.
- **Backend:** `backend/app/core/errors.py`; FastAPI/Pydantic 422 responses; `OpportunityService.delete` conflict detail `{code, message}`; ad hoc errors in `routes/automation.py`, `travel_preferences.py`, and `career_development.py`.
- **Mismatch:** the frontend extracts an object’s `message` but drops its `code`; FastAPI validation details are flattened into one message and never populate `fieldErrors` because FastAPI returns `detail`, not top-level `errors`. Backend status/message shape also varies by route.
- **Why it matters:** clients must string-match messages and cannot reliably attach validation to fields or branch on stable conflict codes.
- **Smallest safe cleanup:** preserve `detail.code` and map FastAPI `detail[].loc/msg` into `fieldErrors`, starting with the protected opportunity-delete conflict.
- **Protection/gap:** request utility tests cover message formatting; contract smoke protects the backend 409 object, but there is no cross-stack parser test using that real body.

### C-10 — Several frontend-consumed endpoints lack declared backend response models

- **Severity:** medium
- **Confidence:** confirmed
- **Frontend:** typed calls to `/system/capabilities`, `/intelligence/materials/performance`, `/automation/travel/recalculate`, and command-center resolution across system, analytics, settings, and chief-of-staff APIs.
- **Backend:** `routes/system.py:capabilities`; `routes/intelligence.py:get_material_performance`; `routes/automation.py:recalculate_travel_exceptions`; `routes/command_center.py:resolve_outcome_nudge` have no `response_model`.
- **Mismatch:** TypeScript presents stable named types while FastAPI does not validate or document those response shapes.
- **Why it matters:** service dictionary changes can ship without OpenAPI/schema failure and silently break frontend assumptions.
- **Smallest safe cleanup:** add response schemas to the highest-risk frontend-consumed dictionary endpoints without changing their JSON.
- **Protection/gap:** capability and analytics UI tests protect selected fields, but OpenAPI does not.

## 2. Potential mismatches requiring runtime verification

### P-01 — TypeScript enums are narrower than backend schemas

- **Confidence:** strong inference
- **Frontend:** unions in `frontend/src/types/domain.ts`, including `Opportunity.source_type`, `SubmissionStatus`, calendar event types, source-research states, priorities, match types, and import statuses.
- **Backend:** many corresponding fields are plain `str` in `schemas/opportunity.py`, `submission.py`, `operations.py`, `discovery.py`, `agent.py`, and `intelligence.py`.
- **Risk:** current services mostly emit values covered by TypeScript, but neither Pydantic nor database constraints guarantee that future or legacy values stay inside the unions.
- **Runtime verification:** export distinct production/database values for these columns and compare them with frontend unions before tightening either side.

### P-02 — Optionality differs between TypeScript and Pydantic

- **Confidence:** strong inference
- **Frontend:** many properties in `frontend/src/types/domain.ts` use optional-plus-nullable (`field?: T | null`).
- **Backend:** response schemas usually guarantee the key and use nullable (`field: T | None = None`).
- **Risk:** the frontend is generally more permissive, which is safe at runtime but hides missing-field mock drift and weakens exhaustiveness. Conversely, some frontend-required properties are backend dictionary fields rather than schema-enforced fields.
- **Runtime verification:** capture representative OpenAPI-validated responses and check exact key presence before narrowing TypeScript.

### P-03 — Naive local datetimes cross a timezone-aware backend

- **Confidence:** strong inference
- **Frontend:** `datetime-local` values are sent directly in `OpportunityFormWorkspace.tsx`, `ActorCalendar.tsx`, `SubmissionTracker.tsx`, and feature form hooks; the DST E2E mock asserts a timezone-free string.
- **Backend:** Pydantic accepts `datetime`; SQLAlchemy columns are frequently timezone-aware; services mix `datetime.utcnow()` with `datetime.now(timezone.utc)`; `BreakdownDeadlineService` applies `America/New_York`.
- **Risk:** browser-local wall time, server/database timezone interpretation, and returned ISO offsets can differ around DST or non-Eastern clients.
- **Runtime verification:** use the real PostgreSQL contract client to POST timezone-free DST-boundary values and assert stored/returned instants in at least two process timezones.

### P-04 — Actor profile PATCH schema is only partially optional

- **Confidence:** strong inference
- **Frontend:** `updateActorProfile` currently uses PUT with a full form; API barrels expose general update semantics.
- **Backend:** `ActorProfileUpdate` inherits `ActorProfileCreate` and only overrides some fields as optional, leaving arrays and several demographic fields required.
- **Risk:** a future partial PATCH call would receive unexpected 422 errors.
- **Runtime verification:** confirm PATCH is unused externally and decide whether it is intentionally “mostly full replacement.”

### P-05 — Service dictionaries may contain hidden, unversioned transformations

- **Confidence:** confirmed structure; runtime shape needs verification
- **Frontend:** `SystemCapabilities`, `ActorCommandCenter`, `OperationsDashboard`, `IntelligenceDashboard`, discovery run/report types.
- **Backend:** `CapabilityService`, `CommandCenterService`, `OperationsService`, `IntelligenceService`, and `DiscoveryAutomationService` build nested dictionaries, some behind broad `dict` schema fields.
- **Risk:** names and nested optional fields can change without schema enforcement.
- **Runtime verification:** snapshot only stable business keys in contract smoke; avoid snapshotting incidental wording/order.

## 3. Endpoint ownership by frontend feature

| Frontend feature | Backend namespaces used | Contract ownership assessment |
|---|---|---|
| Analytics | `/operations`, `/intelligence` | Intentional read-model composition; several broad dictionary responses |
| Auditions | `/submissions`, `/command-center/self-tapes`, `/intelligence/callback-events`, `/intelligence/audition-journal`, `/operations/calendar/events` | Workflow owner spans four backend domains; Calendar side-effect ownership is ambiguous |
| Breakdowns | `/opportunities`, `/automation`, `/agents`, `/intelligence` | Broad orchestration feature; includes the missing discovery-report contract |
| Calendar | `/operations/calendar`, `/operations/availability` | Clear primary ownership |
| Career Intelligence | `/career-development`, `/agents`, `/intelligence` | User workflow spans career, agent, and intelligence resources |
| Chief of Staff | `/command-center`, `/operations`, `/agents` | Intentional read/action composition |
| Dashboard | `/dashboard` plus hooks from many features | Dashboard API owns preferences only; widget data is composed client-side |
| Journal | `/journal` | Clear primary ownership |
| Materials | `/assets`, `/intelligence/self-tapes`, `/opportunities/material-matches`, `/platform-imports` | Materials duplicates some Profile import/mapping access |
| Profile | `/actor-profile`, `/travel-preferences`, `/representation`, `/operations`, `/platform-imports` | Broad workflow owner; import mutations affect other feature caches |
| Relationships | `/intelligence/relationships`, `/intelligence/communication-logs` | Clear frontend ownership under a broad backend namespace |
| Script Finder | `/intelligence/scripts`, `/intelligence/materials`, `/system` | Coherent workflow; material-plan endpoint is also used by Career |
| Settings | `/automation/discovery/providers`, `/automation/travel`, `/system` | Configuration owner; capability invalidation is explicit |
| Source Library | `/automation/source-research` | Clear UI ownership, coupled to discovery runtime state |

Frontend feature ownership intentionally follows user workflows and does not mirror route namespaces. The risky cases are those where mutation side effects cross those workflow boundaries without an invalidation contract.

## 4. Response-shape consistency assessment

### Strong patterns

- Core CRUD endpoints return Pydantic response models with snake_case fields and UUIDs serialized as strings.
- List endpoints consistently return bare JSON arrays rather than mixing `{items: ...}` and arrays.
- DELETE endpoints generally return 204 and the shared request utility maps them to `undefined`.
- Timestamped ORM resources normally include `id`, `created_at`, and `updated_at` through `TimestampedModel`.

### Weak patterns

- Bare lists provide no total, cursor, or truncation indication.
- Dictionary-heavy read models are typed more strongly in TypeScript than in FastAPI.
- Some action endpoints return full resources, some return `{status}`, and some have no declared shape.
- Pydantic defaults often guarantee keys that frontend types mark optional, allowing mocks to omit real-contract fields.
- Naming is mostly consistent snake_case, but semantics diverge in names such as `updateTravelPreferences(actorProfileId)` and in duplicate frontend terms for workflow versus reusable self-tapes.

## 5. Error-contract assessment

The shared frontend parser correctly handles:

- FastAPI string `detail`;
- Pydantic validation arrays as a readable combined message;
- object `detail.message`;
- network/timeout-like failures as retryable `ApiError`s.

It does not preserve:

- structured error codes such as `opportunity_has_submissions`;
- per-field validation mappings from FastAPI’s `detail[].loc`;
- a stable backend-wide application-error envelope.

Backend error status is also inconsistent: custom `NotFoundError`, `ConflictError`, and `ValidationError` coexist with raw `HTTPException`, `ValueError`, `KeyError`, and message-based status selection. The smallest useful contract is not a global rewrite; it is a versioned `{code, message, fields?}` detail for errors on the highest-risk mutations.

## 6. Query invalidation assessment

### Already strong

- `frontend/src/services/api/invalidationContracts.ts` documents direct, derived, forbidden, and no-op families for the highest-risk opportunity/submission workflows.
- `invalidationContracts.test.ts`, feature hook tests, Playwright request-graph tests, and backend contract smoke triangulate important side effects.
- Opportunity create/update/manual parse/deep parse/reject/delete, recommendation feedback, submission lifecycle, callback, workflow tape, Calendar, and material changes have intentional coverage.

### Confirmed gaps

1. Profile update invalidates only the actor despite backend opportunity recomputation.
2. Platform-profile approval omits actor and derived-fit owners.
3. Discovery report invalidation targets a query whose endpoint does not exist.
4. `useApproveBreakdown` and `useRefreshDemographicCheck` use manually assembled key groups instead of named contracts, increasing drift risk.
5. Profile import/mapping endpoints are duplicated in Materials and Profile, so equivalent mutations may not share invalidation policy.

### Important non-gap

`queueExecution` correctly avoids invalidating submissions: backend `SubmissionAutomationService.execute` records adapter execution state but does not create a local `Submission`.

## 7. Mock API drift assessment

`frontend/e2e/support/mockApi.ts` is valuable as a deterministic UI integration harness, but it is not currently a contract simulator.

Confirmed drift:

- catch-all success for unsupported routes;
- missing discovery-report route masked;
- resource fields differ from Pydantic/TypeScript;
- many real 201/204/404/422 statuses become 200;
- filtering, default 100 limits, and most query parameters are ignored;
- backend submission-linked Calendar side effects are absent;
- server validation and UUID parsing are absent;
- Pydantic rejection of missing/invalid fields is absent;
- default response selection is based on path substrings rather than declared route contracts.

Recommended role: keep this mock for fast UI workflows, but make explicit-handler coverage mandatory and add a smaller real-FastAPI browser/contract layer for the highest-risk flows.

## 8. Unused or orphaned endpoint candidates

### Frontend orphan

- `GET /automation/discovery/report` is called but has no backend route.

### Dormant/broken frontend helper

- `updateTravelPreferences` is unused and sends the wrong semantic ID.

### Backend endpoints with no confirmed frontend request call

Candidates include:

- duplicate/legacy agent routes: `/agents/discovery/run`, `/agents/assets/{id}/analyze`, `/agents/opportunities/{id}/recommend`;
- agent operations: `/agents/learning/run`, `/agents/career/run`, `/agents/recommendations/{id}/explanation`, `/create-submission`;
- alias/hidden reads: `/agents/executive/*`, `/intelligence/trends`;
- detail analytics: `/intelligence/archetypes/performance`, casting-office analytics, role similarity, opportunity history/similar;
- discovery configuration/detail endpoints: `/automation/discovery/settings`, per-provider run, `/automation/capabilities`;
- import text, waiting submissions, and individual readiness;
- all supervised-breakdown browser/import endpoints;
- several generated file routes are used through URL helpers rather than `api.*` calls and should not be classified as unused solely from request-wrapper search.

These are candidates, not deletion recommendations. CLI/manual integrations and planned UI may own them. Confirm access logs, README workflows, and generated URL usage before removal.

## 9. Highest-risk production contracts

| Rank | Contract | Risk |
|---:|---|---|
| 1 | Breakdowns discovery report | Guaranteed 404 masked by mocks |
| 2 | Submission → Calendar | Duplicate/unwanted persisted events and ambiguous ownership |
| 3 | Actor profile → opportunity eligibility/readiness | Stale cross-feature state after successful save |
| 4 | Platform profile approval → actor/credits/readiness | Stale profile and derived data |
| 5 | Opportunity and asset list completeness | Silent truncation at 100 |
| 6 | Naive local datetime → timezone-aware persistence | DST and deployment-timezone ambiguity |
| 7 | Opportunity delete conflict | Structured code is lost by the frontend parser |
| 8 | Dictionary read models | TypeScript stability is not guaranteed by FastAPI |
| 9 | Discovery/source-research state transitions | Broad cross-domain effects and enum strings |
| 10 | Local upload/import responses | Filesystem and database behavior plus broad invalidation |

## 10. Contract-test coverage gaps

The following production flows deserve cross-stack or real-contract coverage:

1. Breakdowns page with every query hitting real FastAPI, which would expose the report 404.
2. Submission creation with Calendar opt-in on and off, asserting exact row counts.
3. Actor-profile demographic/role-preference change followed by immediate readiness/list reads.
4. Platform-profile approval followed by actor, credit, material/mapping, and readiness reads.
5. More than 100 opportunities/assets.
6. Timezone-free `datetime-local` input across a DST boundary.
7. Real 409 opportunity-delete body parsed by `parseApiError`.
8. Representative mock fixture validation against Pydantic-generated JSON.
9. Source-research approval/rejection effects on discovery provider state.
10. One browser flow using real FastAPI/PostgreSQL rather than the catch-all mock.

## 11. Recommended contract cleanup order

1. **Resolve `/automation/discovery/report`.** Remove the orphan query or define a typed latest-report endpoint.
2. **Make unhandled Playwright mock routes fail.** This immediately exposes drift without changing production behavior.
3. **Characterize submission/Calendar ownership with real PostgreSQL.** Decide how opt-in and deduplication should work only after the combined test exists.
4. **Add profile and platform-import invalidation contracts.** Match exact backend side effects.
5. **Address silent list truncation.** Choose explicit pagination or an intentionally complete bounded list.
6. **Preserve structured error codes and field errors.** Start with opportunity-delete 409 and FastAPI 422.
7. **Add response models to frontend-consumed dictionary endpoints.**
8. **Type the mock fixtures with frontend domain types and representative backend JSON.**
9. **Run a datetime/DST contract pass before deployment.**
10. **Inventory orphan backend endpoints using runtime/access evidence before deleting anything.**

## 12. Deployment conclusion

The cross-stack contract is not yet fully portfolio-ready because one active frontend query has no backend endpoint and the browser mocks conceal that failure. Submission/Calendar ownership and profile-derived invalidation also need characterization or correction before deployment.

The overall architecture is still credible: core CRUD shapes are consistent, UUID/string and snake_case conventions align, the shared request layer handles basic FastAPI errors, invalidation contracts are unusually explicit, and real-PostgreSQL contract smoke covers many mutation side effects. The correct next step is bounded contract repair and stronger mock enforcement, not generated-client adoption or a broad API rewrite.
