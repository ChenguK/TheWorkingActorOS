# Full Discovery: Current Public-Web Contract

Date: 2026-08-02

Branch: `feature/full-discovery-capabilities`

This document characterizes current behavior. It is not the desired routing policy. All external inputs in the tests are synthetic and all network/provider calls are mocked.

## Actor-specific public-web query contract

`backend/app/automation/discovery/public_web_search.py::PublicWebBreakdownSearch.search_queries` now builds a deterministic, layered Film/TV query plan from persisted actor data. It can use the primary and valid secondary playable-age ranges; configured gender identities, including an explicit open-gender value; chosen racial and ethnic identities; union/SAG status; languages; supported Film/TV included-role types; general current location; local-work, flight/international, self-tape, and virtual-audition travel flags; and bounded `Asset.archetype_names` values.

The planner emits at most 6 queries of at most 220 characters each. It uses at most 3 archetypes, 3 location/travel terms, and 3 languages, preserves saved-field order, deduplicates case-insensitively, and uses layered queries instead of a Cartesian product. The Parallel request remains one provider call with `max_results=10`.

Missing dimensions are omitted rather than replaced with demographic, language, union, age, location, or archetype defaults. Excluded or unsupported roles do not become positive terms, and the plan remains Film/TV-only. The planner does not read or include actor name, contact/account identifiers, exact addresses or coordinates, notes, availability, agency contacts, asset filenames/paths/descriptions, resume or headshot content, or medical data. Address-like current-location values are rejected rather than searched. Disabled provider configuration and `portfolio_demo` both produce zero queries and zero Parallel calls.

## Static public-content fetch contract

`backend/app/automation/discovery/public_content_fetch.py::PublicContentFetcher` owns the static page-fetch boundary used by `PublicWebBreakdownSearch._fetch_visible_text`. It accepts only HTTP and HTTPS URLs without embedded credentials, requires a hostname, and rejects localhost plus every loopback, private, link-local, multicast, reserved, unspecified, carrier-grade-NAT/non-global, or rejected IPv4-mapped IPv6 destination. Hostnames are resolved before a request, every returned address must be public, and mixed public/private DNS answers are rejected.

HTTP redirects are followed manually with automatic redirects disabled. The fetcher validates each target, detects loops, rejects HTTPS-to-HTTP downgrade and unsafe/unsupported targets, and permits at most 4 redirects. Each request is stateless and sends only the bounded generic `User-Agent` and an `Accept` header for supported text; it sends no provider credentials, actor data, authorization, cookies, or referer. Cross-origin redirects receive only those same generic headers.

The total request timeout is 12 seconds, with explicit 5-second connect and 8-second read limits. Response iteration stops when decoded/decompressed content would exceed 500,000 bytes. Only `text/html` and `text/plain` media types are accepted; a missing or ambiguous type and PDF, JSON, image, audio, video, and binary responses are rejected. Visible text is capped at 12,000 characters and must contain at least 25 words.

The fetch result uses stable outcomes for success, invalid URL, unsupported scheme, non-public destination, DNS failure, mixed public/private DNS, rejected redirect, redirect-limit exhaustion, timeout, unsupported content type, oversized response, login/authentication protection, CAPTCHA/access denial, HTTP failure, and empty usable content. Candidate reports receive only the reason code and a bounded safe message; raw exceptions, addresses, DNS details, response bodies, and full rejected pages are not exposed or retained. Deterministic checks reject password forms and explicit login/authentication, access-denied, CAPTCHA, and common bot-challenge language without attempting bypass.

DNS validation and connection are not fully pinned to the same resolved address: the standard HTTPX transport performs its own DNS lookup when connecting. Validating every destination immediately before each request narrows the time-of-check/time-of-use gap but does not eliminate DNS rebinding. Fetched text remains transient input to parsing and is not archived.

## Public-discovery decision contract

`backend/app/automation/discovery/decision_policy.py::PublicDiscoveryDecisionPolicy` assigns every public-web candidate exactly one typed outcome: `accept_visible`, `review_hidden`, or `reject_discarded`. The record contains one stable primary reason code, a bounded plain-text explanation of at most 240 characters, optional ordered supporting reason codes, and parse confidence when available. Provider evidence remains a separate report field and is never incorporated into the explanation.

Decision precedence is fixed. Proven hard rejection runs first: crew/staff or non-acting classification, expired deadline, irrelevant project mode or search intent, malformed/unusable fetched content, and blocked trust results reject. Proven existing eligibility rules run next: excluded role type, hard demographic mismatch, required-language failure represented by the eligibility engine, required-date availability conflict, and hard audition-travel failure reject. These rules cannot be overridden by uncertainty.

Reviewable uncertainty runs only when no hard failure exists. It includes article/resource ambiguity, generic or missing role detail, parse confidence below 70, missing or ambiguous deadline, missing location, missing/unknown union status, uncertain project type, material trust warnings, in-person travel that cannot be calculated, and existing travel exceptions. A created visible candidate receiving a review outcome is moved to `hidden`; the existing `travel_exception` persistence state is retained but is reported as `review_hidden`, not rejected.

The named confidence constants are 70 for visible acceptance, 1 as the lower reviewable bound, and 0 for an unusable parse. This preserves the parser's existing below-70 warning boundary without changing confidence calculation. A direct candidate needs a confidence of at least 70, a specific role, known project type, usable location, known union value, an identified submission/audition deadline, no material trust warning, and no hard rule before it receives `accept_visible` / `direct_eligible_notice`.

The current actor/profile model and eligibility engine do not prove union incompatibility. Known saved/listing values such as union, non-union, and eligible are therefore not invented or hard-rejected by this policy; missing or unknown union information routes to `review_hidden` / `union_uncertain`. Self-tape, virtual, and allowed local auditions can be visible. Uncalculable in-person travel and otherwise-relevant travel exceptions are reviewable; the existing eligibility engine's proven hard in-person limit remains discarded.

Candidate reports retain the compatibility `decision` label while adding `outcome`, `reason_code`, `explanation`, and optional `supporting_reason_codes`. Hidden review is labeled `Needs Review`; discarded rejection is labeled `Rejected`. Duplicate candidates continue to reuse existing Opportunity identity and do not create or merge evidence, while the repeated candidate report receives `reject_discarded` / `duplicate_candidate`. Tasks 2–4 query budgets, provider evidence, and safe-fetch behavior remain unchanged. Public-web transaction durability and `DiscoveryRun` ownership remain unresolved.

## Report-scoped provider-result evidence

`backend/app/automation/discovery/public_web_search.py::PublicWebProviderEvidence` retains only the installed Parallel SDK's documented per-result fields: provider name, canonical URL, optional title, the first valid optional excerpt as a short snippet, and an optional valid `YYYY-MM-DD` publication date. The explicit limits are 80 characters for provider name, 1,000 for canonical URL (matching the existing source-URL boundary), 240 for title, 600 for snippet, and 10 for publication date. A 200-character result-ID boundary is reserved, but no result ID is currently accepted because Parallel documents request-level search/session IDs rather than a stable per-result ID.

Title and snippet values are converted to bounded readable plain text: script/style blocks and HTML tags are removed, HTML entities decoded, Markdown link/image destinations discarded, control characters removed, repeated whitespace collapsed, and the result trimmed. Arbitrary nested payloads, undocumented IDs, additional excerpts, full provider responses, full HTML, and provider metadata outside the typed structure are discarded.

Candidate identity remains the normalized HTTP(S) URL with fragments removed. Duplicate canonical URLs retain the first valid result's evidence deterministically; later titles, snippets, and dates are neither merged nor substituted. The candidate report carries evidence separately under `provider_evidence`, and its canonical URL is also the candidate source URL. The snippet is labeled as search-result context rather than verified fetched-page content. This evidence exists only in the discovery-run response and component lifecycle: it is not added to Opportunity/source metadata, committed to the database, or associated with a `DiscoveryRun`.

## Request-to-persistence flow

1. `frontend/src/features/breakdowns/components/BreakdownDiscovery.tsx::AutomationDashboard.runDiscovery` invokes `useBreakdownDiscovery.run`; `frontend/src/features/breakdowns/api/index.ts::runBreakdownDiscovery` sends `POST /automation/discovery/run`.
2. `backend/app/api/v1/routes/automation.py::run_discovery` calls `backend/app/automation/discovery/service.py::DiscoveryAutomationService.run_all`.
3. After enabled registry plugins, `run_all` calls `_run_public_web_search`. That constructs `backend/app/automation/discovery/public_web_search.py::PublicWebBreakdownSearch` with the first `ActorProfile` and calls `search("FilmTV")` only when Parallel is configured.
4. `PublicWebBreakdownSearch.search` sends bounded queries, then `_extract_candidate_records` reads only documented result objects/dictionaries and deduplicates typed, bounded provider evidence by canonical URL. It retains the first excerpt and valid publication date for the report while discarding request IDs, undocumented result IDs, ranking, additional excerpts, and arbitrary payloads.
5. `_fetch_visible_text` fetches static HTML/plain content. `_normalize_candidate` runs `automation/discovery/classification.py::classify_breakdown_text`, rejects `Non-Acting Job`, `Crew Job`, and `Unknown`, and delegates field parsing to `services/breakdown_details_service.py::BreakdownDetailsService.from_fields`.
6. `DiscoveryAutomationService._process_public_web_search_result` applies `_matches_mode`, `_matches_search_intent`, and `BreakdownDeadlineService.validate_normalized`, then calls `_create_opportunity`.
7. `_create_opportunity` detects duplicates by `_key`: normalized project + role + location + source host + selected dates. It does not use the full URL as the identity. It assigns initial status through `_visibility`, deep-parses through `BreakdownIntelligenceEngine.run_for_opportunity`, applies deadline state, synchronizes roles/watchlists, then runs `OpportunityIntelligenceService.enrich` and `TrustVerificationService.verify`.
8. `OpportunityIntelligenceService` applies audition visibility/travel, `DemographicMatchService`, excluded-role and demographic/availability/travel eligibility, scoring, confidence, and risk. Union affects quality scoring but is not a hard eligibility rule. Language is evaluated when detected in parsed text. Self-tape sets travel time to zero.
9. A newly visible public-web opportunity causes `_suggest_source_from_public_breakdown` to create or update a separate `SourceResearchItem`. A new source remains `Suggested`, `approved_by_user=False`, with no `approved_discovery_url`; individual opportunity acceptance does not approve monitoring.
10. Registry `run_source` owns a transaction: it flushes a `DiscoveryRun`, commits success, rolls back partial writes on any error, and persists one failed run from a clean transaction. The separate public-web path has no `DiscoveryRun`, `commit`, or exception rollback boundary. `get_db` only closes the session. Therefore public-web Opportunity and source-suggestion writes remain transaction-pending and are rolled back at request close. This is a confirmed current gap, not corrected in Task 1.

## Current-behavior fixture matrix

| Input category | Provider-result shape | Fetch result | Classification | Confidence | Eligibility | Routing/report | Persisted records | Evidence retained | Source-research effect | Known gap |
|---|---|---|---|---|---|---|---|---|---|---|
| Direct eligible acting notice | URL + title; duplicate fragments canonicalized | Static public text with project, supporting role, SAG-AFTRA, Black woman 25–40, English, self-tape, future deadline | `Acting Role` | Deep-parser value is copied into the run candidate report; fixture routing uses `82` | Configured actor yields `demographic_match_status="Match"`; self-tape travel is zero; union is score-only | Opportunity is `visible`; report is `Accepted` | Opportunity, role/parse children, source, and source suggestion exist only in the open request transaction; no `DiscoveryRun`; request-close rollback removes them | Bounded provider evidence survives in the report; canonical `original_post_url` and regenerated `source_url` survive on the Opportunity, but provider title/snippet/date do not persist there | Separate `Suggested`, unapproved domain candidate linked to opportunity | Successful public-web results and report evidence are not durably committed |
| Ambiguous article/resource | URL + title | Static article mentions actors, auditions, roles, self tapes, but no actionable role/deadline | Currently `Theater Role` and normalized, because deterministic page-wide signals over-classify the article | A low parser value such as `55` does not itself route to review | Whatever `_create_opportunity` returns governs routing | Characterized current result is `visible`/`Accepted`, not hidden | Same pending-write behavior if processed with real DB | Bounded provider title/snippet/date can remain in the report but are not verified page evidence or durable metadata | A visible newly created false positive can suggest its domain | No direct-notice discriminator or medium-confidence review policy |
| Staff/crew listing | URL + optional title | Static staff-job text | `Non-Acting Job` or `Crew Job`; `_normalize_candidate` returns `None` | None | Not reached | Fetch-stage report remains `Rejected` with `Not an acting role` | No Opportunity or source suggestion | Bounded provider evidence remains in the run response only | None | Source-exclusion gate is not connected; rejection is recalculated on later runs |
| Expired notice | Normalized acting result with explicit past submission deadline | Supported text | Actor-facing classification may succeed | Not calculated/persisted because deadline rejects first | Not reached | `_process_public_web_search_result` reports `Rejected` / `Expired`; `deadline_expired=1` | No Opportunity or source suggestion | Bounded provider evidence can remain in the run response only | None | Past notices are not retained for audit/history |
| Same URL twice in one provider response | Two records differing only by fragment/title | Page fetched once after canonical URL dedupe | Depends on fetched page | One parsed candidate | Normal path | One candidate report | At most one Opportunity | First valid canonical result's bounded title/snippet/date survives in the report; later evidence and undocumented IDs are discarded | At most one suggestion | Dedupe is URL-only at this early stage and does not merge evidence |
| Same normalized identity in separate processing calls | Same project + role + location + host + relevant dates; URL can differ | Supported text | Acting | Existing Opportunity confidence remains | Existing eligibility remains | Existing visible row is counted as visible, but candidate report is overwritten to `Rejected` / `Duplicate` | One Opportunity; one SourceResearchItem | Existing metadata is neither merged nor replaced by later provider evidence | Source role-match count remains `1`, because suggestion update runs only when `was_created` | Duplicate reporting says rejected while result totals still count the existing row visible; no times-seen counter |
| One-off useful post | Exact public post URL | Supported static text | Acting | Parser-derived | Eligible | Can become `visible` without source approval | Pending Opportunity plus separate pending source suggestion | Exact post URL retained | Domain suggestion is `Suggested`, unapproved, inactive | Acceptance is operationally separated correctly, but the current transaction gap prevents durability |
| Hidden review | Parsed candidate whose created Opportunity is `hidden` | Supported | Usually acting with date/location uncertainty | Characterized report carries `68` | Existing services set hidden reason/rule | Result counts `hidden=1`, `rejected=1`; report is `Rejected`; raw rule `needs_date_review` survives rather than friendly copy | Opportunity is created in the open transaction | URL plus current Opportunity metadata | No suggestion because only visible newly created results suggest sources | No explicit medium-confidence route; hidden outcomes are labeled rejected in report |
| Travel exception | In-person candidate outside travel policy but otherwise retained | Supported | Acting | Characterized report carries `82` | Travel evaluator returns `travel_exception` | `travel_exceptions=1`, `rejected=0`; report still says `Rejected` / `Travel restriction` | Opportunity is created in open transaction | URL plus travel metadata when real evaluator runs | No suggestion | Aggregate and candidate decision semantics disagree |
| Discarded eligibility result | Parsed acting candidate with hard demographic/role/availability/travel failure | Supported | Acting | Characterized report carries `82` | Hard eligibility sets `discarded` and an exact `hidden_by_rule` | `discarded=1`, `rejected=1`; report currently exposes raw rule such as `dealbreaker_demographic_mismatch` | Opportunity is created in open transaction with discarded state | URL, reasons, and eligibility metadata | No suggestion | Public report reason is not consistently plain-language |

## Transaction and rollback contract

`backend/tests/contract_smoke/test_discovery_run_transactions.py` proves the registry-provider boundary:

- provider failure rolls back partial source writes;
- database failure rolls back Opportunity and child writes;
- exactly one failed `DiscoveryRun` is persisted when possible;
- commit-time failure retains the original error;
- failed-run persistence failure does not mask the original error;
- the same session remains usable;
- success commits once.

`backend/tests/contract_smoke/test_public_web_discovery_contract.py` proves the separate public-web boundary:

- a one-off Opportunity and source suggestion can be flushed and queried inside the session;
- there is no public-web `DiscoveryRun`;
- neither write is committed by `_process_public_web_search_result` or `run_all`;
- rollback removes both and the session remains usable;
- a repeated normalized identity reuses the Opportunity, does not merge evidence, does not increment source match count, and reports `Duplicate`.

## Existing coverage incorporated

- `backend/tests/test_public_web_search.py`: query shape, real documented response-object shape, URL dedupe, fetch/normalize behavior, empty/malformed responses, disabled configuration, current ambiguous/crew classification, and evidence reduction.
- `backend/tests/test_public_web_routing_contract.py`: exact visible/hidden/travel/discarded/duplicate report counters and reasons, expired pre-persistence rejection, and absence of a medium-confidence review rule.
- `backend/tests/test_discovery_modes.py`: mode, intent, visibility primitives, coverage honesty, and report aggregation.
- `backend/tests/test_discovery_role_source_separation.py`: direct-role versus repeat-source-card separation.
- `backend/tests/test_source_evidence.py`, `test_source_identity.py`, and `test_source_exclusion_architecture.py`: bounded evidence/identity contracts and intentionally dormant exclusion gate.
- `backend/tests/test_source_health_checks.py` and `test_source_research_cleanup.py`: repeat-source validation, lifecycle, and rejection/deletion behavior.
- `backend/tests/test_trust_verification_service.py`: protected-platform, role, travel, demo, and plain-language trust checks.

## Proven gaps and unreachable desired outcomes

1. **Durable public-web success is currently unreachable through the request path.** The separate Parallel path never commits and has no success/failure `DiscoveryRun`.
2. **Medium-confidence hidden review is not an explicit reachable policy.** A parser confidence of 55 can remain visible if other rules leave the Opportunity visible. Hidden is reachable through date/location/classification rules, not confidence alone.
3. **An ambiguous article can be normalized and accepted.** Page-wide deterministic signals do not establish an actionable direct role.
4. **Provider evidence is report-scoped rather than durable.** The result adapter now keeps bounded title/snippet/date evidence in the candidate report, but `_ensure_details` does not persist that evidence on the Opportunity and no successful public-web run record stores it.
5. **Duplicate evidence and sightings are not merged.** There is no times-seen update for public-web Opportunity duplicates, and the dormant source-exclusion system is not involved.
6. **Candidate decisions and aggregates are semantically inconsistent.** Hidden and travel-exception candidates are labeled `Rejected`; a duplicate existing visible Opportunity still increments visible while its report is rejected.
7. **Union compatibility is not an eligibility rule.** It influences quality scoring; query targeting and future policy must define the intended behavior before changing it.

These gaps are evidence for later tasks. Task 1 intentionally makes no production change.
