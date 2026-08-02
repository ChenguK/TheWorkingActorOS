# Phase 2 Architecture Inventory

**Branch audited:** `release/portfolio-readiness`  
**Audit date:** 2026-07-26  
**Scope:** Evidence-based inventory of the current repository. This document describes what the code does today; it does not treat directory names as proof of enforced boundaries.

## Evidence conventions

- **Confirmed** means the conclusion follows from an inspected symbol, import, route registration, configuration, or test.
- **Hypothesis** means the code suggests an intent, but runtime ownership, organizational intent, or production behavior cannot be established from this repository alone.
- File citations name an exact path and, where useful, the relevant symbol. Line numbers are included for stable entry points and compact configuration files; symbols are preferred for larger files that are likely to move during later work.

## 1. Executive summary

The repository is a two-process application:

1. a React/Vite single-page frontend whose application entry is `frontend/src/main.tsx:8` and whose route entry is `frontend/src/App.tsx:54` (`App`); and
2. a FastAPI backend whose ASGI entry is `backend/app/main.py:9` (`app`) and whose versioned API is assembled by `backend/app/api/v1/router.py:23` (`api_router`).

The frontend has a substantially implemented feature-oriented architecture. Pages import feature public barrels, compose data from multiple features, and pass it into feature panels. Remote state is owned by TanStack Query through the single `QueryClient` created by `frontend/src/app/queryClient.ts:15` (`createQueryClient`) and installed by `frontend/src/app/providers/AppProviders.tsx:5` (`AppProviders`). Feature API modules call a shared fetch adapter, while feature hooks declare query keys, freshness policy, mutations, and invalidation. This direction is reinforced by the custom `architecture/imports` ESLint rule in `frontend/eslint.config.js` (`architecturePlugin`), not merely by folder naming.

The backend is layered, but not uniformly. FastAPI routes commonly delegate to services, Pydantic schemas validate transport data, SQLAlchemy models and Alembic migrations define persistence, and repositories encapsulate CRUD for five core aggregates. However, repository use is selective: many services, agents, automation services, and some routes query ORM models directly. The actual backend dependency graph is therefore a pragmatic service-centered graph rather than a strict controller → service → repository architecture.

Business behavior is concentrated in backend services and deterministic agent classes. Opportunity ingestion is a particularly dense orchestration path: `OpportunityService.create` coordinates parsing, deadlines, role synchronization, intelligence, trust verification, self-tape creation, journal events, and one final commit. Discovery automation is a second application-service center in `DiscoveryAutomationService`. Agent classes are deterministic decision engines that also persist results; they are not currently an LLM runtime. This matches the explicit README statement that agents and automation are deterministic/mock-safe (`README.md:26`).

The architecture has good explicit boundaries around frontend server state, human approval before submission automation, guarded real-database contract tests, and mock-isolated browser tests. The highest-value next pass should examine transactional ownership, read-side mutation, backend dependency direction, API/schema/domain validation gaps, and production deployment/security boundaries.

## 2. Current frontend architecture

### 2.1 Application entry points and shell

**Confirmed**

- `frontend/src/main.tsx:8-15` mounts React into `#root`, enables `React.StrictMode`, installs `AppProviders`, and then installs `BrowserRouter`.
- `frontend/src/app/providers/AppProviders.tsx:5-6` currently provides only TanStack Query through a module-level `queryClient`.
- `frontend/src/App.tsx:6-17` lazy-loads every route page.
- `frontend/src/App.tsx:31-52` supplies a route-level error boundary, and `frontend/src/App.tsx:61-81` wraps all routes in that boundary and `Suspense`.
- `frontend/src/App.tsx:64-78` is the authoritative browser route table. `/discovery` and `/opportunities` redirect to `/breakdowns`; unknown paths redirect to `/`.
- `frontend/src/App.tsx:55-59` loads system capabilities at shell level and passes them to `TopNavigation`.
- `frontend/src/layout/TopNavigation.tsx:6-18` defines primary navigation, while `TopNavigation` owns only local mobile-menu state (`useState` at line 21).

**Intended responsibility inferred from implementation**

- `main.tsx`: process/bootstrap composition.
- `AppProviders`: global infrastructure providers.
- `App`: application shell, route selection, route loading/error isolation.
- `layout`: persistent shell presentation and ephemeral UI state.
- `pages`: route-level feature composition.

### 2.2 Route pages and feature composition

**Confirmed**

Pages are thin composition roots in the inspected set:

- `frontend/src/pages/DashboardPage.tsx` renders only `DashboardPanel`.
- `frontend/src/pages/OpportunitiesPage.tsx` renders only `BreakdownsPanel`.
- `frontend/src/pages/AuditionsPage.tsx` composes actor, breakdown, and material queries and passes data to `AuditionsPanel`.
- `frontend/src/pages/CalendarPage.tsx` composes Calendar with Profile, Breakdowns, Auditions, and Chief of Staff public hooks.
- `frontend/src/pages/JournalPage.tsx` composes Journal with Career, Materials, Breakdowns, and Auditions public hooks.
- `frontend/src/pages/MaterialsPage.tsx` composes Materials with Profile, Breakdowns, Auditions, and System data.
- `frontend/src/pages/RelationshipsPage.tsx` composes Relationships with Profile, Breakdowns, and Auditions data.
- `frontend/src/pages/AnalyticsPage.tsx` and `frontend/src/pages/CareerPage.tsx` compose domain panels with submissions and system capabilities.

These imports go through feature barrels such as `frontend/src/features/auditions/index.ts` and `frontend/src/features/profile/index.ts`; the inspected pages do not import feature internals.

The custom ESLint rule `architecture/imports` in `frontend/eslint.config.js` confirms that these are intended, enforced directions:

- pages may import feature public APIs and approved shared roots;
- cross-feature imports must use the target feature's root barrel;
- shared components must not import features/pages;
- the design system must not import features/pages/services/components;
- direct shared API-client access is restricted to approved API/infrastructure modules;
- feature barrels must not export pages or another feature's implementation.

This is stronger evidence than the folder structure alone. The Phase 1 baseline also confirmed `npm run lint` passes, so the checked source currently satisfies these static rules.

### 2.3 Feature-internal layers

The representative features show a recurring four-part pattern:

1. `api/index.ts`: endpoint-specific transport functions;
2. `hooks/*.ts`: query/mutation ownership and cache coordination;
3. `components/*.tsx`: workflow UI and local form/presentation state;
4. `types`, `constants`, and `utils`: feature-specific supporting contracts.

**Breakdowns**

- `frontend/src/features/breakdowns/api/index.ts` defines typed endpoint calls such as `listBreakdowns`, `createBreakdown`, `deepParseBreakdown`, `runBreakdownDiscovery`, and submission-queue commands.
- `frontend/src/features/breakdowns/hooks/useBreakdownQueries.ts` owns `breakdownKeys`, queries, mutations, selectors, and invalidation.
- Cross-feature invalidation is explicit: for example, `useCreateBreakdown`, `useDeleteBreakdown`, and `useGenerateBreakdownStrategy` resolve named contracts from `frontend/src/services/api/invalidationContracts.ts`.
- `frontend/src/features/breakdowns/components/opportunityFormModel.ts` converts API models to editable drafts and drafts back to request payloads through `opportunityToFormDraft` and `formDraftToOpportunityRequest`.
- `frontend/src/features/breakdowns/components/BreakdownsPanel.tsx` is the feature workflow composition component.

**Auditions**

- `frontend/src/features/auditions/api/index.ts` spans submission, self-tape workflow, callback, Calendar-event, and audition-journal endpoints.
- `frontend/src/features/auditions/hooks/useAuditionQueries.ts` owns the `auditionKeys` query families and uses shared invalidation contracts for submission, callback, and workflow mutations.
- `frontend/src/features/auditions/components/AuditionsPanel.tsx` composes the visible Auditions workflow.

**Calendar**

- `frontend/src/features/calendar/api/index.ts` owns persisted Calendar-event and availability transport.
- `frontend/src/features/calendar/hooks/useCalendarQueries.ts` owns their server-state queries and mutations.
- `frontend/src/features/calendar/hooks/useActorCalendar.ts` adapts persisted Calendar data plus read-only projections from submissions, callbacks, self-tapes, breakdown deadlines, and command-center reminders into display events.
- `frontend/src/pages/CalendarPage.tsx:7-27` proves that those cross-domain records remain owned by their source features and are supplied to Calendar as inputs.

**Materials**

- `frontend/src/features/materials/api/index.ts` owns asset and reusable self-tape endpoints.
- `frontend/src/features/materials/hooks/useMaterials.ts` owns material queries, selectors, uploads, analysis, updates, and deletions.
- `frontend/src/features/materials/components/MaterialsPanel.tsx`, `AssetLibrary.tsx`, and `SelfTapeLibraryPanel.tsx` separate the page-level materials workflow, asset management, and reusable self-tape presentation.

**Profile**

- `frontend/src/features/profile/api/index.ts` aggregates actor profile, travel, representation, credits, equipment, platform import, mapping, and subscription endpoints.
- `frontend/src/features/profile/hooks/useProfileQueries.ts` owns query families and import/profile mutations.
- `frontend/src/features/profile/components/ProfilePanel.tsx` and `ProfileSetupPanel.tsx` are separate workflow presentations over the same feature API.

**Dashboard**

- `frontend/src/features/dashboard/components/DashboardPanel.tsx` is a cross-domain dashboard composition point.
- `frontend/src/features/dashboard/hooks/useDashboardQueries.ts` owns dashboard-specific server state.
- `frontend/src/features/dashboard/api/index.ts` owns dashboard endpoint calls.

### 2.4 Frontend dependency direction

**Confirmed dominant direction**

```text
main
  → app providers / router
  → route pages
  → feature public barrels
  → feature components and hooks
  → feature API modules
  → shared API request infrastructure
  → FastAPI /api/v1
```

Supporting imports point from feature code toward shared `components`, `constants`, `design-system`, `services`, `types`, and utilities. The ESLint rule described above rejects several reverse or internal cross-feature imports.

**Confirmed qualification**

Features are not isolated domains in the strict sense. Some public hooks are intentionally consumed across features/pages, and some feature API modules call endpoints nominally owned by another backend route group. For example, Auditions calls `/operations/calendar/events` in `frontend/src/features/auditions/api/index.ts` (`createCalendarEvent`), and Profile owns UI access to `/operations/*` and `/platform-imports/*`. The frontend boundary is organized around user workflow ownership, not one-to-one backend URL namespaces.

### 2.5 Server-state ownership

**Confirmed**

- The only production `QueryClient` is created by `frontend/src/app/queryClient.ts:15-29` and exported at line 31.
- Default query behavior is centralized: ten-minute garbage collection, reconnect refetch, no focus refetch, and at most one retry depending on `ApiError` semantics (`shouldRetryQuery`, lines 5-13).
- Mutation retries are disabled (`frontend/src/app/queryClient.ts:24-25`).
- Query keys are centralized into feature families by `frontend/src/services/api/queryKeys.ts:3-31`.
- Freshness classes are centralized by `frontend/src/services/api/queryPolicy.ts:1-6`.
- `frontend/src/services/api/queryPolicyInventory.ts` documents owner, endpoint, consumers, volatility, stale behavior, and invalidation for query families.
- `frontend/src/services/api/invalidationContracts.ts` maps mutation owners to direct, derived, and forbidden invalidation families and provides `keysForContract` and `invalidateInBackground`.
- Feature hooks, not components, construct `useQuery`/`useMutation` calls in the representative features inspected.
- Local component state remains appropriate for transient UI/form state, as demonstrated by `TopNavigation` and feature form components.

**Important finding**

The failed Phase 1 Playwright contract for `live route queries still refetch on immediate return` shows the documented/encoded Calendar freshness expectation and observed behavior currently diverge. The test expects a second `GET /operations/calendar/events`, but none occurs. This does not change the ownership map, but it makes freshness policy a high-value follow-up.

### 2.6 Frontend validation

**Confirmed**

- Browser-native form constraints and component submit guards provide first-pass UX validation in feature components.
- Form-to-request normalization occurs in feature model/helpers, e.g. `formDraftToOpportunityRequest` in `frontend/src/features/breakdowns/components/opportunityFormModel.ts`.
- Frontend API functions frequently accept `unknown` payloads (for example, `createBreakdown`, `updateBreakdown`, and `recordSubmission`), so the frontend does not provide a comprehensive runtime validation boundary.
- Backend FastAPI/Pydantic validation is therefore authoritative for request structure.
- `frontend/src/services/api/request.ts:59-95` converts FastAPI validation details and other error payloads into `ApiError` messages/field errors.

### 2.7 Shared frontend infrastructure

| Concern | Evidence | Responsibility |
|---|---|---|
| HTTP transport | `frontend/src/services/api/request.ts` (`request`) | Base URL, JSON encoding, timeout/abort, response/error parsing |
| API convenience | `frontend/src/services/api/client.ts` (`api`) | HTTP verbs, upload, asset/document URLs |
| Cache identity | `frontend/src/services/api/queryKeys.ts` (`queryKeys`) | Stable public query families |
| Cache policy | `frontend/src/services/api/queryPolicy.ts`; `queryPolicyInventory.ts` | Freshness classes and documented ownership |
| Mutation propagation | `frontend/src/services/api/invalidationContracts.ts` | Cross-feature synchronous side-effect map |
| App-wide capabilities | `frontend/src/services/system/api.ts`; `useSystemCapabilities.ts` | Configuration/capability state outside a user feature |
| Providers | `frontend/src/app/providers/AppProviders.tsx` | Installs the shared QueryClient |
| Domain transport types | `frontend/src/types/domain.ts` | Shared frontend representations of backend resources |
| Shared UI | `frontend/src/components/ui.tsx`; `frontend/src/components/ui/index.ts` | Reusable presentation primitives |
| Design tokens | `frontend/src/design-system/*` | Colors, spacing, typography, status, variants |
| Date/tag utilities | `frontend/src/utils/dateTime.ts`; `frontend/src/utils/tags.ts` | Cross-feature value adapters |

## 3. Current backend architecture

### 3.1 Application and HTTP entry

**Confirmed**

- `backend/app/main.py:7-17` loads settings, creates the FastAPI application, and installs CORS.
- `backend/app/main.py:20-22` exposes unversioned `/health`.
- `backend/app/main.py:25` mounts the versioned API at `/api/v1`.
- `backend/app/api/v1/router.py:23-48` registers 17 route modules: actor profile, agents, automation, career development, command center, dashboard, intelligence, journal, operations, travel, assets, opportunities, platform imports, representation, submissions, system, and supervised breakdown imports.
- `backend/app/core/database.py:14-23` creates one SQLAlchemy engine/session factory and supplies a per-request `get_db` dependency.

### 3.2 Actual backend layers

#### Transport/API layer

Files: `backend/app/api/v1/routes/*.py`

Typical responsibilities:

- route/path and status-code definitions;
- FastAPI dependency injection;
- Pydantic request/response selection;
- delegation to a service/agent/automation object.

Examples:

- `opportunities.list_opportunities` delegates to `OpportunityService.list`.
- `actor_profiles.upsert_actor_profile` delegates to `ActorProfileService`.
- submission routes delegate to `SubmissionService`.

Exceptions are material:

- `opportunities.material_matches` and `opportunities.recommend_opportunity` query `ActorProfile` directly with SQLAlchemy.
- `opportunities.refresh_demographic_check` commits and refreshes directly in the route.
- `backend/app/api/v1/routes/agents.py` imports many ORM models and directly coordinates agents and services.
- A repository-wide import scan confirms multiple route modules import SQLAlchemy and/or `app.db.models`.

Therefore “routes are thin controllers” is a **partial**, not universal, finding.

#### Schema/validation layer

Files: `backend/app/schemas/*.py`

Responsibilities:

- request parsing and serialization;
- field constraints;
- transport defaults;
- cross-field validation.

Examples:

- `OpportunityBase` in `backend/app/schemas/opportunity.py` requires non-empty bounded role/project/union/location and a non-empty description.
- `BreakdownTextParse.raw_text` requires at least ten characters.
- `ActorProfileCreate.validate_age_ranges` in `backend/app/schemas/actor_profile.py:33-47` enforces ordered primary and secondary playable-age ranges.
- FastAPI `response_model` declarations in route modules validate/serialize returned ORM objects.

Validation is not wholly centralized here. Business invariants also appear in services (`SubmissionAutomationService.execute` requires approval), models/database constraints, and domain value objects such as `SourceEvidence.__post_init__`.

#### Service/application layer

Files: `backend/app/services/*.py`

This is the main business and workflow layer.

Representative confirmed responsibilities:

- `OpportunityService`: opportunity lifecycle orchestration, parsing, enrichment, trust checks, workflow creation, journal side effects, transaction commits.
- `SubmissionService`: submission lifecycle, status history, asset association, workflow/journal/learning side effects.
- `ActorProfileService`: actor-profile lifecycle and profile-related business behavior.
- `IntelligenceService` and specialized engines: dashboards, readiness, parsing, scoring, character intelligence, material matching.
- `OperationsService`: operational dashboard, Calendar, availability, subscriptions, equipment, and related workflow state.
- `PlatformImportService`: import staging, approval/rejection, and mapping.
- `TravelService`: provider selection, external travel estimates, and caching.
- `SourceResearchService`, `SourceIdentityService`, `SourceExclusionService`, and `TrustVerificationService`: source governance and evidence.
- `FileStorageService`, `ResumePdfService`, and `SkillParserService`: file/document processing.

The service layer is not persistence-agnostic. Most services import SQLAlchemy and ORM models and own commits directly.

#### Repository layer

Files: `backend/app/repositories/*.py`

**Confirmed scope**

- `BaseRepository` provides common session-backed operations.
- Concrete repositories exist for actor profiles, assets, opportunities, submissions, and travel preferences.
- `OpportunityService`, `SubmissionService`, `ActorProfileService`, `AssetService`, and `TravelService` use repositories.

**Confirmed limitation**

Only a subset of domains has repositories. Even services with a repository also execute direct SQLAlchemy queries for related records and orchestration. Repositories are aggregate-specific CRUD/query helpers, not a universal persistence boundary.

#### ORM persistence layer

Files: `backend/app/db/models/*.py`; migrations: `backend/alembic/versions/*.py`

Responsibilities:

- SQLAlchemy table mappings, relationships, defaults, indexes, and constraints;
- PostgreSQL-specific types including `ARRAY`, `JSONB`, and UUID;
- schema evolution through Alembic.

Examples:

- `Opportunity` in `backend/app/db/models/opportunity.py` maps source, representation, casting, classification, visibility, deadlines, extracted facts, and relationships.
- `Submission` and `SubmissionStatusHistory` in `backend/app/db/models/submission.py` own submission persistence and history relationships.
- agent result tables are defined in `backend/app/db/models/agent.py`.
- automation queue/run/provider state is defined in `backend/app/db/models/automation.py`.

PostgreSQL is a real architectural boundary, not an interchangeable implementation detail, because models use PostgreSQL-specific column types and contract tests require real PostgreSQL.

#### Agent layer

Files: `backend/app/agents/*.py`

**Confirmed**

- `StrategyAgent.analyze` computes and persists recommendation scores, asset selections, notes, and explanations.
- `LearningAgent` derives learning signals from tracked outcomes.
- `CareerAgent.analyze` and `generate_swot` derive role lanes, material gaps, tasks, and SWOT records and persist them.
- `ExecutiveAgent` computes priorities/brief-oriented intelligence.
- `DiscoveryAgent` presents a higher-level discovery entry over discovery behavior.
- `AssetAnalysisAgent` analyzes and persists asset metadata.

These agents are deterministic Python policy/orchestration objects. The inspected agents do not invoke an OpenAI client. `backend/app/core/config.py:18` exposes `openai_api_key`, but current agent behavior uses local rules and stored data. The README explicitly labels current agents deterministic (`README.md:26`).

Agents are not pure domain functions: several query ORM state, add records, flush, and commit. They therefore combine decision behavior with application/persistence behavior.

#### Automation layer

Files: `backend/app/automation/*`

Two distinct automation domains exist:

1. **Discovery automation**
   - `DiscoveryProvider` and `NormalizedOpportunity` in `backend/app/automation/discovery/contracts.py` define provider contracts.
   - `DiscoveryPluginRegistry` builds/resolves providers.
   - `DiscoveryAutomationService` coordinates provider settings, runs, normalization, filtering, persistence, enrichment, coverage reporting, and source suggestions.
   - `PublicWebBreakdownSearch` integrates with the optional Parallel client and public HTTP pages.
   - `PublicPlaybillJobsSource` is a concrete public-source implementation.
   - `SourceExclusionGate` and `SourceEvidence` enforce source identity/evidence constraints.

2. **Submission automation**
   - `SubmissionAutomationService` manages prepared, approved, rejected, running, retry-ready, failed, and completed queue states.
   - `SubmissionAutomationService.execute` at `backend/app/automation/queue/service.py:54-72` enforces approval before adapter execution.
   - `SubmissionAdapterRegistry` selects mock platform-managed/direct-upload adapters.
   - `PlaywrightAutomationService` is explicitly a boundary stub; `execute_mock` returns a synthetic execution log and does not drive a real browser.

### 3.3 Backend dependency direction

**Confirmed dominant direction**

```text
FastAPI app
  → versioned router
  → route modules
  → schemas + services / agents / automation
  → repositories and/or SQLAlchemy ORM
  → PostgreSQL
```

Shared infrastructure (`core.config`, `core.database`, `core.errors`, `core.constants`) is imported from all upper layers.

**Confirmed exceptions and cycles of responsibility**

- Routes sometimes access ORM state directly.
- Services frequently bypass repositories.
- Services may call agents: `WorkflowConnectorService` imports `LearningAgent`; `ExecutiveIntelligenceService` imports `ExecutiveAgent`.
- Agents call services and persist ORM objects.
- Automation calls services and persists ORM objects.
- `DiscoveryAutomationService` imports several services and performs a local import of opportunity intelligence/trust services.

This is not necessarily a Python import cycle, but it is a bidirectional conceptual dependency between “services” and “agents.” The next pass should test whether transaction and ownership boundaries remain understandable under failure.

### 3.4 Where validation, logic, persistence, integrations, agents, and automation occur

| Concern | Primary location | Confirmed examples |
|---|---|---|
| Transport validation | Pydantic schemas | `OpportunityBase`, `BreakdownTextParse`, `ActorProfileCreate.validate_age_ranges` |
| Workflow/business invariants | Services and automation | protected opportunity deletion in `OpportunityService.delete`; approval gate in `SubmissionAutomationService.execute` |
| Deterministic scoring/parsing | Services/engines and agents | `BreakdownIntelligenceEngine`, `CompatibilityEngine`, `CharacterIntelligenceEngine`, `StrategyAgent` |
| Persistence queries | Repositories plus direct ORM access | `OpportunityRepository.search`; direct `select(...)` in `OpportunityService` and routes |
| Transaction commits | Services, agents, automation, and some routes | `OpportunityService.create`; `CareerAgent.analyze`; `DiscoveryAutomationService`; `refresh_demographic_check` route |
| External web search | Automation discovery | `PublicWebBreakdownSearch._client` and `.search` |
| External public-page retrieval | Automation discovery | `PublicWebBreakdownSearch._fetch_visible_text`; `PublicPlaybillJobsSource` |
| Travel providers | Services | `TravelService` using provider config/API keys |
| File/document I/O | Services | `FileStorageService`, `ResumePdfService`, `SkillParserService`, platform-import services |
| AI-agent behavior | Agent classes | Strategy, Learning, Career, Executive, Discovery, Asset Analysis |
| Browser/submission automation | Automation adapters | mock-only `PlaywrightAutomationService.execute_mock` behind `SubmissionAdapterRegistry` |

## 4. Request and data flow

### 4.1 Standard frontend read

**Confirmed flow**

```text
Route page or feature component
  → feature query hook
  → feature api/index.ts function
  → shared api.get/request
  → GET /api/v1/...
  → FastAPI route
  → service/repository or direct ORM query
  → SQLAlchemy/PostgreSQL
  → Pydantic response model
  → JSON
  → TanStack Query cache
  → component render
```

Evidence:

- `useBreakdowns` → `listBreakdowns` → `api.get("/opportunities")`.
- `opportunities.list_opportunities` → `OpportunityService.list` → `OpportunityRepository.search`.
- `request` in `frontend/src/services/api/request.ts` supplies the shared fetch/error boundary.

### 4.2 Standard mutation and cache propagation

```text
Feature form/component
  → feature mutation hook
  → feature API command
  → FastAPI/Pydantic request
  → service orchestration
  → one or more ORM writes/side effects
  → commit
  → response
  → mutation onSuccess
  → direct + proven-derived query invalidation
  → active consumers refetch
```

Evidence:

- `useCreateBreakdown` uses `invalidationContracts.opportunityCreate`.
- `OpportunityService.create` performs synchronous parse/enrichment/workflow/journal work and commits.
- `frontend/src/services/api/invalidationContracts.ts` records which caches are direct, derived, and explicitly forbidden for each mutation.

### 4.3 Opportunity creation as a representative cross-domain flow

**Confirmed**

`POST /api/v1/opportunities`:

1. FastAPI validates `OpportunityCreate` (`backend/app/api/v1/routes/opportunities.py:28-30`).
2. `OpportunityService.create` creates the ORM entity via `OpportunityRepository`.
3. The service parses the breakdown, applies manual defaults and deadline rules, synchronizes roles, enriches opportunity intelligence, verifies trust, potentially creates a self-tape workflow, and records an actor-work journal event.
4. The service commits once at the end (`backend/app/services/opportunity_service.py`, `OpportunityService.create`).
5. Contract test `test_opportunity_create_synchronous_contract` in `backend/tests/contract_smoke/test_contract_smoke.py` verifies persisted parse/role/journal/workflow side effects and read-model changes against PostgreSQL.
6. Frontend `useCreateBreakdown` invalidates the declared direct and derived owners.

### 4.4 Discovery flow

**Confirmed**

```text
Breakdowns UI
  → useRunBreakdownDiscovery
  → POST /automation/discovery/run
  → automation route
  → DiscoveryAutomationService
  → registry/provider or optional public web search
  → normalize/classify/deduplicate/exclusion gate
  → opportunity + source/run persistence
  → enrichment services
  → discovery report
  → frontend invalidates Breakdowns, analytics, report, and Source Library owners
```

`DiscoveryAutomationService` is both orchestrator and persistence owner for this flow. External provider behavior is disabled by default through `WEB_SEARCH_PROVIDER=none` in `backend/.env.example`.

### 4.5 Recommendation and submission-automation flow

**Confirmed**

1. `POST /opportunities/{id}/recommend` calls `StrategyAgent.analyze`.
2. The agent computes and persists an `AgentRecommendation`.
3. The frontend can call `/automation/submission-queue/from-recommendation/{id}`.
4. `SubmissionAutomationService.queue_from_recommendation` chooses an adapter and stores a prepared payload with `Pending Approval`.
5. Approval and rejection are explicit commands.
6. Execution is rejected unless status is `Approved`.
7. Current adapters use `PlaywrightAutomationService.execute_mock`, so “execution” remains local synthetic logging.

This confirms the human-in-the-loop boundary described in `README.md` and distinguishes it from a production submission integration.

## 5. Feature/domain map

### 5.1 Frontend feature map

| Frontend feature | Primary responsibility | Important public consumers / backend namespaces |
|---|---|---|
| `breakdowns` | Opportunity CRUD, discovery, parse/review, readiness, recommendations, queue | `/opportunities`, `/automation`, `/agents`, `/intelligence` |
| `auditions` | Submissions, workflow self-tapes, callbacks, performance journal | `/submissions`, `/command-center`, `/intelligence`, one `/operations` command |
| `calendar` | Persisted Calendar/availability plus projections of other owners | `/operations`; consumes Auditions, Breakdowns, Chief of Staff, Profile |
| `materials` | Asset library and reusable self-tapes | `/assets`, `/intelligence` |
| `profile` | Actor identity, representation, credits, travel, equipment, imports | `/actor-profile`, `/representation`, `/travel-preferences`, `/operations`, `/platform-imports` |
| `career-intelligence` | Career recommendations, tasks, goals, SWOT, related intelligence | `/career-development`, `/agents`, `/intelligence` |
| `analytics` | Operational, intelligence, pattern, material performance views | `/operations`, `/intelligence` |
| `relationships` | Casting relationships and communication history | `/intelligence` |
| `journal` | Actor journal CRUD and linked references | `/journal` |
| `dashboard` | User dashboard composition/preferences/focus | `/dashboard` plus cross-feature public hooks |
| `chief-of-staff` | Command-center and executive brief views | `/command-center`, `/agents` |
| `source-library` | Discovery-source research and lifecycle | `/automation/source-research` |
| `script-finder` | Script sources, scene candidates, material plans | `/intelligence/scripts`, `/intelligence/materials` |
| `settings` | Capabilities and discovery-provider configuration | `/system`, `/automation/discovery` |

**Confirmed boundary characteristic:** frontend feature ownership follows user workflows and cache ownership; it does not mirror backend route-module names one-to-one.

### 5.2 Backend domain map

| Backend domain | HTTP entry | Primary implementation |
|---|---|---|
| Actor profile | `routes/actor_profiles.py` | `ActorProfileService`, `ActorProfileRepository`, actor models/schemas |
| Opportunities/breakdowns | `routes/opportunities.py` | `OpportunityService`, `OpportunityRepository`, parsing/intelligence/trust services |
| Submissions/auditions | `routes/submissions.py`, parts of `command_center.py` and `intelligence.py` | `SubmissionService`, `SubmissionRepository`, workflow connector services |
| Assets/materials | `routes/assets.py`, parts of `intelligence.py` | `AssetService`, `AssetRepository`, `AssetAnalysisAgent`, material services |
| Career/agents | `routes/agents.py`, `career_development.py` | Career/Strategy/Learning/Executive agents and career services |
| Discovery/source governance | `routes/automation.py` | `DiscoveryAutomationService`, provider contracts, source services |
| Operations | `routes/operations.py`, `dashboard.py` | `OperationsService`, `DashboardService`, operational ORM models |
| Intelligence | `routes/intelligence.py` | `IntelligenceService` and specialized deterministic engines |
| Profile imports | `routes/platform_imports.py`, `supervised_breakdowns.py` | platform/supervised import services |
| Representation | `routes/representation.py` | `RepresentationService`, resume/document services |
| Journal | `routes/journal.py` | `JournalService`, `ActorWorkEventService` |
| System/capabilities | `routes/system.py` | `CapabilityService`, settings/provider state |
| Travel | `routes/travel_preferences.py`, automation recalculation route | `TravelService`, `TravelPreferenceRepository` |
| Submission automation | automation routes | queue service, adapter registry, mock Playwright boundary |

## 6. Shared infrastructure map

### 6.1 Frontend

- Runtime composition: `frontend/src/app/*`
- Routing/shell: `frontend/src/App.tsx`, `frontend/src/layout/TopNavigation.tsx`
- HTTP/errors: `frontend/src/services/api/request.ts`, `client.ts`, `errors.ts`
- Cache identity/policy: `queryKeys.ts`, `queryPolicy.ts`, `queryPolicyInventory.ts`
- Cross-feature consistency: `invalidationContracts.ts`
- Global configuration read: `frontend/src/services/system/*`
- Shared transport types: `frontend/src/types/domain.ts`
- Shared presentation/tokens: `frontend/src/components/*`, `frontend/src/design-system/*`

### 6.2 Backend

- Configuration: `backend/app/core/config.py` (`Settings`, `get_settings`)
- Database/session: `backend/app/core/database.py` (`engine`, `SessionLocal`, `get_db`)
- Shared HTTP-aware exceptions: `backend/app/core/errors.py`
- Cross-domain enumerations/policy constants: `backend/app/core/constants.py`
- ORM base/mixins/models: `backend/app/db/models/*`
- API serialization: `backend/app/schemas/*`
- Schema migrations: `backend/alembic/*`

**Area to inspect later:** `core.errors` subclasses FastAPI `HTTPException`, so services depend on an HTTP concern. This is a confirmed coupling, but whether it is harmful at the current scale remains an audit question rather than a rewrite recommendation.

## 7. Test architecture

### 7.1 Frontend unit/component/architecture tests

**Confirmed**

- Vitest runs in jsdom and excludes `e2e/**` (`frontend/vite.config.ts:23-29`).
- `frontend/src/test/setup.ts` installs jest-dom, cleans React and query clients after every test, restores mocks, stubs browser APIs, and rejects unexpected `fetch` calls. The error explicitly instructs tests to mock feature API modules.
- `frontend/src/test/testUtils.tsx` gives each test an isolated no-retry `QueryClient` and router helper.
- Tests are colocated with app, feature, hook, component, API, and utility code.
- Several tests are explicitly architectural/contractual, including:
  - `frontend/src/app/globalServerStateRetirement.test.ts`
  - feature `*Architecture.test.ts` files
  - `frontend/src/services/api/queryPolicyInventory.test.ts`
  - `frontend/src/services/api/invalidationContracts.test.ts`
  - Breakdowns presentation/query boundary tests.
- The Phase 1 baseline passed 309 frontend tests across 63 files.

### 7.2 Frontend browser tests

**Confirmed**

- Playwright runs Chromium against a locally started Vite server (`frontend/playwright.config.ts:17-22`).
- It fixes timezone to `America/New_York` and retains failure diagnostics (`frontend/playwright.config.ts:10-15`).
- Browser tests cover app shell, cross-feature flows, Calendar constraints, mutation failure/retry behavior, invalidation, deletion protection, and request graphs (`frontend/e2e/*.spec.ts`).
- The README states these tests intercept every `/api/v1` request and do not contact the developer database or external providers (`README.md:394-398`).
- The Phase 1 baseline found one stable request-graph failure in `e2e/request-graphs.spec.ts` concerning immediate-return Calendar refetch.

### 7.3 Backend fast tests

**Confirmed**

- Most `backend/tests/test_*.py` files exercise services/engines with in-memory objects, fakes, mocks, or lightweight session substitutes.
- Coverage is organized by capability/domain rather than mirroring every implementation file.
- Some tests verify frontend source text from the backend suite, e.g. `test_frontend_copy_distinguishes_parallel_run_state` in `backend/tests/test_public_web_search.py`. That is a cross-process source-level contract and should be treated as such.
- The Phase 1 baseline passed 183 tests; contract-marked tests skipped without their guarded environment.

### 7.4 Backend contract smoke tests

**Confirmed**

- `backend/tests/contract_smoke/conftest.py` refuses a database whose name lacks `test` or when `ALLOW_TEST_DATABASE_RESET` is not `true`.
- The suite blocks non-loopback network connections.
- It truncates all application tables for each test and uses FastAPI `TestClient` plus a real SQLAlchemy session.
- `backend/scripts/run_contract_smoke.py` creates a disposable PostgreSQL cluster, applies all Alembic migrations, disables external providers, runs the marker, and tears the cluster down.
- Contract tests validate synchronous persistence, API response shapes, transaction rollback, schema constraints, migration downgrade/re-upgrade, and source-exclusion behavior.
- The Phase 1 baseline passed all 47 contract tests.

### 7.5 Test boundary assessment

**Confirmed strength:** the suite distinguishes fast deterministic tests, browser workflow tests with intercepted APIs, and guarded real-FastAPI/real-PostgreSQL contract tests.

**Confirmed gap:** existing GitHub Actions run only frontend Playwright and backend contract smoke. Frontend unit/lint/build and backend fast tests/Ruff are not CI jobs.

## 8. Deployment architecture

### 8.1 Frontend

**Confirmed**

- Vite produces a static SPA through `npm run build` (`frontend/package.json:14`).
- Runtime API location is compiled from `VITE_API_URL`, defaulting to `http://localhost:8000/api/v1` (`frontend/src/services/api/request.ts:3`).
- `frontend/public/_redirects` contains the Netlify SPA fallback added by the current HEAD commit, so client-side routes resolve to `index.html`.
- No repository Netlify configuration declaring build command, publish directory, environment, or project linkage was found.

### 8.2 Backend

**Confirmed**

- The runnable ASGI target is `app.main:app`; local documentation uses `uvicorn app.main:app --reload` (`README.md:493`).
- Runtime configuration comes from process environment or `backend/.env` through Pydantic Settings (`backend/app/core/config.py:7-25`).
- PostgreSQL is required and migrations are applied with Alembic.
- Uploaded files default to local filesystem storage (`Settings.upload_dir`).
- No Dockerfile, Procfile, Render manifest, production process declaration, or backend deployment workflow was found.
- README “Production Roadmap” describes containerized backend, managed PostgreSQL, object storage, auth, secrets, observability, workers, rate limits, backups, and tenant authorization as planned rather than implemented (`README.md:587-601`).

### 8.3 CI/CD boundary

**Confirmed**

- `.github/workflows/frontend-e2e.yml` runs on pull requests, main pushes, and manual dispatch; it installs the pinned Node version, npm dependencies, and Chromium, then runs Playwright.
- `.github/workflows/backend-contract-smoke.yml` provisions PostgreSQL 17, installs Python 3.12 dependencies, migrates, and runs contract tests with external providers disabled.
- Neither workflow deploys.
- There is no confirmed backend production deployment boundary in this repository.

**Hypothesis:** Netlify is intended as the frontend host because of `_redirects` and the current commit message. The actual Netlify site, build settings, environment variables, and deployment status cannot be established from repository code alone.

## 9. Areas that appear intentionally well-structured

1. **Frontend server-state ownership is explicit and testable.**  
   Query keys, freshness classes, ownership inventory, and mutation invalidation are first-class code in `frontend/src/services/api/*`, and feature hooks consume them.

2. **Frontend import direction is enforced rather than merely documented.**  
   `frontend/eslint.config.js` encodes page, feature, shared UI, design-system, API-client, and barrel rules. The lint baseline passes.

3. **Route pages are composition boundaries.**  
   The inspected pages use feature public APIs and avoid embedding workflow implementation, particularly `CalendarPage`, `JournalPage`, and `RelationshipsPage`.

4. **Human approval gates automation.**  
   `SubmissionAutomationService.execute` refuses non-approved work, and adapters isolate execution behind a registry/service boundary.

5. **Current AI/automation claims are honest in code and documentation.**  
   Agent behavior is deterministic, and the Playwright service is labeled and implemented as mock-only.

6. **Cross-domain synchronous behavior has contract coverage.**  
   Real PostgreSQL contract tests assert downstream records, read-model effects, rollback, and destructive-test safety.

7. **Discovery integrations have explicit contracts and evidence controls.**  
   Provider contracts, normalization, health, source identity, evidence, and exclusion gates are named objects rather than unstructured route logic.

8. **Configuration and external provider fallbacks are centralized.**  
   `Settings` and `CapabilityService` expose whether optional AI, search, travel, scheduling, notification, and import capabilities are configured.

## 10. Areas requiring deeper inspection

These are audit targets, not rewrite recommendations.

1. **Transaction ownership and atomicity across services, agents, and automation**  
   Commits occur in many layers. `OpportunityService.create` is intentionally one transaction, but nested collaborators and other flows may commit independently. Map commit/rollback ownership for submissions, discovery, career generation, imports, and workflow connectors.

2. **Read endpoints that mutate persistent state**  
   `OpportunityService.list` applies deadlines, trust verification, parsing, role sync, character intelligence, and commits when changed. `OpportunityService.get` may verify and commit. Determine whether this is intentional repair-on-read behavior and whether it creates surprising latency, locking, cache, or idempotency effects.

3. **Backend dependency direction and repository consistency**  
   Routes, services, agents, and automation all access ORM state. Inspect whether aggregate ownership is still clear and whether bidirectional service↔agent conceptual dependencies complicate reuse/testing.

4. **Validation consistency across transport, service, and database**  
   Some schema fields are strongly constrained, while others—such as `SubmissionCreate.current_status`—are plain strings despite shared constants. Map which invariants are guaranteed by Pydantic, service checks, model constraints, or only UI options.

5. **Frontend cache-policy/runtime alignment**  
   The stable Playwright request-graph failure suggests the live-refetch contract and actual navigation behavior diverge. Trace the Calendar query configuration, query-client lifetime, route remount behavior, and policy inventory.

6. **Large orchestration surfaces**  
   `DiscoveryAutomationService`, `OpportunityService`, `IntelligenceService`, `OperationsService`, `PlatformImportService`, and the agents each span multiple responsibilities. Measure cohesion and failure boundaries before considering any extraction.

7. **Frontend feature API breadth versus domain ownership**  
   Auditions and Profile call several backend namespaces. Confirm whether workflow ownership is deliberate and whether public barrels expose more internals than consumers need.

8. **Production security boundary**  
   No authentication/authorization middleware or tenant boundary is visible at `app.main` or route registration. Confirm intended deployment exposure, user model, secrets handling, upload access, and CORS policy.

9. **Production persistence and background execution**  
   Local uploads, synchronous long-running intelligence/discovery operations, and absent worker/job contracts are documented limitations. Determine expected portfolio deployment constraints before judging fitness.

10. **CI completeness and baseline debt**  
    CI omits passing unit/lint/build checks and does not enforce backend Ruff, which currently has known lint and formatting failures.

## 11. Open questions that cannot be answered from the code alone

1. Is the deployed portfolio intended for a single trusted user, public read-only demonstration, or authenticated multi-user use?
2. Is there an existing Netlify site, and what build directory, `VITE_API_URL`, redirects, preview policy, and secrets are configured there?
3. Where, if anywhere, is the backend currently hosted, and who runs Alembic migrations during deployment?
4. Is local filesystem upload storage acceptable for the portfolio environment, or is an external object store already configured outside the repository?
5. Are service/agent commits an intentional transaction convention, or historical growth without a documented unit-of-work policy?
6. Is repair/enrichment on `GET /opportunities` an intentional product guarantee, a migration bridge, or temporary behavior?
7. Which capabilities are expected to be genuinely enabled in the portfolio: OpenAI, Parallel search, travel providers, public imports, scheduling, notifications, or none?
8. Are agent prompt files in `backend/app/prompts/*.md` active contracts for a future integration, documentation, or currently unused artifacts?
9. What latency and data-volume targets should guide evaluation of synchronous discovery, parsing, intelligence, and dashboard aggregation?
10. Which backend namespace should be authoritative when a frontend workflow spans several route modules—for example Auditions creating an Operations Calendar event?
11. Is the stable Calendar immediate-return refetch failure a regression in implementation or an obsolete expectation in the browser test/policy inventory?
12. The README links an `outputs/` documentation set that is absent from the audited working tree. Is that documentation intentionally excluded, moved, or missing?

## Highest-value areas for the next audit pass

1. **Transaction and side-effect map:** trace commits, rollbacks, and synchronous downstream writes for opportunity, submission, discovery, career, and import workflows.
2. **Read-path purity and query behavior:** inspect repair-on-read backend behavior alongside the failing frontend Calendar freshness contract.
3. **Backend boundary enforcement:** quantify route/service/agent/automation direct ORM access and identify actual aggregate owners.
4. **Invariant map:** compare frontend constraints, Pydantic validation, service rules, ORM/database constraints, and contract-test coverage for core lifecycle states.
5. **Production boundary:** establish the real frontend/backend hosting, authentication, secrets, migrations, file storage, observability, and CI/CD story before portfolio-readiness conclusions.
