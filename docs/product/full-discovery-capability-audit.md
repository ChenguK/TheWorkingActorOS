# Full Discovery Capability Audit

Date: 2026-08-02

Branch: `feature/full-discovery-capabilities`

Scope: source and test inspection only; no live provider calls or production records.

## 1. Executive summary

The application already has a coherent discovery spine: a user starts a run, enabled and approved sources produce normalized candidates, deterministic parsing/classification and eligibility services enrich them, SQLAlchemy models persist opportunities, and visible/hidden review screens expose outcomes. This is **confirmed** by `backend/app/api/v1/routes/automation.py::run_discovery`, `backend/app/automation/discovery/service.py::DiscoveryAutomationService.run_all/run_source`, and `frontend/src/features/breakdowns/components/BreakdownDiscovery.tsx::AutomationDashboard.runDiscovery`.

Real external discovery is not yet broadly useful because only `PublicPlaybillJobsSource` is a concrete registry provider, all registry providers default disabled, and the only broad-web path requires opt-in Parallel configuration and Film/TV mode. Its queries contain hard-coded gender, geography, and union assumptions; its result adapter retains URL/title but not provider snippets; and medium-confidence public-web candidates are rejected rather than deliberately routed to review. These are **confirmed** in `backend/app/automation/discovery/public_sources.py::PublicPlaybillJobsSource`, `backend/app/automation/discovery/providers.py::PlaceholderDiscoveryProvider/build_discovery_providers`, `backend/app/automation/discovery/service.py::_settings_from_provider/_process_public_web_search_result`, and `backend/app/automation/discovery/public_web_search.py::PublicWebBreakdownSearch.search/search_queries/_extract_candidate_records`.

The smallest valuable slice is therefore not another platform adapter. It is to make the existing opt-in Parallel path actor-specific, preserve bounded result/page evidence, introduce an explicit confidence routing decision, and prove the existing demographic/language/union/location/travel gates end to end against fixtures. Protected platforms and direct social automation remain out of scope.

## 2. Original product promise

The product promise is to find legitimate public acting opportunities an actor would otherwise miss, especially one-off notices outside familiar casting platforms, while showing provenance and sending uncertainty to review. It is not a promise to scrape authenticated platforms or autonomously submit. Current source copy reflects the narrower implemented truth: `frontend/src/features/breakdowns/components/BreakdownDiscovery.tsx::AutomationDashboard` says coverage is limited to approved active sources plus configured Parallel results. **Confirmed.**

## 3. Current implemented discovery flow

1. The user selects a discovery mode/search intents and submits in `AutomationDashboard.runDiscovery`; `frontend/src/features/breakdowns/hooks/useBreakdownDiscovery.ts::useBreakdownDiscovery.run` invokes `useRunBreakdownDiscovery`; `frontend/src/features/breakdowns/api/index.ts::runBreakdownDiscovery` sends `POST /automation/discovery/run`. **Confirmed.**
2. `backend/app/api/v1/routes/automation.py::run_discovery` calls `DiscoveryAutomationService.run_all`. A source-specific route, `run_discovery_source`, also exists. **Confirmed.**
3. `run_all` synchronizes registry settings, runs enabled/approved sources, and considers `PublicWebBreakdownSearch`; `run_source` owns the provider-run transaction and failure rollback. **Confirmed** in `backend/app/automation/discovery/service.py`.
4. Registry candidates pass provider `deduplicate/validate`, discovery mode, intent, and deadline checks, then `_create_opportunity` persists and enriches. Public-web candidates enter `_process_public_web_search_result` and the same creation/enrichment path. **Confirmed** in `DiscoveryAutomationService.run_source/_create_opportunity/_process_public_web_search_result`.
5. `BreakdownIntelligenceEngine.deep_parse`, `OpportunityIntelligenceService.enrich`, `DemographicMatchService`, travel/deadline rules, and `TrustVerificationService.verify` add parsing, eligibility, visibility, and trust metadata. **Confirmed** in `backend/app/services/breakdown_intelligence_engine.py`, `opportunity_intelligence_service.py`, `demographic_match_service.py`, and `trust_verification_service.py`.
6. The mutation returns run totals, coverage, a `public_web_search` summary, and `discovery_report`; `AutomationDashboard` keeps that report in component state and renders URL, decision, rejection reason, and parser confidence. **Confirmed** in `backend/app/automation/discovery/service.py::_discovery_report`, `frontend/src/features/breakdowns/types/index.ts::DiscoveryRunResult/DiscoveryReport`, and `BreakdownDiscovery.tsx::DiscoveryReportPanel`.

## 4. Provider map

| Provider/path | Current behavior | Finding |
|---|---|---|
| Playbill public jobs | Fetches the public jobs index and static detail HTML; emits acting candidates | **Confirmed:** `backend/app/automation/discovery/public_sources.py::PublicPlaybillJobsSource.discover/normalize` |
| Parallel public web | Separate aggregator path for Film/TV when `WEB_SEARCH_PROVIDER=parallel` and `PARALLEL_API_KEY` exist | **Confirmed:** `backend/app/automation/discovery/public_web_search.py::PublicWebBreakdownSearch.configured/search` |
| Actors Access, Casting Networks, Casting Frontier | Supervised/manual placeholders; no automated results | **Confirmed:** `backend/app/automation/discovery/providers.py::SupervisedPlatformProvider` and `PlaceholderDiscoveryProvider.discover` |
| Backstage, Mandy, Project Casting, NYCastings, casting offices, film commissions | Registry placeholders returning no candidates | **Confirmed:** `providers.py::PublicCastingSiteProvider/CastingOfficeProvider/FilmCommissionProvider/build_discovery_providers` |
| Instagram, Facebook, Threads, LinkedIn | Placeholder health explicitly calls for manual/API-based future access; no scraping | **Confirmed:** `providers.py::SocialDiscoveryProvider.health_check` |
| Approved researched sources | Approval can enable the mapped provider, but only a concrete adapter can produce results | **Confirmed:** `backend/app/services/source_research_service.py::add_to_discovery/_set_provider_enabled`; **strong inference** for usefulness because most mapped providers are placeholders |

The requested `backend/app/automation/providers/` directory and several named service modules do not exist. Their responsibilities currently live in `automation/discovery/providers.py`, `public_web_search.py`, `source_evidence.py`, `classification.py`, `services/source_research_service.py`, `opportunity_intelligence_service.py`, and `breakdown_intelligence_engine.py`. **Confirmed.**

All registry settings are initialized disabled by `DiscoveryAutomationService._settings_from_provider`. The portfolio-demo external-provider defaults therefore need no relaxation. **Confirmed.**

## 5. Query-generation map

`PublicWebBreakdownSearch.search_queries` builds 20 fixed queries plus at most three archetype queries. It uses actor playable-age bounds, a reduced ethnicity phrase, actor skills/assets as archetypes, and actor languages only to decide whether to prefix “English-language.” It hard-codes `gender = "woman"`, NYC/Philadelphia/regional locations, SAG-AFTRA and non-union variants, and female/woman wording. **Confirmed** in `backend/app/automation/discovery/public_web_search.py::search_queries` and characterized by `backend/tests/test_public_web_search.py::test_generates_profile_first_english_queries`.

| Actor input | Used in query generation? | Evidence |
|---|---|---|
| Playable age | Yes | `PublicWebBreakdownSearch.search_queries` — **confirmed** |
| Race/ethnicity | Partially; collapses identities into a narrow phrase/open ethnicity | same symbol — **confirmed** |
| Gender identity | No; hard-coded woman/female wording | same symbol — **confirmed** |
| Union status | No actor-specific use; fixed union/non-union queries | same symbol — **confirmed** |
| Languages | Only English-prefix behavior; no language-specific query set | same symbol — **confirmed** |
| Current location | No | same symbol — **confirmed** |
| Travel preferences | No | same symbol — **confirmed** |
| Included/excluded role types | No | same symbol; downstream only — **confirmed** |
| Archetypes/skills | Yes, bounded to three | `search_queries/_actor_archetypes` — **confirmed** |

Parallel receives queries without domain restrictions, so the code requests broad indexed-web results rather than a known-domain allowlist. Which domains and public social pages Parallel actually returns is **requires live-provider verification**; no paid call was made. `PARALLEL_BREAKDOWN_OBJECTIVE` excludes crew, extras, workshops, expired notices, and favors actor-facing roles, but that objective is provider guidance rather than a deterministic guarantee. **Confirmed** in `public_web_search.py`.

## 6. Source-fetching and extraction map

Before page fetch, `_extract_candidate_records` recursively extracts URL/link/source URL/href and optional title from the Parallel response; `_extract_urls` canonicalizes fragments and deduplicates. Provider snippets, quoted passages, rankings, timestamps, and result IDs are not retained. **Confirmed** in `PublicWebBreakdownSearch._extract_candidate_records/_extract_urls`; the exact live response richness is **requires live-provider verification**.

`_fetch_visible_text` then performs a normal HTTP request, accepts HTML/plain text, reads at most 500 KB, strips script/style/noscript/SVG/tags, requires meaningful text, and caps stored working text. `PublicPlaybillJobsSource._detail_text/_clean_visible_page` is similar. **Confirmed.**

| Content | Current support |
|---|---|
| Server-rendered standard HTML/plain text | Yes — **confirmed** by `PublicWebBreakdownSearch._fetch_visible_text` and `PublicPlaybillJobsSource._detail_text` |
| JavaScript-rendered content | No rendering — **confirmed** |
| Public social posts | Only if indexed and returned as fetchable static public HTML — **strong inference**; actual domains require live verification |
| PDFs | No; rejected by content type — **confirmed** |
| Linked documents | No traversal — **confirmed** |
| Authenticated/private content | No login or bypass path; ordinary fetch generally cannot access it — **confirmed** for design, **strong inference** for every site response |

## 7. Parsing and classification map

`automation/discovery/classification.py::classify_breakdown_text` uses deterministic phrase signals for acting, background, voiceover, theater, commercial, staff/crew, and non-acting. Unknown, crew, and non-acting candidates are rejected before public-web normalization; Playbill filters its listing titles similarly. **Confirmed.** Mixed pages can be misclassified because an acting signal can override surrounding crew/article language; this is a **strong inference** from rule order, not a demonstrated production incident.

`BreakdownDetailsService.from_text/from_fields` heuristically extracts production, role, dates, audition, location, union, language, and submission details. `BreakdownIntelligenceEngine.deep_parse` builds sections/roles and an overall confidence score from field/section presence. It starts from a fixed base and is not a calibrated probability. Confidence below its threshold adds low-confidence/manual-review metadata, but the engine alone does not guarantee hidden routing. **Confirmed** in `backend/app/services/breakdown_intelligence_engine.py::deep_parse`.

Direct opportunity versus resource is partially protected: `DiscoveryAutomationService._matches_search_intent` and tests in `test_discovery_role_source_separation.py` reject source cards from role search, while `SourceResearchService._looks_like_individual_breakdown` prevents one-off job/casting URLs from being treated as repeatable source suggestions. Article-versus-direct-breakdown detection remains heuristic. **Confirmed** for rules; **strong inference** for residual false positives.

Expired explicit deadlines are discarded and unparseable explicit deadlines are hidden for date review by `BreakdownDeadlineService.evaluate`; a missing deadline is allowed. **Confirmed** in `backend/app/services/breakdown_deadline_service.py` and `tests/test_breakdown_deadline_service.py`.

Duplicates are checked at provider batch level and again through normalized opportunity lookup in `DiscoveryAutomationService._create_opportunity`; URL/source identity is not the universal opportunity dedupe key. **Confirmed.** Generic roles/projects may therefore collide or changed URLs may re-enter: **strong inference**.

Scam handling is warning-oriented rather than a dedicated scam classifier. `TrustVerificationService.verify` checks source URL, protected platform, contact, source category, duplicate, dates, confidence, and role eligibility and records plain-language reasons. **Confirmed.** Whether that catches representative real scams requires fixture/live verification.

## 8. Evidence and trust model

The durable Opportunity preserves `original_breakdown_url` plus source metadata and parse/trust details (`backend/app/db/models/opportunity.py::Opportunity`; `backend/app/schemas/opportunity.py::OpportunityRead`). The run report preserves candidate URL/title/source/decision/reason/parser confidence (`frontend/src/features/breakdowns/types/index.ts::DiscoveryCandidateReport`; `BreakdownDiscovery.tsx::DiscoveryReportPanel`). It does not preserve a bounded provider snippet or quoted source passage that supports each extracted role field. **Confirmed.**

`SourceEvidence`, `SourceClassificationEvidence`, `SourceCapabilities`, and `SourceIdentityService` are strong bounded, immutable contracts for authoritative identity/version evidence. `SourceExclusionGate` permits automatic tombstones only for trusted, versioned, authoritative, unequivocal crew/non-acting evidence. **Confirmed** in `backend/app/automation/discovery/source_evidence.py`, `source_exclusion_gate.py`, and `services/source_identity.py`.

That gate is deliberately dormant: `backend/tests/test_source_exclusion_architecture.py::test_source_exclusion_gate_is_provider_neutral_dormant_infrastructure` verifies it is not imported by providers/service production flow. Consequently it does not yet reduce live Playbill or Parallel work. **Confirmed.** PostgreSQL contract behavior exists in `tests/contract_smoke/test_source_exclusion_gate.py` but was skipped in this local run due to its environment guard.

## 9. Demographic and travel matching map

Demographic matching occurs after the initial Opportunity is added to the session, during `OpportunityIntelligenceService.enrich/apply_hard_eligibility`, not before any storage operation. `DemographicMatchService.evaluate` compares explicit role text against actor playable age, gender, race/ethnicity/culture, languages, and accents; absent requirements become unknown/review rather than fabricated mismatch. **Confirmed** in `backend/app/services/demographic_match_service.py`.

`OpportunityIntelligenceService.apply_hard_eligibility` applies excluded role types, explicit demographic mismatch, availability, and audition travel. Self-tape stays visible; in-person distance uses actor location/travel settings through the travel service; missing in-person location becomes needs-information/manual review. **Confirmed** in `backend/app/services/opportunity_intelligence_service.py` and `tests/test_breakdown_eligibility_rules.py`.

Union is parsed and contributes to scoring/reasons (`OpportunityIntelligenceService._fit_score`), but source inspection found no actor-union hard eligibility gate. **Confirmed.** Language can participate in demographic mismatch only when it is extracted into role language. Query generation does not faithfully target either union or language. **Confirmed.**

## 10. Hidden-review and approval flow

Hidden/travel-exception opportunities are returned by `GET /automation/opportunities/hidden` in `backend/app/api/v1/routes/automation.py::list_hidden_opportunities`. `frontend/src/features/breakdowns/components/HiddenOpportunityReview.tsx::HiddenOpportunityReview` presents reason, edit/parse/view, approve-as-acting-breakdown, reject, and delete actions. `POST /opportunities/{id}/approve-acting-breakdown` delegates to `OpportunityService.approve_as_acting_breakdown`; reject delegates to `OpportunityService.reject`. **Confirmed** in `backend/app/api/v1/routes/opportunities.py` and `frontend/src/features/breakdowns/api/index.ts`.

The architecture tests `hiddenOpportunityReviewArchitecture.test.ts` and `breakdownViewerArchitecture.test.ts` protect meaningful ownership: the review child remains presentational and uses the shared viewer rather than fetching directly. Strict mock behavior rejects unknown API calls in `frontend/e2e/support/mockApi.ts::installMockApi` and `frontend/e2e/mock-api.spec.ts`. **Confirmed.**

Important gap: `DiscoveryAutomationService._process_public_web_search_result` treats non-visible public-web outcomes as rejected candidate-report decisions even when `_create_opportunity` produced hidden/travel-exception state. Low parse confidence metadata is not an explicit medium-confidence-to-hidden policy. **Confirmed** from the symbol; exact intended product semantics need a new characterization test.

## 11. Confirmed working capabilities

- Opt-in typed discovery run from React through FastAPI and a transaction-owning service. **Confirmed:** paths/symbols in Sections 3 and 10.
- One concrete public Playbill adapter and one configured broad-web aggregator path. **Confirmed:** `PublicPlaybillJobsSource`; `PublicWebBreakdownSearch`.
- Static HTML fetching with bounded response size and content-type checks. **Confirmed:** `_fetch_visible_text`, `_detail_text`.
- Deterministic actor-facing versus crew/non-acting classification and explicit deadline handling. **Confirmed:** `classify_breakdown_text`; `BreakdownDeadlineService.evaluate`.
- Role parsing, demographic/language matching, travel/availability checks, trust warnings, hidden review, manual approval/rejection. **Confirmed:** cited services/routes/UI.
- Source research lifecycle with health check, classification, approval, activation, rejection, restore, and deletion. **Confirmed:** `SourceResearchService` and `frontend/src/features/source-library/components/SourceLibraryPanel.tsx`.
- Honest coverage/report UI and strict mocked request graph. **Confirmed:** `DiscoveryReportPanel`, `frontend/e2e/support/mockApi.ts`, `request-graphs.spec.ts`.

## 12. Partially connected capabilities

- Actor matching is strong downstream but weak upstream: age/ethnicity/archetype partially affect search while gender, union, language, location, travel, and role preferences do not accurately shape queries. **Confirmed.**
- One-off result URLs can become Opportunities without domain approval, and `_suggest_source_from_public_breakdown` separately suggests the domain for future monitoring. The exact post URL is retained. **Confirmed:** `DiscoveryAutomationService._process_public_web_search_result/_suggest_source_from_public_breakdown`.
- Source approval assumes repeat usefulness: `SourceResearchService._looks_like_individual_breakdown` excludes individual posts and `add_to_discovery` activates a source/provider. This is appropriate for monitoring, but separate from accepting a single post. **Confirmed.**
- Evidence contracts/exclusion persistence are implemented and tested in isolation but are not connected to ingestion. **Confirmed.**
- Parse confidence is displayed and verified by trust checks but is not a clear three-way accept/review/reject router. **Confirmed.**

## 13. Placeholder or nonfunctional capabilities

- Every provider in `providers.py` except the separately registered `PublicPlaybillJobsSource` returns an empty list. **Confirmed.**
- Social, supervised casting-platform, casting-site, office, and film-commission provider classes are capability/placeholders, not integrations. **Confirmed.**
- No JS renderer, PDF reader, linked-document traversal, social API, authenticated browser ingestion, or protected-platform automation exists in this flow. **Confirmed.**
- Existing provider/search tests mock network/provider responses. They prove adapters and routing, not live index quality. **Confirmed:** `backend/tests/test_public_web_search.py`.
- Source-exclusion gate integration is intentionally absent. **Confirmed:** `test_source_exclusion_architecture.py`.

## 14. Primary causes of poor or empty results

1. Registry providers default disabled and most are placeholders (`DiscoveryAutomationService._settings_from_provider`; `PlaceholderDiscoveryProvider.discover`). **Confirmed.**
2. Parallel is opt-in, Film/TV-only, and requires provider/key configuration (`PublicWebBreakdownSearch.configured/search`). **Confirmed.**
3. Query assumptions are hard-coded and omit important actor constraints (`search_queries`). **Confirmed.**
4. Static HTML-only fetching cannot read many modern/social/document sources (`_fetch_visible_text`). **Confirmed.**
5. Heuristic page-wide classification/parser can confuse articles/resource pages and direct notices. **Strong inference.**
6. There is no explicit medium-confidence review router or field-level source evidence. **Confirmed.**
7. Live Parallel recall, ranking, payload, and accessible-domain coverage remain **requires live-provider verification**.

The primary reason is configuration plus connection quality, not missing CRUD/UI: the only broad provider is disabled by default, query targeting is incomplete, and retrieved evidence is reduced before classification.

## 15. Legal, ethical, platform, privacy, and operational boundaries

Current provider health copy correctly reserves protected casting platforms for supervised/manual use and social platforms for future manual/API access (`providers.py::SupervisedPlatformProvider/SocialDiscoveryProvider`). The fetcher performs no authentication or anti-bot bypass. **Confirmed.**

Missing explicit controls in the broad fetch path include robots-policy evaluation, domain/redirect policy, private-network address rejection (SSRF defense), per-domain rate limiting, and malicious prompt/content quarantine. **Confirmed absence by source inspection**; exploitability is a **strong inference** and should be threat-modeled before enabling arbitrary result fetches beyond a trusted development environment. Content-size/type limits and no script execution are useful existing controls.

Portfolio-demo must remain provider-disabled. API keys belong only in runtime secrets, and enabling should require both a non-demo environment and explicit configuration. No evidence/snippet should store private/authenticated data or unnecessary personal data.

## 16. Gaps between original goal and current behavior

The system can discover some indexed public pages, but cannot yet reliably search actor-specific demographics/union/language/location/travel preferences; distinguish every direct notice from an article/resource; preserve exact supporting evidence; route uncertainty consistently; or access JS/PDF/social content. It does already support one-off acceptance, downstream matching, source URL display, review, and source-domain research. **Confirmed** except actual public-web recall, which **requires live-provider verification**.

## 17. Recommended provider strategy

Keep a single configured public-web aggregator as the first broad discovery adapter and treat returned domains as untrusted public inputs. Add no protected-platform scraper. Use supported static HTML first, record unsupported content for review/metrics, and add a new content adapter only after fixtures prove repeated value. Keep provider enablement opt-in and portfolio-demo off. Evaluate official social/search access separately after legal, cost, and platform review.

## 18. Recommended first vertical slice

1. Replace hard-coded query assumptions with a deterministic, bounded query plan derived from actor age, gender, identities, union status, languages, location/travel policy, included/excluded roles, and archetypes.
2. Extend the Parallel result contract to retain bounded result title/snippet/provider identity and canonical source URL before fetch.
3. Add safe-fetch policy for public HTTP(S) static HTML: reject private/local destinations, validate redirects/content type/size, and report unsupported content without bypassing access controls.
4. Parse and classify with existing services, but introduce an explicit decision object: high-confidence eligible direct acting notice -> visible; medium/ambiguous -> hidden review; explicit crew/non-acting/expired/hard mismatch -> discarded.
5. Preserve bounded evidence and a plain-language match/review explanation on the Opportunity/run report.
6. Prove one-off posts work without approving their domains; domain suggestions remain a separate repeat-monitoring workflow.

This sequence reuses the current service, transaction, UI, and source-research architecture. It does not require a provider framework rewrite.

## 19. Acceptance criteria for that vertical slice

- A fixture actor produces bounded queries that accurately include all configured matching dimensions and never invent gender/location/union values.
- A mocked configured Parallel response yields a durable canonical URL plus bounded result/page evidence.
- Static public HTML produces parsed role/production data; unsupported/private/authenticated/document content is not bypassed and is reported safely.
- Explicit crew/non-acting and past-deadline fixtures are discarded; direct high-confidence eligible acting notices become visible; ambiguous/medium-confidence notices become hidden with reasons.
- Demographic, union, language, location, travel, role-preference, and availability decisions are explained and tested. Union must have an explicit product policy (filter, review, or score), not an accidental score-only effect.
- One useful post can be accepted without domain approval; approving a domain remains optional and separate.
- The UI shows source link, evidence excerpt/fields, confidence, and decision reason.
- Portfolio-demo and unconfigured environments make zero external provider calls.

## 20. Tests required before enabling a real provider

- Unit tests for query generation across missing/complete profiles and every actor constraint.
- Adapter contract tests for actual documented Parallel response fixtures, malformed responses, dedupe, snippets, costs, and pagination/limits.
- Safe-fetch tests for private IPs, redirects, content types, size limits, auth/login pages, timeouts, and unsupported JS/PDF.
- Direct notice/article/resource/crew/non-acting/expired/scam-like fixtures.
- Decision-router tests for high/medium/low confidence and hard eligibility, including union/language/travel.
- Persistence/transaction tests proving evidence, visibility, dedupe, rollback, and one-off/domain separation.
- API contract and React component tests for evidence/reason display and hidden approval/rejection.
- Strict Playwright request-graph test proving one run, refreshed visible/hidden owners, and no unknown endpoints.
- Configuration tests proving portfolio-demo, missing key, and disabled provider make no external calls.
- A deliberately controlled, cost-capped provider canary outside portfolio-demo before broader enablement.

## 21. Explicitly deferred work

- Direct Facebook, Instagram, X, Threads, LinkedIn, or Reddit automation.
- Authenticated casting-platform scraping, anti-bot bypass, and background crawling.
- JavaScript browser rendering, PDF/document traversal, or OCR until measured source yield justifies each adapter.
- Additional paid search providers, ML classifiers, vector databases, and autonomous submissions.
- Source-exclusion gate integration until a concrete provider supplies authoritative version evidence.
- Broad provider-framework, persistence, Breakdowns UI, or source-library redesign.

## Direct answers to the 30 audit questions

1. Trigger: `AutomationDashboard.runDiscovery` -> `useBreakdownDiscovery.run` -> `POST /automation/discovery/run` -> `run_discovery/run_all`. **Confirmed.**
2. Providers: concrete Playbill plus opt-in Parallel broad search; all others are empty placeholders, and registry defaults are disabled. **Confirmed.**
3. Parallel objective: current Film/TV actor-facing principal/supporting roles, excluding extras/crew/workshops/expired and favoring feasible audition travel. `PARALLEL_BREAKDOWN_OBJECTIVE`. **Confirmed.**
4. Queries: 20 fixed templates plus up to three actor archetype templates. `search_queries`. **Confirmed.**
5. Actor inputs: age/limited ethnicity/archetypes partially; gender, union, specific languages, location, travel, and role preferences are not faithfully used. **Confirmed.**
6. Scope: no domain allowlist; intended broad indexed web. Actual coverage **requires live-provider verification**.
7. Pre-fetch data: URL and optional title; rich provider evidence is discarded. `_extract_candidate_records`. **Confirmed.**
8. Page fetch: yes, bounded urllib static HTML/plain fetch. `_fetch_visible_text`. **Confirmed.**
9. Unfetchable: authenticated/private, JS-only, blocked/anti-bot, unsupported content types, oversized/too-short responses. **Confirmed/strong inference** depending on remote response.
10. Reads: standard HTML yes; JS/PDF/linked docs no; social only when a static public result is fetchable. **Confirmed/strong inference.**
11. Protections: no login/bypass, size/type/time limits, script stripping, protected-platform placeholders; no explicit robots/SSRF/domain/redirect/malicious-content policy. **Confirmed absence.**
12. Transformation: result record -> fetched/normalized candidate -> `_create_opportunity` -> visibility/eligibility enrichment -> hidden/visible/discarded; approval via `approve_as_acting_breakdown`. **Confirmed.**
13. Required normalized fields: result type, URL, role, project, union, location, description in `DiscoveryProvider.validate`. **Confirmed.**
14. Unknowns: semantic placeholders such as Unknown/See source can satisfy validation; many parsed fields are nullable. **Confirmed.**
15. Confidence: deterministic completeness/section scoring in `BreakdownIntelligenceEngine`, not calibrated. **Confirmed.**
16. Evidence: URL/title/run decision and Opportunity source/parse metadata survive; provider snippet/field quotations do not. **Confirmed.**
17. Distinctions: deterministic text rules, intent/source separation, deadlines, normalized dedupe, and trust warnings; articles/resources/scams remain heuristic. **Confirmed/strong inference.**
18. Demographic matching: occurs during enrichment after initial session add, using explicit age/gender/identity/language/accent requirements. **Confirmed.**
19. Discarded: demo, wrong mode/intent, crew/non-acting/unknown, expired, duplicates, hard demographic/role/availability failures; exact branches vary by path. **Confirmed.**
20. Hidden: uncertain date, unknown/low-information/travel-location cases and manual-review states; medium parse confidence is not consistently routed by an explicit policy. **Confirmed.**
21. Match explanation: partial, through fit/demographic/trust/hidden reasons and report rejection reason. **Confirmed.**
22. Exact supporting evidence: source URL yes; field-level quotation/snippet no. **Confirmed.**
23. One-off sources: accepted Opportunity can use exact URL; domain can separately become a source suggestion. **Confirmed.**
24. Source approval: yes, source-research approval is designed for repeatable monitoring. **Confirmed.**
25. Single-post acceptance: yes through public-web opportunity creation without domain approval. **Confirmed.**
26. Already implemented: run orchestration, one public adapter, optional broad search, parsing, classification, matching, persistence, review, source research, reporting. **Confirmed.**
27. Tested but disconnected: source-evidence/exclusion gate is the clearest case; mocked Parallel tests do not prove live yield. **Confirmed.**
28. Placeholders/approximations: most providers, deterministic classifiers/parsers, mocked external responses, static-only fetching. **Confirmed.**
29. Main blockers: disabled/placeholder providers, incomplete query personalization, evidence loss, static fetch limits, and no explicit medium-confidence routing; live recall remains unknown. **Confirmed plus live-verification caveat.**
30. Smallest useful slice: improve the existing opt-in Parallel vertical path end to end as specified in Sections 18–20. **Strong recommendation based on confirmed architecture.**
