# Phase 2 Frontend Architecture Audit

**Branch:** `release/portfolio-readiness`  
**Audit date:** 2026-07-26  
**Scope:** `frontend/src`, frontend configuration, frontend unit/architecture tests, and Playwright tests.  
**Constraint:** This is an evidence-based audit only. No production code was changed.

## Audit method

This audit inspected:

- application entry and composition: `frontend/src/main.tsx`, `App.tsx`, `app/*`, `pages/*`, and `layout/*`;
- shared server-state infrastructure: `frontend/src/services/api/*` and `services/system/*`;
- every feature public barrel and every feature `api`, `hooks`, `components`, `types`, `utils`, and `constants` directory;
- shared UI, global domain types, utilities, and design-system files;
- relevant unit, component, architecture, and browser tests;
- production import edges, query-key declarations, direct request calls, QueryClient construction, browser storage, and file line counts.

“Confirmed” findings follow directly from inspected imports/symbols/tests. “Strong inference” is used when the structure strongly indicates a risk but runtime impact depends on usage. “Needs verification” is reserved for intent or deployment behavior not provable from source.

## Executive assessment

The frontend is already meaningfully feature-oriented. Previous cleanup established enforceable boundaries around route pages, query ownership, public feature imports, shared API access, query keys, cache freshness, invalidation, and route-private Breakdowns components. The correct next move is not a framework change or broad reorganization.

The principal architecture debt is concentrated in:

1. very large workflow components that combine orchestration, derived data, forms, and rendering;
2. direct same-feature API calls from Career presentation components, bypassing mutation hooks and cache coordination;
3. duplicated API ownership between Profile, Materials, Career Intelligence, and Script Finder;
4. broad feature barrels and a 1,381-line global transport-type file;
5. dense but intentional cross-feature composition in Dashboard, Career Intelligence, and Breakdowns;
6. architecture tests that mix valuable invariant enforcement with brittle source-text assertions.

No critical finding was identified. One high-severity maintainability/runtime-risk finding is present in the Career direct-API path. Most other findings are medium or low and should be addressed only through bounded, behavior-preserving changes.

## 1. What is already strong

### 1.1 Entry points and route composition are clean

- `frontend/src/main.tsx:8-15` limits bootstrap concerns to React mounting, `AppProviders`, `BrowserRouter`, and global CSS.
- `frontend/src/App.tsx:6-17` lazy-loads route pages.
- `frontend/src/App.tsx:54-85` owns only shell-wide capabilities, navigation, loading/error isolation, and the route table.
- The route pages are composition roots. For example:
  - `frontend/src/pages/CalendarPage.tsx:7-27` composes public hooks from Calendar, Profile, Breakdowns, Auditions, and Chief of Staff;
  - `frontend/src/pages/JournalPage.tsx:7-20` composes public options from Career, Materials, Breakdowns, and Auditions;
  - `frontend/src/pages/AuditionsPage.tsx:6-16` supplies actor, opportunity, and material data to `AuditionsPanel`.
- No feature-specific mutation or workflow logic was found in `App.tsx`.

Protection:

- `frontend/src/App.test.tsx`
- `frontend/src/app/globalServerStateRetirement.test.ts`
- `frontend/e2e/app-shell.spec.ts`
- the `architecture/imports` rule in `frontend/eslint.config.js`.

### 1.2 Server state is consistently owned by TanStack Query

- `frontend/src/app/queryClient.ts:15-31` creates the only production `QueryClient`.
- `frontend/src/app/providers/AppProviders.tsx:5-6` installs that client once.
- No production feature constructs another `QueryClient`.
- No raw query-key array was found in production `queryKey` or invalidation declarations.
- No production `localStorage`, `sessionStorage`, Redux, Zustand, or custom server-state context was found.
- The only production `fetch` is inside `frontend/src/services/api/request.ts:16-56`.
- Feature API modules call the shared `api` adapter; presentation modules do not call the base request client.

Protection:

- `frontend/src/app/globalServerStateRetirement.test.ts:21-29`
- `frontend/src/app/queryClient.test.ts`
- `frontend/src/app/providers/AppProviders.test.tsx`
- `frontend/src/services/api/queryKeys.test.ts`
- feature query-boundary tests.

### 1.3 Query freshness and invalidation are explicit

- `frontend/src/services/api/queryKeys.ts` provides a common feature-key factory.
- `frontend/src/services/api/queryPolicy.ts` defines four named freshness budgets.
- `frontend/src/services/api/queryPolicyInventory.ts` records owners, consumers, endpoints, volatility, and consequences.
- `frontend/src/services/api/invalidationContracts.ts` distinguishes direct, derived, forbidden, and no-op invalidation.
- `invalidateInBackground` uses `Promise.allSettled`, so a refetch failure does not turn a successful mutation into a failed mutation.

Protection:

- `frontend/src/services/api/queryPolicyInventory.test.ts`
- `frontend/src/services/api/invalidationContracts.test.ts`
- mutation hook tests;
- targeted Playwright invalidation/request-graph tests.

The known Playwright failure in `frontend/e2e/request-graphs.spec.ts` means one live Calendar refetch expectation currently diverges from runtime behavior; it does not erase the value of the policy architecture.

### 1.4 Cross-feature imports go through public APIs

The custom `architecture/imports` rule in `frontend/eslint.config.js` rejects:

- page imports of feature internals;
- cross-feature internal imports;
- features importing pages;
- shared components importing features/pages;
- design-system imports of features/pages/services/components;
- unapproved direct shared API-client imports;
- feature barrels exporting pages or other feature implementations.

The Phase 1 lint baseline passed, confirming current source obeys those rules.

Feature-specific tests add narrower checks:

- `frontend/src/features/analytics/analyticsArchitecture.test.ts`
- `frontend/src/features/breakdowns/query-boundary.test.ts`
- `frontend/src/features/calendar/calendarInteractionArchitecture.test.ts`
- `frontend/src/features/chief-of-staff/commandCenterArchitecture.test.ts`
- `frontend/src/features/profile/profileArchitecture.test.ts`
- `frontend/src/features/materials/reusableSelfTapeArchitecture.test.ts`.

### 1.5 Earlier Breakdowns cleanup created useful route-private boundaries

The Breakdowns feature contains unusually strong evidence of prior deliberate cleanup:

- `OpportunityFormWorkspace` and its model are route-private and own the bounded create/edit draft.
- `BreakdownViewer` is route-private, receives callbacks, and does not fetch.
- `RoleViewer` is route-private and presentation-only.
- `HiddenOpportunityReview` owns selection by ID rather than copying full server records into state.
- `SubmissionQueuePanel` is deliberately not public.

Protection:

- `frontend/src/features/breakdowns/presentation-boundary.test.ts`
- `query-boundary.test.ts`
- `breakdownViewerArchitecture.test.ts`
- `breakdownRoleDetailsArchitecture.test.ts`
- `hiddenOpportunityReviewArchitecture.test.ts`
- `OpportunityFormWorkspace.test.tsx`
- `opportunityFormModel.test.ts`.

These are working patterns worth preserving. A different state library or folder taxonomy would not improve them by itself.

### 1.6 Accessibility and failure-state handling are visible design concerns

Confirmed patterns include:

- labeled controls through shared `Field` and explicit labels;
- `role="status"` for loading/pending messages;
- `role="alert"` for local and partial errors;
- `aria-expanded` and `aria-controls` on disclosures/navigation;
- focus restoration after local mutation failure/success in Breakdowns and Materials;
- `rel="noreferrer"` or `noopener,noreferrer` on external navigation;
- semantic role-based tests throughout Testing Library and Playwright.

Examples:

- `frontend/src/features/breakdowns/components/BreakdownDetails.tsx:776-859` (`RecommendationFeedbackControls`);
- `frontend/src/features/breakdowns/components/OpportunityFormWorkspace.tsx:59-95`;
- `frontend/src/features/calendar/components/ActorCalendar.tsx`;
- `frontend/src/components/ui.tsx`.

No automated axe-style accessibility suite was found; that is recorded as a low-severity gap below, not evidence that the current UI is inaccessible.

## 2. Ten largest frontend production files

Counts exclude tests and are based on the current working tree.

| Rank | Lines | File | Architectural role |
|---:|---:|---|---|
| 1 | 1,381 | `frontend/src/types/domain.ts` | Global frontend transport/domain type registry |
| 2 | 870 | `frontend/src/features/breakdowns/components/BreakdownDetails.tsx` | Breakdown presentation helpers, recommendation UI, feedback workflow |
| 3 | 748 | `frontend/src/features/career-intelligence/components/CareerIntelligencePanel.tsx` | Career route orchestration and multiple career subviews/forms |
| 4 | 694 | `frontend/src/features/dashboard/components/DashboardPanel.tsx` | Cross-feature query composition, widget registry, customization, rendering |
| 5 | 645 | `frontend/src/features/career-intelligence/components/CareerLegacyPanels.tsx` | Legacy intelligence, career tasks, materials, script-finder orchestration |
| 6 | 639 | `frontend/src/features/source-library/components/SourceLibraryPanel.tsx` | Source queries, mutations, forms, grouping, external search, rendering |
| 7 | 544 | `frontend/src/features/breakdowns/components/BreakdownManager.tsx` | Visible breakdown list, filters, parse/reject/role/strategy orchestration |
| 8 | 536 | `frontend/src/features/profile/components/ActorProfilePanel.tsx` | Actor profile plus representation form/workflow |
| 9 | 458 | `frontend/src/components/ui.tsx` | Shared UI primitive collection |
| 10 | 428 | `frontend/src/features/profile/components/PlatformProfileImportAssistant.tsx` | Profile-import workflow and asset-mapping UI |

Line count is not itself a defect. It is used here to identify where multiple responsibility changes are most likely to collide.

## 3. Suspected cross-feature dependency map

All confirmed production cross-feature imports use the target feature's public barrel.

```text
auditions
  → materials (MaterialOption)
  → calendar (calendarEventListKey)

breakdowns
  → source-library (panel, form, hooks, list/archive keys)
  → profile (actor and representation hooks)
  → materials (material hook)

career-intelligence
  → chief-of-staff (panel)
  → analytics (industry/intelligence hooks)
  → relationships (analytics hook)
  → materials (options, upload/analyze)
  → profile (actor hook)
  → breakdowns (opportunity hook)
  → script-finder (panel, controls, hook)

dashboard
  → analytics
  → calendar
  → relationships
  → source-library
  → chief-of-staff
  → career-intelligence
  → breakdowns
  → auditions

journal
  → breakdowns (OpportunityOption)
  → materials (MaterialOption)

profile
  → materials (MaterialOption/useMaterialOptions)
```

Interpretation:

- Dashboard is intentionally a read-composition hub.
- Career Intelligence is both a composition hub and a workflow owner; its breadth needs more scrutiny than Dashboard's.
- Breakdowns owns a combined opportunity/discovery workspace and therefore depends on Source Library, Profile, and Materials.
- The highest-risk edges are not the component/type edges. They are cache-key edges (`auditions → calendar`, `breakdowns → source-library`) and duplicate endpoint ownership (`materials ↔ profile`, `career-intelligence ↔ script-finder`).
- No confirmed production import cycle was found. The graph has future cycle risk because broad barrels export API functions, query hooks, keys, types, and panels together.

## 4. Detailed findings

### F-01 — Career presentation bypasses mutation/query hooks

- **Severity:** high
- **Confidence:** confirmed
- **Paths and symbols:**
  - `frontend/src/features/career-intelligence/components/CareerIntelligencePanel.tsx`
    - import of `simulateCareerPath` from `../api`;
    - `CareerPathSimulatorSection`.
  - `frontend/src/features/career-intelligence/components/CareerLegacyPanels.tsx`
    - imports `createMaterialPlan`, `prepareOpportunity`, and `simulateCareerPath` from `../api`;
    - `AIIntelligencePanel`.
- **Why it matters:** These components await API functions directly and place returned server results in component state. They bypass TanStack mutation state, the shared retry/error conventions, cache invalidation, request de-duplication, and canonical hook test patterns. Errors from the awaited calls can also escape local UI handling depending on the event path.
- **Smallest safe improvement:** Add feature-owned `useMutation` hooks for simulation, preparation, and material-plan creation. Preserve current local result display state if it is intentionally ephemeral, but move network pending/error ownership into those hooks. Do not reorganize the entire Career feature.
- **Tests that protect current behavior:** `frontend/src/features/career-intelligence/hooks/useCareerQueries.test.tsx` protects existing canonical career query/mutation behavior, but no focused component test was found for these direct calls. Playwright request-graph tests exercise Career route entry, not these commands.
- **Risk of changing it:** medium-high. These are user-triggered workflows with result rendering; moving them can alter pending states, error display, and whether cached records refresh.
- **Impact:** runtime behavior, maintainability, portfolio readiness.

### F-02 — Platform import and asset-mapping API ownership is duplicated

- **Severity:** medium
- **Confidence:** confirmed
- **Paths and symbols:**
  - `frontend/src/features/materials/api/index.ts:51-68`
    - `importPublicProfileUrl`
    - `importProfileUpload`
    - `createPlatformAssetMapping`
    - `updatePlatformAssetMapping`
    - `deletePlatformAssetMapping`.
  - `frontend/src/features/profile/api/index.ts:81-138` defines the same endpoints and symbol names.
- **Why it matters:** Two features can drift in endpoint shape, return type, error behavior, or cache invalidation while appearing to own the same backend resources. It also makes it unclear whether platform imports are Profile-owned and Materials consumes mappings, or whether both are independent owners.
- **Smallest safe improvement:** Establish one canonical feature API owner for each endpoint. Reuse public hooks or a narrowly exported command from that owner; remove duplicates only after consumer and invalidation characterization.
- **Tests that protect current behavior:** `frontend/src/features/profile/profileArchitecture.test.ts`, `ProfilePanel.test.tsx`, Materials component/hook tests, and `frontend/e2e/cross-feature.spec.ts`. No test currently asserts single endpoint ownership.
- **Risk of changing it:** medium. Profile import approval can change credits/mappings/material options, so incorrect consolidation could omit necessary invalidations.
- **Impact:** maintainability, runtime behavior, portfolio readiness.

### F-03 — Material-plan creation has two feature API owners

- **Severity:** medium
- **Confidence:** confirmed
- **Paths and symbols:**
  - `frontend/src/features/career-intelligence/api/index.ts:50-52` (`createMaterialPlan`);
  - `frontend/src/features/script-finder/api/index.ts:12-14` (`createMaterialPlan`);
  - `CareerLegacyPanels` consumes the Career version while `useScriptFinder` consumes the Script Finder version.
- **Why it matters:** The same endpoint (`POST /intelligence/materials/plan`) has two transport definitions and two potential orchestration policies. Plan approval/denial exists only in Script Finder, suggesting resource ownership is split.
- **Smallest safe improvement:** Decide which feature owns material-plan lifecycle and expose a narrow public hook/command to the other feature. Preserve present request and result shapes.
- **Tests that protect current behavior:** `frontend/src/features/script-finder/hooks/useScriptFinder.ts` has no focused hook test; Career query tests do not cover the direct component call. Existing browser tests cover the “Find Scene Options” navigation path but not full material-plan ownership.
- **Risk of changing it:** medium.
- **Impact:** maintainability and runtime behavior.

### F-04 — `domain.ts` is a global 1,381-line transport-type registry

- **Severity:** medium
- **Confidence:** confirmed
- **Paths and symbols:**
  - `frontend/src/types/domain.ts` contains types from `ActorProfile` through `WatchList`;
  - all feature `types/index.ts` files largely import, alias, or re-export these global types.
- **Why it matters:** Almost every feature depends on one file, so unrelated backend contract changes widen the change surface and make feature ownership difficult to read. It also encourages components to import another feature's resource types from the global file rather than through an intentional public contract.
- **Smallest safe improvement:** During bounded feature work, move only clearly feature-owned transport types into that feature and re-export compatibility aliases temporarily. Keep genuinely cross-domain DTOs shared. Do not split all 1,381 lines in one change.
- **Tests that protect current behavior:** TypeScript build, all feature tests, and feature public barrels. There is no dedicated type-ownership test.
- **Risk of changing it:** high if attempted broadly; low-to-medium for one characterized resource family.
- **Impact:** maintainability and portfolio readiness; no current runtime impact.

### F-05 — Feature type layers sometimes rename shared types without creating a real boundary

- **Severity:** low
- **Confidence:** confirmed
- **Paths and symbols:**
  - `frontend/src/features/analytics/types/index.ts` aliases `CostDashboard` to `CostSummary` and `IndustryTrendDashboard` to `CastingPatternDashboard`;
  - `frontend/src/features/calendar/types/index.ts` aliases `AuditionCalendarEvent` to `CalendarEvent`;
  - `frontend/src/features/chief-of-staff/types/index.ts` contains multiple aliases to `CommandCenterCard`/`ExecutiveBrief`;
  - `frontend/src/features/dashboard/types/index.ts` re-exports shared widget types.
- **Why it matters:** Aliases can express a useful feature vocabulary, but broad aliasing may imply isolation that does not exist and creates two names for the same transport contract.
- **Smallest safe improvement:** Keep aliases that communicate a real UI abstraction; remove only redundant aliases when touching their consumers. Document whether a type is a transport DTO, feature view model, or form state.
- **Tests that protect current behavior:** TypeScript build and feature component tests.
- **Risk of changing it:** low mechanically, medium for reviewer confusion if done broadly.
- **Impact:** maintainability and style only.

### F-06 — `DiscoveryMode` is independently duplicated

- **Severity:** low
- **Confidence:** confirmed
- **Paths and symbols:**
  - `frontend/src/features/breakdowns/types/index.ts:36` (`DiscoveryMode`);
  - `frontend/src/features/source-library/types/index.ts:31` (`DiscoveryMode`).
- **Why it matters:** The identical union can diverge silently while both features participate in one discovery workflow.
- **Smallest safe improvement:** Choose the workflow owner and export the type from its public API, or define a deliberately shared discovery contract. Avoid creating a new global “miscellaneous types” file.
- **Tests that protect current behavior:** Breakdowns discovery tests and Source Library hook/component tests compile against the current unions.
- **Risk of changing it:** low.
- **Impact:** maintainability only.

### F-07 — Public feature barrels expose more than the inter-feature contract needs

- **Severity:** medium
- **Confidence:** confirmed
- **Paths and symbols:**
  - wildcard exports in most `frontend/src/features/*/index.ts`;
  - examples: Auditions exports all query hooks and all raw API functions; Breakdowns exports all APIs, discovery hooks, query hooks, and types; Career Intelligence exports all APIs and hooks; Profile exports all APIs and hooks.
- **Why it matters:** A consumer can bypass canonical hooks by importing a raw command from the public barrel. Broad exports make dependency edges less intentional and increase name-collision/cycle risk. F-01 demonstrates that direct API usage already occurs inside a feature; public export makes the same pattern available cross-feature.
- **Smallest safe improvement:** Inventory actual outside consumers and replace wildcard exports with explicit panels, selectors, types, and hooks. Keep raw transport functions private unless another feature has a documented reason to call them.
- **Tests that protect current behavior:** ESLint protects use of the barrel but does not restrict what the barrel exports. Breakdowns route-private tests protect a few deliberately private components.
- **Risk of changing it:** medium because consumers may rely on names indirectly and tests mock public modules.
- **Impact:** maintainability and portfolio readiness.

### F-08 — Cross-feature invalidation sometimes depends on another feature's concrete key export

- **Severity:** medium
- **Confidence:** confirmed
- **Paths and symbols:**
  - `frontend/src/features/auditions/hooks/useSubmissionTracker.ts:4,85-87` imports and invalidates `calendarEventListKey`;
  - `frontend/src/features/breakdowns/hooks/useBreakdownQueries.ts:6,60` imports `sourceArchiveKey` and `sourceListKey`.
- **Why it matters:** These edges make mutation owners depend on another feature's cache implementation rather than only on a stable shared invalidation contract. The repository already has `publicInvalidationKeys` and typed invalidation contracts for this purpose, so the mixed pattern is harder to reason about.
- **Smallest safe improvement:** Add the proven relationships to the shared invalidation registry or expose a purpose-named public invalidation key, then update only the characterized mutations.
- **Tests that protect current behavior:** `useAuditionQueries.test.tsx`, Breakdowns query tests, `invalidationContracts.test.ts`, `frontend/e2e/cross-feature.spec.ts`, and request-graph tests.
- **Risk of changing it:** high relative to code size because a missed invalidation creates stale cross-route UI.
- **Impact:** runtime behavior and maintainability.

### F-09 — Query ownership is consistent, but hook naming and responsibility are not

- **Severity:** medium
- **Confidence:** confirmed
- **Paths and symbols:**
  - `frontend/src/features/journal/hooks/useJournalEntries.ts:42-132` (`useJournalEntries`) owns the query plus form-open state, edit state, drafts, success messages, grouping, and submit handlers;
  - `frontend/src/features/settings/hooks/useDiscoveryProviders.ts` owns query/mutations plus grouping and user messages;
  - `frontend/src/features/settings/hooks/useSystemCapabilities.ts:6-18` defines a feature hook with the same name as `frontend/src/services/system/useSystemCapabilities.ts:8-15`, but augments the shared query with travel-recalculation mutation and UI message;
  - `frontend/src/features/script-finder/hooks/useScriptFinder.ts` stores API-returned scene candidates and plan results in local state while also owning a TanStack query.
- **Why it matters:** These hooks are workflow controllers, not simple data hooks. Their names make it easy for consumers to misunderstand whether they receive a query object or a full view model. The duplicate `useSystemCapabilities` name is especially ambiguous in imports and reviews.
- **Smallest safe improvement:** Rename only when touching a feature: use names such as `useJournalWorkspace`, `useDiscoveryProviderSettings`, or `useCapabilitySettingsWorkflow`, while retaining narrow query hooks separately. Do not move transient form state into TanStack Query.
- **Tests that protect current behavior:** Journal, Settings, and Script Finder component/hook tests where present; `services/system/useSystemCapabilities.test.tsx`.
- **Risk of changing it:** medium because many component props and tests use the composite return shape.
- **Impact:** maintainability; potential runtime risk during refactor, but current behavior is valid.

### F-10 — Career Intelligence is an oversized workflow and dependency hub

- **Severity:** medium
- **Confidence:** confirmed
- **Paths and symbols:**
  - `frontend/src/features/career-intelligence/components/CareerIntelligencePanel.tsx` (748 lines);
  - `CareerIntelligencePanel`, `WatchListDashboard`, `QuarterlyReviewsSection`, `CareerPathSimulatorSection`, `CastingGoalsPanel`, `CareerSwotSection`, `IndustryTrendsSection`, `RelationshipInsightsSection`;
  - imports public hooks/panels from six other features.
- **Why it matters:** One module owns route fetching, loading/error aggregation, scrolling behavior, data derivation, multiple independent forms/mutations, and many rendered sections. A change in any career sub-workflow has a large review/test blast radius.
- **Smallest safe improvement:** First add focused tests for one independently stateful section. Then extract one route-private section with a narrow data/command contract, starting with Career Path Simulator only after F-01 adds a mutation hook. Preserve the parent as the route/workflow composition owner.
- **Tests that protect current behavior:** `useCareerQueries.test.tsx`, request-graph browser coverage, and backend contract tests indirectly. No focused `CareerIntelligencePanel` component test was found.
- **Risk of changing it:** high because current direct API calls and cross-feature query ownership are not comprehensively characterized.
- **Impact:** maintainability, runtime behavior, portfolio readiness.

### F-11 — Dashboard is large, but much of its cross-feature breadth is intentional

- **Severity:** medium
- **Confidence:** confirmed
- **Paths and symbols:**
  - `frontend/src/features/dashboard/components/DashboardPanel.tsx` (694 lines);
  - `widgetDefinitions`;
  - `DashboardPanel`;
  - `DashboardQuickActions`;
  - `recommendationsByType`, `recommendationLabel`, and `findOpportunityLabel`.
- **Why it matters:** The module fetches many public feature queries, defines the widget registry, transforms domain data, owns drag/drop customization, persists preferences/focus mode, and renders the dashboard. That density makes failures and changes harder to isolate.
- **Smallest safe improvement:** Keep Dashboard as the read-composition owner. Extract the pure widget registry/derived selectors into tested feature-local modules, or extract customization UI after characterization. Do not push all Dashboard data fetching back into the page or global app shell.
- **Tests that protect current behavior:** `frontend/src/features/dashboard/DashboardPanel.test.tsx`, `dashboardArchitecture.test.ts`, `frontend/e2e/dashboard.spec.ts`, `request-graphs.spec.ts`, and `app-shell.spec.ts`.
- **Risk of changing it:** high because request count, cache reuse, drag/drop state, focus mode, and quick actions are all user-visible.
- **Impact:** maintainability and runtime behavior.

### F-12 — Source Library combines fetching, transformation, orchestration, forms, external navigation, and rendering

- **Severity:** medium
- **Confidence:** confirmed
- **Paths and symbols:**
  - `frontend/src/features/source-library/components/SourceLibraryPanel.tsx` (639 lines);
  - `SourceLibraryPanel`;
  - `SourceSection`;
  - `SourceEditForm`;
  - `SourceRow`.
- **Why it matters:** `SourceLibraryPanel` owns multiple queries/mutations, two forms, hidden/edit selection, grouping/filtering, approval/rejection/disable semantics, message state, focus/scroll effects, Google search navigation, and rendering. The architecture test proves it is behind hooks, but not that responsibilities are small.
- **Smallest safe improvement:** Extract a feature-local controller hook for form/command orchestration or one route-private form section, keeping query hooks and all mutation semantics unchanged.
- **Tests that protect current behavior:** `frontend/src/features/source-library/SourceLibraryPanel.test.tsx`, `useSourceLibrary.test.tsx`, `sourceLibraryArchitecture.test.ts`, Breakdowns discovery tests, and request-graph tests.
- **Risk of changing it:** medium-high because status terms (“Active,” “Paused,” “Rejected,” approval) drive backend behavior and cross-feature discovery.
- **Impact:** maintainability and runtime behavior.

### F-13 — `BreakdownDetails.tsx` is a feature-local grab bag despite successful private extractions

- **Severity:** medium
- **Confidence:** confirmed
- **Paths and symbols:**
  - `frontend/src/features/breakdowns/components/BreakdownDetails.tsx` (870 lines);
  - exports presentation components, form-state types, initializers, parsing/formatting helpers, recommendation selectors, and `RecommendationFeedbackControls`;
  - `RecommendationPanel` owns feedback mutations and multiple per-record state maps.
- **Why it matters:** The file has high internal cohesion around “breakdown details” only at a broad product level. It is a frequent dependency for `BreakdownManager`, the form model, and other Breakdowns UI, so unrelated helper/presentation/feedback changes collide.
- **Smallest safe improvement:** Do not perform a broad split. Use the existing Breakdowns preflight pattern: characterize one coherent candidate (for example recommendation feedback or pure formatting/view-model helpers), keep it route-private, and preserve exact query ownership.
- **Tests that protect current behavior:** `breakdownViewerArchitecture.test.ts`, `breakdownRoleDetailsArchitecture.test.ts`, `query-boundary.test.ts`, recommendation feedback characterization/browser tests, and component tests.
- **Risk of changing it:** high. Earlier architecture notes explicitly require fresh evidence before further extraction.
- **Impact:** maintainability and runtime behavior.

### F-14 — Profile has two large workflow components with overlapping resource concerns

- **Severity:** medium
- **Confidence:** strong inference
- **Paths and symbols:**
  - `frontend/src/features/profile/components/ActorProfilePanel.tsx` (536 lines);
  - `frontend/src/features/profile/components/PlatformProfileImportAssistant.tsx` (428 lines);
  - `frontend/src/features/profile/api/index.ts` spans actor, equipment, travel, representation, credits, imports, mappings, and subscriptions.
- **Why it matters:** The Profile feature is a broad user-workspace domain. Actor profile editing, representation editing, resume credits, equipment, travel, subscriptions, and import staging have different lifecycles but share one public API module and two large interactive components. This is manageable now but makes changes collide.
- **Smallest safe improvement:** Keep the Profile route boundary. When a workflow changes, extract its form model/controller within Profile and expose only the minimal hook/type needed by outside consumers.
- **Tests that protect current behavior:** `ProfilePanel.test.tsx`, `profileArchitecture.test.ts`, `useProfileQueries.test.tsx`, and `frontend/e2e/cross-feature.spec.ts`.
- **Risk of changing it:** medium-high because Profile data feeds Breakdowns, Materials, Calendar, and Relationships.
- **Impact:** maintainability and runtime behavior.

### F-15 — Architecture tests mix durable constraints with brittle source-shape assertions

- **Severity:** medium
- **Confidence:** confirmed
- **Paths and symbols:**
  - durable examples:
    - `globalServerStateRetirement.test.ts`;
    - `queryPolicyInventory.test.ts`;
    - `invalidationContracts.test.ts`;
    - `calendarInteractionArchitecture.test.ts`;
    - ESLint `architecture/imports`.
  - brittle examples:
    - `breakdownRoleDetailsArchitecture.test.ts` asserts an exact function signature string;
    - `breakdownViewerArchitecture.test.ts` asserts exact callback/source strings;
    - `presentation-boundary.test.ts` and `query-boundary.test.ts` rely heavily on regex/source inclusion;
    - several tests infer architecture from spelling of symbols rather than behavior or an AST.
- **Why it matters:** Source-text tests are useful guardrails during incremental cleanup, but exact strings can block harmless refactors, reward formatting-compatible violations, or preserve transitional structure after its original risk disappears.
- **Smallest safe improvement:** Keep tests that encode user-visible behavior, cache contracts, absence of broad invalidation, and public/private boundaries. When changing a protected module, replace only brittle exact-string assertions with ESLint rules, import-graph checks, or behavior tests where practical.
- **Tests that protect current behavior:** The tests listed above are themselves the subject. Their corresponding component and Playwright tests provide behavioral coverage.
- **Risk of changing it:** medium. Removing them wholesale would reopen regressions they were created to prevent.
- **Impact:** maintainability and style; indirect portfolio-readiness impact.

### F-16 — Several compatibility/scaffolding surfaces are unused or nearly empty

- **Severity:** low
- **Confidence:** confirmed
- **Paths and symbols:**
  - `frontend/src/components/layouts/index.ts` re-exports `TopNavigation` from `frontend/src/layout/TopNavigation.tsx`;
  - `frontend/src/components/layouts/workflowLayouts.tsx` defines three very small wrappers with no confirmed production consumer;
  - `frontend/src/utilities/index.ts` only re-exports `utils/tags`;
  - Vite aliases include `@/hooks`, but no `frontend/src/hooks` directory exists;
  - most feature `constants/index.ts` and `utils/index.ts` files are tiny re-export/adaptor files;
  - design-system `colors`, `spacing`, `typography`, and `variants` are exported, while production imports currently consume the design system through shared UI status helpers only.
- **Why it matters:** These paths imply architecture that the application does not actually use and create naming choices (`layout` versus `components/layouts`, `utils` versus `utilities`) without functional distinction.
- **Smallest safe improvement:** After deployment, remove proven-unreferenced compatibility paths and unused aliases one at a time with `rg`, TypeScript, lint, and build verification. Do not create placeholder files merely to satisfy the directory template.
- **Tests that protect current behavior:** TypeScript, lint, build, and any import-boundary tests. No runtime test should depend on unused exports.
- **Risk of changing it:** low if references are rechecked, but deployment timing makes the benefit too small for immediate work.
- **Impact:** style and maintainability only.

### F-17 — Naming exposes historical transitions

- **Severity:** low
- **Confidence:** confirmed
- **Paths and symbols:**
  - frontend route `/breakdowns` is implemented by `OpportunitiesPage`;
  - `SourceLibraryPanel` is aliased as `BreakdownSources` in `source-library/index.ts`;
  - Breakdowns also exports `BreakdownSources` from `BreakdownDiscovery`;
  - `CareerLegacyPanels.tsx` contains active exported panels;
  - two different `useSystemCapabilities` hooks exist;
  - both `utils` and `utilities` exist.
- **Why it matters:** Names make ownership and current-versus-legacy status harder to interpret, and duplicate exported names increase import ambiguity.
- **Smallest safe improvement:** Establish naming decisions in documentation first. Rename only alongside a bounded change with compatibility exports if needed.
- **Tests that protect current behavior:** App route tests, feature architecture tests, TypeScript, and build.
- **Risk of changing it:** low-to-medium due to broad import churn and lazy route names.
- **Impact:** maintainability and style only.

### F-18 — Accessibility is behaviorally considered but not systematically audited

- **Severity:** low
- **Confidence:** confirmed
- **Paths and symbols:**
  - semantic patterns across `frontend/src/components/ui.tsx`, feature panels, and `TopNavigation`;
  - role/focus assertions across component and Playwright tests;
  - FullCalendar DOM adaptation in `ActorCalendar`.
- **Why it matters:** Large dynamic forms, disclosure trees, drag/drop Dashboard customization, and FullCalendar integration can have issues that role-based happy-path tests do not detect. No axe-style automated scan or documented keyboard audit was found.
- **Smallest safe improvement:** After functional architecture stabilization, add a small route-level accessibility smoke suite for shell, Dashboard customization, a representative form, and Calendar. Keep existing semantic/focus tests.
- **Tests that protect current behavior:** existing role/focus component tests and Playwright workflows.
- **Risk of changing it:** low for adding tests; remediation risk varies by finding.
- **Impact:** portfolio readiness and runtime usability.

## 5. Public API assessment by feature

| Feature | Current public API | Assessment | Smallest future adjustment |
|---|---|---|---|
| Analytics | panels, selected types/hooks, all API functions | Mostly coherent; raw API wildcard is broader than needed | Keep panels/hooks/types; privatize raw transport after consumer inventory |
| Auditions | four panels, all query hooks, all APIs, all types | Broad; useful cross-feature read hooks but too many raw commands | Explicitly export read hooks/selectors/types and workflow entry panels |
| Breakdowns | main panel, several subpanels/helpers, all APIs/hooks/types | Strong route-private tests, but public surface is still large | Preserve private components; replace wildcard exports incrementally |
| Calendar | panel, view-model hook, query/mutation hooks, types, APIs | Clear ownership; `calendarEventListKey` leaks cache implementation | Prefer purpose-named invalidation contract over concrete key sharing |
| Career Intelligence | main and legacy panels, all APIs/hooks | Weakest public surface; presentation bypasses hooks | Add missing command hooks, then expose explicit workflow API |
| Chief of Staff | multiple panels/widgets, all APIs/hooks/types/utils | Broad but used as Dashboard/Calendar read provider | Separate public read widgets/hooks from raw commands |
| Dashboard | main panel, types, all APIs/hooks | Mostly route-private; outside consumers appear limited | Keep main panel public; privatize raw transport if unused externally |
| Journal | panel, four hooks, all types/APIs | Composite `useJournalEntries` name hides UI controller behavior | Separate/rename workspace controller; keep narrow options public |
| Materials | panels, selected material hooks, all APIs/types | Useful public material options; duplicated import/mapping transport | Keep `MaterialOption`/read hooks public; consolidate duplicated APIs |
| Profile | eight panels, all APIs/hooks, one explicit type | Very broad; workflow hub used by several routes | Explicitly export actor/representation/material-option-facing contracts |
| Relationships | panel, CRUD hooks, log panel, all APIs/types | Reasonably coherent, though raw APIs are unnecessary publicly | Prefer hooks/types/panel only |
| Script Finder | three components, controller hook, all types/APIs | Coherent feature, but material-plan API overlaps Career | Make plan lifecycle ownership explicit |
| Settings | panels, selected types, all APIs | Hook implementations are not exported, reducing bypass risk | Rename composite capabilities hook; explicitly export intended hooks if needed |
| Source Library | panel/form alias, all types/APIs/hooks | Necessary Breakdowns integration, but exposes concrete cache keys and broad commands | Define a smaller discovery-source public contract |

## 6. State ownership assessment

### Confirmed good ownership

- Remote list/detail/configuration state uses TanStack Query.
- Query selection is used instead of copying server records where practical:
  - `useOpportunityOptions`;
  - `useMaterialOptions`;
  - `useSubmissionOptions`;
  - `useCareerTaskOptions`.
- `HiddenOpportunityReview` stores `selectedId`, not a copied `Opportunity`.
- `OpportunityFormWorkspace` copies an authoritative record only into an intentionally bounded editable draft and protects dirty state.
- UI-only state such as open panels, draft text, filters, focus targets, and Dashboard customization remains local.

### State requiring clearer labeling, not a new state library

- `useJournalEntries`, `useDiscoveryProviders`, `useScriptFinder`, and Settings' `useSystemCapabilities` are view-model/controller hooks that combine remote state with UI state.
- `sceneCandidates`, `simulation`, `prep`, and `materialPlan` are API-returned values held outside the Query cache. Some are legitimate ephemeral command results; their lifecycle should be explicit.
- Per-record pending/error maps in `BreakdownManager` and `RecommendationPanel` are local concurrency controls. They are complex, but moving them into global state would be a regression.

## 7. Architecture-test assessment

### Tests that intentionally protect valuable boundaries

- `globalServerStateRetirement.test.ts`: prevents restoration of a global workflow snapshot/loader and multiple QueryClients.
- `queryKeys.test.ts`: enforces feature-key factories.
- `queryPolicyInventory.test.ts`: makes freshness policy reviewable.
- `invalidationContracts.test.ts`: protects cross-feature side-effect exactness and forbidden invalidation.
- `analyticsArchitecture.test.ts`, `commandCenterArchitecture.test.ts`, `dashboardArchitecture.test.ts`, `profileArchitecture.test.ts`, `sourceLibraryArchitecture.test.ts`: keep consumers on public boundaries and presentation off base APIs.
- Breakdowns architecture tests: preserve proven route-private ownership created by earlier cleanup.
- `reusableSelfTapeArchitecture.test.ts`: intentionally keeps reusable Materials tapes separate from Auditions workflow tapes.
- `calendarInteractionArchitecture.test.ts`: preserves the explicitly form-only Calendar contract.

### Tests likely to preserve accidental source shape

- Assertions for exact function signature strings.
- Assertions that a specific identifier spelling appears a precise number of times.
- Regex bans that approximate imports or ownership already enforced by ESLint.
- Source tests tied to transitional names such as legacy loader identifiers indefinitely.

These tests should not be deleted as a batch. Their original regression value is clear. Convert them only when a scoped change provides an equivalent behavioral, import-graph, or lint guarantee.

## 8. Recommended frontend cleanup order

1. **Characterize and wrap Career direct commands.**  
   Add focused tests and canonical mutation hooks for simulation, preparation, and material-plan creation. This is the only high-severity finding.

2. **Resolve duplicated endpoint ownership.**  
   First characterize platform import/mapping invalidation across Profile and Materials; then choose one owner. Separately choose an owner for material-plan lifecycle.

3. **Normalize cross-feature invalidation edges.**  
   Move Auditions→Calendar and Breakdowns→Source Library cache coupling behind the existing shared invalidation-contract mechanism, with exact hook and Playwright coverage.

4. **Tighten public barrels based on real consumers.**  
   Replace wildcard exports feature by feature, starting with Career Intelligence and Profile. Do not change internal file layout in the same step.

5. **Split one Career Intelligence workflow boundary.**  
   After command hooks exist, extract one route-private stateful section with a narrow contract and focused tests.

6. **Extract pure Dashboard definitions/selectors.**  
   Keep Dashboard fetching/composition intact while moving the pure widget registry and derived calculations into tested feature-local modules.

7. **Reduce Source Library and Profile component density opportunistically.**  
   Extract only a form/controller that is already behaviorally characterized.

8. **Migrate global types incrementally.**  
   Move one stable resource family at a time and preserve compatibility exports during migration.

9. **Rename ambiguous controller hooks and historical names.**  
   Do this only with an adjacent functional cleanup to avoid import-only churn.

10. **Retire unused scaffolding and strengthen accessibility checks.**  
    Remove proven-dead aliases/wrappers and add a small automated accessibility smoke suite after deployment stability.

## 9. Items to defer until after deployment

The following should explicitly not be part of pre-deployment cleanup unless they become blockers:

- broad splitting of `frontend/src/types/domain.ts`;
- a full rewrite of Career Intelligence, Dashboard, Breakdowns, Profile, or Source Library;
- replacing TanStack Query, React Router, Vite, Tailwind, or the current feature-folder pattern;
- moving page composition into a new global state/container layer;
- redesigning all feature barrels at once;
- renaming Opportunities/Breakdowns routes and symbols across the application;
- replacing source-text architecture tests wholesale;
- consolidating `layout`, `components/layouts`, `utils`, and `utilities` through a large path migration;
- design-system token adoption across every existing class string;
- introducing a new form library solely to reduce local form code;
- introducing Redux/Zustand for current local UI state;
- changing Calendar from its tested form-only interaction model;
- enabling real browser submission automation;
- major UI redesign or drag/drop behavior changes;
- broad accessibility remediation without first running a focused audit;
- bundle optimization beyond any measured deployment budget failure.

## 10. Portfolio-readiness conclusion

The frontend is architecturally credible for a portfolio deployment. Its strongest story is not perfect isolation; it is the deliberate retirement of global server snapshots, explicit TanStack Query ownership, typed invalidation contracts, route-level failure isolation, public feature boundaries, human-readable architecture tests, and browser-level request-graph verification.

Before calling the frontend fully portfolio-ready, the highest-value bounded work is:

1. remove direct Career API execution from presentation components;
2. establish single owners for duplicated platform-import/mapping and material-plan endpoints;
3. make the remaining cross-feature cache-key edges explicit contracts;
4. document or narrow the broadest public feature APIs;
5. record the known Calendar immediate-return Playwright failure as either a policy defect or obsolete assertion.

Everything else can be sequenced after deployment without undermining the current architecture narrative.
