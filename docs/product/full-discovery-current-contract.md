# Full Discovery: Current Public-Web Contract

Date: 2026-08-02

Branch: `feature/full-discovery-capabilities`

This document characterizes current behavior. It is not the desired routing policy. All external inputs in the tests are synthetic and all network/provider calls are mocked.

## Request-to-persistence flow

1. `frontend/src/features/breakdowns/components/BreakdownDiscovery.tsx::AutomationDashboard.runDiscovery` invokes `useBreakdownDiscovery.run`; `frontend/src/features/breakdowns/api/index.ts::runBreakdownDiscovery` sends `POST /automation/discovery/run`.
2. `backend/app/api/v1/routes/automation.py::run_discovery` calls `backend/app/automation/discovery/service.py::DiscoveryAutomationService.run_all`.
3. After enabled registry plugins, `run_all` calls `_run_public_web_search`. That constructs `backend/app/automation/discovery/public_web_search.py::PublicWebBreakdownSearch` with the first `ActorProfile` and calls `search("FilmTV")` only when Parallel is configured.
4. `PublicWebBreakdownSearch.search` sends bounded queries, then `_extract_candidate_records` recursively extracts and deduplicates canonical URL plus optional title. It discards provider excerpt, ID, ranking, and other response evidence.
5. `_fetch_visible_text` fetches static HTML/plain content. `_normalize_candidate` runs `automation/discovery/classification.py::classify_breakdown_text`, rejects `Non-Acting Job`, `Crew Job`, and `Unknown`, and delegates field parsing to `services/breakdown_details_service.py::BreakdownDetailsService.from_fields`.
6. `DiscoveryAutomationService._process_public_web_search_result` applies `_matches_mode`, `_matches_search_intent`, and `BreakdownDeadlineService.validate_normalized`, then calls `_create_opportunity`.
7. `_create_opportunity` detects duplicates by `_key`: normalized project + role + location + source host + selected dates. It does not use the full URL as the identity. It assigns initial status through `_visibility`, deep-parses through `BreakdownIntelligenceEngine.run_for_opportunity`, applies deadline state, synchronizes roles/watchlists, then runs `OpportunityIntelligenceService.enrich` and `TrustVerificationService.verify`.
8. `OpportunityIntelligenceService` applies audition visibility/travel, `DemographicMatchService`, excluded-role and demographic/availability/travel eligibility, scoring, confidence, and risk. Union affects quality scoring but is not a hard eligibility rule. Language is evaluated when detected in parsed text. Self-tape sets travel time to zero.
9. A newly visible public-web opportunity causes `_suggest_source_from_public_breakdown` to create or update a separate `SourceResearchItem`. A new source remains `Suggested`, `approved_by_user=False`, with no `approved_discovery_url`; individual opportunity acceptance does not approve monitoring.
10. Registry `run_source` owns a transaction: it flushes a `DiscoveryRun`, commits success, rolls back partial writes on any error, and persists one failed run from a clean transaction. The separate public-web path has no `DiscoveryRun`, `commit`, or exception rollback boundary. `get_db` only closes the session. Therefore public-web Opportunity and source-suggestion writes remain transaction-pending and are rolled back at request close. This is a confirmed current gap, not corrected in Task 1.

## Current-behavior fixture matrix

| Input category | Provider-result shape | Fetch result | Classification | Confidence | Eligibility | Routing/report | Persisted records | Evidence retained | Source-research effect | Known gap |
|---|---|---|---|---|---|---|---|---|---|---|
| Direct eligible acting notice | URL + title; duplicate fragments canonicalized | Static public text with project, supporting role, SAG-AFTRA, Black woman 25–40, English, self-tape, future deadline | `Acting Role` | Deep-parser value is copied into the run candidate report; fixture routing uses `82` | Configured actor yields `demographic_match_status="Match"`; self-tape travel is zero; union is score-only | Opportunity is `visible`; report is `Accepted` | Opportunity, role/parse children, source, and source suggestion exist only in the open request transaction; no `DiscoveryRun`; request-close rollback removes them | Canonical `original_post_url` and regenerated `source_url`; incoming `provider`, `page_title`, and excerpt do not survive `_ensure_details` in the characterized incomplete-details fixture | Separate `Suggested`, unapproved domain candidate linked to opportunity | Successful public-web results are not durably committed |
| Ambiguous article/resource | URL + title | Static article mentions actors, auditions, roles, self tapes, but no actionable role/deadline | Currently `Theater Role` and normalized, because deterministic page-wide signals over-classify the article | A low parser value such as `55` does not itself route to review | Whatever `_create_opportunity` returns governs routing | Characterized current result is `visible`/`Accepted`, not hidden | Same pending-write behavior if processed with real DB | URL survives; provider excerpt/ID absent | A visible newly created false positive can suggest its domain | No direct-notice discriminator or medium-confidence review policy |
| Staff/crew listing | URL + optional title | Static staff-job text | `Non-Acting Job` or `Crew Job`; `_normalize_candidate` returns `None` | None | Not reached | Fetch-stage report remains `Rejected` with `Not an acting role` | No Opportunity or source suggestion | Candidate URL/title only in run response | None | Source-exclusion gate is not connected; rejection is recalculated on later runs |
| Expired notice | Normalized acting result with explicit past submission deadline | Supported text | Actor-facing classification may succeed | Not calculated/persisted because deadline rejects first | Not reached | `_process_public_web_search_result` reports `Rejected` / `Expired`; `deadline_expired=1` | No Opportunity or source suggestion | Candidate URL/title in run response | None | Past notices are not retained for audit/history |
| Same URL twice in one provider response | Two records differing only by fragment/title | Page fetched once after canonical URL dedupe | Depends on fetched page | One parsed candidate | Normal path | One candidate report | At most one Opportunity | First URL/title survives the result adapter; second title and all excerpts/IDs are discarded | At most one suggestion | Dedupe is URL-only at this early stage and merges no evidence |
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
4. **Provider evidence does not survive end to end.** The result adapter keeps only URL/title, and `_ensure_details` can replace even provider/title metadata while regenerating source URL.
5. **Duplicate evidence and sightings are not merged.** There is no times-seen update for public-web Opportunity duplicates, and the dormant source-exclusion system is not involved.
6. **Candidate decisions and aggregates are semantically inconsistent.** Hidden and travel-exception candidates are labeled `Rejected`; a duplicate existing visible Opportunity still increments visible while its report is rejected.
7. **Union compatibility is not an eligibility rule.** It influences quality scoring; query targeting and future policy must define the intended behavior before changing it.

These gaps are evidence for later tasks. Task 1 intentionally makes no production change.
