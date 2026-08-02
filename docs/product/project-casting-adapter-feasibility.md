# Project Casting Read-Only Adapter Feasibility

Date: 2026-08-02

Branch: `feature/full-discovery-capabilities`

## 1. Executive verdict

**Verdict: not feasible under the current public-fetch and permission evidence. Recommendation: seek permission, then defer implementation until a bounded index contract is proven.**

- **Confirmed by inspected public material:** `https://projectcasting.com/jobs/` exceeds the existing 500,000-byte safe-response ceiling. The repository fetcher returns `response_too_large` and retains no body.
- **Confirmed by inspected public material:** `https://projectcasting.com/robots.txt` allows the base public jobs path but disallows administrative/login paths and several query/filter patterns, including jobs queries with additional parameters.
- **Confirmed by inspected public material:** the published terms URL is `https://projectcasting.com/terms-of-use`, but the repository safe fetcher classifies its response as `captcha_access_denied`; its substantive terms could not be reviewed.
- **Requires permission or further verification:** recurring automated retrieval, permitted reuse of listing content, a stable bounded listing feed, and individual-page field availability.

Technical reachability does not establish permission. No adapter should be implemented or registered from this audit.

## 2. Existing operational architecture

`backend/app/automation/discovery/contracts.py::DiscoveryProvider` defines `discover`, `normalize`, `validate`, `deduplicate`, and `health_check`. Task 12 adds `operational_adapter`; a provider does not participate merely because it is registered.

`backend/app/automation/discovery/public_sources.py::PublicPlaybillJobsSource` is the only current operational registry adapter. `backend/app/automation/discovery/providers.py::build_discovery_providers` registers it alongside placeholder, supervised-platform, social, casting-site, casting-office, and film-commission declarations. Project Casting currently uses `PublicCastingSiteProvider`, which inherits the empty `PlaceholderDiscoveryProvider` behavior and is not operational.

`backend/app/automation/discovery/service.py::DiscoveryAutomationService.run_all` admits only enabled, approved, mode-eligible, operational, health-eligible providers. `run_source` owns one provider transaction and normalization flow; it persists a successful or failed `DiscoveryRun`. Task 12 reports operational availability, attempts, successful checks, returned candidates, and Parallel hits separately. Film/TV mode eligibility is determined by `_source_supports_mode/_source_family`, followed by item-level `_matches_mode`.

Source approval remains separate from implementation. `backend/app/services/source_research_service.py::SourceResearchService` can maintain suggested or approved research records, but an approved record does not create an adapter. `backend/app/services/source_identity.py::SourceIdentityService` supports source-scoped external IDs or canonical URL hashes; title/full-text identity is not required or preferred.

## 3. Public-access findings

| Surface | Result | Conclusion |
|---|---|---|
| `https://projectcasting.com/jobs/` | `response_too_large` under `PublicContentFetcher` | **Confirmed:** the current fetch contract cannot read the index. No index HTML, listing links, filters, or ordering were retained or inspected. |
| `https://projectcasting.com/robots.txt` | Public text, 604 characters | **Confirmed:** the base jobs path is not disallowed; administrative/login paths and specified query/filter patterns are disallowed. |
| `https://projectcasting.com/terms-of-use` | `captcha_access_denied` under `PublicContentFetcher` | **Confirmed:** substantive terms were not accessible through the permitted static policy. |
| Individual listing pages | Not requested | **Requires further verification:** no listing URL was safely discovered from the bounded index response. |

No login, cookie, account session, API key, form submission, browser automation, CAPTCHA bypass, pagination, or recursive crawl was used. Important listing fields and submission authentication requirements therefore remain unverified.

## 4. Terms and robots findings

The inspected robots file contains `User-Agent: *`, disallows WordPress administration/login/register and internal asset/cache paths, disallows several pagination/age-filter query forms, disallows `/jobs?*&`, and publishes a sitemap URL. It does not disallow the base `/jobs` path.

This is **confirmed technical crawl guidance**, not confirmed permission to copy, retain, or repeatedly retrieve listings. The terms page could not be reviewed because the permitted fetch policy detected an access challenge. Automated recurring access and content reuse are therefore **ambiguous/unverified**. This audit makes no legal conclusion. Permission should be obtained or the published terms should become reviewable before implementation.

## 5. Technical fetch compatibility

The existing static fetcher is **not sufficient for the jobs index** because it correctly rejects responses over 500,000 bytes. Raising the global limit is out of scope and would weaken an established safety boundary. The robots page is compatible. The terms page triggers an access-control outcome that must not be bypassed.

JavaScript requirements, JSON-LD availability, embedded structured data, and stable visible HTML remain **unverified**. No source-specific partial response extraction, browser rendering, authenticated fetch, or alternative transport is approved.

## 6. Listing-index behavior

The audit cannot confirm listing link structure, publication ordering, category filters, pagination, or a Film/TV-only public feed because the one permitted index response was too large and discarded. Robots directives show that some jobs query forms are explicitly disallowed, which makes a filter-query discovery strategy unsuitable without permission.

A bounded adapter cannot be designed from page size and URL guesses alone. A documented feed, sitemap subset, API, or permission-backed bounded index endpoint is an implementation blocker.

## 7. Individual-page behavior and public fields

No individual page was requested because no canonical listing URL was safely obtained from the bounded index inspection. The following fields are therefore all **requires further verification**: project/listing title, role names, age, gender, ethnicity, union, location, audition mode, submission instructions, deadline, shoot dates, compensation, production type, and casting-company/source identity.

The audit does not claim that fields seen in search-engine snippets, Parallel evidence, or marketing copy exist on a stable public listing page. Login-gated submission behavior and whether important fields are hidden until authentication are likewise unverified.

## 8. Stable source identity

**Provisional recommendation, requiring verification:** use a canonical individual listing URL as the primary source identity, normalized through `SourceIdentityService` with a Project Casting-specific URL policy. A documented stable listing ID may be preferable if public pages expose one consistently.

Do not use index position, full text, account identifiers, or title alone. Publication date plus normalized title is too collision-prone except as bounded supporting version evidence. Repeat-sighting, update, expiry, redirect, and removal behavior cannot be confirmed without a permitted individual-page sample.

## 9. Proposed bounded discovery contract

No executable contract is approved. If permission and a bounded public index are later established, the maximum candidate design should be:

- one index/feed request per run;
- no pagination by default;
- at most 20 canonical listing identities read from that response;
- at most 10 individual listing fetches per run;
- the existing 500,000-byte response, 12,000-character visible-text, four-redirect, and 12-second timeout policies;
- a documented maximum listing age, with 30 days as a proposal requiring source evidence;
- deterministic newest-first ordering only if the source proves it;
- no login, cookies, application requests, browser rendering, or access-control bypass.

These are **design bounds, not evidence that the source supports them**.

## 10. Proposed extraction map

Because public listing pages were not inspected, every mapping remains conditional:

| Field | Source location | Requirement | Destination | Bound | Ambiguity behavior |
|---|---|---|---|---:|---|
| Canonical URL | Canonical link or final safe URL | Required | `original_post_url` and source identity | 1,000 | Reject if no safe canonical identity |
| Listing/project title | Visible heading or documented structured data | Required | `project` | 255 | Review; never infer from directory position |
| Role name(s) | Visible role section | Required for direct notice | `role` / `role_details` | 120 each | Multi-role single production may remain one direct notice; unrelated cards are an index |
| Production type | Explicit visible/structured value | Optional | `production_details.project_type` | 120 | Unknown when absent |
| Location | Explicit visible/structured value | Optional | `location` / shoot/audition fields | 255 | Unknown when absent |
| Demographics and age | Explicit role requirements | Optional | `role_details` | Existing bounded detail fields | Never infer |
| Union | Explicit listing value | Optional | `union` | 120 | Unknown when absent |
| Audition mode | Explicit instructions | Optional | `audition_type` | 120 | Unknown when absent |
| Deadline | Explicit submission/audition date | Optional | deadline fields | ISO date after deterministic parsing | Hidden review when missing/ambiguous |
| Shoot dates | Explicit production dates | Optional | `production_details` | Existing date bounds | Unknown when absent |
| Compensation | Explicit rate/paid status | Optional | production/role details | Existing bounded text | Unknown when absent |
| Submission method | Public, non-credential instructions | Optional | bounded source metadata/details | 500 | Never follow or submit automatically |
| Casting/source identity | Explicit organization label | Optional | bounded source metadata | 255 | Unknown when absent |

No extraction may invent union, compensation, demographics, deadline, location, or application method.

## 11. Page-kind risks

The oversized jobs page is structurally a `multi_listing_index`, not one Opportunity. Existing Task 10 classification would protect role-level eligibility only after bounded visible text is available; here the fetch rejects before classification. Direct listings, modeling/content-creator work, crew/staff employment, articles, expired posts, and syndicated duplicates remain **requires fixture or permitted sample verification**.

A future adapter must classify the index separately, fetch only bounded canonical listing pages, then require `direct_opportunity` before normalization. It must preserve hard crew/non-acting and expiry handling.

## 12. Authentication, privacy, and credential boundary

The adapter may read only public, statically accessible pages. It must not store or use actor credentials, cookies, account sessions, contact data, profile dimensions, or application tokens. It must never submit or apply. Login-gated details are unavailable, not an invitation to automate authentication.

## 13. Expected value over Parallel

Potential value is a **strong inference**, not confirmed: a permitted source-specific index could reduce broad-directory noise and yield stable individual Project Casting URLs more reliably than Parallel. It could also retrieve page fields omitted from provider snippets.

Actual value is unproven because this audit could not safely inspect one listing. Recall, Film/TV relevance, detail completeness, duplicate rate, expiry quality, maintenance burden, and overlap with the actor's manual workflow remain unknown. Current evidence does not justify implementation cost.

## 14. Maintenance and breakage risks

- Oversized index and potential client-rendered content.
- Access challenge on the terms surface.
- Ambiguous automated-access permission.
- Possible HTML/JSON-LD changes without a documented API contract.
- Mixed acting, modeling, creator, staff, expired, and syndicated content.
- Query/filter paths constrained by published robots directives.
- Unknown canonical URL and update/removal stability.
- Ongoing fixture and source-health maintenance for one third-party site.

## 15. Required tests before any implementation

If blockers are resolved, characterize sanitized, permission-compatible fixtures for: bounded index links and ordering; canonical identity and tracking removal; direct/multi-listing/resource page kinds; single- and multi-role productions; Film/TV versus modeling/creator/crew content; optional fields; missing/ambiguous deadline; expiry; duplicate and update behavior; oversized/protected responses; health failure; zero results; transaction rollback; Task 12 attempt/success/hit accounting; and zero credential/cookie/form behavior.

## 16. Explicit implementation blockers

1. Published terms could not be reviewed through the permitted access path.
2. Recurring automated retrieval and content reuse are not confirmed as permitted.
3. The jobs index exceeds the existing safe response limit.
4. No bounded public Film/TV feed or index endpoint is proven.
5. No individual listing URL or field contract was safely inspected.
6. Stable identity, update, expiry, and removal behavior are unverified.
7. Static-versus-client-rendered detail availability is unverified.

## 17. Recommendation

**Seek permission, then defer.** Ask Project Casting for a documented public feed/API or written permission for bounded read-only retrieval and clarify permitted retention of listing facts and canonical URLs. Re-run a separately authorized audit against one bounded index/feed and at most three individual pages only after that. If permission or a bounded endpoint is unavailable, reject the adapter and continue using Parallel plus user-supervised/manual source workflows.

No conditional implementation plan is created because the current verdict is `not feasible`.
