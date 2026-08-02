# Full Discovery First-Slice Implementation Plan

Date: 2026-08-02

Target branch: `feature/full-discovery-capabilities`

Objective: one safe, opt-in, evidence-preserving public-web discovery path; no architecture rewrite.

## Guardrails

- Preserve portfolio-demo defaults and make zero provider calls unless explicitly enabled and configured.
- Do not scrape authenticated casting platforms, bypass anti-bot controls, or add direct social automation.
- Reuse `DiscoveryAutomationService`, current Opportunity persistence/enrichment, source research, and hidden review.
- Keep one-off post acceptance separate from repeat-source approval.
- Use fixtures/mocks until a separately authorized, cost-capped canary.

## Recommended order

1. Characterize the current public-web decision and persistence contract.
2. Generate actor-specific bounded queries.
3. Preserve bounded provider-result evidence.
4. Enforce safe public-content fetching.
5. Add an explicit accept/review/reject decision policy.
6. Persist and expose evidence and match explanations.
7. Prove the complete API/UI vertical slice and configuration gate.
8. Run an optional controlled provider canary only after review.

Each numbered task is intended as one focused commit unless its tests make a smaller split preferable.

## Task 1 — Characterize the current public-web contract

**Problem.** Public-web creation, visibility, source suggestion, and transaction behavior exist but lack a single end-to-end characterization. Refactoring without it could change tested behavior.

**Current source evidence.** `backend/app/automation/discovery/service.py::DiscoveryAutomationService.run_all/_process_public_web_search_result/_create_opportunity/_suggest_source_from_public_breakdown`; `backend/tests/test_public_web_search.py`; `test_discovery_modes.py`; `test_discovery_role_source_separation.py`.

**Exact scope.** Add fixture-driven tests for a direct eligible notice, ambiguous page, crew page, expired notice, duplicate URL/content, and one-off source/domain suggestion separation. Record current transaction and visibility outputs before changing policy.

**Out of scope.** Production behavior changes, real provider calls, new database fields, source-exclusion integration.

**Acceptance criteria.** Tests identify the exact current outcome and metadata for every fixture; failures distinguish intentional next-task changes from regressions.

**Tests.** Focused service tests with mocked Parallel/fetcher and in-memory DB; retain the existing discovery/source suites.

**Configuration requirements.** None; inject/mimic provider client and page responses.

**API-cost considerations.** Zero external calls/cost.

**Security and privacy.** Fixtures contain synthetic public text and no credentials/PII.

**Risk.** Low.

**Commit boundary.** `test(discovery): characterize public web routing`

## Task 2 — Generate actor-specific bounded queries

**Problem.** `PublicWebBreakdownSearch.search_queries` hard-codes woman/female, cities, and union variants and uses languages only as an English prefix. That can miss relevant work and search for mismatched roles.

**Current source evidence.** `backend/app/automation/discovery/public_web_search.py::search_queries/_actor_archetypes`; `backend/tests/test_public_web_search.py::test_generates_profile_first_english_queries`; actor fields consumed downstream in `demographic_match_service.py::DemographicMatchService.evaluate` and travel preferences in `opportunity_intelligence_service.py`.

**Exact scope.** Introduce a small pure query-plan builder owned by the public-web adapter. Derive bounded query variants from saved playable age, gender identities, race/ethnicity/culture, union status, languages, current/allowed locations and travel policy, included/excluded role types, and up to a fixed number of archetypes. Omit absent dimensions rather than inventing defaults. Keep Film/TV scope and configured provider.

**Out of scope.** Profile schema changes, AI query generation, unlimited query combinations, Theater expansion, ranking redesign.

**Acceptance criteria.** Complete profiles yield representative constrained queries; incomplete profiles yield neutral queries; excluded role terms never become positive targets; total query count and string length are capped; no hard-coded actor identity/location remains.

**Tests.** Parameterized pure unit tests for every dimension, empty values, escaping, dedupe, caps, union and non-English cases; update mocked search-call assertions.

**Configuration requirements.** Add only documented query-count limits if configuration is truly operational; otherwise code constants. No key changes.

**API-cost considerations.** Bound queries per run and results per query; document expected maximum calls/results. Do not increase the current cap without approval.

**Security and privacy.** Send only the minimum actor attributes needed to form public search phrases; never send contact details, exact street address, private notes, or asset content.

**Risk.** Medium because result recall/precision changes.

**Commit boundary.** `feat(discovery): generate actor-specific public search queries`

## Task 3 — Preserve bounded provider-result evidence

**Problem.** `_extract_candidate_records` reduces provider output to URL/title, discarding snippets and provider identifiers before source fetch. The system cannot later show what the search provider claimed.

**Current source evidence.** `backend/app/automation/discovery/public_web_search.py::PublicWebSearchResult/_extract_candidate_records/_response_summary`; `frontend/src/features/breakdowns/types/index.ts::DiscoveryCandidateReport`; `BreakdownDiscovery.tsx::DiscoveryReportPanel`.

**Exact scope.** Define a typed, bounded result-evidence record containing provider name, canonical URL, title, a short sanitized snippet when supplied, and stable provider result ID/date only when documented. Carry it through `PublicWebSearchResult` and candidate report. Redact/limit lengths and never store arbitrary provider payloads.

**Out of scope.** Full HTML storage, screenshots, provider-response blobs, field-level extraction evidence, source-exclusion authority.

**Acceptance criteria.** Known response fixtures retain bounded evidence; malformed/oversized fields are safely omitted/truncated; URL dedupe remains; serialization is stable; old result shapes still parse defensively if compatibility is required.

**Tests.** Adapter fixtures for documented response shapes, missing/oversized/malicious markup snippets, dedupe, and report schema/API contract.

**Configuration requirements.** None.

**API-cost considerations.** No additional calls; small storage/response overhead with strict caps.

**Security and privacy.** Sanitize display text; do not render HTML; do not persist undocumented payloads or protected content.

**Risk.** Low to medium due to contract change.

**Commit boundary.** `feat(discovery): preserve public search result evidence`

## Task 4 — Add a safe public-content fetch policy

**Problem.** `_fetch_visible_text` bounds size/content type and executes no scripts, but arbitrary result URLs lack explicit private-network, redirect, scheme, and authentication-page policy.

**Current source evidence.** `backend/app/automation/discovery/public_web_search.py::PublicWebBreakdownSearch._fetch_visible_text/_clean_visible_page`; analogous `public_sources.py::PublicPlaybillJobsSource._detail_text`; current protected-platform stance in `providers.py::SupervisedPlatformProvider.health_check`.

**Exact scope.** Add a narrowly owned fetch policy for HTTP(S) public destinations: validate host and resolved addresses, reject localhost/private/link-local destinations, revalidate redirects, cap redirects/time/bytes, retain content-type allowlist, identify common login/access-denied responses as unsupported, and return a typed fetch outcome/reason. Respect access failures and never bypass them.

**Out of scope.** Browser rendering, proxy rotation, CAPTCHA solving, robots circumvention, cookies/login, PDF/OCR, crawling linked pages. A legal review should decide whether explicit robots evaluation is required for one-page retrieval before live enablement.

**Acceptance criteria.** Private/local/unsafe schemes and redirects are blocked; supported static public HTML is parsed; auth/blocked/JS/PDF/oversized content returns a non-fatal reason suitable for metrics/review; no provider call is made in disabled/demo mode.

**Tests.** Mock DNS/HTTP cases for IPv4/IPv6 private addresses, redirect chains, timeout, content type, size, login page, malformed URL, and successful HTML. No internet calls.

**Configuration requirements.** Conservative time/byte/redirect constants; optional allow/deny domains only if operational evidence requires them.

**API-cost considerations.** No search-call increase; bounded page-fetch bandwidth and concurrency.

**Security and privacy.** This is the primary SSRF/privacy control. Log reasons and canonical hosts, not full sensitive query strings or page bodies.

**Risk.** Medium; network handling is security-sensitive.

**Commit boundary.** `feat(discovery): enforce safe public source fetching`

## Task 5 — Introduce an explicit discovery decision policy

**Problem.** Classification, parse confidence, eligibility, and trust checks exist, but public-web processing lacks a clear three-way policy. Medium confidence can appear as rejection instead of hidden review.

**Current source evidence.** `backend/app/automation/discovery/service.py::_process_public_web_search_result/_create_opportunity`; `classification.py::classify_breakdown_text`; `breakdown_intelligence_engine.py::BreakdownIntelligenceEngine.deep_parse`; `breakdown_deadline_service.py::evaluate`; `opportunity_intelligence_service.py::enrich/apply_hard_eligibility`; `trust_verification_service.py::verify`.

**Exact scope.** Add a small pure decision result with `accept_visible`, `review_hidden`, or `reject_discarded`, reason codes, and explanation. Reuse existing classifiers and enrichment outputs. Explicit crew/non-acting, expired, irrelevant mode/intent, and hard eligibility mismatch reject. Direct, adequately parsed, eligible, trusted-enough notices accept. Ambiguous directness, medium parse confidence, missing material fields/date/location, or trust warnings route to hidden review. Define union policy explicitly using actor union status: hard reject only if product rules prove incompatibility; otherwise review/score.

**Out of scope.** ML, generalized rules engine, rewriting parsers, deleting compatibility visibility states, automatic source exclusion.

**Acceptance criteria.** Every candidate receives one deterministic decision and reasons; no medium-confidence result is silently discarded solely for uncertainty; crew and expired fixtures never become visible; current downstream demographic/language/travel/availability behavior is preserved; transaction ownership remains in `DiscoveryAutomationService`.

**Tests.** Decision-table unit tests and service integration tests for confidence thresholds, article/resource ambiguity, demographic/language/union/travel outcomes, and rollback. Update Task 1 characterization only where the new intended contract differs.

**Configuration requirements.** Confidence thresholds should be named constants initially; configuration only if operators have a demonstrated need.

**API-cost considerations.** None; may reduce repeated searches by retaining review candidates.

**Security and privacy.** Untrusted content never supplies executable instructions; reasons derive from bounded deterministic facts.

**Risk.** Medium to high because visibility and discard behavior changes.

**Commit boundary.** `feat(discovery): route uncertain public results to review`

## Task 6 — Persist evidence and match explanations

**Problem.** Opportunities preserve URLs and general parse/trust metadata but not bounded result/source excerpts tied to a discovery decision; users cannot verify why each field or match was inferred.

**Current source evidence.** `backend/app/db/models/opportunity.py::Opportunity.source_metadata`; `backend/app/schemas/opportunity.py::OpportunityRead`; `DiscoveryAutomationService._matched_breakdown_discovery_reason/_discovery_report`; `frontend/src/features/breakdowns/components/BreakdownViewer.tsx::parsingConfidence`; `BreakdownDiscovery.tsx::DiscoveryReportPanel`.

**Exact scope.** Store a versioned, bounded evidence object in existing JSON metadata if its contract is adequate: canonical URL, provider-result snippet, selected sanitized page excerpts with labels, retrieval timestamp, decision reasons, and actor-match explanation. Expose it through existing schemas and render it as plain text/link in discovery report, Breakdown viewer, and hidden review. Preserve compatibility for old records without evidence.

**Out of scope.** Full page snapshots, screenshots, new document storage, source-exclusion version authority, broad UI redesign, migration unless existing JSON cannot safely carry the bounded contract.

**Acceptance criteria.** New records show source, bounded evidence, decision, and match/review reasons; old records render normally; no raw HTML/secrets are stored; one-off posts remain independent of domain approval.

**Tests.** Serialization/size/redaction tests, API response tests, React rendering/accessibility tests, old-record compatibility, malicious-markup display test.

**Configuration requirements.** Evidence length/count constants; no provider credentials exposed.

**API-cost considerations.** No extra provider requests; bounded database/response growth.

**Security and privacy.** Plain-text escaping, minimal retention, no authenticated/private content, no sensitive query parameters in displayed canonical URLs.

**Risk.** Medium; JSON contract and UI change. If a migration becomes necessary, isolate it in a separate commit.

**Commit boundary.** `feat(discovery): expose source evidence and match reasons`

## Task 7 — Verify the complete opt-in vertical slice

**Problem.** Unit-tested parts do not prove the browser-to-API-to-persistence-to-review workflow, configuration isolation, or strict request graph.

**Current source evidence.** `frontend/src/features/breakdowns/api/index.ts::runBreakdownDiscovery`; `hooks/useBreakdownDiscovery.ts`; `components/BreakdownDiscovery.tsx`; `HiddenOpportunityReview.tsx`; `frontend/e2e/support/mockApi.ts::installMockApi`; `frontend/e2e/request-graphs.spec.ts`; backend discovery tests.

**Exact scope.** Add backend contract/integration fixtures and focused frontend/Playwright tests for configured run, visible high-confidence result, hidden ambiguous result, rejected crew/expired result, source evidence, approval/rejection, and exact invalidation/request graph. Add capability/configuration assertions for local opt-in versus portfolio-demo off.

**Out of scope.** Live paid search, broad E2E redesign, unrelated invalidation, portfolio/demo configuration changes.

**Acceptance criteria.** Complete backend and frontend suites pass; strict mock has every intentional endpoint and rejects unknown calls; disabled/demo cases make zero provider calls; docs list configuration and bounded canary procedure.

**Tests.** Backend full suite, contract smoke suite with PostgreSQL, frontend unit/lint/build, focused Playwright plus full E2E when stable.

**Configuration requirements.** Document `WEB_SEARCH_PROVIDER=parallel` and secret-managed `PARALLEL_API_KEY` only for an approved non-demo environment; preserve blueprint/deployed values.

**API-cost considerations.** Automated tests are fully mocked. CI must never receive/use a paid key.

**Security and privacy.** Assert secrets never reach API responses, logs, frontend bundles, fixtures, or committed files.

**Risk.** Low for tests/docs; medium for any fixes uncovered, which should use separate commits.

**Commit boundary.** `test(discovery): verify evidence-preserving public search flow`

## Task 8 — Optional controlled provider canary

**Problem.** Mocked fixtures cannot establish real Parallel recall, response shape, domain coverage, rate limits, or cost.

**Current source evidence.** `backend/tests/test_public_web_search.py` injects mocked clients/pages; the audit therefore marks live quality unverified.

**Exact scope.** After Tasks 1–7 and explicit authorization, run a non-production, non-portfolio, read-only canary with a capped query/result budget. Do not persist Opportunities. Record aggregate yield: returned, fetchable, direct/ambiguous/irrelevant, supported content types, domains, latency, and estimated cost. Review terms and retention first.

**Out of scope.** Continuous scheduling, production enablement, social-platform targeting, user data beyond a synthetic/minimized actor profile.

**Acceptance criteria.** Budget and stop conditions are set before execution; no production records/config changes; results contain no committed credentials or private content; findings decide whether to enable, revise queries, or stop.

**Tests.** Preflight config and dry-run tests; this is an operational validation, not CI.

**Configuration requirements.** Ephemeral secret in an isolated approved environment; explicit opt-in; portfolio-demo remains disabled.

**API-cost considerations.** Hard monetary/query cap and one run; report actual cost.

**Security and privacy.** Terms/legal review, synthetic/minimum profile data, no auth bypass, no raw page-body retention outside the approved evidence contract.

**Risk.** Medium operational/legal risk; requires user approval.

**Commit boundary.** No production commit solely for the canary. Commit only reviewed fixture/docs updates separately.

## Release gate for enabling a real provider

- Tasks 1–7 accepted and all relevant suites green, including PostgreSQL contract smoke.
- Portfolio-demo and deployed Render/Netlify configuration unchanged and externally disabled.
- Query/result/page/cost limits documented.
- Safe-fetch threat review complete.
- Evidence retention and plain-text display reviewed.
- Actor union/language/location/travel decision policy approved as product behavior.
- Controlled canary demonstrates useful direct-notice yield with acceptable ambiguity/cost.
- Rollback is configuration-only: disable the provider without schema or data repair.
