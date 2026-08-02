# Phase 2 Architecture Audit Review

**Branch:** `release/portfolio-readiness`  
**Review date:** 2026-07-26  
**Scope:** skeptical source-and-test review of every Category A, B, and C task in `phase-2-cleanup-plan.md`  
**Release context:** a sanitized, single-actor public portfolio demonstration, not a production multi-user SaaS launch

## 1. Executive recommendation

Complete a **reduced, evidence-driven pre-deployment batch and then deploy the frontend**.

Only one audited item is a confirmed active runtime contract defect: `BreakdownDiscovery` mounts `useDiscoveryReport`, whose `getDiscoveryReport` requests `/automation/discovery/report`, but the FastAPI router has no such endpoint. The Playwright catch-all currently conceals that defect. Those two items should be fixed before deployment.

The profile mutation invalidation gaps are also confirmed contract gaps, but their runtime severity was overstated. Breakdown queries use `refetchOnMount: "always"` in `frontend/src/features/breakdowns/hooks/useBreakdownQueries.ts`, so route navigation often self-heals. Exact invalidation is still a small, well-established improvement and belongs in the reduced batch because mounted consumers can remain stale.

The submission-to-Calendar concern is credible but not yet a proven user-facing failure. Backend submission creation intentionally creates linked Calendar events and is protected by `backend/tests/test_cross_module_workflows.py`; the frontend can independently create an event when its checkbox is selected. A real-backend characterization must precede any behavioral change.

The unauthenticated API, process-global supervised browser, and local filesystem are **deployment constraints**. They are not reasons to build authentication, distributed browser infrastructure, or object storage for a sanitized single-user portfolio. The release must document and enforce the chosen posture: sanitized data, restricted origin, risky capabilities disabled, and a host compatible with any enabled uploads.

The broad read-repair, transaction, repository, barrel, type, accessibility, and large-file recommendations are not deployment blockers. Most are preferences or maintenance opportunities without demonstrated failures. The repository already has meaningful boundary tests and strong contract coverage; tested behavior should be preserved.

## 2. Review of all Category A tasks

### A1. Portfolio deployment exposure model

- **Classification:** `APPROVE WITH REDUCED SCOPE`
- **Evidence and symbols:** `backend/app/main.py:create_app` mounts the full v1 router; `backend/app/api/v1/router.py:api_router`; `backend/app/core/config.py:Settings`; `README.md` lists authentication as future work. No authentication dependency or middleware exists under `backend/app`.
- **Genuinely wrong or risky:** a remotely reachable backend containing real actor data or enabled mutation/import/browser controls would be publicly writable. CORS is not authentication.
- **Excessive in the original recommendation:** “define and enforce” could grow into capability frameworks, hosting-control integration, or an authentication project. None is justified for a sanitized demo.
- **Smallest justified implementation:** document the demo/data classification; use only sanitized seed data; set the exact frontend CORS origin; keep provider secrets out of the deployment; disable supervised-browser and other unsupported external-integration entry points using one production/demo setting.
- **Explicitly out of scope:** authentication, authorization, accounts, tenant ownership, billing, a policy engine, and generalized feature flags.
- **Required tests:** configuration test for exact production CORS; route smoke proving disabled capabilities return a stable unavailable response; `/health` plus representative read-only smoke against sanitized data.
- **Implementation risk:** low to medium.
- **Blocks frontend deployment:** **yes only if the deployed frontend will reach a public backend**. It does not block a static frontend using no live backend.
- **GitHub Issue:** yes, for the concrete hosting/data decision; not an authentication epic for this release.
- **Commit boundary:** one `chore(deploy)` commit, shared with the reduced A7 guard.

### A2. Missing discovery-report contract

- **Classification:** `APPROVE BEFORE DEPLOYMENT`
- **Evidence and symbols:** `frontend/src/features/breakdowns/api/index.ts:getDiscoveryReport`; `frontend/src/features/breakdowns/hooks/useBreakdownQueries.ts:useDiscoveryReport`; `frontend/src/features/breakdowns/components/BreakdownDiscovery.tsx:BreakdownDiscovery`; `backend/app/api/v1/routes/automation.py`; `backend/app/automation/discovery/service.py:_discovery_report`.
- **Genuinely wrong or risky:** the mounted query calls a route FastAPI does not register, producing a real 404 against the backend.
- **Excessive in the original recommendation:** adding durable report storage, report history, or a new read endpoint is unsupported by current persistence.
- **Smallest justified implementation:** remove the unsupported standalone query and retain the discovery mutation result in the existing UI lifecycle, unless a source inspection during implementation identifies already-persisted report data.
- **Explicitly out of scope:** new tables, report history, analytics, discovery-service restructuring, and broad Breakdowns cleanup.
- **Required tests:** API/hook/component test proving initial render makes no orphan request; discovery-run rendering test; strict-mock Playwright Breakdown flow; route inventory assertion.
- **Implementation risk:** low to medium.
- **Blocks frontend deployment:** **yes** for a live-backend deployment.
- **GitHub Issue:** no; this is a bounded defect.
- **Commit boundary:** isolated `fix(contract)` commit before A3.

### A3. Playwright catch-all mock behavior

- **Classification:** `APPROVE BEFORE DEPLOYMENT`
- **Evidence and symbols:** `frontend/e2e/support/mockApi.ts:installMockApi`, `handle`, and `defaultResponse`; `frontend/e2e/request-graphs.spec.ts`; `frontend/e2e/cross-feature.spec.ts`.
- **Genuinely wrong or risky:** an unknown method/path receives successful empty data, so browser tests can pass while the live backend would return 404. A2 demonstrates the failure mode.
- **Excessive in the original recommendation:** reproducing backend business logic, exhaustively typing every fixture, or building a generated mock server.
- **Smallest justified implementation:** make unmatched requests fail with method/path context and add only the explicit handlers exercised by the present Playwright suite.
- **Explicitly out of scope:** a TypeScript backend simulator, generated clients, fixture redesign, and unrelated E2E refactors.
- **Required tests:** a focused unknown-route failure test; all Playwright tests; frontend typecheck and build.
- **Implementation risk:** medium because it will expose latent test-fixture gaps, not because the code change is large.
- **Blocks frontend deployment:** **yes** as a release-confidence gate.
- **GitHub Issue:** no.
- **Commit boundary:** isolated `test(e2e)` commit after A2.

### A4. Submission-to-Calendar ownership

- **Classification:** `REQUIRES MORE EVIDENCE`
- **Evidence and symbols:** `frontend/src/features/auditions/hooks/useSubmissionTracker.ts:submit` and `createAuditionLinkedRecords`; `frontend/src/features/auditions/types/index.ts:SubmissionFormState`; `backend/app/services/submission_service.py:SubmissionService.create`; `backend/app/services/workflow_connector_service.py:after_submission_created`, `_ensure_calendar_events`, and `_create_event_once`; `backend/app/services/operations_service.py:create_event`; `backend/tests/test_cross_module_workflows.py:test_submission_added_records_linked_journal_and_calendar`; `frontend/e2e/cross-feature.spec.ts`.
- **Genuinely wrong or risky:** the backend automatically creates opportunity-derived events, while the selected frontend path can make a second independent Calendar POST. `OperationsService.create_event` does not apply the connector's deduplication key. The checkbox can therefore imply control it may not possess.
- **Excessive in the original recommendation:** immediately choosing a new owner and changing product semantics. The backend behavior is intentional and tested; the two event payloads may represent distinct intended events in some flows.
- **Smallest justified implementation:** first run a real PostgreSQL characterization using the exact frontend-equivalent payloads. If it proves duplicate events or an inaccurate opt-out, make the UI text reflect automatic behavior or pass one narrowly typed option to the backend. Preserve connector idempotency.
- **Explicitly out of scope:** Calendar redesign, generalized event synchronization, background jobs, changing Journal side effects, or moving all cross-feature orchestration.
- **Required tests:** real-backend checked/unchecked/retry characterization; existing cross-module workflow test; focused Auditions hook test; strict-mock cross-feature Playwright flow.
- **Implementation risk:** medium for characterization; high for an uncharacterized ownership change.
- **Blocks frontend deployment:** **the evidence check blocks; a code change blocks only if the failure is reproduced**.
- **GitHub Issue:** yes if reproduction confirms a semantic decision is required.
- **Commit boundary:** characterization test and any resulting narrowly scoped fix must be separate commits.

### A5. Profile and platform-import invalidation

- **Classification:** `APPROVE WITH REDUCED SCOPE`
- **Evidence and symbols:** `frontend/src/features/profile/hooks/useProfileQueries.ts:useUpdateActorProfile`, `useInvalidateImports`, and `usePlatformImportAction`; `frontend/src/services/api/invalidationContracts.ts`; `backend/app/services/actor_profile_service.py:_refresh_breakdown_eligibility`; `backend/app/services/workflow_connector_service.py:profile_changed`; `backend/app/services/platform_import_service.py:approve_profile`, `_create_credits_from_parsed`, and `_apply_skills_to_actor`; `frontend/src/features/breakdowns/hooks/useBreakdownQueries.ts`.
- **Genuinely wrong or risky:** actor updates recompute opportunity-derived data but invalidate only the actor query. Platform approval can create credits and change actor skills while import invalidation omits those owners. Already-mounted consumers can remain stale.
- **Excessive in the original recommendation:** invalidating every command-center, analytics, readiness, and material query without proving consumption. Breakdown navigation already refetches on mount, reducing the user-facing severity.
- **Smallest justified implementation:** extend the existing named invalidation-contract pattern with only actor, credits, import state, and directly proven opportunity-derived query keys. Keep forbidden unrelated owners explicit.
- **Explicitly out of scope:** broad `invalidateQueries()` calls, API consolidation, Profile component restructuring, and a new invalidation abstraction.
- **Required tests:** exact direct/derived/forbidden key assertions in `invalidationContracts.test.ts`; mutation success/failure tests in `useProfileQueries.test.tsx`; focused request-graph E2E; existing backend eligibility/import tests.
- **Implementation risk:** low to medium.
- **Blocks frontend deployment:** **yes for a portfolio flow that demonstrates profile/import changes and derived matching; otherwise it is a very small pre-deployment confidence improvement**.
- **GitHub Issue:** no.
- **Commit boundary:** one focused `fix(profile)` commit.

### A6. Opportunity read-side repair

- **Classification:** `DEFER UNTIL AFTER DEPLOYMENT`
- **Evidence and symbols:** `backend/app/services/opportunity_service.py:OpportunityService.list` and `get`; `backend/app/services/breakdown_role_service.py`; `backend/app/services/breakdown_deadline_service.py`; `backend/app/services/trust_verification_service.py`; `backend/app/services/character_intelligence_engine.py`.
- **Genuinely wrong or risky:** nominal GET operations may write and commit, so a read-only database role would fail and request latency/side effects are surprising.
- **Excessive in the original recommendation:** treating compatibility repair as a release defect and inferring current debt from Alembic history. The code deliberately repairs legacy/partially enriched rows, and no current-data failure or harmful write has been demonstrated.
- **Smallest justified implementation:** document that the current backend requires a write-capable database connection; run an observational pre-deployment data check. Open a follow-up only after identifying which current rows still trigger repair.
- **Explicitly out of scope:** moving repair code, one-shot migrations, read-model architecture, repository expansion, transaction rewrites, or deleting compatibility paths.
- **Required tests:** none before deployment beyond the existing opportunity/contract suite. A later issue should begin with current-row write characterization and legacy-row compatibility tests.
- **Implementation risk:** high if changed; negligible if documented.
- **Blocks frontend deployment:** **no** for the current single-user writable-database deployment.
- **GitHub Issue:** yes, narrowly titled around measuring repair-on-read.
- **Commit boundary:** no pre-deployment production commit; documentation may be included with B2.

### A7. Process-global supervised browser

- **Classification:** `APPROVE WITH REDUCED SCOPE`
- **Evidence and symbols:** `backend/app/services/supervised_breakdown_import_service.py:SupervisedBrowserController` and module-global `supervised_browser`; `backend/app/api/v1/routes/supervised_breakdowns.py:start_supervised_browser`, `supervised_browser_status`, `close_supervised_browser`; `backend/app/core/config.py:Settings`.
- **Genuinely wrong or risky:** one process-global browser/page cannot provide safe remote concurrency or isolation and a headful browser may not run on the host.
- **Excessive in the original recommendation:** changing browser ownership or lifecycle for production when the portfolio need is simply not to expose the local-only tool remotely.
- **Smallest justified implementation:** one production/demo capability check that prevents launch/capture and returns a stable unavailable response. Preserve the current local behavior.
- **Explicitly out of scope:** per-user sessions, browser farms, queues, locks, multi-worker coordination, or a new browser abstraction.
- **Required tests:** configuration/route tests for disabled production behavior and a retained local-mode service test.
- **Implementation risk:** low.
- **Blocks frontend deployment:** **yes only if these endpoints would otherwise be remotely reachable**.
- **GitHub Issue:** no for the guard; a distributed replacement is speculative and should not be opened now.
- **Commit boundary:** combine with A1's deployment-posture commit.

### A8. Local file upload/storage behavior

- **Classification:** `REQUIRES MORE EVIDENCE`
- **Evidence and symbols:** `backend/app/services/file_storage_service.py:FileStorageService`; `backend/app/services/asset_service.py:AssetService.create` and `delete`; `backend/app/services/platform_import_service.py:import_from_upload`; `backend/app/services/resume_pdf_service.py`; `backend/app/core/config.py:Settings.upload_dir`.
- **Genuinely wrong or risky:** local files require a persistent single host. A database failure after a file save can orphan a file, and deletion after commit can leave residue.
- **Excessive in the original recommendation:** treating object storage or compensation logic as mandatory before selecting a host or demonstrating a failure. For a single persistent demo instance, occasional orphan cleanup is operational debt, not data-integrity corruption.
- **Smallest justified implementation:** verify host persistence and whether uploads are part of the public demo. If storage is ephemeral, disable upload/import UI and routes for this release. Add compensation only after a focused failure test demonstrates the exact leak.
- **Explicitly out of scope:** object storage, CDN, media pipelines, cross-host synchronization, and generalized filesystem transactions.
- **Required tests:** deployment persistence smoke if enabled; otherwise disabled-capability route/UI test. Later compensation work needs temporary-directory failure tests.
- **Implementation risk:** low for disabling/documenting; medium for changing cleanup ordering.
- **Blocks frontend deployment:** **only if uploads are enabled on an ephemeral host or the deployment depends on durable uploaded assets**.
- **GitHub Issue:** yes only for a confirmed host/storage mismatch or reproduced orphan path.
- **Commit boundary:** host guard belongs with A1; compensation, if proven necessary, must be separate.

### A9. Verification suite and CI enforcement

- **Classification:** `APPROVE WITH REDUCED SCOPE`
- **Evidence and symbols:** `frontend/e2e/request-graphs.spec.ts`; `frontend/src/services/api/queryPolicy.ts`; `frontend/src/services/api/queryPolicyInventory.ts`; `.github/workflows/frontend-playwright.yml`; `.github/workflows/backend-contract-smoke.yml`; baseline results in `docs/architecture/phase-2-architecture-inventory.md`.
- **Genuinely wrong or risky:** the recorded immediate-return Calendar request-graph test fails, so the release has an unexplained contract disagreement. CI does not currently execute every documented local check.
- **Excessive in the original recommendation:** requiring every check to be newly wired into CI before portfolio deployment, or changing query policy merely to satisfy a potentially accidental test expectation.
- **Smallest justified implementation:** decide the Calendar freshness contract from user behavior, correct the test or smallest implementation accordingly, run and document the complete release suite, and keep the two existing critical workflows. Add broader CI wiring after deployment unless it is trivial.
- **Explicitly out of scope:** CI-provider migration, warning eradication outside configured gates, global query-policy changes, performance tests, and unrelated flaky-test work.
- **Required tests:** frontend unit, lint, `tsc --noEmit`, production build, full Playwright; backend fast pytest, configured Ruff check/format check, and contract smoke.
- **Implementation risk:** low to medium.
- **Blocks frontend deployment:** **yes for an unexplained required test failure; no for missing duplicate CI wiring when the documented local gate is green**.
- **GitHub Issue:** no for resolving the known failure; yes only for post-release CI coverage expansion.
- **Commit boundary:** one narrowly scoped Calendar contract commit if needed, then a separate `ci`/documentation commit.

## 3. Review of all Category B tasks

### B1. Route Career commands through mutation hooks

- **Classification:** `DEFER UNTIL AFTER DEPLOYMENT`
- **Evidence and symbols:** `frontend/src/features/career-intelligence/components/CareerIntelligencePanel.tsx:CareerPathSimulatorSection`; `frontend/src/features/career-intelligence/components/CareerLegacyPanels.tsx:AIIntelligencePanel`; `frontend/src/features/career-intelligence/api/index.ts`; `frontend/src/features/career-intelligence/hooks/useCareerQueries.ts`.
- **Genuinely wrong or risky:** presentation components directly await same-feature API functions and manually store ephemeral results, which makes pending/error behavior less uniform.
- **Excessive in the original recommendation:** describing this as a boundary violation or meaningful release risk. The calls remain inside the Career feature, and ephemeral command results are legitimate component state.
- **Smallest justified implementation:** when Career is next changed, add a mutation hook only where repeated pending/error/invalidation behavior exists.
- **Explicitly out of scope:** moving ephemeral results into Query cache, splitting the panels, or a hook-for-every-request rule.
- **Required tests:** focused success/error component characterization before any refactor; hook tests only if a hook is added.
- **Implementation risk:** medium.
- **Blocks frontend deployment:** no.
- **GitHub Issue:** yes, low-priority and narrowly scoped.
- **Commit boundary:** one Career-only refactor commit after deployment.

### B2. Publish the verified architecture and deployment narrative

- **Classification:** `APPROVE WITH REDUCED SCOPE`
- **Evidence and symbols:** `README.md`; the five Phase 2 documents; `frontend/src/services/api/invalidationContracts.ts`; `frontend/src/features/breakdowns/ARCHITECTURE.md`; `.github/workflows/backend-contract-smoke.yml`.
- **Genuinely wrong or risky:** a reviewer cannot quickly distinguish implemented deterministic behavior, demo constraints, verification commands, and future roadmap claims.
- **Excessive in the original recommendation:** a comprehensive architecture publication or marketing rewrite before deployment.
- **Smallest justified implementation:** update README with the actual entry points, sanitized-demo posture, deterministic agent/automation limits, exact verification sequence, and links to concise architecture evidence.
- **Explicitly out of scope:** screenshots, design refresh, exhaustive module documentation, and claims of auth/LLM capabilities.
- **Required tests:** link/path review and the release gate; no new runtime tests.
- **Implementation risk:** low.
- **Blocks frontend deployment:** no technically, but it should precede portfolio presentation because accurate framing is the task's value.
- **GitHub Issue:** no.
- **Commit boundary:** documentation-only commit after technical gates are settled.

### B3. Document public feature APIs and backend transaction ownership

- **Classification:** `REJECT`
- **Evidence and symbols:** `frontend/src/features/*/index.ts`; `frontend/eslint.config.js`; `backend/app/services/*`; `backend/app/agents/*`; `backend/app/automation/discovery/service.py`.
- **Genuinely wrong or risky:** some export and commit ownership must be inferred locally.
- **Excessive in the original recommendation:** it combines unrelated frontend export policy and backend transaction documentation without a failed workflow or concrete audience. Comments can become stale, and blanket documentation adds another ownership layer rather than reducing complexity.
- **Smallest justified implementation:** none as a standalone task. Document only a transaction or public contract when a concrete workflow is changed; retain existing lint and architecture tests.
- **Explicitly out of scope:** export inventories, commit annotations on every method, universal repository or unit-of-work conventions.
- **Required tests:** none.
- **Implementation risk:** low code risk but high documentation-drift cost.
- **Blocks frontend deployment:** no.
- **GitHub Issue:** no.
- **Commit boundary:** none; any future documentation belongs with the concrete behavior change.

### B4. Add a small accessibility smoke gate

- **Classification:** `DEFER UNTIL AFTER DEPLOYMENT`
- **Evidence and symbols:** `frontend/src/components/ui.tsx`; `frontend/src/layout/TopNavigation.tsx`; semantic/focus tests across Dashboard, Profile, Breakdowns, and Calendar; no `axe` integration found in frontend source or E2E tests.
- **Genuinely wrong or risky:** automated route-level accessibility coverage is absent, so cross-page regressions may escape selective component tests.
- **Excessive in the original recommendation:** absence of an automated scanner is not evidence of a critical violation. Adding a dependency and fixing newly surfaced issues can expand unpredictably.
- **Smallest justified implementation:** perform a manual keyboard/landmark/form-label smoke before launch; add a bounded automated scan after deployment.
- **Explicitly out of scope:** WCAG certification, design-system rewrite, third-party Calendar internals, and broad visual changes.
- **Required tests:** pre-release manual smoke; later one shell, one form, Dashboard, and Calendar automated scan.
- **Implementation risk:** low for the test, variable for remediation.
- **Blocks frontend deployment:** no unless the manual smoke finds a workflow-blocking defect.
- **GitHub Issue:** yes for a bounded post-release gate.
- **Commit boundary:** one test-only commit, with separate remediation commits if needed.

## 4. Review of all Category C tasks

### C1. Tighten schemas, errors, mocks, and list completeness

- **Classification:** `REJECT`
- **Evidence and symbols:** `backend/app/api/v1/routes/system.py`; `backend/app/api/v1/routes/intelligence.py:get_material_performance`; `backend/app/api/v1/routes/automation.py:recalculate_travel_exceptions`; `backend/app/api/v1/routes/command_center.py:resolve_outcome_nudge`; `frontend/src/services/api/request.ts`; `backend/app/repositories/base.py:BaseRepository.list`; `backend/app/repositories/opportunity.py:OpportunityRepository.search`.
- **Genuinely wrong or risky:** individual dictionary responses are broad, error detail is normalized, and some lists cap at 100.
- **Excessive in the original recommendation:** four unrelated concerns are bundled into an open-ended contract program without a failing production flow or dataset near the cap. A3 already addresses the material mock defect.
- **Smallest justified implementation:** none as one task. Open endpoint-specific work only after a concrete mismatch, error-handling need, or dataset threshold is demonstrated.
- **Explicitly out of scope:** generated clients, API versioning, repository-wide pagination, global error redesign, and fixture typing campaigns.
- **Required tests:** endpoint-specific characterization when evidence exists.
- **Implementation risk:** medium.
- **Blocks frontend deployment:** no.
- **GitHub Issue:** no umbrella issue; only evidence-specific future issues.
- **Commit boundary:** one endpoint family per future commit.

### C2. Consolidate duplicated endpoint ownership

- **Classification:** `DEFER UNTIL AFTER DEPLOYMENT`
- **Evidence and symbols:** duplicated platform functions in `frontend/src/features/profile/api/index.ts` and `frontend/src/features/materials/api/index.ts`; duplicated `createMaterialPlan` in `frontend/src/features/career-intelligence/api/index.ts` and `frontend/src/features/script-finder/api/index.ts`.
- **Genuinely wrong or risky:** duplicate transport definitions can drift and make invalidation ownership ambiguous.
- **Excessive in the original recommendation:** a new cross-feature owner or shared abstraction may create more coupling than the small duplicate wrappers remove. No current URL/payload drift is proven.
- **Smallest justified implementation:** after deployment, compare signatures and consolidate one resource only when the next behavior change needs a shared contract.
- **Explicitly out of scope:** merging features, changing backend URLs, a generic API layer, or moving unrelated types.
- **Required tests:** current feature tests, exact invalidation tests, build/lint, and a focused E2E for the touched resource.
- **Implementation risk:** medium.
- **Blocks frontend deployment:** no.
- **GitHub Issue:** yes, split platform resources and material plans.
- **Commit boundary:** one resource family per commit.

### C3. Reduce large modules through characterized seams

- **Classification:** `REJECT`
- **Evidence and symbols:** `frontend/src/features/breakdowns/components/BreakdownDetails.tsx`; `frontend/src/features/career-intelligence/components/CareerIntelligencePanel.tsx`; `frontend/src/features/dashboard/components/DashboardPanel.tsx`; `frontend/src/features/source-library/components/SourceLibraryPanel.tsx`; `backend/app/services/intelligence_service.py`; `backend/app/automation/discovery/service.py`; `backend/app/services/source_research_service.py`.
- **Genuinely wrong or risky:** some files are costly to review and may contain extraction seams.
- **Excessive in the original recommendation:** line count is not a defect. These modules largely represent cohesive workflows, and the proposal itself supplies no concrete repeated behavior or failing seam.
- **Smallest justified implementation:** none independently. Extract only as part of an adjacent feature change when characterization shows a simpler interface.
- **Explicitly out of scope:** size targets, folder redesign, “clean architecture,” service splitting, and extraction-only issues.
- **Required tests:** none until a concrete behavior change exists.
- **Implementation risk:** medium to high.
- **Blocks frontend deployment:** no.
- **GitHub Issue:** no vague “split large files” issue.
- **Commit boundary:** any future extraction belongs with its motivating behavior or in an immediately preceding characterized refactor.

### C4. Migrate types and public barrels incrementally

- **Classification:** `DEFER UNTIL AFTER DEPLOYMENT`
- **Evidence and symbols:** `frontend/src/types/domain.ts`; `frontend/src/features/*/types/index.ts`; `frontend/src/features/*/index.ts`; duplicated `DiscoveryMode`; `frontend/eslint.config.js`.
- **Genuinely wrong or risky:** ownership is sometimes obscure and compatibility barrels can expose more than consumers require.
- **Excessive in the original recommendation:** file size and duplicate aliases do not show runtime harm. Moving types can produce import churn while preserving exactly the same complexity.
- **Smallest justified implementation:** move one domain family only during adjacent work, retain compatibility exports, and let existing import-boundary lint protect internals.
- **Explicitly out of scope:** a global type migration, barrel ban, directory moves, or generated contracts.
- **Required tests:** TypeScript, lint architecture rules, unit tests, and build for the touched family.
- **Implementation risk:** medium.
- **Blocks frontend deployment:** no.
- **GitHub Issue:** only for a concrete domain family, not a repository-wide migration.
- **Commit boundary:** one family per post-release commit.

### C5. Clarify backend transaction and persistence boundaries

- **Classification:** `REJECT`
- **Evidence and symbols:** commit behavior varies in `backend/app/api/v1/routes/agents.py`, `career_development.py`, `travel_preferences.py`, and `command_center.py`; services under `backend/app/services`; agents under `backend/app/agents`; selective repositories under `backend/app/repositories`.
- **Genuinely wrong or risky:** a composed workflow can become unsafe if a future caller assumes an incorrect commit owner.
- **Excessive in the original recommendation:** selective repositories and direct ORM queries are not defects in this single-process application. No rollback failure is identified for the proposed umbrella task, and introducing non-committing variants can enlarge the API.
- **Smallest justified implementation:** none generically. When a concrete transaction bug is reproduced, characterize that workflow and establish one commit owner locally.
- **Explicitly out of scope:** repository-wide repository pattern, unit-of-work layer, service API duplication, agent purity rewrite, and moving every ORM query.
- **Required tests:** focused rollback/commit-count test only for a reproduced workflow.
- **Implementation risk:** high.
- **Blocks frontend deployment:** no.
- **GitHub Issue:** no umbrella issue; only a specific reproduced transaction defect.
- **Commit boundary:** one workflow per future fix.

### C6. Retire dead compatibility surfaces and naming ambiguity

- **Classification:** `DEFER UNTIL AFTER DEPLOYMENT`
- **Evidence and symbols:** `frontend/src/components/layouts/index.ts` exports `workflowLayouts`; `frontend/src/utilities/index.ts`; `frontend/src/features/profile/api/index.ts:updateTravelPreferences`; `frontend/src/features/career-intelligence/components/CareerLegacyPanels.tsx`; orphan candidates in `docs/architecture/phase-2-contract-audit.md`.
- **Genuinely wrong or risky:** unused helpers and ambiguous legacy names add search noise; `updateTravelPreferences` has no discovered frontend caller.
- **Excessive in the original recommendation:** frontend search cannot prove backend endpoints are unused, and “legacy” can denote an active compatibility path. Deletion creates little portfolio value.
- **Smallest justified implementation:** after deployment, remove only symbols proven unused by source search, build, tests, and—where relevant—access logs.
- **Explicitly out of scope:** route renaming, compatibility removal based on age, mass directory cleanup, and deleting placeholders that document intended seams.
- **Required tests:** `rg` consumer inventory, TypeScript, lint, build, and route smoke for any backend removal.
- **Implementation risk:** low per proven symbol; medium for endpoints.
- **Blocks frontend deployment:** no.
- **GitHub Issue:** usually no; create one only for a grouped, verified compatibility retirement.
- **Commit boundary:** narrowly grouped dead surfaces only.

## 5. Findings whose severity should change

| Audit finding | Original posture | Revised severity | Reason |
|---|---|---|---|
| Missing discovery-report route | High | **High, confirmed** | It is an active mounted query with no registered backend route. |
| Catch-all mock success | High | **High for test confidence; medium for runtime** | It demonstrably concealed A2, but it does not itself ship in production. |
| Submission/Calendar ownership | High | **Medium, needs runtime characterization** | Static paths can produce two events, but backend auto-projection is intentional and tested; equivalence of the two event intents is not yet proven. |
| Profile/import invalidation | High | **Medium** | The cache gap is confirmed, but `refetchOnMount: "always"` often self-heals and no data is lost. |
| Career components calling same-feature APIs | High/major maintainability concern | **Low to medium** | This is local orchestration of ephemeral command results, not cross-feature transport bypass. |
| Opportunity repair on GET | High | **Medium operational constraint** | Surprising and write-dependent, but explicitly compatibility-oriented with no demonstrated current-row failure. |
| Process-global supervised browser | High | **Low when disabled/local; high only if remotely exposed** | Risk depends entirely on deployment posture. |
| Local filesystem storage | Medium/high release concern | **Needs verification; low for persistent single-host demo** | Host choice and enabled demo flows determine the risk. |
| Silent list cap at 100 | Medium | **Low for current portfolio scope** | No evidence the demo dataset approaches the cap; pagination remains future scalability work. |
| Inconsistent transaction ownership/direct ORM | High architectural concern | **Medium only for a reproduced composed workflow** | Direct ORM and selective repositories are not inherently harmful; important workflows already have contract tests. |
| Large frontend/backend files | Medium | **Informational** | Size alone does not prove mixed responsibilities; several files implement cohesive workflows. |
| No route-level automated accessibility scan | Medium | **Low/needs verification** | Existing semantic and focus tests are meaningful; no actual critical accessibility failure was identified. |
| Public unauthenticated backend | Implied critical | **High only for private/live data; acceptable constrained demo posture** | This is a release-model decision, not evidence that Phase 2 needs authentication. |

No finding warrants an unconditional severity upgrade. The exposure model becomes a genuine high-severity blocker only if the team intends to publish real private data or unrestricted mutation capabilities.

## 6. Recommendations that should be rejected entirely

1. **B3 as a standalone documentation program.** It combines two unrelated concerns, risks stale ownership prose, and has no demonstrated failure. Document contracts beside concrete changes.
2. **C1 as an umbrella contract cleanup.** Schema precision, error preservation, mocks, and pagination require separate evidence and acceptance criteria. A3 already addresses the confirmed mock defect.
3. **C3 size-driven module reduction.** The audit does not demonstrate unrelated responsibilities or a simpler target boundary for each named file.
4. **C5 generalized transaction/persistence clarification.** It would invite repository and non-committing-service proliferation without a reproduced rollback problem.
5. Any authentication, multi-tenancy, object-storage, distributed-browser, design-system, generated-client, repository-pattern, or unit-of-work work for this sanitized portfolio release.
6. Treating historical Alembic migrations as current architectural debt without showing a current schema/data defect.
7. Removing compatibility paths or orphan endpoint candidates based only on frontend source search.

## 7. The smallest high-confidence pre-deployment cleanup batch

The bounded batch is:

1. Resolve the unsupported discovery-report request (A2).
2. Make Playwright reject unhandled requests and add only required handlers (A3).
3. Add exact profile/platform-import invalidation contracts (reduced A5).
4. Establish the sanitized-demo deployment configuration and disable remote supervised browsing (reduced A1 + A7).
5. Verify the chosen host's upload persistence; disable uploads for the release if persistence is unavailable (evidence-only/conditional A8).
6. Characterize the combined submission/Calendar path against the real backend; change behavior only if duplicate or misleading opt-out behavior is reproduced (evidence-first A4).
7. Resolve the known Calendar request-graph disagreement, run the full standard suite, and document the result (reduced A9).
8. Publish a concise, accurate README deployment/architecture narrative (reduced B2).

A6, B1, B3, B4, and every Category C refactor are excluded.

## 8. Exact execution order for that batch

1. Record the target host, backend reachability, sanitized-data rule, exact CORS origin, enabled integrations, and upload persistence.
2. Implement A2 so the frontend no longer makes the nonexistent report request.
3. Implement A3 and run the full Playwright suite to expose any other unhandled route.
4. Implement reduced A5 using the existing invalidation-contract mechanism.
5. Implement the A1/A7 deployment guard; conditionally disable upload surfaces if step 1 found no persistent storage.
6. Add and run the A4 real-backend characterization. Stop without changing product behavior if no duplicate/misleading behavior is reproduced.
7. Adjudicate the existing Calendar freshness test from the intended user behavior, make only the necessary test or policy correction, and run the complete verification sequence.
8. Update README with verified architecture, constraints, and commands.
9. Build a release candidate and run deployed health, route, browser, capability, CORS, and sanitized-data smoke checks.

## 9. Deployment blockers versus non-blockers

### Blockers

- A2's active nonexistent endpoint.
- A3's permissive mock behavior as long as it can conceal unknown release requests.
- Any unexplained failure in the required release suite.
- Public backend exposure with private data, permissive origin, provider secrets, or remotely enabled supervised-browser controls.
- Enabled upload workflows on a host known not to persist files.
- A reproduced submission/Calendar duplicate or false opt-out in a portfolio-demonstrated flow.

### Non-blockers

- Removing opportunity repair-on-read on the current writable single-user backend.
- Routing same-feature Career commands through mutation hooks.
- Broad feature-barrel or global-type migration.
- Adding response models to every dictionary endpoint.
- Repository or unit-of-work standardization.
- Large-file extraction without an adjacent behavior change.
- Automated accessibility tooling when a manual smoke finds no critical defect.
- Dead-helper cleanup, endpoint consolidation, pagination below demonstrated dataset limits, or historical migration consolidation.
- Wiring every locally documented check into CI, provided the exact release gate is run and recorded.

## 10. Proposed commit sequence

1. `fix(contract): remove unsupported discovery report request`
2. `test(e2e): reject unhandled mock API requests`
3. `fix(profile): invalidate proven profile and import consumers`
4. `chore(deploy): enforce sanitized demo capabilities`
5. `test(auditions): characterize submission calendar projection`
6. `fix(auditions): align calendar behavior with characterized contract` — **only if the characterization fails**
7. `test(calendar): align immediate-return freshness contract` — use `fix(calendar)` only if production code is actually wrong
8. `ci: document and enforce the release verification gate` — CI wiring may be omitted from this release if the local gate is recorded
9. `docs: document portfolio architecture and deployment limits`

Do not combine the conditional A4 behavior change with its characterization, and do not mix documentation or CI changes into production fixes.

## 11. Proposed GitHub Issues for deferred work

No Issues should be created during this audit. If the evidence remains relevant after deployment, use:

1. `Measure and document opportunity repair-on-read for current data`
2. `Add a bounded accessibility smoke gate for portfolio routes`
3. `Consolidate platform import transport ownership when next changed`
4. `Consolidate material-plan transport ownership when next changed`
5. `Standardize Career command pending and error handling`
6. `Verify and compensate orphaned local uploads after reproduced database failures` — only if reproduced
7. `Expand CI to run the complete portfolio release gate`
8. `Define pagination for opportunities before the portfolio dataset reaches 100 records` — only when data growth justifies it

Do not open issues named “clean architecture,” “split large files,” “migrate global types,” “standardize repositories,” or “clarify all transactions.”

## 12. Final deployment recommendation

Deploy the frontend immediately after the reduced cleanup batch and release-candidate smoke checks pass. This recommendation assumes a sanitized single-user demo, an explicitly constrained backend exposure model, no private data, and disabled unsupported integrations. It does not endorse the same architecture as a public multi-user SaaS deployment.

The reduced batch preserves tested product behavior, fixes the one confirmed active API defect, makes browser tests capable of detecting contract drift, closes narrowly proven freshness gaps, and addresses deployment constraints through configuration rather than speculative architecture.

## Implementation handoff

1. Resolve A2's unsupported discovery-report request.
2. Make A3's Playwright mocks fail on every unhandled method/path.
3. Add reduced A5 invalidation for only proven actor, credit/import, and opportunity-derived owners.
4. Enforce the reduced A1/A7 sanitized-demo, exact-CORS, provider-off, supervised-browser-off posture.
5. Verify A8 host persistence and disable uploads if persistence is unavailable.
6. Characterize A4 against PostgreSQL; fix only a reproduced duplicate or misleading opt-out.
7. Resolve A9's Calendar freshness disagreement and run the complete release suite.
8. Publish reduced B2 deployment and architecture documentation.
9. Deploy the release candidate and run production smoke checks.
