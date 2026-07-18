# Breakdowns architecture decision ledger

This ledger records evidence and decisions specific to the Breakdowns feature. It is not a general frontend architecture guide.

## 1. Feature ownership

Breakdowns owns visible opportunities, hidden/travel-exception opportunities, recommendations, discovery plugins, the submission queue, audition readiness, material matches, and the discovery report. TanStack Query is the server-state owner. Presentation components must not copy opportunity records into local state except as form-draft initial values.

Breakdowns consumes only public boundaries from Profile, Materials, Source Library, and shared system infrastructure. Auditions, Calendar, Dashboard, Journal, Materials, Relationships, and Career may consume public Breakdowns hooks or public invalidation keys; they must not import Breakdowns internals.

## 2. Public query boundaries

The route composes queries in `components/BreakdownsPanel.tsx`. Query keys and policies live in `hooks/useBreakdownQueries.ts` and the shared query-key/policy registries. The existing public hooks and keys are stable decomposition constraints.

The public barrel currently exposes `BreakdownsPanel`, selected legacy presentation exports, the feature API, query hooks, discovery controllers, and types. New route-only presentation such as `SubmissionQueuePanel` must remain private. Decomposition does not justify expanding the public barrel.

## 3. Mutation ownership

All Breakdowns network mutations are defined in `api/index.ts` and wrapped by `hooks/useBreakdownQueries.ts`.

The hidden-review mutation set is:

| User action | API function | Hook | Response |
| --- | --- | --- | --- |
| Complete fields / update travel / append role data | `updateBreakdown` (`PATCH /opportunities/{id}`) | `useUpdateBreakdown` | Updated `Opportunity` |
| Paste actual text | `parseBreakdownText` (`POST /opportunities/{id}/parse-breakdown-text`) | `useParseBreakdownText` | Updated `Opportunity` |
| Deep parse | `deepParseBreakdown` (`POST /opportunities/{id}/deep-parse`) | `useDeepParseBreakdown` | Updated `Opportunity` |
| Approve/promote | `approveActingBreakdown` (`POST /opportunities/{id}/approve-acting-breakdown`) | `useApproveBreakdown` | Updated `Opportunity` |
| Hard delete from hidden review | `deleteBreakdown` (`DELETE /opportunities/{id}`) | `useDeleteBreakdown` | No content (`204`) |
| Reject/archive | `rejectBreakdown` (`POST /opportunities/{id}/reject`) | `useRejectBreakdown` | Updated `Opportunity` |
| Refresh demographic match | `refreshDemographicCheck` (`POST /opportunities/{id}/demographic-check`) | `useRefreshDemographicCheck` | Updated `Opportunity` |

The current hidden-review UI uses hard delete, not the reject/archive endpoint. It displays demographic status but does not expose demographic refresh. Source approval/editing belongs to the discovery/source-research area, not hidden review.

## 4. Backend side-effect summary

All effects below are synchronous in the current backend; none of these endpoints starts a background job.

- `PATCH /opportunities/{id}` applies supplied fields, may parse a changed description, reapplies deadline and eligibility/intelligence classification, synchronizes breakdown roles, verifies trust, writes manual-override logs, and may create or update an opportunity-owned self-tape workflow.
- Manual paste reparses and replaces description, reapplies deadline/intelligence/trust, synchronizes parsed records, and may create or update an opportunity-owned self-tape workflow.
- Deep parse rebuilds parse details/roles/character intelligence, reapplies deadline/intelligence/trust, and does not currently call the self-tape workflow helper.
- Approve forces Acting Role + visible, clears review fields, enriches intelligence, verifies trust, ensures a self-tape workflow when applicable, creates an accepted-breakdown Actor Journal work event, and writes override logs.
- Reject marks the opportunity discarded/archived and records the manual override. It does not hard-delete related rows.
- Hard delete deletes the authoritative opportunity. Database foreign keys cascade submissions, recommendations, queue rows, self-tape workflows, and several intelligence records; some Journal/Calendar/source links use `SET NULL`.
- Demographic refresh applies demographic matching and commits the changed opportunity. Eligibility/intelligence code may change classification/visibility when invoked by update/parse flows.

No hidden-review action directly generates a recommendation or submission. Readiness, material matches, analytics, Calendar projections, command center, Journal, and Auditions can nevertheless change as derived reads or synchronous related records.

## 5. Invalidation contracts

Current direct classification invalidation for update, parse, deep parse, reject, and demographic refresh covers visible opportunities, hidden opportunities, readiness, material matches, intelligence analytics, and industry trends. Approve additionally invalidates workflow self-tapes, Calendar, Journal, command center, and operations analytics. Delete additionally invalidates recommendations.

### Confirmed gap (Step 50)

The backend proves two cases not fully represented by current frontend invalidation:

1. Update and manual paste can create or update `SelfTapeWorkflow`, but their hooks do not invalidate workflow self-tapes or consumers derived from that record.
2. Hard delete can cascade submissions, self-tape workflows, recommendations, queue/intelligence rows and null linked references, but its hook invalidates only Breakdowns classification/aggregates and recommendations.

This gap must be corrected and characterized before moving mutation ownership into a hidden-review controller. Step 50 intentionally does not change invalidation contracts.

### Step 51A correction and new backend defect

Step 51A added typed `opportunity.update`, `opportunity.manualParse`, and `opportunity.delete` contracts and made the three canonical mutation hooks consume them through background invalidation. Update and manual parse now invalidate visible/hidden opportunities, readiness, material matches, Auditions-owned workflow self-tapes, operational/intelligence/industry Analytics, and command center. They explicitly forbid submissions, callbacks, audition notes, persisted Calendar rows, actor Journal, recommendations, queue, relationships, Materials assets/reusable tapes, and material-performance Analytics.

Successful hard delete for an opportunity without linked submissions invalidates visible/hidden opportunities, readiness, material matches, recommendations, queue, workflow self-tapes, callbacks, audition notes, persisted Calendar links, actor Journal links, relationships, reusable self-tape links, all four affected Analytics reads, and command center. Materials assets and Career data are forbidden.

Disposable PostgreSQL characterization disproved the assumption that linked submissions currently cascade successfully through `OpportunityService.delete`: SQLAlchemy attempts to set `submissions.opportunity_id` to null even though the column is non-null, producing `NotNullViolation` before PostgreSQL `ON DELETE CASCADE` can complete. The failed mutation commits no deletion, so `submissions` is forbidden from the successful frontend delete contract rather than receiving compensating invalidation. This is a backend correctness defect and keeps the extraction gate blocked.

## 6. Component map

- `BreakdownsPanel` is the route query/composition layer.
- `BreakdownManager` owns the visible opportunity list and embedded create/edit/parse/reject/role forms.
- `MergedAuditionReadinessPanel` owns readiness, material selection, strategy, and feedback presentation.
- `AutomationDashboard` currently owns discovery execution, source suggestions, hidden review composition, and the route-private queue child.
- `SubmissionQueuePanel` was extracted in Step 49. It owns the existing queue action controller and receives four explicit domain-array props.
- The proposed hidden-review boundary currently spans the list block, `HiddenBreakdownDetailsDrawer`, and `HiddenBreakdownActionForm` inside `BreakdownDiscovery.tsx`.
- `BreakdownDetails.tsx` contains shared Breakdowns renderers/selectors. It is explicitly out of scope until a later decision.

The proposed hidden-review child needs one server-data prop (`hiddenOpportunities`). It can own the approve, delete, update, parse, and deep-parse hooks directly. It does not need plugins, recommendations, queue items, visible opportunities, source-research records, capabilities, discovery status, search intent, provider state, or source-expansion callbacks.

## 7. Local-state ownership

| State | Current owner | Narrow owner | Classification and lifecycle |
| --- | --- | --- | --- |
| `hiddenAdminOpen` | `AutomationDashboard` | Hidden-review workspace | Disclosure state; resets on unmount |
| `selectedHiddenOpportunity` | `AutomationDashboard` | Hidden-review workspace | Selection currently stores a server-record snapshot; replace with selected ID and derive from query props so refetches remain current |
| `hiddenAction` | `AutomationDashboard` | Hidden-review workspace | Action kind + opportunity snapshot; replace with action kind + opportunity ID |
| Completion form | `HiddenBreakdownActionForm` | Same extracted form | Draft; initialize when form opens, preserve on mutation failure, reset only on cancel/success/unmount |
| Travel form | `HiddenBreakdownActionForm` | Same extracted form | Draft with the same preservation/reset rules |
| Paste text | `HiddenBreakdownActionForm` | Same extracted form | Draft with the same preservation/reset rules |
| Manual-role draft | `HiddenBreakdownActionForm` | Same extracted form | Draft with the same preservation/reset rules |
| `saving` / form `error` | `HiddenBreakdownActionForm` | Same extracted form or focused controller | Transient presentation state; section-owned and independent from discovery |
| Approve/delete/deep-parse pending/error | Mutation objects in parent, with little explicit UI | Hidden-review controller/workspace | Must become independently visible/disabled without a route-wide error |
| Parse result | Query-invalidated opportunity | TanStack Query | Server state; never copy into local state |
| Demographic state | Opportunity query | TanStack Query | Server state; current hidden UI is display-only |
| Discovery run/report/search/provider/source expansion | `AutomationDashboard` | Discovery workspace | Unrelated; must not move into hidden review |

## 8. Route-private versus public exports

`SubmissionQueuePanel` and the future hidden-review workspace are route-private implementation details. They must not be exported from `features/breakdowns/index.ts`. The public query hooks and types remain unchanged. No child may import a base API client or another feature's internal modules.

## 9. Confirmed product behavior

- The hidden list contains non-demo `hidden` and `travel_exception` records, excluding hard deal-breaker/debug-only cases under the normal endpoint mode.
- Selecting a record reveals classification, demographic, travel, source, raw text, parsed facts, production details, role details, and the Breakdown Viewer.
- Complete and Travel Info are edits, not guaranteed promotion commands. Backend eligibility/intelligence decides resulting visibility.
- Approve anyway is the explicit forced promotion action and records accepted work in Journal.
- Delete / Reject in this workspace currently performs a hard delete despite its mixed label.
- Paste reparses actual text. Manual role appends to `role_details.available_roles`, then runs deep parse.
- Cached visible and hidden lists update through focused invalidation; a failure in hidden review must not hide discovery or queue sections.
- There is no navigation side effect in hidden review. Source links open in a new tab.

## 10. Rejected assumptions

- Visual grouping alone does not prove an extraction boundary; endpoint and side-effect tracing was required.
- “Complete” does not itself mean approve/promote.
- “Delete / Reject” does not call the reject endpoint; it hard-deletes.
- A selected `Opportunity` object is not harmless UI state; it can become a stale server snapshot after invalidation.
- Manual role entry is not a dedicated role endpoint; it is an opportunity patch followed by deep parse.
- Demographic refresh and source approval are not currently part of the hidden-review interaction surface.
- Existing classification-key invalidation is not sufficient for every backend side effect.
- Extracting JSX alone would not resolve mutation ownership, pending/error behavior, or stale selected-record state.

## 11. Open product/API questions

- Should hidden review expose Reject/Archive as its own control alongside protected permanent Delete? Step 51C keeps the backend operations separate and does not add that product surface.
- Should Complete explicitly promote after required data is entered, or continue relying on eligibility reclassification?
- Should hidden review expose demographic refresh, or remain display-only?
- Should manual role creation eventually use a typed dedicated role endpoint instead of patching `role_details`?
- Should mutation responses or backend contracts expose an explicit list of synchronous affected resources?

These questions do not require backend changes for the preparatory invalidation correction, but changing their product behavior would require a separate decision.

## 12. Decomposition history

- **Step 49:** extracted route-private `SubmissionQueuePanel`. It owns `useSubmissionQueueActions`, receives four explicit domain props, and leaves query keys, policies, invalidation, APIs, and public exports unchanged.
- **Step 50:** audited hidden review. The UI/state boundary is coherent and can be narrow, but backend-side-effect invalidation gaps make immediate extraction unsafe. Decision: **B — one prerequisite correction first**.
- **Step 51A:** corrected and characterized update/manual-parse/successful-delete invalidation. PostgreSQL contract tests prove update creates then reuses one workflow self-tape without writing Journal or persisted Calendar rows; manual parse replaces text, records parse output, reuses the workflow, and also leaves Journal/Calendar unchanged; successful unlinked delete cascades owned workflow/queue/recommendation records and nulls historical Calendar/Journal/audition-note/reusable-tape links.
- **Step 51C:** selected **B — protected deletion**. Submissions are user-created audition history used by Analytics, Career, Journal, Relationships, Command Center, Calendar, materials performance, readiness, and callback tracking. The existing hidden-review confirmation did not disclose that history could be destroyed, while submission deletion is already an independent explicit operation. The rejected alternative was cascading submission history merely because the old foreign key declared `ON DELETE CASCADE`. The service now checks for linked submissions and returns HTTP 409 with `{detail: {code: "opportunity_has_submissions", message: ...}}` before any delete. The ORM uses `passive_deletes` and migration 0054 changes the database foreign key to `ON DELETE RESTRICT`, so service, ORM, and schema agree. A rejected delete retains the opportunity, all submissions and all related records, is retry-safe, and invalidates no cache. Unlinked deletion retains the Step 51A success contract. The hidden review preserves selection and shows the backend message in an accessible local alert; its confirmation distinguishes permanent Delete from the separate Reject/Archive operation. Disposable PostgreSQL tests cover two linked submissions, workflow/queue/recommendation records, retained Journal/Calendar state, repeated failure, response shape, and separate rejection. Gate status: **APPROVED**.
- **Step 51D:** extracted the route-private hidden-review workspace into `HiddenOpportunityReview.tsx` and `HiddenOpportunityActionForm.tsx`. Its complete prop contract is `hiddenOpportunities: Opportunity[]`; it owns disclosure, ID-based selection/action state, local drafts and feedback, and the canonical update/manual-parse/deep-parse/approve/delete hooks. `BreakdownDiscovery` now only composes it and retains discovery/report/provider/source-expansion/skipped-source state. The existing hidden query, query keys, freshness, Step 51A invalidation, and Step 51C protected-delete contract are unchanged. Selection and active actions derive current records by ID, disappear when the authoritative prop no longer contains the record, preserve context on protected failure, and reset action drafts only on cancel/success. New component and static tests cover empty/list/disclosure, current-record derivation, mutation ownership, protected failure, draft preservation, success reset, privacy, no duplicate query, and no discovery-state leakage. Mocked browser coverage adds update/workflow projection without persisted Calendar writes or broad requests plus parse-draft failure. Confirmed assumptions: one prop is sufficient; discovery state is unrelated; canonical hooks can move without wrappers. Disproven assumption: the old full-record selection was safe across refetches. Remaining debt: a dedicated Reject/Archive control is still a separate product question, and detail rendering remains shared in `BreakdownDetails.tsx`. The next major candidate requires a new check-in and preflight; `BreakdownManager` is not approved by this extraction.

## 13. Next approved extraction

The hidden-review workspace gate was **APPROVED** by Step 51C and the extraction was completed in Step 51D.

Hidden-review extraction gate: **APPROVED — COMPLETED IN STEP 51D**.

## 15. Step 52 — BreakdownManager preflight

### Current responsibility map

`BreakdownManager.tsx` is 698 lines. Approximately 45 lines define route inputs and local state, 195 lines implement the create/edit form model and payload conversion, 55 lines render filters and the form shell, 255 lines render/expand opportunity cards and detail disclosures, 60 lines own reject/archive UI, and 68 lines own manual-role UI. It consumes authoritative visible and hidden opportunities plus representations by prop; it does not own a query.

| Responsibility | State / records | Mutations | Current feedback and coordination |
| --- | --- | --- | --- |
| List/filter/expansion | `breakdownFilter`, `expandedBreakdowns`; visible and hidden opportunity props | none | Parent-owned; filter and disclosure buttons are accessible, no sorting exists |
| Create/edit form | `formOpen`, `editingBreakdownId`, 32-field `form`; representations and selected opportunity | create, update | Same controlled schema and payload mapper; resets only after success, so drafts survive rejection, but mutation errors are not rendered and submit has no pending disable |
| Paste/manual parse | `pasteOpenById`, `pasteTextById`; opportunity | manual parse | Per-ID drafts survive failure because reset follows success; errors/pending are not locally rendered |
| Deep parse | opportunity | deep parse | Entry points in role fallback and viewer; no local pending/error presentation |
| Manual role | `addingRoleForBreakdown` currently stores a full opportunity snapshot; role draft inside child form | update | Local pending/error and failure preservation; closes on success |
| Reject/archive | `rejectingBreakdown` currently stores a full opportunity snapshot; rejection draft inside child form | reject | Local pending/error and failure preservation; closes on success |
| Strategy/demographic | opportunity | recommendation generation, demographic refresh | Inline actions; pending/error presentation is absent |
| Delete | none | none | Despite the text “Delete / reject,” this component calls only the reject/archive endpoint; Step 51C hard-delete behavior is not reachable here |

### Local-state ownership map

| State | Classification | Ideal owner / lifecycle |
| --- | --- | --- |
| `formOpen` | dialog state | Create/edit workspace mode; parent may retain a narrow mode signal because Add and Edit entry points live in separate parent regions |
| `editingBreakdownId` | list-to-dialog selection | ID-based parent/workspace contract; derive the current record from `opportunities`, never store the record |
| `breakdownFilter` | list filter | Remain in manager/list workspace; resets on unmount |
| `pasteOpenById` | parsing disclosure state | Future parsing/role workspace; independent per opportunity |
| `pasteTextById` | paste drafts | Future parsing/role workspace; reset only after successful parse/cancel |
| `expandedBreakdowns` | list disclosure state | Remain with list; independent per opportunity |
| `rejectingBreakdown` | copied server record | Replace with ID before or during its own bounded action extraction; derive from current props |
| `addingRoleForBreakdown` | copied server record | Replace with ID before or during its own bounded action extraction; derive from current props |
| `form` | intentional editable snapshot | Move with create/edit workspace; initialize on mode change, preserve on failure, reset on cancel/success |
| `visibleBreakdowns` | derived value | Remain with list/filter owner; never copy to state |

No other workflow reads the form draft. Create and edit share all controlled fields, normalization, null handling, date conversion, enum mapping, travel/source/role metadata, and one submit/reset lifecycle. Create uses client defaults; edit snapshots server values into the same controlled schema. That snapshot is intentional form state, unlike the two full-record action states.

### Mutation and backend map

| Action | Endpoint | Direct change | Synchronous side effects | Current public invalidation |
| --- | --- | --- | --- | --- |
| Create | `POST /opportunities` | New opportunity, classification and parsed detail | Deep parse, deadline, conditional roles, intelligence, trust, conditional workflow self-tape, Accepted Breakdown Journal entry, persisted Calendar row when dated | Typed `opportunity.create` contract |
| Update/edit and manual role | `PATCH /opportunities/{id}` | Opportunity and manual-override log | Reparse when description changes, deadline/roles/intelligence/trust, optional workflow self-tape | Typed `opportunity.update`; Journal, persisted Calendar, submissions, recommendations and queue forbidden |
| Paste/manual parse | `POST /opportunities/{id}/parse-breakdown-text` | Description and parse output | Deadline/intelligence/trust, optional workflow self-tape | Typed `opportunity.manualParse`; no Journal or persisted Calendar write |
| Deep parse | `POST /opportunities/{id}/deep-parse` | Parse output, roles, classification/intelligence/trust | No accepted-work Journal event and no explicit workflow-tape synchronization | Classification/list/material/readiness and analytics keys |
| Reject/archive | `POST /opportunities/{id}/reject` | Visibility `discarded`, status `archived`, rejection metadata and override log | Trust verification only | Classification/list/material/readiness and analytics keys |
| Hard delete | `DELETE /opportunities/{id}` | Not rendered by this component | Step 51C protected/unlinked contract | Typed `opportunity.delete`, success-only |
| Strategy | `POST /opportunities/{id}/recommend` | Recommendation | Deadline check and recommendation analysis | Recommendations, opportunities, material-performance analytics |
| Demographic refresh | `POST /opportunities/{id}/demographic-check` | Demographic fields | Demographic matching | Classification/list/material/readiness and analytics keys |

Create and update are therefore not interchangeable contracts. Create intentionally writes Journal and may write a derived Calendar row; update is characterized not to do so. Neither directly changes submissions, queue items, relationships, or materials. Recommendations change only when explicitly generated. Readiness, material matches, analytics, and command-center projections can change from new opportunity/classification data.

### Candidate comparison

| Candidate | Cohesion / contract | Prop/query shape | Reduction | Risk / decision |
| --- | --- | --- | --- | --- |
| A — Create/Edit form | High: one field schema, payload mapper, draft lifecycle, and two canonical mutations | Proposed four-part contract below; no query | ~210–240 parent lines | Safest boundary, but create invalidation is not yet typed or contract-characterized |
| B — Parsing and role | Medium: related parsing intent, but entry points and outputs are embedded across list details and `BreakdownViewer`; manual role currently uses update without deep parse | Likely opportunity prop per expanded card, risking repeated hooks or callback orchestration | ~100–160 | Not next; parse/role product and side-effect differences need a separate preflight |
| C — List and selection | Low/medium: filtering and expansion are coherent, but edit/reject/role/parse/strategy/demographic entry points would create a large handler bag | Would require >10 mixed props/handlers or duplicate mutations | ~250+ | Rejected as callback-heavy orchestration |
| D — Destructive/classification | Small coherent reject form, but no hard delete is present and the mixed label misstates behavior | Opportunity ID/record plus close signal | ~60–80 | Too small for the next major boundary; retain as later bounded cleanup |

### Decision and proposed contract

**DECISION B — PREREQUISITE IDENTIFIED (resolved by Step 52A below).** Candidate A remained blocked at this checkpoint until `OpportunityService.create` was characterized in disposable PostgreSQL and `useCreateBreakdown` adopted a typed `opportunity.create` contract. Step 52A completed that prerequisite without extracting the form.

After that prerequisite passes, the proposed route-private contract is:

```ts
type OpportunityFormMode = { kind: "closed" } | { kind: "create" } | { kind: "edit"; opportunityId: string };

type OpportunityFormWorkspaceProps = {
  mode: OpportunityFormMode;
  onModeChange: (mode: OpportunityFormMode) => void;
  opportunities: Opportunity[];
  representations: Representation[];
};
```

The parent retains the mode signal because Add and Edit entry points remain in the section header and list. The child derives an edited record by ID, owns the controlled draft, initialization/payload conversion, create/update hooks, validation, pending/error/success behavior, and cancel/success reset. The parent retains filters, expansion, authoritative props, visible-list derivation, parsing, role, reject/archive, strategy and demographic actions. No child query, query key, QueryClient, generic handler bag, or public export is permitted.

### Required characterization before movement

Add component tests for: closed/create mode; initial auto-open when the list is empty; every controlled default needed to prevent uncontrolled inputs; create payload normalization; create success/reset/close; create failure with accessible error and full draft preservation; create pending disable; edit-by-ID initialization including null/date/metadata fallbacks; current-record refresh before dirty editing; edit success/reset/close; edit failure and draft preservation; cancel reset; switching edit IDs; removed edit record; representations; create versus edit hook ownership; no broad reload; exact create/update invalidation; parent composition and narrow props; route-private barrel protection. Retain existing Step 51A update/workflow and Step 51C deletion tests. Add mocked browser coverage for one create and one edit failure/success request graph after the prerequisite contract is proven.

### Rejected assumptions, gaps, and stop conditions

- Visual reuse did not prove create/update contract equivalence; backend evidence disproved it.
- “Delete / reject” is not hard delete and must not be used as evidence that Step 51C deletion belongs in this candidate.
- The form’s server-record snapshot is legitimate draft initialization; `rejectingBreakdown` and `addingRoleForBreakdown` full-record state are not.
- No sorting, restore, explicit approval, readiness mutation, material mutation, or hidden-review action exists in this component.
- Existing frontend coverage exercises hooks and static ownership but has no focused `OpportunityManager` interaction suite; contract smoke covers creation as setup but does not characterize its full invalidation matrix.
- Unresolved product questions: whether the reject action should be relabeled Archive/Reject, and whether manual role should trigger deep parse like hidden review. Neither blocks the form prerequisite and neither may be folded into it.
- Stop if the prerequisite reveals additional create side effects, requires conditional guessed invalidation, or changes backend behavior; reassess the contract first.
- Stop if form extraction requires parsing/reject/role state, more than the four proposed props, duplicate queries, parent-owned drafts/errors, or changes to `BreakdownDetails`.

Expected extraction bundle effect is neutral to a few hundred compressed bytes of module overhead. Expected `BreakdownManager` reduction is approximately 210–240 lines. The next major candidate after the form requires a new check-in; this preflight does not approve parsing/role, list, destructive actions, or `BreakdownDetails`.

### Step 52A — opportunity-create contract

The route validates `OpportunityCreate`, calls `OpportunityService.create`, and returns the committed `OpportunityRead`. One transaction adds the opportunity, runs parse/default/deadline/role/intelligence/trust processing, synchronizes a workflow self-tape when the normalized audition type is `Self-Tape`, records actor work and any dated Calendar rows, then commits. No create-specific retry or idempotency key exists: repeating the HTTP request creates a distinct opportunity and distinct linked Journal/workflow/Calendar records. Synchronization is unique only within one opportunity ID. A forced failure after Journal/Calendar construction rolls the entire request transaction back; the frontend runs invalidation only after success and background refetch rejection cannot change mutation success.

| Record family | Frequency / change | Condition and authoritative owner |
| --- | --- | --- |
| Visible / hidden opportunities | Always creates one in exactly one classification-backed list | Breakdowns owns both public list keys; expired submission deadline proved discarded/hidden ownership |
| Parse and intelligence | Always creates a parse run and updates normalized opportunity JSON/trust metadata | Breakdowns opportunity response; trust verification is stored in `source_metadata` |
| Roles | Conditional create | `BreakdownRole` rows exist only when structured parser output supplies roles; `role_details` and `breakdown_roles` remain stable response fields |
| Workflow self-tapes | Conditional create | Normalized `audition_type == Self-Tape` and non-demo; Auditions `workflowSelfTapes`; no deadline is required, but parsing may normalize sparse input to `Unknown` |
| Actor Journal | Always creates one historical `Accepted Breakdown` row | Journal owner, linked by `linked_breakdown_id`; hidden/discarded creates also receive it; `record_once` prevents duplicates only for the same linked opportunity/event |
| Persisted Calendar | Conditional create | Calendar owner; Self-Tape/Virtual/In-Person plus `audition_deadline`, and/or any `callback_date`; uniqueness is within matching opportunity/type/time |
| Calendar projections | Derived, no extra row | Breakdowns and Auditions caches can also be projected by Calendar; these do not replace the persisted-row invalidation above |
| Readiness | Derived change for visible acting opportunities | Breakdowns readiness query calculates from opportunity/role/profile; no readiness row is persisted |
| Material matches | Derived change when actor assets exist and score qualifies | Breakdowns material-match query calculates from opportunities/assets; no asset or `last_used_date` changes |
| Operational Analytics | Conditional derived change | Reads persisted Calendar/upcoming operational sources; dated creates can change it |
| Intelligence Analytics | Never / unchanged | Dashboard reads submissions, outcomes, casting offices and material archetypes, not unsubmitted opportunities |
| Industry trends | Derived change | Reads non-demo opportunity classification dimensions, including hidden records where the service permits |
| Command center | Derived change | Reads visible opportunities, deadlines and workflow self-tapes; hidden-only creates may leave visible cards unchanged |
| Submissions, callbacks, queue, recommendations, audition notes | Never / unchanged | No corresponding create service is called |
| Materials assets, reusable Materials self-tapes, material-performance Analytics | Never / unchanged | Material matching is calculation-only; material performance is submission/reusable-material based |
| Relationships / relationship Analytics | Never / unchanged | No submission or contact/relationship event is created |
| Career tasks, casting goals | Never / unchanged | No career service is called |
| Dashboard widget/focus preferences, executive briefs, provider/system capabilities | Never / unchanged | Preferences, briefs and capabilities have independent owners and are not regenerated |

The typed `opportunity.create` contract directly invalidates `breakdownOpportunities` and `breakdownHidden`. Its exact derived set is `breakdownReadiness`, `breakdownMaterialMatches`, `workflowSelfTapes`, `calendarEvents`, `journalEntries`, `analyticsOperations`, `analyticsIndustryTrends`, and `commandCenter`. Its forbidden set explicitly covers submissions, callbacks, audition performance notes, recommendations, queue, relationships and relationship Analytics, Materials assets, reusable self-tapes, Intelligence and material-performance Analytics, Career tasks, Dashboard preferences, and executive briefs. A static contract is appropriate because every key names a family that a successful create can synchronously affect; conditional families cannot be safely inferred from the request because parsing can normalize the returned classification, audition type, dates and roles.

Confirmed facts: create and update are distinct; Journal is unconditional on success; Calendar rows are persisted only for dated audition/callback inputs; hidden creates still write Journal; sparse input is normalized and may not retain the schema's initial `Self-Tape` default; no affected owner lacks a public key. Rejected assumptions: role-like prose always creates a role row; a crew-like description overrides an explicitly supplied acting classification; every sparse create creates a workflow tape; Calendar visibility is projection-only. Unresolved gaps: there is no HTTP idempotency contract, so automatic replay after an ambiguous transport failure can duplicate the user intent. That does not block moving the form because the current hook has no mutation retry and the extraction will preserve that behavior.

Tests added: disposable PostgreSQL visible, dated Self-Tape, expired/hidden, sparse/default, workflow uniqueness, stable response, forbidden-record, and forced rollback coverage; registry exactness/disjointness/create-vs-update tests; canonical hook exact success and zero-on-failure invalidation tests.

**BreakdownManager Candidate A extraction gate: APPROVED.** Create side effects are characterized, create/update ownership is stable, the typed success-only contract is complete, and no form mutation-contract ambiguity remains. This approves only the later create/edit form extraction; parsing/role, list, destructive actions, hidden review, and `BreakdownDetails` remain outside the approved boundary.

### Step 53A — create/edit workspace extraction

**Gate result: COMPLETED.** The Step 52A approval was present and all mandatory pre-implementation checks passed. A three-test embedded-form characterization baseline passed before production movement, covering empty-list create opening, defined defaults, payload normalization, success reset/close, authoritative edit initialization, update submission, and cancel/reopen reset.

Created route-private `OpportunityFormWorkspace.tsx` and `opportunityFormModel.ts`; neither is exported from the Breakdowns public barrel. The approved contract is unchanged: `mode`, `onModeChange`, `opportunities`, and `representations`. The parent owns only the closed/create/edit mode and supplies authoritative records. The child owns the typed 32-field editable draft, dirty flag, validation through required controls, create/update hooks, pending/error presentation, success/cancel reset, and mode close. It performs no query and receives no QueryClient, query key, handler bag, or route error/loading state.

Initialization is session-keyed. Create opens with a fully defined default draft. Edit derives the current opportunity by ID and normalizes nullable strings/arrays/booleans/numbers/dates plus nested metadata to controlled values. A same-ID authoritative refresh may replace a pristine draft; after the first user edit, later refreshes do not overwrite it. Switching target IDs initializes the new current record without leaking values. A missing/deleted/reclassified-out record closes the bounded workspace. A deleted representation renders the stable empty option without copying representation records into draft state.

`formDraftToOpportunityRequest` preserves the existing create/update payload: empty optional values become `null`, archetype text becomes an array, travel hours become a number or `null`, the selected representation ID is preserved, the audition deadline remains both submission and audition deadline, and existing source/production/role nested metadata is constructed exactly once outside JSX. Server-managed response fields are not included. Create and edit intentionally use their separate canonical hooks, preserving typed `opportunity.create` and `opportunity.update` invalidation. Manual-role update remains a separate parent-owned hook instance because it is a different retained action.

Failure stays local, preserves the entire draft and target, announces through `role="alert"`, and runs no success invalidation. Pending disables submit, sets `aria-busy`, and announces status. Success clears draft/error/dirty state and closes. Cancel discards the session and closes. All fields remain labeled and controlled; create/edit headings and button names are distinct. Focus restoration remains the browser's existing section-button behavior; no new prop was added solely for focus orchestration.

`BreakdownManager.tsx` fell from 698 to 465 lines, a 233-line reduction. Moved: create/edit draft, initialization, normalization, payload mapping, create mutation, form-edit update mutation, pending/error/success/cancel handling, and form JSX. Retained: filters, list and expansion/detail orchestration, authoritative props, parsing/deep parse, paste drafts, manual-role state/update, reject/archive, strategy, demographic refresh, and all `BreakdownDetails` composition.

Tests added: pure model defaults/fallbacks/payload mapping; workspace closed/create/edit, local failure, dirty refresh, ID switch and missing-record behavior; embedded manager composition characterization; static route-private/no-query/no-create-hook ownership; and mocked Playwright create/edit success/failure request graphs. The focused browser scenarios passed three consecutive repetitions (12/12). Full Vitest passed 271 tests, PostgreSQL contract smoke passed 10, and backend passed 166 with 10 integration skips. Full mocked Playwright passed all four new form scenarios and 24/25 overall; the sole failure is the pre-existing timing-sensitive Journal immediate-return freshness assertion, which observed one `/journal` refetch and was already reproducible before this extraction. No query policy changed.

Confirmed assumptions: four props are sufficient; representation and opportunity queries remain parent-owned; create/update invalidation needs no change; ID derivation supports refresh and disappearance; the expected parent reduction was accurate. Disproven assumptions: the populated browser route always starts with a closed form—the existing initial empty query snapshot can open create before data arrives, so this behavior remains characterized; a generic static ban on all `form` state in the manager would incorrectly reject retained manual-role/reject forms.

Bundle impact is bounded module overhead: Opportunities route `117.27 kB / 27.74 kB gzip` to `117.85 kB / 28.04 kB gzip`; main `271.16 kB / 85.88 kB gzip` to `271.16 kB / 85.90 kB gzip`. No backend, query key, stale-time, mount-policy, or request-contract change occurred.

No other extraction is approved. The next step requires a fresh evidence-based check-in and preflight; parsing/role, reject/archive, list, hidden review, and `BreakdownDetails` remain explicitly unapproved.

After that correction, extract:

- `components/HiddenOpportunityReview.tsx` — disclosure, hidden list, selection-by-ID, detail composition, action choice, and mutation pending/error ownership.
- `components/HiddenOpportunityActionForm.tsx` — completion, travel, paste, and role drafts.
- Optionally `hooks/useHiddenOpportunityReviewActions.ts` only if it gives approve/delete/deep-parse consistent pending/error semantics without wrapping or duplicating query caches.

Expected child contract: `hiddenOpportunities: Opportunity[]`. State moved: disclosure, selected ID, action kind/ID, form drafts, action pending/error/success. State retained in discovery: all run/report/search/provider/source-research state. Expected parent reduction is approximately 350–380 lines. Extraction alone is expected to be bundle-neutral or add minor module overhead.

## 14. Stop conditions for future extractions

Stop and reassess if an extraction requires more than 10–12 unrelated props, a universal data/handler bag, copied server records, parent-owned mutation state, a base-client import, an internal cross-feature import, public export of route presentation, inline query keys, broad/root invalidation, discovery-run coordination, backend contract changes, or work inside `BreakdownDetails.tsx` without a separate decision.

Before moving hidden-review code, characterization tests must cover list/empty rendering, selection and current-record derivation, detail rendering, Complete, Travel Info, paste, deep parse, manual role, approve, hard delete, pending/disabled behavior, API failure and draft preservation, success reset/close, hidden/visible list invalidation, partial failure isolation, accessible disclosure/form/error behavior, exact invalidation, API ownership, and route-private/public-barrel boundaries. Mocked Playwright should cover at least one promotion or edit and one destructive confirmation; contract smoke should cover update/approve/delete side effects if not already represented.

## 16. Step 54 — post-Step-53A BreakdownManager preflight

### Current responsibility map

`BreakdownManager.tsx` is 465 lines. It is now primarily the visible-opportunity list/detail orchestrator plus two small nested action forms.

| Lines | Responsibility | State / hooks | Rendered ownership |
| --- | --- | --- | --- |
| 10–48 | Route inputs, mutation entry points, presentation state, filtering | `formMode`, `breakdownFilter`, paste maps, expansion map, two selected full records; parse/deep-parse/strategy/demographic hooks | Parent-owned route orchestration; no query |
| 50–121 | Section, filters, create/edit composition, list cards and action entry | mode setter, expanded IDs, reject/role selection | `OpportunityFormWorkspace`, action header, `ActionCard` |
| 122–177 | Summary, trust, production and role overview | authoritative opportunity only | `TrustVerificationPanel`, `KeyValueGrid`, `RoleViewer` |
| 178–293 | Viewer and detailed disclosures, including parsing entry points | three callbacks into `BreakdownViewer`; paste open/draft maps | `BreakdownViewer`, submission/preparation/parse/travel/strategy/source/raw disclosures |
| 294–335 | Watch-list and demographic detail | demographic mutation | watch-list rows and demographic refresh |
| 338–396 | Reject/archive nested form | reject hook; local rejection draft, saving and error | action-local form |
| 398–465 | Visible manual-role nested form | update hook; local role draft, saving and error | action-local form |

`BreakdownReadiness` is a sibling panel composed outside this manager and receives its own query-owned readiness/material data; it neither reads nor coordinates manager state. `OpportunityFormWorkspace` receives the already-authoritative opportunity and representation props and owns create/edit only. The manager itself has no public query hook, base client, API function, query key, or QueryClient.

### Remaining local-state ownership

| State | Current owner / shape | Reset and failure behavior | Ideal owner / refresh behavior |
| --- | --- | --- | --- |
| `formMode` | manager, ID-based mode | child closes on cancel/success/missing record | Correct narrow parent signal |
| `breakdownFilter` | manager value | unmount only | Correct list owner |
| `expandedBreakdowns` | manager ID map | unmount only; independent of mutations | Correct list/detail owner |
| `pasteOpenById` / `pasteTextById` | manager ID maps / form drafts | clear/close only after parse success; mutation failure preserves draft but has no local error UI | Coherent with a future details/parsing decision; no other workflow reads them |
| parse/deep-parse pending/error | hook state exists but is not rendered | entry points remain clickable; rejected promise is not locally announced | Missing action feedback; a details preflight must choose its owner |
| `rejectingBreakdown` | manager full `Opportunity` snapshot | cancel/success clears; failure stays selected inside nested form | Prefer an ID derived from authoritative props, but do not freeze product language first |
| rejection draft / saving / error | nested reject form | failure preserves; success calls parent close; error text lacks `role="alert"` | Correctly action-local, with accessibility coverage needed |
| `addingRoleForBreakdown` | manager full `Opportunity` snapshot | cancel/success clears; failure stays selected | Prefer an ID derived from authoritative props after visible-role semantics are decided |
| role draft / saving / error | nested role form | validation/failure preserve; success clears through unmount | Correctly action-local; duplicate roles are appended and order is insertion order |
| strategy pending/error | hook only | neither rendered nor caught locally | Future details/action-feedback concern |
| demographic pending/error | hook only | neither rendered nor caught locally | Future details/action-feedback concern |

The two full-record selectors are stale-snapshot risks across query refreshes, but replacing them without moving their forms would be a cosmetic intermediate change. No other workflow consumes either snapshot, so this is bounded debt rather than a current cross-owner defect.

### BreakdownDetails dependency and callback map

The manager imports display helpers/components from `BreakdownDetails.tsx`: `BreakdownViewer`, `KeyValueGrid`, `OpportunityLink`, `RoleViewer`, `TextAction`, `TrustVerificationPanel`, formatting/derivation helpers, and the two form-state types. Only `BreakdownViewer` receives action props:

| Prop | Classification | Owner |
| --- | --- | --- |
| `opportunity` | authoritative query data | manager passes current list record |
| `onRunDeepParse` | action callback | manager-owned deep-parse hook |
| `onPasteText` | form opener | manager-owned per-ID paste state |
| `onManualAddRole` | form opener | manager-owned selection state |

Those same three actions also appear in the manager's role-fallback block, and paste UI lives in the raw-text disclosure. Parsing output is rendered through roles, detected sections, parse history, raw text, trust, and other details. Moving parsing now would therefore either duplicate entry state or require changing `BreakdownDetails` internals and synchronizing callbacks. Most remaining line volume is detail composition, not independent manager business state.

### Remaining mutation and invalidation map

| Action | Endpoint | Direct and synchronous derived effects | Invalidation status | UI owner |
| --- | --- | --- | --- | --- |
| Paste/manual parse | `POST /opportunities/{id}/parse-breakdown-text` | replaces description; parse/intelligence/trust/deadline processing; conditionally synchronizes Auditions workflow self-tape; no Journal or persisted Calendar write | Typed `opportunity.manualParse`: visible/hidden, readiness, material matches, workflow tape, operations/intelligence/industry Analytics and command center | manager paste state/hook |
| Deep parse | `POST /opportunities/{id}/deep-parse` | parse run, sections/details, role sync, intelligence/classification/trust; no explicit workflow sync | Ad hoc `classificationKeys + analyticsIntelligence + analyticsIndustryTrends`; no typed contract | manager hook; entry duplicated in fallback and viewer |
| Visible manual role | `PATCH /opportunities/{id}` | appends `available_roles`, then update service ensures details, syncs roles, enriches/trust-verifies and conditionally synchronizes workflow tape; no subsequent deep-parse request | Typed `opportunity.update`; distinct action-local hook instance | nested visible-role form |
| Reject/archive | `POST /opportunities/{id}/reject` | sets visibility `discarded`, status `archived`, `hidden_by_rule=user_rejected`, reason/highlight metadata and manual-override history; trust verification; not a hard delete | Ad hoc classification and intelligence/industry keys; no typed reject contract | nested reject form |
| Strategy | `POST /opportunities/{id}/recommend` | persists/updates recommendation analysis after deadline/actor checks | Ad hoc recommendations, opportunities and material-performance Analytics | manager hook/action link |
| Demographic refresh | `POST /opportunities/{id}/demographic-check` | updates demographic match fields and commits | Ad hoc classification and intelligence/industry keys | manager hook/detail disclosure |

No current remaining hook uses root/broad invalidation. However, only manual parse and update are typed; deep parse, reject/archive, strategy, and demographic refresh remain focused but ad hoc. This preflight does not change them. Before any future action extraction, its mutation should be characterized and typed rather than copying the existing list.

### Candidate comparison

| Candidate | Possible contract | Cohesion and reduction | Decision |
| --- | --- | --- | --- |
| A — Reject/archive | `{ opportunityId, opportunities, onClose }`; child could derive record and own reject mutation/draft | Coherent ~59-line action boundary | **Blocked.** Current UI repeatedly says Delete although endpoint only rejects/archives; extracting would canonize materially inaccurate language. Reject invalidation is also not typed. |
| B — Manual role | `{ opportunityId, opportunities, onClose }`; child could derive record and own update/draft | Coherent ~67-line action boundary | **Blocked.** Visible flow performs update only; hidden flow performs update then deep parse. Intended equivalence/difference is unresolved, and duplicate semantics lack coverage. |
| C — Parsing | Would need opportunity ID/data, open state, paste draft, deep/paste entry coordination and feedback | Potentially 35–70 lines, but action entry/output is distributed | Rejected now: would require callback synchronization or `BreakdownDetails` changes and still leave parse display distributed. |
| D — List/action composition | Would require opportunities plus filter/expansion and roughly six action openers/mutations | Moves most JSX but creates a callback/handler bag | Rejected: current manager is the legitimate list/detail/action-entry owner. |
| E — Stop manager decomposition | No new contract | Keeps a cohesive 465-line orchestration layer; next complexity is details | **Selected.** Additional movement would be tiny, product-blocked, or a JSX shuffle. |

### Product-decision gates

1. **“Delete / reject” naming:** architectural blocker for a reject/archive extraction, not cosmetic. The backend contract is clearly reject/archive/discard, while hard delete exists elsewhere with protected-history semantics. The next product prompt must choose user-facing language such as “Reject / Archive.”
2. **Visible manual role deep parse:** architectural blocker for a role extraction. Existing evidence establishes a real difference from hidden review but not whether it is intentional. Do not unify or preserve it as a new boundary without a product decision.
3. **Removal from visible results:** already answered by backend/current filters. Reject sets `visibility_status=discarded`; the visible authoritative query excludes it after focused invalidation.
4. **Rejection reasons as history:** current backend persists reason/highlight plus manual-override history, so they are historical user data. Whether a later action may edit/reverse them is unresolved and non-blocking while no extraction proceeds.
5. **Parsing location:** architectural question for the next details preflight. Current evidence favors keeping action entry/output near details rather than creating a manager-only workspace, but ownership is not yet approved.

### Decision

**DECISION C — STOP MANAGER DECOMPOSITION.** `BreakdownManager` is now an acceptable route orchestration component. No further manager extraction is approved. Reject/archive and manual-role are small but product-blocked; parsing is inseparable from current details entry/output without a new details contract; list extraction would worsen the prop/callback surface.

State to retain is all current manager orchestration state listed above. State to move: none in Step 54. There is no approved component contract. Expected line reduction and bundle effect are both zero for this preflight.

### Characterization required before any later action work

- Reject/archive: open and exact labels; endpoint and payload fields; pending/disabled; accessible failure and full draft preservation; success and visible-list disappearance; reason/history behavior; exact typed invalidation; ID refresh/disappearance; mocked request graph.
- Manual role: open/defaults; payload/order; duplicate-name behavior; pending/error/success reset; ID refresh/disappearance; exact update invalidation; explicit proof of deep-parse absence in visible flow and presence in hidden flow; product decision before convergence.
- Parsing/details: both entry points; independent per-ID paste drafts; success/failure and accessible pending/error; deep-parse failure; expansion preservation; workflow self-tape effect for manual paste versus absence for deep parse; output refresh across roles/sections/history/raw text; exact typed deep-parse invalidation; a narrow details action contract.
- Manager composition: all filters, empty/list rendering, expansion by ID, action-entry routing, authoritative refresh, partial failures, strategy/demographic feedback, and public-barrel/no-query/no-handler-bag boundaries.

Rejected assumptions: 465 lines alone requires another extraction; every nested form deserves a component; “Delete” is equivalent to reject/archive; visible and hidden role workflows should automatically match; parsing can move without touching details; full-record selectors are harmless across refetches. Unresolved questions are limited to reject/archive language and reversibility, visible-role deep parsing/duplicates, and details-owned action feedback.

Stop conditions remain: do not extract an action while its language/behavior is undecided; do not pass more than roughly 8–10 unrelated props or generic handlers; do not duplicate queries or mutations; do not move parsing without a `BreakdownDetails` preflight; do not copy ad-hoc invalidation into a new owner.

**Recommended next architectural area:** a separate evidence-based `BreakdownDetails` preflight. Its exact prompt scope should map the display sections, the three `BreakdownViewer` action callbacks, parsing output ownership, strategy/demographic feedback, route-private contracts, and whether action entry belongs inside details. It must not extract code until it selects and gates one boundary.

## 17. Step 55 — extraction gate result

**GATE STOPPED.** Step 54 records `DECISION C — STOP MANAGER DECOMPOSITION`, not Decision A. It approves no candidate, component contract, state movement, mutation movement, query movement, or production implementation. The characterization list in Step 54 is evidence required before any hypothetical later action work; it is not extraction approval.

Accordingly Step 55 made no production or test changes. `BreakdownManager` remains the 465-line list, expansion, details, and action-entry orchestration layer. All current state, query ownership, mutation ownership, invalidation behavior, backend effects, product language, partial-failure behavior, accessibility behavior, and request graphs remain unchanged. Manager decomposition is complete under the current decision. The next permitted architectural check-in is the separately scoped `BreakdownDetails` preflight described above, not another manager extraction.

## 18. Step 56 — BreakdownDetails preflight

### Inventory and responsibility map

The current `BreakdownDetails.tsx` is 1,224 lines, but there is no component named `BreakdownDetails`. The file is a historical mixed presentation module rather than one render tree.

| Lines | Responsibility | State / actions | Consumers |
| --- | --- | --- | --- |
| 29–198 | Recommendation constants, links, trust warning, text action, hidden-review form types and initializers | No server state; pure helpers/components | Manager, discovery, queue, readiness, hidden review, public `OpportunityLink` |
| 199–405 | `BreakdownViewer` and parsing inspection derivations/renderers | Local selected parsed-section ID; three action-entry callbacks; no mutation hook/query | Visible manager and hidden review |
| 407–588 | Role, character, and compatibility renderers | Display-only derivation from parsed roles | Manager, viewer |
| 590–860 | Fact/inference renderers and opportunity formatting/domain-derived display helpers | Pure display derivation | Manager, hidden review, form model, discovery |
| 861–1,224 | `RecommendationPanel`, recommendation feedback, material/readiness helpers | Recommendation selection and feedback drafts; canonical feedback mutation | Public Breakdowns recommendation/readiness consumers |

The details experience rendered by `BreakdownManager` spans manager lines 122–335 and uses helpers from this module. `BreakdownViewer` itself is lines 208–273 plus private viewer helpers at 275–405 and 663–692. `BreakdownReadiness` is a separate sibling query owner and is not a child or dependency of the viewer.

### Prop, callback, and ownership map

The only details-like component with action props is `BreakdownViewer`:

```ts
type BreakdownViewerProps = {
  opportunity: Opportunity;
  onRunDeepParse: () => Promise<void>;
  onPasteText: () => void;
  onManualAddRole: () => void | Promise<void>;
};
```

`opportunity` is authoritative query data passed from the current visible or hidden list. The viewer does not copy it, query it, or mutate it. It owns only `selectedId`, a local display selection initialized from the derived section list.

| Callback | Visible owner | Hidden owner | Endpoint / invalidation | Feedback |
| --- | --- | --- | --- | --- |
| `onRunDeepParse` | manager `useDeepParseBreakdown` | hidden-review action hook | `POST /opportunities/{id}/deep-parse`; focused classification + Intelligence/industry keys, ad hoc | Hook pending/error are not shown in visible details; hidden action form owns error |
| `onPasteText` | opens manager per-ID paste draft | opens hidden action form | Later manual parse uses typed `opportunity.manualParse` | Visible draft survives failure but error/pending are not announced; hidden form announces error |
| `onManualAddRole` | selects full visible record and opens role form | opens hidden role action | `PATCH /opportunities/{id}` via typed `opportunity.update`; hidden then deep-parses, visible does not | Form-local pending/error; visible error lacks alert semantics |

Strategy generation and demographic refresh are not viewer props. Their controls and mutation hooks remain in the manager. Reject/archive and edit are manager action-bar controls. Create/edit, approve, protected delete, readiness, materials and recommendation feedback are separate existing owners.

### Display-section map

| Section | Data source / derivation | Actionable / shared state | Candidate status |
| --- | --- | --- | --- |
| Summary badges and AI summary | Opportunity fields; `projectTypeLabel`, `roleFitLabel`, `parseConfidence` | Manager-only display | Retain in manager orchestration |
| Trust verification | `source_metadata.trust_verification` | Display-only | Too small alone |
| Production overview | `production_details` plus `productionFallback` | Display-only | Coherent but already a compact manager section |
| Role/character overview | `breakdown_roles`, `role_details`; role/character/compatibility derivations | Manual-role entry is adjacent but not owned by renderer | Existing role renderer remains shared locally |
| Parsing confidence | parse runs, metadata, detected section confidence | Viewer-local derived cards | Viewer module boundary |
| Original text and highlighting | `description` plus selected section highlight | Selected viewer section | Viewer module boundary |
| Parsed structured sections | extracted facts, inference, production/audition/preparation/roles/submission/location/source fields | Selected viewer section; three fallback action entries | Viewer module boundary |
| Submission/preparation | role/source metadata and preparation section | Display-only disclosures | Retain in manager |
| Detected sections | `breakdown_sections` in server order | Display-only disclosure | Retain; duplicated conceptually inside viewer but different inspection presentation |
| Parse history | first five `breakdown_parse_runs` as returned | Display-only disclosure | Retain; no ordering is performed locally |
| Travel/audition | opportunity locations/hours/coverage | Display-only disclosure | Retain |
| Strategy preview | quality/risk fields | Generation control remains manager-owned | Retain |
| Demographic rejection and checks | match fields/details | Refresh control remains manager-owned | Retain |
| Source/raw text/watch-list | source metadata, description, watch-list fields | Raw-text disclosure owns manager paste form entry | Retain |
| Readiness/materials | separate readiness/material queries | Query-owned sibling | Outside details boundary |
| Casting relationships/override history | Not rendered as dedicated details sections | None | No candidate supported by current UI |

### Derived-data ownership

Viewer-specific derivations are `breakdownViewerSections`, `parsingConfidence`, `fieldConfidence`, `sectionHighlight`, `pickInference`, and highlighted-text segmentation. They select display-ready values only and belong with the viewer. The selected parsed-section ID is ephemeral UI state and also belongs there.

`productionFallback`, `preparationText`, `parseConfidence`, `detailValue`, `boolLabel`, `isTheaterBreakdown`, `FactInferencePanel`, and `RoleViewer` have consumers outside the viewer; moving or duplicating them would create a second boundary and is not approved. Their current rules affect presentation and classification language, so Step 56 does not relocate them to the query layer or backend. `formatDateTime` duplicates a shared utility in another module, but resolving that unrelated debt is not part of this boundary.

Visible and hidden details intentionally reuse `BreakdownViewer`, `FactInferencePanel`, `KeyValueGrid`, and role renderers. The opportunity form uses separate normalization helpers. Readiness, Calendar and Auditions own different projections and do not justify a shared view model here.

### Action, feedback, backend, and invalidation map

| Action | Backend effects / conditional effects | Current invalidation | Typed? | UI ownership / gap |
| --- | --- | --- | --- | --- |
| Manual parse | Replaces description; creates parse data; deadline/intelligence/trust processing; conditionally syncs workflow self-tape; no Journal or persisted Calendar write | Opportunity lists, readiness, matches, workflow tape, Analytics and command center | Yes, `opportunity.manualParse` | Manager/hidden form; visible missing pending/error announcement is an existing accessibility/correctness defect, but not part of a display-module move |
| Deep parse | Parses existing description; syncs roles; deadline/intelligence/trust; no explicit workflow sync, Journal or Calendar write | Classification/list/readiness/matches plus Intelligence/industry Analytics | No, focused ad hoc | Entry is in viewer and manager fallback; missing visible pending/error feedback is an accessibility defect and future extraction blocker |
| Manual role | Update service appends current available roles, syncs role/details/intelligence/trust and may sync workflow tape | Typed opportunity-update owner set | Yes, `opportunity.update` | Visible form update-only; hidden update then deep parse. Unresolved product blocker for action convergence |
| Strategy | Persists recommendation analysis after actor/deadline checks | Recommendations, opportunities, material-performance Analytics | No, focused ad hoc | Manager control; missing pending/error presentation is an accessibility defect and later enhancement |
| Demographic refresh | Applies and commits demographic match fields | Classification/list/readiness/matches plus Intelligence/industry Analytics | No, focused ad hoc | Manager demographic section; missing pending/error presentation is an accessibility defect and later enhancement |
| Reject/archive | Discards/archives and stores rejection metadata/override history; not delete | Classification/list/readiness/matches plus Intelligence/industry Analytics | No, focused ad hoc | Manager action bar; inaccurate product language remains a separate architectural blocker |
| Edit | Updates opportunity and synchronous workflow-derived fields; no Journal/Calendar persistence | Typed update contract | Yes | Existing form workspace, outside details |
| Approve/hard delete | Hidden-review-only promotion or protected deletion | Existing hidden hooks/contracts | Mixed | Outside viewer boundary |

No action currently performs root/global invalidation. The approved module boundary owns no hook, endpoint, pending/error state, draft, success behavior, or invalidation contract.

### Accessibility findings

- `DetailDisclosure` uses a keyboard-operable button and `aria-expanded`, but has no `aria-controls`/region association. This is a narrow shared-primitive accessibility debt, not a viewer extraction prerequisite.
- Viewer section selectors are buttons with visible names, but expose no tablist/tab/tabpanel relationship or selected state beyond styling. Characterize existing keyboard/click behavior before movement; richer tab semantics are a later accessibility correction.
- Headings descend from manager `h4` into role `h5`/`h6`, but the viewer can also render in hidden review under a different heading context. The move must preserve current elements.
- Raw source text correctly uses wrapping `<pre>` presentation and highlighting uses `<mark>`.
- Empty states exist for missing roles/inference/history. Sparse and malformed object metadata are normalized through existing display helpers, but are not directly tested.
- Visible deep parse/manual parse/strategy/demographic pending and failure feedback is missing. This is real action-level accessibility/correctness debt, but moving viewer code cannot safely fix it and it does not block a behavior-preserving module boundary.
- Focus after viewer action open/close is not explicitly managed or covered. No focus behavior may be invented during extraction.

### Candidate comparison

| Candidate | Contract / ownership | Result |
| --- | --- | --- |
| A — display-only parsing output | `{ opportunity }`; selected section and pure derivations | Conceptually coherent, but separating the fallback actions from the parsed-data panel would alter structure or require a slot. Reject as a new component contract. |
| B — production and role overview | Opportunity or a large mapped view model | Display-coherent but split across compact manager sections and shared role renderers; speculative reuse and weak reduction. |
| C — trust/classification | Opportunity metadata | Combines trust, classification, demographics, watch lists and overrides only because they are metadata; domain cohesion is insufficient. |
| D — details action controller | Multiple hooks, drafts and unresolved semantics | Rejected: untyped invalidation, visible/hidden role difference, missing feedback and unrelated lifecycles would create a generic action controller. |
| E — generic disclosure shell | Shared primitive already exists | Rejected: another wrapper would be cosmetic and duplicate `DetailDisclosure`. |
| F — no extraction | Leave mixed 1,224-line module intact | Safer than workflow movement, but misses a stable existing module seam. |
| Different boundary — move existing viewer intact | Existing four-prop contract; move viewer-local state/renderers/derivations to route-private `BreakdownViewer.tsx`; callers and action owners unchanged | **Approved.** This is module ownership, not an action/controller redesign. |

### Product-decision gates

1. Parsing actions currently remain manager/hidden-review controlled: answered for this move; changing ownership is blocked.
2. Visible manual role deep parse: unresolved architectural blocker for role/action convergence; irrelevant to intact viewer movement.
3. Strategy pending/error inline: narrow accessibility/correctness correction and later enhancement; not part of viewer.
4. Demographic status inline: narrow accessibility/correctness correction and later enhancement; not part of viewer.
5. Raw text remains disclosed in the manager and duplicated as the viewer's original-text inspection: current behavior to preserve; product consolidation is unresolved.
6. Hidden and visible already share the viewer but not the surrounding details renderer: speculative broader reuse is rejected.
7. Parse history/trust are currently user-facing diagnostics behind disclosures: answered by current behavior for preservation, but future product simplification remains possible.

### Decision and exact next boundary

**DECISION D — DIFFERENT BOUNDARY.** Approve only moving the existing `BreakdownViewer` and its private parsing-inspection helpers into route-private `components/BreakdownViewer.tsx`, without changing its prop contract, render structure, callbacks, or behavior.

The exact contract is the existing four props shown above. State to move: only viewer `selectedId`. Pure code to move: `BreakdownViewerSectionId`, `HighlightedBreakdownText`, `breakdownViewerSections`, `pickInference`, `parsingConfidence`, `fieldConfidence`, and `sectionHighlight`. Actions/mutations/drafts/pending/errors/queries to move: none. Shared role/fact renderers and shared formatting/domain helpers remain in `BreakdownDetails.tsx`; manager and hidden review retain their callback implementations and authoritative opportunity lists.

The new file must not query, import the base client, import hooks, receive QueryClient/query keys, store a copied opportunity, or enter the public barrel. It may import the existing route-local render helpers from `BreakdownDetails.tsx`; `BreakdownDetails.tsx` must not import the viewer back. Callers import the viewer directly from its route-private file, preventing a cycle.

### Characterization gate and expected effect

Before movement add focused viewer tests for: all six confidence cards and low/high styling; initial section selection; every section button and content; highlight found/not-found/empty; sparse sections; zero-role fallback; all three callbacks and rejected callback preservation; current-opportunity rerender without copied state; raw text semantics; role rendering delegation; and accessible button names/keyboard activation. Add a static test for route-private status, exact four-prop contract, no hooks/query/client/API paths, one-way dependency, and both caller imports. Existing hidden-review deep-parse/paste tests and manager composition tests must pass unchanged.

Stop if movement requires changing callback signatures, lifting `selectedId`, adding a slot/handler bag, moving `RoleViewer`/`FactInferencePanel`, changing manager or hidden action behavior, altering invalidation, or creating a circular dependency.

Expected `BreakdownDetails.tsx` reduction is approximately 200–210 lines; total production lines and bundle output should be effectively neutral apart from module wrapper overhead. `BreakdownManager` remains 465 lines. This decision approves no second module split and no action-feedback fix.

Confirmed facts: the stable viewer is already used in both visible and hidden contexts; it has no query/mutation hook; its action contract is already narrow; the file-size problem is mixed module ownership rather than one component render tree. Rejected assumptions: a component named `BreakdownDetails` exists; all 1,224 lines belong to the visible details experience; parsing output can become opportunity-only without changing fallback structure; metadata sections form one evaluation domain; action ownership should move with action controls. Unresolved gaps: visible action feedback, role deep-parse semantics, reject/archive language, disclosure/tab semantics, and raw-text duplication.

**Explicit next-step gate:** a later implementation prompt may move only the intact viewer after the full characterization baseline passes. It must not extract role renderers, recommendation code, manager disclosures, action hooks, or any other details section. After that move, require a new check-in; do not automatically approve further `BreakdownDetails.tsx` decomposition.

## 19. Step 57 — BreakdownViewer module extraction

**Gate result: COMPLETED.** Step 56 Decision D approved exactly the existing viewer module boundary. Four user-observable characterization tests passed against the embedded implementation before movement: confidence and initial production rendering, all parsed-section controls with keyboard activation, sparse/malformed display plus all three action entries, and authoritative opportunity rerendering without copied server state.

Created route-private `components/BreakdownViewer.tsx` with the unchanged four-prop contract: authoritative `opportunity`, `onRunDeepParse`, `onPasteText`, and `onManualAddRole`. The component remains absent from the public barrel. Visible manager and hidden review import it directly. Dependency direction is one-way: the viewer imports existing shared route-local role/fact/display helpers from `BreakdownDetails.tsx`; that module does not import the viewer.

Moved sections are the six confidence cards, original source-text/highlight panel, parsed structured-data selector/content, and existing missing-role action-entry block. Moved pure derivations are viewer section construction, field/parsing confidence, highlight selection/rendering, inference selection, and section-text joining. Moved state is only the parsed-section `selectedId`. No server record is copied into state.

Actions moved: none. The existing buttons continue invoking the same callbacks. Manager and hidden review retain all parse/deep-parse/manual-role hooks, targets, drafts, pending/error/success behavior and authoritative opportunity lists. Queries moved or added: none. Query keys, stale times and mount policies are unchanged. Invalidation remains exactly as before: typed manual parse/update and focused ad-hoc deep parse; no root/global refresh was introduced. A callback failure therefore remains isolated in its existing action owner and cannot erase the last authoritative viewer output.

Accessibility behavior is preserved: semantic headings, raw `<pre>` text, `<mark>` highlights, visible button names and keyboard-operable section/action controls are unchanged. This boundary does not add tab semantics, disclosure regions, pending announcements or focus restoration; those remain separately documented accessibility debt.

`BreakdownDetails.tsx` decreased from 1,224 to 982 lines, a 242-line reduction. The extracted viewer is 218 lines. The difference from the preflight estimate is formatting/module-boundary accounting, not additional responsibility movement. `BreakdownManager` remains behaviorally unchanged and is 466 lines after the direct import occupies one additional line. It retains filters, list, expansion, all detail composition, action entry/ownership, forms and mutations. `BreakdownDetails.tsx` retains links, trust/actions/form types, role/character/compatibility renderers, fact/inference and formatting helpers, and the recommendation/feedback workflow.

Tests added: four focused viewer behavior tests and two static boundary assertions. The static test enforces the exact contract, local display state, no hooks/query/client/API access, route-private status, one-way dependency, and direct visible/hidden callers. Existing manager and hidden-review composition tests pass unchanged.

Confirmed assumptions: the four-prop contract is sufficient; the viewer owns only display selection and derivation; shared render helpers can remain in place without a cycle; both callers preserve their existing action owners. Disproven assumptions: no new opportunity-only display contract or action-controller abstraction was needed; moving the existing boundary did not require query, invalidation, backend or callback changes.

No second extraction is approved. Remaining candidates include role/character renderers, generic detail helpers, recommendation workflow separation, manager-owned disclosures, and action-feedback corrections. Each requires a fresh evidence-based check-in; do not infer approval from the remaining file size.

Verification: the focused post-move composition set passed 14 tests; Breakdowns plus invalidation/query-policy coverage passed 84 tests; the full frontend passed 277 tests; backend passed 166 with 10 explicit integration skips; and disposable PostgreSQL contract smoke passed 10. ESLint, TypeScript no-emit, production build and static architecture audits passed. The focused complete/sparse viewer browser scenarios passed three repetitions (6/6). The full mocked browser suite passed the two new scenarios and 26/27 overall; its sole failure was the pre-existing timing-sensitive Journal immediate-return assertion, which observed one Journal request. That isolated scenario then passed 3/3. No query policy or request owner changed.

A clean full mocked-browser rerun then passed all 27 scenarios, including both viewer tests and the Journal immediate-return check.

Bundle impact is neutral: the Opportunities route remained `117.85 kB` and improved from `28.04 kB` to `27.85 kB` gzip; main remained `271.16 kB` and changed from `85.90 kB` to `85.89 kB` gzip. The new module does not produce an additional route chunk.

## 20. Step 58 — post-Viewer BreakdownDetails preflight

### Gate and current shape

This is an audit-only decision. No production declaration, import, hook, query key, invalidation contract, backend behavior, or public export moved. `BreakdownDetails.tsx` is exactly 982 lines. Its name is now historical: the module contains feature-internal display primitives, hidden-review form models, opportunity formatters, the role-display domain, and recommendation/readiness presentation rather than one `BreakdownDetails` component.

### Top-level declaration inventory

| Declaration | Kind | Approx. lines | Consumers | Domain owner | Candidate destination |
| --- | --- | ---: | --- | --- | --- |
| `recommendationFeedbackTypes`, `fitReasonOptions` | constants | 28–47 | recommendation feedback controls | recommendation feedback | retain pending a separate workflow decision |
| `formatDateTime` | formatter | 49–54 | manager | opportunity metadata | retain; shared duplicate cleanup is unrelated |
| `OpportunityLink` | React component | 56–71 | manager, queue, hidden review, public barrel | opportunity details support | retain |
| `externalBreakdownUrl` | domain derivation | 73–77 | hidden review | source metadata | retain |
| `TrustVerificationPanel` | renderer | 79–100 | manager | trust/confidence | retain |
| `hiddenBreakdownReason` | domain derivation | 102–111 | hidden review | hidden review | future hidden-review ownership correction only |
| `TextAction` | action primitive | 113–136 | manager, discovery, viewer, hidden review, readiness | feature presentation | retain |
| `HiddenBreakdownAction` | type | 138 | hidden action form | hidden review | future hidden-review-private move |
| `CompleteBreakdownFormState`, `TravelInfoFormState`, `PasteBreakdownTextFormState` | types | 140–159 | hidden action form | hidden review | future hidden-review-private move |
| `BreakdownRoleFormState` | type | 160–165 | manager and hidden action form | shared role action model | retain until visible/hidden semantics are resolved |
| `BreakdownRejectFormState` | type | 166–169 | manager | reject/archive | retain |
| `completeBreakdownInitialState`, `travelInfoInitialState`, `parseManualHours` | form helpers | 171–196 | hidden action form | hidden review | future hidden-review-private move |
| `RoleViewer` | React renderer | 198–221 | manager and `BreakdownViewer` | role display | **approved future role module** |
| `RoleInformationPanel`, `CharacterInformationPanel`, `CompatibilitySummary` | private renderers | 223–357 | `RoleViewer` | role/character display | move with `RoleViewer` |
| `compatibilityLabel`, `formatArchetypeScores` | private formatters | 359–379 | compatibility renderer | role compatibility | move with `RoleViewer` |
| `FactInferencePanel` | renderer | 381–418 | viewer and hidden review | fact/inference display | retain |
| `KeyValueEntries` | renderer | 420–431 | fact panel and role cluster | structured metadata display | retain; role module may import it one-way |
| `InferenceItem`, `NeedsReviewLabel` | private renderers | 433–452 | fact panel / key-value grid | fact/inference display | retain |
| `missingFields` | derivation | 454–457 | manager | opportunity completeness | retain |
| `KeyValueGrid` | renderer | 459–475 | manager and hidden review | structured metadata display | retain |
| `withoutKeys` | helper | 477–479 | manager and hidden review | structured metadata display | retain |
| `breakdownFamily`, `projectTypeLabel`, `isTheaterBreakdown` | domain derivations | 481–510 | manager / hidden review | opportunity classification | retain |
| `productionFallback`, `roleFallback`, `roleFitLabel`, `parseConfidence`, `preparationText` | domain derivations | 512–576 | manager, viewer, hidden review | opportunity-details presentation | retain |
| `stringValue`, `formStringValue`, `toDateTimeLocal`, `detailValue`, `boolLabel`, `humanizeKey` | formatters | 578–617 | forms, manager, discovery, viewer, hidden review, role/fact renderers | multiple explicit display domains | retain; reject a generic `utils.ts` |
| `RecommendationPanel` | recommendation workflow component | 619–758 | public barrel consumer | recommendation workflow | not approved |
| `actorRecommendationLabel`, `recommendationFitItems`, `ethnicityFitLabel` | recommendation derivations | 760–798 | recommendation panel/readiness | recommendation display | retain |
| `missingRecommendationMaterials`, `mergedReadinessStatus`, `recommendedAssetId`, `mergedMissingMaterials`, `stretchExplanation` | readiness/material derivations | 800–844 | recommendation panel/readiness | readiness/material display | retain with current sibling consumers |
| `RecommendedMaterialSelect`, `RecommendedMaterialsList`, `materialReason` | renderers/helper | 846–916 | recommendation panel/readiness | material recommendation display | retain |
| `RecommendationFeedbackControls` | form component | 918–975 | recommendation panel/readiness | recommendation feedback | retain; owns canonical feedback mutation |
| `formatScoreLabel` | formatter | 977–980 | readiness | readiness score display | retain |

### Export and consumer map

Only `OpportunityLink` and `RecommendationPanel` are public feature exports. Every other exported declaration is feature-internal, though many are exported from the mixed file for sibling imports rather than as an intentional API. Manager imports the opportunity link, trust/action primitives, role renderer, classification/detail derivations and reject/role form types. Hidden review imports fact/key-value renderers plus source, reason and display helpers; its action form imports hidden form models and initializers. Viewer imports `RoleViewer`, `FactInferencePanel`, `TextAction` and opportunity-display derivations. Readiness imports recommendation/material components and derivations. Discovery imports `TextAction`/`humanizeKey`; queue imports `OpportunityLink`; the form model imports form/date normalization.

No cross-feature code imports the file directly. The public barrel makes the two intentional public components available to pages. Several sibling consumers currently import a large mixed module for one helper, but moving those helpers individually would fragment ownership rather than improve it. `RoleViewer` is different: two real route-private consumers pull an entire coherent private renderer tree from the mixed module. Moving that tree creates one-way imports and removes no public API. The role module may import `KeyValueEntries` and `detailValue` from `BreakdownDetails`; `BreakdownDetails` must not import the role module, so no circular pressure is introduced.

### Updated responsibility map

The remaining module owns: link/trust/action primitives; hidden-review support types and initializers; role/character/compatibility display; fact/inference and structured-value display; opportunity classification/metadata formatting; recommendation generation-result presentation; recommendation feedback state/mutation; and readiness/material presentation helpers. It does not own the extracted parsing viewer, authoritative opportunity queries, manager action hooks, readiness queries, or create/edit workspace.

Legacy co-location is most evident in hidden-review form models and role display. Hidden form models are narrow ownership debt but moving them would not materially improve runtime composition. Role display is a true component domain with two consumers and private subrenderers. Pure formatters are not one domain: compensation, date, trust, role, source and metadata rules are interleaved, and a generic helper file would obscure product logic.

### Recommendation workflow and backend map

`RecommendationPanel` owns selected recommendation and feedback drafts; `RecommendationFeedbackControls` owns the canonical `useRecommendationFeedback` mutation. Strategy generation itself remains owned independently by manager and readiness through `useGenerateBreakdownStrategy`. `POST /opportunities/{id}/recommend` calls `StrategyAgent.analyze`, applies deadline validation, reads actor/assets/travel/latest learning data, **always inserts and commits a new `AgentRecommendation`**, and returns that row. There is no uniqueness constraint or replace/update branch, so retries append history. The recommendation list orders rows newest first.

`POST /recommendations/{id}/feedback` always inserts a new `RecommendationFeedback`, then synchronously runs `LearningAgent.analyze`, which persists a new learning insight in the same request transaction path; feedback is append-only in this UI and endpoint. Recommendation rows feed the executive agent and executive-intelligence aggregation; the workflow connector selects the latest recommendation for material defaults. Feedback influences later strategy through the latest learning insight. There is no direct Journal or Calendar write. Current strategy invalidation is focused but ad hoc: recommendations, opportunities and material-performance Analytics. Feedback invalidates recommendations only, despite synchronously changing learning data. These contracts and the missing inline generation/feedback failure presentation make a recommendation move riskier than a display-only extraction; this preflight does not change them.

### Role/fact dependency sketch

```text
BreakdownManager ───────┐
                       ├─> RoleViewer
BreakdownViewer ───────┘      ├─> RoleInformationPanel
                              ├─> CharacterInformationPanel
                              └─> CompatibilitySummary
                                      ├─> compatibilityLabel
                                      └─> formatArchetypeScores

RoleViewer ────────────────> KeyValueEntries, detailValue
BreakdownViewer ───────────> FactInferencePanel
HiddenOpportunityReview ──> FactInferencePanel, KeyValueEntries/Grid
```

The role cluster is display-only. It receives `Opportunity["breakdown_roles"]`, owns no state, callbacks, hooks, query, mutation, recommendation/readiness dependency, or copied server data. Fact/inference remains a separate display domain used directly by viewer and hidden review. Moving the role cluster intact requires no callback prop and no circular import.

### Action-feedback audit

| Action | Pending presented? | Error presented? | Success presented? | Accessible? | Current owner / classification |
| --- | --- | --- | --- | --- | --- |
| Deep parse | no | no in visible manager | no | no | manager; correctness + accessibility defect and blocker to moving this action |
| Strategy generation | no | no | refreshed result only | no | manager/readiness; correctness + accessibility defect |
| Demographic refresh | no | no | refreshed fields only | no | manager; correctness + accessibility defect |
| Reject/archive | disabled text `Saving...` | inline text without alert | removal after refresh | partial | nested manager form; alert/focus debt, plus inaccurate product language |
| Manual text parse | no | no in visible manager | form closes/draft clears | no | manager; correctness + accessibility defect; failure preserves draft because resets follow success |
| Visible manual role | disabled text `Saving...` | inline text without alert | form closes after refresh | partial | nested manager form; alert/focus debt; failure preserves draft |

These gaps are real, but none is caused or repaired by moving a display-only renderer. Standardizing them is more valuable than a recommendation/action extraction, but is unrelated to the approved role-display boundary and is not implemented here.

### Remaining invalidation audit

| Mutation | Direct/synchronous effects | Current exact owners | Finding |
| --- | --- | --- | --- |
| Deep parse | parse run/sections/roles/intelligence/classification/trust; no explicit workflow, Journal or Calendar persistence | visible/hidden opportunities, readiness, material matches, Analytics intelligence and industry trends | focused and evidence-consistent, but ad hoc/untyped |
| Strategy | appends recommendation after deadline/actor/material/learning reads | recommendations, opportunities, Analytics material performance | focused but ad hoc; opportunity invalidation and downstream learning/executive ownership require characterization before movement |
| Demographic refresh | commits demographic match fields | visible/hidden opportunities, readiness, material matches, Analytics intelligence and industry trends | focused and evidence-consistent, but ad hoc/untyped |
| Reject/archive | archives/discards opportunity and records reason/highlight/manual-override history | visible/hidden opportunities, readiness, material matches, Analytics intelligence and industry trends | focused but ad hoc/untyped; no hard-delete owner |

None uses root/broad invalidation or global refresh. Repository evidence is enough to describe direct effects, but disposable PostgreSQL characterization is still required before typing any contract with conditional derived effects. No invalidation work is prerequisite to the role renderer move because that module owns no action.

### Public/private and accessibility findings

`OpportunityLink` and `RecommendationPanel` are public feature API. The proposed role module is route-private/feature-internal and must not enter the public barrel. Hidden form types and most display helpers are exported only for sibling convenience; tests do not justify making them public. No direct API client, query hook, or cross-feature internal import exists in the renderer cluster.

Remaining UI has semantic headings and labeled material selectors/feedback controls, but recommendation failure is not presented inline; feedback controls do not expose mutation failure as an alert; several action errors lack alert semantics; pending changes are not announced; viewer selector tab semantics and shared disclosure region/focus behavior remain separate debt. Role display uses headings, paragraphs, badges and key/value lists and is callback-independent. Moving it must preserve those elements exactly; unrelated accessibility repairs must not be bundled into the move.

### Candidate comparison and product gates

| Candidate | Evidence | Decision |
| --- | --- | --- |
| A — recommendation workflow | Cohesive presentation, but public/private use, split strategy ownership, append-only persistence, learning side effect, ad-hoc invalidation and missing failure UI complicate ownership | Reject for the next move; characterize/repair separately |
| B — role and character renderers | One display domain, two real consumers, private renderer tree, no state/actions/server ownership, one-way dependency | **Approve one future module extraction** |
| C — fact/inference renderers | Coherent display but already a small shared primitive cluster; movement offers less ownership gain and depends on generic metadata renderers | Reject now |
| D — pure helpers | Helpers belong to several product domains; no single multi-consumer cluster beats the role boundary | Reject generic utility movement |
| E — hidden-review support | Ownership correction is real but primarily types/initializers and would not improve runtime composition | Defer |
| F — readiness/material support | Real sibling owner exists, but recommendation panel also consumes the helpers and readiness owns the query; movement would create ambiguous direction | Defer |
| G — stop | Safe, but misses a clean display-domain seam | Not selected |

Product gates: recommendation append versus replace is answered by current backend behavior (append); feedback editability is unsupported and a future product enhancement; inline recommendation failures are a correctness/accessibility defect and blocker for recommendation workflow movement; compatibility explanations and fact/inference panels are current user-facing UI to preserve; visible and hidden role display already share the same renderer contract; standardized action feedback is future correctness work; reject/archive reversibility remains unresolved and blocks archive workflow redesign. None blocks a behavior-preserving role renderer move.

### Decision and exact future contract

**DECISION A — APPROVE ONE MODULE EXTRACTION.** The only approved future boundary is the existing role/character/compatibility display cluster, moved intact to route-private `components/BreakdownRoleDetails.tsx`.

Exact export and prop contract:

```ts
export function RoleViewer({ roles }: { roles: Opportunity["breakdown_roles"] })
```

Move `RoleViewer`, `RoleInformationPanel`, `CharacterInformationPanel`, `CompatibilitySummary`, `compatibilityLabel`, and `formatArchetypeScores`. The child owns only pure display derivation. It owns no state, hook, query, mutation, invalidation, callback, or authoritative snapshot. Consumers are `BreakdownManager` and `BreakdownViewer`, importing the route-private module directly. It may depend one-way on existing `KeyValueEntries` and `detailValue`; it must not accept a QueryClient, query key, data/handler bag, or action callback. It must not be publicly exported.

Retain every other declaration listed above, including `FactInferencePanel`, structured metadata renderers, recommendation/readiness workflow, hidden-review models and all opportunity formatters. Do not move action ownership, alter role order/deduplication, add compatibility explanations, or refactor `BreakdownViewer`.

Required pre-move characterization tests are: complete multi-role rendering; sparse/null role arrays and malformed role/character/archetype metadata; role labels and all character fields; compatibility label thresholds and archetype-score formatting; key-value delegation; input-order preservation; no callbacks/actions; identical manager and viewer composition; and a static boundary test for route-private status, exact one-prop contract, no hooks/query/API client, no public-barrel export, direct two-consumer imports and acyclic one-way dependency. All must pass against the embedded implementation before movement.

Stop if the move requires changing the prop shape, moving `FactInferencePanel`/`KeyValueEntries`/`detailValue`, adding state or hooks, copying roles, changing labels/order/fallbacks, exposing the module publicly, or creating a cycle. Expected `BreakdownDetails.tsx` reduction is approximately 180 lines (to roughly 800); total source and bundle output should be effectively neutral, with no new route chunk expected.

Confirmed facts: the role renderer tree is pure and has two current consumers; visible/hidden parsing reuse reaches it through the viewer; it has no recommendation/readiness/action dependency; recommendation and feedback append records and feedback recomputes learning synchronously. Rejected assumptions: remaining line count alone justifies movement; recommendation generation replaces prior rows; readiness owns all recommendation presentation; hidden-review helpers should move merely because their names are hidden-specific; pure helpers form one generic utility domain. Unresolved gaps: exact downstream invalidation needed after feedback learning changes, action-level accessible feedback, archive reversibility/language, and whether recommendation history should remain append-only as product policy. These do not block the approved display boundary but matter for later work.

**Explicit next-step gate:** a later implementation prompt may extract only `BreakdownRoleDetails.tsx` after the required embedded characterization baseline passes. It must not move recommendation, fact/inference, hidden-review, readiness/material, action, query or mutation code. No additional `BreakdownDetails` extraction is automatically approved after that move; require a new check-in.

## 21. Step 59 — BreakdownRoleDetails ownership correction

**Gate result: COMPLETED.** Step 58 Decision A approved exactly one route-private role/character/compatibility renderer boundary. The current source matched every mandatory gate item. Three role-renderer characterization tests plus existing manager and viewer composition tests passed against the embedded implementation before production movement: 10 tests total.

Created `components/BreakdownRoleDetails.tsx`. Moved exactly `RoleViewer`, private `RoleInformationPanel`, private `CharacterInformationPanel`, private `CompatibilitySummary`, private `compatibilityLabel`, and private `formatArchetypeScores`. The only export remains:

```ts
export function RoleViewer({ roles }: { roles: Opportunity["breakdown_roles"] })
```

`BreakdownManager` and `BreakdownViewer` now import that export directly from the route-private module. `BreakdownDetails.tsx` no longer exports or imports `RoleViewer`; the public Breakdowns barrel remains unchanged and does not expose the new module. Dependency direction remains acyclic and one-way: the renderer module imports only the existing feature-local `KeyValueEntries` and `detailValue` display primitives from `BreakdownDetails.tsx`; the mixed module does not import back.

No state moved. The module owns pure render derivation only and receives the current authoritative role array as a prop. No hook, query, mutation, API call, query key, invalidation, callback, draft, server snapshot, pending/error state, or error boundary moved or was added. Manager, viewer, hidden review, recommendation, readiness/material, manual role, parsing, strategy, demographic and reject/archive ownership is unchanged. Typed and focused ad-hoc invalidation lists, stale times, mount policies, request graphs and partial-failure behavior are therefore unchanged.

Rendering and accessibility semantics are preserved exactly: role input order, empty state, headings, badges, definition lists, casting shorthand, character facts, AI interpretation fallback, compatibility labels, confidence values and archetype evidence formatting are unchanged. No unrelated accessibility repair was combined with the move.

`BreakdownDetails.tsx` decreased from 982 to 799 lines. The new module is 186 lines. Total production source changed from 982 to 985 lines, a net three-line increase for explicit module imports and boundary declarations. The Opportunities route remains 117.85 kB and changed from 27.85 kB to 27.91 kB gzip; main remains 271.16 kB / 85.89 kB gzip. This is effectively neutral and creates no additional route chunk.

Tests added are three direct role-renderer characterization cases and two static architecture assertions. They cover complete role/casting/character/compatibility/archetype output, empty and sparse/malformed data, fallback labels, input ordering, exact one-prop export, absence of hooks/query/API/callback ownership, route-private status, two direct consumers and acyclic dependency direction. The post-move module/composition set passed 19 tests; Breakdowns plus invalidation/query-policy coverage passed 74; full frontend passed 282.

The complete/sparse mocked viewer scenarios, including no duplicate opportunity request, passed 6/6 over three repetitions. The full mocked browser suite passed every Breakdowns scenario and 26/27 overall; the sole failure was the previously documented timing-sensitive Journal immediate-return assertion observing one `/journal` request. Its isolated three-run rerun passed 3/3. Backend passed 166 with 10 explicit integration skips, and disposable PostgreSQL contract smoke passed 10. ESLint, TypeScript no-emit, production build and static architecture audits passed.

Confirmed assumptions: the exact role-array prop is sufficient; both consumers can import directly; the private renderer tree has no hidden state or server ownership; `KeyValueEntries`/`detailValue` provide a safe one-way dependency; compatibility fallbacks and malformed metadata survive unchanged. Disproven assumptions: no view model, barrel, callback, public export, copied state or action relocation was required; source reduction does not require reducing total production lines.

Unresolved gaps remain outside this boundary: recommendation/feedback persistence and invalidation ownership, missing accessible feedback for several actions, reject/archive language and reversibility, hidden-review form-model co-location, fact/inference ownership, and readiness/material helper ownership. `BreakdownDetails.tsx` still owns link/trust/action primitives, hidden-review support, fact/inference and structured metadata display, opportunity formatters, and recommendation/readiness/material presentation.

No further extraction is approved. The next step requires a fresh evidence-based check-in that compares the remaining mixed-module responsibilities with the higher-value action-feedback and invalidation correctness work; do not infer approval from any remaining candidate or from the 799-line count.

## 22. Step 60 — post-Step-59 prioritization preflight

### Current declaration and ownership inventory

`BreakdownDetails.tsx` is exactly 799 lines. It is still a historical mixed feature-internal presentation module, but its remaining declarations are stable and mostly have real sibling consumers.

| Declaration | Kind / lines | Consumers | State/hooks | Domain owner | Risk |
| --- | --- | --- | --- | --- | --- |
| `recommendationFeedbackTypes`, `fitReasonOptions` | constants, 28–47 | feedback controls | none | recommendation feedback | Low |
| `formatDateTime` | formatter, 49–54 | manager | none | opportunity metadata | Low; historical co-location |
| `OpportunityLink` | component, 56–71 | manager, queue, hidden review, recommendation panel, public barrel | none | opportunity details | Low |
| `externalBreakdownUrl` | derivation, 73–77 | hidden review | none | source metadata | Low; historical co-location |
| `TrustVerificationPanel` | renderer, 79–100 | manager | none | trust display | Low |
| `hiddenBreakdownReason` | derivation, 102–111 | hidden review | none | hidden review | Low; exported for sibling convenience |
| `TextAction` | action primitive, 113–136 | manager, discovery, viewer, hidden review, readiness | none | feature-internal shared presentation | Low |
| `HiddenBreakdownAction` | type, 138 | hidden action form | none | hidden review | Low; historical co-location |
| `CompleteBreakdownFormState`, `TravelInfoFormState`, `PasteBreakdownTextFormState` | types, 140–159 | hidden action form | none | hidden review | Low; historical co-location |
| `BreakdownRoleFormState` | type, 160–165 | manager and hidden action form | none | shared role action model | Medium because visible/hidden deep-parse semantics differ |
| `BreakdownRejectFormState` | type, 166–169 | manager reject form | none | reject/archive | Medium because UI language is unresolved |
| `completeBreakdownInitialState`, `travelInfoInitialState`, `parseManualHours` | form helpers, 171–196 | hidden action form | none | hidden review | Low; historical co-location |
| `FactInferencePanel` | renderer, 198–235 | viewer and hidden review | none | fact/inference presentation | Low |
| `KeyValueEntries` | renderer, 237–248 | fact renderer and role module | none | feature-internal structured display | Low |
| `InferenceItem`, `NeedsReviewLabel` | private renderers, 250–269 | fact/key-value renderers | none | fact/inference presentation | Low |
| `missingFields` | derivation, 271–274 | manager | none | opportunity completeness | Low |
| `KeyValueGrid`, `withoutKeys` | renderer/helper, 276–296 | manager and hidden review | none | structured metadata display | Low |
| `breakdownFamily`, `projectTypeLabel`, `isTheaterBreakdown` | domain derivations, 298–327 | manager, hidden review, readiness | none | opportunity classification | Low |
| `productionFallback`, `roleFallback`, `roleFitLabel`, `parseConfidence`, `preparationText` | domain derivations, 329–393 | manager, viewer, hidden review | none | opportunity-details presentation | Low |
| `stringValue`, `formStringValue`, `toDateTimeLocal`, `detailValue`, `boolLabel`, `humanizeKey` | formatters, 395–434 | form model, discovery, manager, viewer, hidden review, role/fact/recommendation display | none | several explicit display domains | Low; a generic utility move would be worse |
| `RecommendationPanel` | workflow/presentation component, 436–575 | public barrel consumer | selected recommendation, feedback open/reasons/message; `useRecommendationFeedback` | recommendation and feedback | **High:** append-only mutation failure is not caught or announced |
| `actorRecommendationLabel`, `recommendationFitItems`, `ethnicityFitLabel` | recommendation derivations, 577–615 | recommendation panel and readiness | none | recommendation presentation | Medium product-language dependency |
| `missingRecommendationMaterials`, `mergedReadinessStatus`, `recommendedAssetId`, `mergedMissingMaterials`, `stretchExplanation` | derivations, 617–661 | recommendation panel/readiness | none | readiness/material presentation | Low |
| `RecommendedMaterialSelect`, `RecommendedMaterialsList`, `materialReason` | renderers/helper, 663–733 | readiness and recommendation panel | selection callback only | material recommendation presentation | Low |
| `RecommendationFeedbackControls` | form renderer, 735–792 | recommendation panel and readiness | parent-owned controlled state/callbacks | recommendation feedback | High because pending/error are absent in both owners |
| `formatScoreLabel` | formatter, 794–799 | readiness | none | readiness display | Low; historical co-location |

Only `OpportunityLink` and `RecommendationPanel` are intentional public feature exports. Most other exports exist for feature-internal sibling imports. Fact/inference and readiness/material groups are genuine display domains, but their current dependency direction is acceptable and their movement would primarily reduce file size.

### Mutation priority matrix

| Action | User consequence | Backend side effects | Invalidation status | Feedback status | Data-loss / duplication risk | Priority |
| --- | --- | --- | --- | --- | --- | --- |
| Manual parse | authoritative text and parsed details replaced | parse run, roles, deadlines, classification/intelligence/trust; conditional workflow self-tape | typed `opportunity.manualParse` | visible manager has no pending/error; draft clears only on success | draft preserved on failure; authoritative replacement on success | High feedback priority, but invalidation is already safe |
| Deep parse | current details/roles may change or opportunity may move lists | parse run, roles, deadlines, visibility/classification/intelligence/trust; no self-tape/Journal/Calendar write | focused ad hoc; appears complete | visible manager has no pending/error; hidden owner has local error | repeated parse runs possible; no draft | High |
| Strategy generation | creates recommendation and can change deadline visibility | **append-only** recommendation; deadline metadata can hide/archive opportunity; affects material performance and executive priorities | focused ad hoc but **incomplete**: hidden list and command center omitted | no pending/error in manager/readiness; result list is indirect success | retries append duplicate history | **Highest** |
| Recommendation feedback | teaches future scoring | append-only feedback plus synchronous append-only learning insight | only recommendations invalidated even though recommendation rows do not change; learning consumers omitted | success message exists; no pending/error; draft resets only after success | retries can duplicate feedback/learning rows | Highest, but not one of the currently characterized contract owners |
| Demographic refresh | match advice can change | demographic status/explanation/details only; endpoint does not re-run eligibility/visibility | focused ad hoc and likely over-broad for visible/hidden/Analytics | no pending/error/success | no draft or history | Medium |
| Reject/archive | removes item from normal workflow and preserves reason/history | discarded/archive fields, rejection metadata, trust and manual-override history | focused ad hoc; likely missing queue/recommendation implications require product/service characterization | pending text; inline error lacks alert; success removes item | historical/archive semantics; inaccurate label | High but product-blocked |
| Visible manual role | role data changes | typed opportunity update, roles/intelligence/trust and conditional workflow self-tape; no deep parse | typed `opportunity.update` | pending text; inline error lacks alert; draft preserved | appended role draft; duplicate semantics unresolved | Medium |

### Backend side-effect summary

- **Deep parse:** `POST /opportunities/{id}/deep-parse` reparses the existing description, creates parse/section output, syncs roles twice through parse/enrichment paths, applies deadline validation, classification, demographic/eligibility, character intelligence, watch-list and trust derivation, and commits. It does not call `_ensure_self_tape_workflow` and makes no Journal or persisted Calendar write. Deadline/intelligence can move the opportunity between visible, hidden, travel-exception and discarded owners. Current visible/hidden/readiness/material/Intelligence/industry invalidation is focused and appears consistent, but is undocumented and lacks direct failure/rollback characterization.
- **Strategy:** `POST /opportunities/{id}/recommend` runs deadline validation first and always inserts/commits a new `AgentRecommendation`, including blocked/expired cases. Deadline application writes source/extracted date metadata and may hide or archive the opportunity. Recommendations feed the recommendations list, Dashboard recommendation widgets, executive strong-match priorities, material-performance Analytics, and latest-recommendation workflow material defaults. There is no Journal or Calendar write. Retry appends another row. Current invalidation covers recommendations, visible opportunities and material performance, but omits hidden opportunities and command center/executive priorities.
- **Recommendation feedback:** `POST /agents/recommendations/{id}/feedback` appends feedback, then synchronously runs `LearningAgent`, which appends a new `LearningInsight` and commits the transaction path. Later strategies read the latest learning insight. Executive logic also reads latest learning state. It does not update the recommendation row, Journal or Calendar. Current invalidation of recommendations is not semantically aligned and omits learning-derived consumers. Retry duplicates both history signals.
- **Demographic refresh:** `POST /opportunities/{id}/demographic-check` updates demographic status, explanation and detail fields and commits. It does not call `OpportunityIntelligenceService.apply_hard_eligibility`; therefore it does not itself reclassify visibility, readiness records, command center, Journal or Calendar. Existing classification/Analytics invalidation appears broader than direct evidence and needs hook/service characterization before typing.
- **Reject/archive:** `POST /opportunities/{id}/reject` sets `visibility_status=discarded`, `status=archived`, `hidden_by_rule=user_rejected`, hidden/rejection reason and highlighted metadata; it clears review, re-verifies trust and appends manual-override history. It is not hard delete and preserves linked history. It does not directly change recommendation/queue rows, Journal or Calendar. Whether dependent queue/recommendation presentation should remain visible is product-sensitive.

### Action-feedback ownership map

| Action | Trigger / hook owner | Pending/error/success owner | Draft / focus owner | Required locality |
| --- | --- | --- | --- | --- |
| Manual parse | manager raw-text section / manager hook | same per-opportunity raw-text section; currently absent | `pasteTextById`; return to trigger/textarea | form-level, keep list and other details usable |
| Deep parse | manager role fallback and viewer callbacks / manager hook; hidden review has separate hook | each existing action owner; visible absent, hidden local | no draft; return to initiating button | action-local, not route-wide |
| Strategy | manager action strip and readiness row / separate hook instances | each initiating section; currently absent | no draft; focus stays on trigger | action-local; disable only the active owner |
| Recommendation feedback | recommendation panel and readiness each own hook plus controlled drafts | each feedback form; success currently parent message, pending/error absent | per-recommendation reasons and toggle button | form-level; preserve reasons on failure |
| Demographic refresh | manager demographic disclosure / manager hook | same disclosure; absent | no draft; refresh button | section-level |
| Reject/archive | nested manager form owns hook and local state | form-level pending/error/success; alert semantics missing | form draft; opener restoration absent | form-level |
| Visible manual role | nested manager form owns hook and local state | form-level pending/error/success; alert semantics missing | form draft; opener restoration absent | form-level |

Manual parse and demographic refresh are the cleanest independent feedback corrections. Strategy and feedback have two legitimate local owners; a global message bus/controller would be rejected. No correction should blank the list or disable unrelated actions.

### Invalidation readiness map

| Contract | Readiness | Proposed direct keys | Proposed derived keys | Forbidden keys / branches | Evidence/tests needed |
| --- | --- | --- | --- | --- | --- |
| Deep parse | needs focused service plus disposable PostgreSQL characterization | opportunities, hidden | readiness, material matches, Analytics intelligence/industry | workflow self-tapes, Calendar, Journal, submissions, reusable tapes; deadline branch must cover list movement | parse/role/trust/classification rows, expired/needs-review branch, rollback, exact hook keys |
| **Strategy generation** | **ready to type from existing service evidence, with characterization first** | recommendations, opportunities, hidden | material-performance Analytics, command center | readiness query itself, queue, workflow tapes, Calendar, Journal, submissions, reusable tapes; deadline-valid versus hide/archive branches | append count, deadline list movement, executive/material reads, failure rollback, exact hook/no broad invalidation |
| Demographic refresh | current key list appears over-broad; needs focused service tests | opportunities | possibly material matches/readiness only as frontend projections | hidden unless product expects eligibility rerun; command center/Analytics need proof | prove endpoint does not alter visibility/eligibility; owner-cache responses |
| Reject/archive | blocked partly by product semantics and needs PostgreSQL characterization | opportunities, hidden | readiness/material matches and possibly command center | Calendar, Journal, submissions; recommendation/queue visibility needs product decision | archive/history preservation, linked records, dependent views, failure rollback |

Strategy contract sketch: operation `opportunity.strategyGenerate`; synchronous timing; direct owners `breakdownRecommendations`, `breakdownOpportunities`, `breakdownHidden`; derived owners `analyticsMaterialPerformance`, `commandCenter`; explicit forbidden owners include submissions, callbacks, workflow/reusable self-tapes, Calendar, Journal, relationships, materials, queue, readiness query, Analytics operations/intelligence/industry, career tasks and dashboard preferences. Dashboard recommendation widgets share the recommendations query and need no separate key. Background invalidation failure must not change mutation success.

### Remaining candidates and user-impact ranking

| Rank | Candidate | User-impact evidence | Decision |
| ---: | --- | --- | --- |
| 1 | **Type strategy invalidation** | Prevents stale hidden/visible state and executive priorities after an append-only action; documents forbidden cross-feature owners; unlocks safe strategy feedback/recommendation work | **Selected** |
| 2 | Correct strategy or recommendation-feedback UX | Makes failures visible and can block duplicate clicks, but two separate legitimate owners require a later explicitly scoped workflow correction | Defer until strategy contract is typed; feedback contract also needs its own preflight |
| 3 | Correct manual-parse feedback | Clear single owner, preserves draft and high user value; typed invalidation already makes it safe | Best subsequent feedback candidate |
| 4 | Type deep-parse invalidation | Unlocks parsing feedback/ownership and prevents stale classification, but conditional parse/intelligence effects need more database characterization | Defer |
| 5 | Correct reject/manual-role alert semantics | Small accessible improvement, but archive language/reversibility and role semantics remain unresolved | Product-blocked in broader form |
| 6 | Type demographic invalidation | Current list may be over-broad rather than incomplete; endpoint is narrower than assumed | Characterize first |
| 7 | Recommendation module extraction | Append-only and feedback correctness/invalidation ownership are unresolved | Reject now |
| 8 | Fact/inference extraction | Stable display domain with multiple consumers but little user-risk reduction | Low priority |
| 9 | Readiness/material extraction | Would mostly rearrange imports while query ownership stays in readiness | Reject as cleanup-only |
| 10 | Stop Breakdowns work | Architecture is improving, but one proven stale-cache contract has higher immediate value | Not selected yet |

The weighting favors stale/incorrect decisions and append-only history over source reduction. Display extraction earns no priority merely because 799 lines remain.

### Product gates

1. Recommendation history is append-only in current backend behavior; whether it should remain product policy requires a later decision, but does not block typing current effects.
2. Feedback editability is unsupported and is a future product decision.
3. Idempotency/duplicate protection for strategy retry is a product/backend decision; current behavior establishes duplication risk, not desired policy.
4. Visible manual role deep parse remains a narrow blocker for converging role actions.
5. Correct reject/archive wording requires a product decision and blocks UI extraction/rename, not invalidation characterization.
6. Archive reversibility requires a product decision.
7. Explicit deep-parse success confirmation is architecture-neutral; failure/pending accessibility is a later correctness step.
8. Explicit demographic-refresh success confirmation is architecture-neutral; refreshed authoritative fields may suffice, but pending/error do not.
9. Refreshed recommendation results can constitute success feedback only when visible in the same section; this is not true for every current trigger, so pending/error ownership remains required.

### Decision and exact next gate

**DECISION A — TYPE ONE INVALIDATION CONTRACT.** Approve only the strategy-generation contract, named `opportunityStrategyGenerate` with operation `opportunity.strategyGenerate`. Do not add feedback UI, move recommendation JSX/hooks/state, alter append behavior, change query keys, or type any other mutation.

Required characterization before implementation:

- backend valid-deadline generation appends exactly one recommendation and leaves visibility unchanged;
- expired and needs-review generation append one recommendation and persist the corresponding opportunity/list-owner change;
- recommendation material IDs affect material-performance reads;
- strong-match recommendation affects executive/command-center priorities;
- failure rolls back recommendation and opportunity mutations;
- retry behavior is explicitly characterized as append-only without endorsing it as desired policy;
- contract direct/derived/forbidden sets and synchronous timing;
- hook invalidates exactly `keysForContract(invalidationContracts.opportunityStrategyGenerate)` on success;
- hook performs no invalidation on failure;
- background invalidation rejection does not turn a successful mutation into failure;
- no root/broad invalidation and no unrelated request owners.

Stop if evidence shows recommendation generation writes Journal, Calendar, workflow tapes, submissions, queue or unrelated Analytics; if command-center/material-performance dependencies are not synchronous reads of the committed rows; if a transaction failure leaves partial rows; or if implementation requires changing append semantics, query keys, endpoint behavior or UI ownership. In that case update the ledger and return to preflight rather than widening the contract.

Expected files for the next step are limited to `services/api/invalidationContracts.ts`, its tests, `features/breakdowns/hooks/useBreakdownQueries.ts` and hook tests, narrowly relevant backend/service or disposable PostgreSQL characterization tests, and this ledger. Expected runtime request count is unchanged: only post-success cache invalidation owners become exact; no new query or endpoint is introduced.

Confirmed facts: strategy always appends; deadline validation can mutate visibility; material performance and executive priorities read recommendations; current hidden and command-center owners are omitted; no Journal/Calendar/workflow write occurs. Rejected assumptions: another display extraction is automatically valuable; demographic refresh itself re-runs eligibility; recommendation feedback changes the recommendation row; current focused strategy keys are complete; file length should outrank mutation correctness. Unresolved gaps: desired recommendation idempotency/history policy, feedback invalidation/learning owners, archive language/reversibility, visible-role deep parse, and standardized action feedback.

**Explicit next-step gate:** the next prompt may characterize and type only `opportunityStrategyGenerate`. After it is complete, require another check-in before any feedback correction, recommendation extraction, or second invalidation contract.

## 23. Step 61 — typed strategy invalidation contract

**Gate result:** passed. Step 60 explicitly approved `DECISION A — TYPE ONE INVALIDATION CONTRACT` for `opportunityStrategyGenerate`, with complete characterization, ownership, file, and stop-condition requirements. No feedback, extraction, label, query-key, or backend product change was included.

The pre-change disposable-PostgreSQL characterization passed before production code moved. It confirms that each successful `POST /opportunities/{id}/recommend` appends one distinct `AgentRecommendation`; retry therefore appends history under current behavior. Deadline validation can leave the opportunity visible or move it to hidden `needs_date_review`. The action did not change Journal, Calendar, workflow self-tapes, submissions, or submission queue records. Existing service dependencies confirm that committed recommendations feed material-performance Analytics and command-center prioritization.

Implemented contract:

- owner/operation: `breakdowns` / `opportunity.strategyGenerate`;
- direct owners: `breakdownRecommendations`, `breakdownOpportunities`, `breakdownHidden`;
- derived owners: `analyticsMaterialPerformance`, `commandCenter`;
- forbidden owners: submissions, workflow self-tapes, callback/performance notes, Calendar, Journal, career tasks, submission queue, readiness/material-match queries, relationships, materials/reusable tapes, unrelated Analytics, dashboard preferences, and executive briefs;
- timing: synchronous;
- canonical hook: `useGenerateBreakdownStrategy`, now invalidating exactly `keysForContract(invalidationContracts.opportunityStrategyGenerate)` after success.

Failure remains owned by the mutation hook and runs no success invalidation. The established invalidator isolates background refetch failure from mutation success. Query ownership, query keys, request payload/response, retry behavior, UI pending/error/success behavior, and accessibility are unchanged. No local or copied server state was added.

Files changed for this boundary are `services/api/invalidationContracts.ts`, its registry tests, `features/breakdowns/hooks/useBreakdownQueries.ts`, its hook tests, the disposable contract smoke suite, the focused mocked request-graph scenario/support, and this ledger. Tests cover registry completeness and disjoint groups, exact hook invalidation, failure invalidating nothing, append/list-owner behavior, unaffected backend owners, and absence of broad or unrelated browser requests.

Confirmed assumptions: strategy generation appends rather than replaces; deadline validation can change list ownership; recommendation data is consumed by material-performance and command-center projections; the named forbidden persistence owners are unaffected. Disproven assumptions: the former focused key list was complete; a recommendations-only refresh was sufficient; strategy generation writes Journal, Calendar, workflow, submission, or queue state.

Remaining debt is unchanged: desired recommendation idempotency/history policy, local strategy and recommendation-feedback status, deep-parse invalidation and feedback, demographic invalidation/feedback, reject/archive language and accessibility, visible-role behavior, and the remaining mixed details module. No next change is approved automatically. A fresh check-in must choose exactly one subsequent boundary.

Verification result: the pre-change focused PostgreSQL characterization passed; the final disposable contract smoke passed 11/11; typed registry/hook tests passed 38/38; all Breakdowns plus registry/query-policy tests passed 87/87; the full frontend suite passed 285/285; the normal backend suite passed 166 with 11 contract tests skipped by design; lint, TypeScript no-emit, and production build passed. The strategy request graph passed three consecutive browser runs and made no broad/unrelated requests. The full mocked browser suite passed the new scenario and 27/28 overall; its only failure was the pre-existing Journal immediate-return timing assertion, which passed 3/3 when isolated. The Opportunities and main production chunks remained 117.85 kB and 271.16 kB respectively; only the invalidation registry chunk increased to 4.03 kB (0.82 kB gzip).

## 24. Step 62 — manual-parse feedback versus deep-parse invalidation

This is an audit-only decision. No production JSX, state, hook, query, invalidation, endpoint, or parsing behavior changed.

### Manual-parse flow and feedback ownership

| Concern | Current behavior | Correct owner | Defect | Implementation risk |
| --- | --- | --- | --- | --- |
| Trigger | `Paste Actual Breakdown Text` opens the per-card raw-text area; `Re-run Parsing` calls the manager action | that opportunity's raw-text disclosure | no | low |
| Target | current authoritative `Opportunity` prop supplies the ID | manager card/action function | no durable target defect | low |
| Draft | `pasteTextById[id]`; independent across opportunities | raw-text disclosure in `OpportunityManager` | no | low |
| Hook/request | manager owns `useParseBreakdownText`; POST payload is `{raw_text: trimmedDraft}` | manager parsing section | no | low |
| Pending | mutation state exists but is not rendered; submit remains enabled | same raw-text disclosure | correctness/accessibility defect | low |
| Error | rejected promise has no local catch or alert | same raw-text disclosure | correctness/accessibility defect | low |
| Failure | statements after `await` do not run, so draft and open state survive | same disclosure | desired behavior already established | low |
| Success | typed `opportunity.manualParse` refreshes authoritative owners, then local draft clears and disclosure closes | hook owns refresh; disclosure owns reset | parsed output is implicit success; an explicit success message is not required for this correction | low |
| Retry | same open disclosure and same draft can retry | same disclosure | no | low |
| Focus | opening does not explicitly focus textarea; close/reset does not deliberately return focus | disclosure trigger/form | accessibility gap; bounded focus behavior requires characterization | medium |
| Request graph | one POST followed by typed focused invalidation; no global reload | canonical hook | no | low |

The visible manual-parse owner can independently add local pending status, disable only its submit button, render an accessible error, preserve the complete draft on failure, retry it, and reset only after success. It does not require changing the endpoint, payload, query ownership, invalidation, manager/viewer boundary, or `BreakdownViewer` callback contract. Hidden review already has a distinct form-local pending/error implementation and is not part of the approved correction.

### Deep-parse backend side-effect map

| Record family | Frequency | Change | Condition | Frontend owner |
| --- | --- | --- | --- | --- |
| Visible/hidden opportunities | always evaluated | opportunity fields and list membership can update | parser confidence, deadline, classification, eligibility, demographics, travel | breakdown opportunities / hidden |
| Breakdown roles | always synchronized, replacing relationship contents from parsed `available_roles` | replace/update | parsed roles | opportunity query |
| Parser output/sections | always | creates one parse run and replaces section rows | endpoint success | opportunity query |
| Parse history | always attempted | appends `BreakdownParseRun`; succeeded on commit | every attempt inside the transaction | opportunity query; no separate frontend key |
| Intelligence/trust | always evaluated | opportunity scores, risk, confidence, demographic/eligibility/watch-list, character/trust data update | early deadline/classification branches can short-circuit some enrichment | opportunity plus derived Analytics/readiness owners |
| Workflow self-tapes | never in this service path | unchanged | `_ensure_self_tape_workflow` is not called | Auditions workflow cache forbidden |
| Recommendations/submissions/queue | never | unchanged | no service call/write | respective owners forbidden |
| Journal/persisted Calendar | never | unchanged | no actor-work or Calendar service call | Journal/Calendar forbidden |
| Calendar projections | conditional read impact only | derived display may reflect opportunity deadlines where consumers use opportunity state; no Calendar row changes | parsed deadline changes | no persisted Calendar invalidation proven necessary |
| Readiness/material matches | derived | calculated output can change | roles, visibility, fit, trust, deadlines | breakdown readiness/material-match owners |
| Material assets | never | unchanged | no asset write | Materials owner forbidden |
| Operations Analytics | derived | opportunity counts/alerts may change | visibility/classification/deadlines | Analytics operations candidate |
| Intelligence Analytics/industry trends | derived | opportunity-stage, classification, archetype and trend reads can change | parsed opportunity/roles | Analytics intelligence and industry owners |
| Material-performance Analytics | unchanged | submission/recommendation material history is not written | no relevant mutation | forbidden |
| Command center | derived | visible opportunity cards, priorities, deadlines and travel exceptions can change | visibility/scores/deadlines | command-center owner candidate |
| Relationships/Career/preferences/executive briefs | never directly written | unchanged | no calls/writes; executive briefs are separate persisted records | forbidden unless future evidence proves a live projection |

`OpportunityService.deep_parse` performs one database commit after parse-run/section replacement, role synchronization, deadline validation, enrichment, character/demographic/eligibility/watch-list derivation and trust verification. Retry creates another parse-run record and replaces current parsed sections/roles; it does not append recommendations. A thrown exception before commit should roll back the unit of work, but disposable PostgreSQL characterization is still required to prove parse-run/section/role rollback and conditional list transitions.

### Current and proposed deep-parse invalidation

Current `useDeepParseBreakdown` invalidates exactly `classificationKeys + opportunityAggregateKeys`: visible opportunities, hidden opportunities, readiness, material matches, Intelligence Analytics, and industry trends. It covers role/parser/trust state through the opportunity lists. It omits operations Analytics and command center, both of which read visibility, classification, scores and deadlines. No current key is proven unnecessary; Calendar, Journal, workflow tapes and material-performance Analytics should not be added merely for symmetry.

Proposed future contract sketch, not implemented:

- owner/operation: `breakdowns` / `opportunity.deepParse`;
- direct: `breakdownOpportunities`, `breakdownHidden`;
- derived: `breakdownReadiness`, `breakdownMaterialMatches`, `analyticsOperations`, `analyticsIntelligence`, `analyticsIndustryTrends`, `commandCenter`;
- forbidden: submissions, workflow self-tapes, callbacks, audition notes, persisted Calendar, Journal, recommendations, queue, relationships, relationship analytics, materials, reusable tapes, material-performance Analytics, Career tasks, dashboard preferences, executive briefs;
- timing: synchronous;
- conditional variants: probably unnecessary if all owner keys are invalidated after every success, but visible-to-hidden, hidden-to-visible/travel/discarded, early deadline and rejected-classification branches must be characterized first.

### Candidate comparison and product gates

| Criterion | Manual-parse feedback | Deep-parse invalidation |
| --- | --- | --- |
| User can miss a failure | high: visible failure is silent | high: visible context is silent; hidden context already reports it |
| Stale authoritative data risk | low: typed contract already exact | high: command center/operations appear omitted |
| Historical duplication risk | none beyond parse-run audit history; retry is user-controlled | parse-run history appends on retry; current content replaces |
| Product-policy blocker | none for pending/error/draft behavior | none for typing after characterization, but parse-history intent remains unconfirmed |
| Ownership clarity | high: one manager disclosure owns draft/action | medium: one hook serves visible and hidden initiators |
| Backend characterization burden | low | high: conditional visibility, role/section replacement and rollback |
| Unlocks later architecture | establishes safe local feedback seam | unlocks later deep-parse feedback/ownership work |
| Regression surface | small, local UI and request-graph assertions | medium/high cross-feature cache contract |

Product gates:

1. Explicit manual-parse success messaging is not established; authoritative parsed output plus closing/reset currently signals success. It is not required for the selected pending/error correction.
2. Failed pasted text remains visible by established current behavior and must be preserved.
3. Disabling submit while pending is an accessibility/correctness requirement for the selected step.
4. Retry using the same draft is established current behavior.
5. Deep parse not synchronizing workflow self-tapes is a backend fact, not a policy decision for this step.
6. Deep parse currently appends parse-history entries as a backend fact; desired retention policy remains unresolved.
7. Explicit deep-parse success confirmation is a later product/accessibility question.
8. Visible and hidden deep-parse feedback need not share presentation; their owners differ. Any convergence requires a later preflight.
9. Deep parse can reclassify and move visible/hidden/travel/discarded ownership as a backend fact.
10. Deep parse can alter readiness and material recommendations through roles, eligibility and trust as a derived backend/frontend fact.

### Decision and next gate

**DECISION A — CORRECT MANUAL-PARSE FEEDBACK.** Approve only the visible manager raw-text disclosure's local pending/error/accessibility correction. The exact boundary is: catch the existing manual-parse mutation locally; expose an action-local accessible pending announcement and error alert; disable only that opportunity's parse submit while its request is pending; preserve its open disclosure and complete draft on failure; allow retry; clear/close only after success; characterize focus without changing product behavior. The canonical hook, typed `opportunity.manualParse` contract, request payload, endpoint, authoritative queries, `BreakdownViewer`, hidden-review form and backend remain unchanged.

Required implementation characterization tests:

- open the visible paste disclosure and enter complete text;
- pending status is announced and only the relevant submit is disabled;
- failed request renders a local `role="alert"`, preserves all text and keeps surrounding details usable;
- retry uses the same draft, succeeds, then clears/closes exactly once;
- authoritative parsed output refresh remains driven by the existing typed contract;
- request graph remains one POST plus the exact existing invalidation requests, with no broad/global refresh;
- no invalidation registry or hook change;
- keyboard submission works; focus behavior on open, failure and successful close is characterized and any correction stays local.

Expected files are limited to `BreakdownManager.tsx`, its characterization/component tests, one focused mocked Playwright scenario/support if required, and this ledger. Forbidden adjacent work: deep-parse invalidation or feedback, hidden-review changes, parsing extraction, generic feedback infrastructure, query/freshness changes, success-toast policy, manual-role work, backend changes, and any second action.

Stop if the current manager cannot distinguish the pending/error state of the initiating opportunity without route-wide state, if the hook must change, if focus correction requires moving the disclosure/component boundary, or if the request graph/invalidation must change. In that case return to preflight rather than widening scope.

Confirmed facts: the visible draft is ID-owned and already survives failure; reset/close occur only after success; manual parse has a typed contract; the visible owner renders neither pending nor error; hidden review is a separate already-local owner; deep parse omits workflow/Journal/Calendar writes and its current invalidation omits proven opportunity-derived consumers. Rejected assumptions: manual and deep parse need one controller; deep parse shares the manual-parse contract; explicit manual-parse success text is automatically required; typing deep parse is a prerequisite for correcting manual parse; Calendar/workflow invalidation should be copied from manual parse. Unresolved gaps: deep-parse rollback/list-transition characterization, intended parse-history retention, explicit deep-parse success policy, and whether visible/hidden deep-parse feedback should ever converge.

**Explicit next-step gate:** the next prompt may implement only the visible manual-parse pending/error/accessibility boundary above. After completion, require a fresh check-in before deep-parse characterization or any other parsing work.

Step 62 verification: focused manager/viewer/hidden-review/hook/invalidation/query-policy coverage passed 50/50; six relevant mocked browser scenarios passed; disposable PostgreSQL contract smoke passed 11/11; the full frontend suite passed 285/285; the normal backend suite passed 166 with 11 disposable contract tests skipped by design; ESLint, TypeScript no-emit, production build, static architecture/import/query/broad-invalidation audits, and `git diff --check` passed. No production source file changed for this preflight.

## 25. Step 63 — visible manual-parse feedback correction

**Gate result:** passed. Step 62 explicitly approved only `DECISION A — CORRECT MANUAL-PARSE FEEDBACK`, with an exact visible-manager target, ownership, tests, expected files, forbidden work and stop conditions. Current code matched the ledger. Deep-parse invalidation/feedback, hidden review, manual role, query policy and backend behavior remained outside scope.

The pre-change characterization baseline confirmed that a successful visible manual parse submitted the complete per-opportunity draft and reset/closed only after success. The failure baseline confirmed that the form and draft survived, but also exposed the intended defect: the rejected `mutateAsync` promise was unhandled and no local alert or pending status existed.

Implemented boundary:

- `OpportunityManager` remains the sole visible manual-parse owner and retains `pasteOpenById`, `pasteTextById`, the opportunity ID target and canonical `useParseBreakdownText` hook.
- New state is limited to per-opportunity pending and error maps; trigger and textarea refs provide local focus behavior.
- Opening the paste form focuses its labeled textarea.
- Submission uses the existing endpoint/payload through the existing hook, announces `Re-running breakdown parsing…`, and disables only the initiating submit button.
- Failure catches the existing `ApiError`/error through standardized `errorMessage`, renders a form-associated local `role="alert"`, preserves the full draft and target, keeps the disclosure open, and leaves surrounding details usable.
- Editing or retrying clears the stale error. Retry reuses the same text.
- Success retains the existing typed `opportunity.manualParse` invalidation, clears the draft, closes the local form, and restores focus to its `Paste Actual Breakdown Text` trigger. No explicit success message was added.
- The local form now has a visible `Breakdown Text` label and native submit semantics, preserving button and keyboard activation.

Hook ownership, query ownership, query keys, stale/mount policy, response handling and invalidation are unchanged. Failed requests run no success invalidation. Successful requests issue the same focused refresh graph; no manual refetch, duplicate query, global reload, Journal, persisted Calendar or unrelated request was introduced. Backend evidence remains the characterized manual-parse behavior: authoritative opportunity/parse/intelligence/trust updates with conditional workflow self-tape synchronization and no Journal or persisted Calendar write. No backend file changed.

Files changed for Step 63: `BreakdownManager.tsx`, `BreakdownManager.characterization.test.tsx`, `e2e/manual-parse-feedback.spec.ts`, `e2e/support/mockApi.ts`, and this ledger. Tests added cover success-only reset/focus restoration, pending announcement and duplicate prevention, accessible form-associated failure, draft/target/detail preservation, retry, and the exact browser request boundary. The delayed mock seam is deterministic and limited to browser test support.

Verification: focused characterization/hook/registry tests passed 44/44; all Breakdowns plus invalidation/query-policy tests passed 90/90; the focused browser scenario passed 3/3; the full mocked browser suite passed 29/29; disposable PostgreSQL smoke passed 11/11; the full frontend suite passed 288/288; the normal backend suite passed 166 with 11 contract tests skipped by design; ESLint, TypeScript no-emit and production build passed. The Opportunities route changed from 117.85 kB (27.91 kB gzip) to 118.97 kB (28.23 kB gzip); main remained 271.16 kB (85.89 kB gzip).

Confirmed assumptions: visible manual parse has one local ID-based owner; draft/reset semantics were already correct; typed invalidation required no change; implicit refreshed output remains sufficient success feedback; accessible feedback can be local without moving component boundaries. Disproven assumptions: the old rejected promise was safely handled; a generic feedback controller or hook change was needed; focus behavior required an extraction; hidden-review feedback needed modification.

Remaining parsing debt: deep-parse invalidation still requires disposable PostgreSQL characterization; visible deep-parse pending/error remains absent; parse-history retention policy is unresolved; visible/hidden deep-parse feedback convergence is unapproved. Other strategy, demographic, archive and manual-role debt remains unchanged.

No next change is approved automatically. A fresh check-in must select one boundary before deep-parse characterization, another feedback correction, or any ownership work.

## 26. Step 64 — deep-parse invalidation preflight

This is an audit-only gate. No production code, test behavior, backend behavior, hook, query, invalidation, UI, parse-history, workflow or recommendation behavior changed.

### Backend mutation map

`POST /opportunities/{id}/deep-parse` calls only `OpportunityService.deep_parse`. The service loads the authoritative opportunity, reparses its existing `description` in `Deep Parse` mode, applies manual-entry defaults, deadline validation, role synchronization, opportunity intelligence and trust verification, then performs one session commit.

| Record/owner family | Proven service behavior | Invalidation classification now supportable |
| --- | --- | --- |
| Opportunity fields and visible/hidden membership | parse details, classification, deadlines, manual-review state, demographic/eligibility, travel, scores, risk, priority, watch-list and trust metadata can change | direct: `breakdownOpportunities`, `breakdownHidden` |
| Parsed sections | current relationship is cleared and replacement section rows are appended | direct through authoritative opportunity owners; no separate query key |
| Parse runs/history | one `BreakdownParseRun` is added per attempt and marked succeeded before the final commit | direct through opportunity owners, but retry/rollback persistence is not characterized |
| Breakdown roles/casting language/character intelligence | relationship is cleared and rebuilt from parsed `available_roles`; enrichment can rebuild fit and character records | direct through opportunity owners |
| Readiness | reads visible opportunity, parsed roles, character intelligence, travel and materials | derived: `breakdownReadiness` |
| Material matches | reads visible/classified opportunity text, archetypes, priority and audition type; asset rows are not written | derived: `breakdownMaterialMatches`; `materials` forbidden |
| Command center | reads visible/classified opportunities, deadlines, urgency, quality, priority and travel-exception counts | derived candidate: `commandCenter` |
| Industry trends | reads classified opportunities, role/archetype/project/location/audition/source fields | derived: `analyticsIndustryTrends` |
| Intelligence dashboard | current dashboard is primarily submission/asset/relationship outcome data; current hook invalidates it, but repository tests do not prove a deep-parse response change | unresolved candidate: `analyticsIntelligence` |
| Operations Analytics | persisted Calendar/submission data is unchanged, but alerts can dereference an existing Calendar event's linked opportunity travel fields | conditional derived candidate: `analyticsOperations` |
| Material-performance Analytics | reads submission/recommendation material history; deep parse writes neither | forbidden: `analyticsMaterialPerformance` |
| Workflow self-tapes | `_ensure_self_tape_workflow` is not called | forbidden: `workflowSelfTapes` |
| Recommendations | no recommendation call or row write | forbidden: `breakdownRecommendations` |
| Journal / persisted Calendar | no actor-work or Calendar service call | forbidden: `journalEntries`, `calendarEvents` as persisted owners |
| Submissions / queue / callbacks / audition notes | no calls or writes | forbidden |
| Relationships / relationship Analytics | no relationship mutation | forbidden |
| Material assets / reusable tapes | no asset or tape mutation | forbidden |
| Career tasks / preferences / executive briefs | no calls or writes | forbidden |

The source establishes intended one-commit transaction structure but does not prove rollback behavior when failure occurs after parse-run, section and role mutation. It also does not prove whether a failed parse-run is retained or rolled back. Existing unit/component tests do not substitute for that database evidence.

### Current invalidation and request graph

`useDeepParseBreakdown` currently invalidates `classificationKeys + opportunityAggregateKeys` after success:

- `breakdownOpportunities`;
- `breakdownHidden`;
- `breakdownReadiness`;
- `breakdownMaterialMatches`;
- `analyticsIntelligence`;
- `analyticsIndustryTrends`.

There is no root invalidation, empty key, broad feature root, global refresh, manual refetch or duplicate query. Failed mutations execute no `onSuccess` invalidation. Active queries alone refetch through the shared background invalidator. Command center is a likely missing owner. Operations Analytics is a conditional candidate. Intelligence Analytics may be unnecessary. Those three conclusions cannot be made exact without response-level database characterization.

### Provisional contract sketch — not approved or implemented

Operation: `opportunity.deepParse`; owner: `breakdowns`; timing: `synchronous`.

- Direct: `breakdownOpportunities`, `breakdownHidden`.
- Derived, already source-supported: `breakdownReadiness`, `breakdownMaterialMatches`, `analyticsIndustryTrends`, `commandCenter`.
- Derived pending database response proof: `analyticsOperations`, `analyticsIntelligence`.
- Forbidden: submissions, workflow self-tapes, callbacks, audition notes, persisted Calendar, Journal, recommendations, submission queue, relationships, relationship Analytics, material assets, reusable self-tapes, material-performance Analytics, Career tasks, dashboard preferences and executive briefs.

No conditional typed variant is justified yet. A single stable owner set after every successful deep parse is preferred if characterization proves it; otherwise the preflight must be revisited rather than inventing payload-based conditions.

### Exact missing characterization

One prerequisite is missing: a disposable-PostgreSQL `opportunity.deepParse` contract characterization suite using real HTTP and isolated rows. It must prove in one bounded suite:

1. Standard deep parse creates one succeeded parse run and replaces, rather than accumulates, parsed sections.
2. Parsed role replacement removes obsolete roles and creates the exact current roles, including casting/character records where applicable.
3. A visible opportunity can move to hidden/travel-exception/discarded when deadline, classification or eligibility evidence demands it.
4. A previously hidden rule-owned opportunity can return to visible when reparsed evidence permits it; if this is impossible under current defaults, record that fact rather than forcing a fixture.
5. Intelligence, trust, demographic, eligibility, watch-list, deadline and classification fields persist as one committed result.
6. Workflow self-tape, recommendation, Journal, persisted Calendar, submission, queue, callback, audition-note, relationship, material asset, reusable-tape, Career-task and executive-brief rows remain unchanged.
7. Readiness and material-match endpoint responses change when the reparsed roles/visibility actually affect them.
8. Industry-trend and command-center endpoint responses change for a fixture whose parsed classification/role/visibility/deadline affects those projections.
9. Operations and Intelligence Analytics responses are compared before/after to determine whether they belong in derived or forbidden sets, including an existing linked Calendar-event case for Operations alerts.
10. An injected post-parse/pre-commit failure rolls back opportunity fields, sections, roles, character/casting records and parse-run state with no partial owner response change.
11. Repeating the request establishes exact retry semantics: one additional parse-run per success, current sections/roles replaced without duplication, and no unrelated historical rows appended.

After that suite passes, frontend implementation characterization would need registry completeness/disjointness, real public owner keys, exact hook invalidation, failure invalidating nothing, background-refetch isolation, visible/hidden owner coverage, forbidden-owner assertions, no root/broad invalidation, and proof that manual-parse and strategy contracts remain unchanged. None of those tests are added in this preflight.

### Decision

**DECISION B — ONE MISSING BACKEND CHARACTERIZATION.** Do not type `opportunity.deepParse` yet. The one missing prerequisite is the disposable-PostgreSQL deep-parse contract suite specified above. This is not a product blocker: current backend semantics are sufficiently defined to characterize without deciding new policy. It is an evidence blocker because rollback, retry/replacement, bidirectional list movement, and the exact Operations/Intelligence Analytics owner classification are not proven.

Confirmed facts: parser sections and roles are replacement relationships; parse runs are created per invocation; opportunity intelligence/trust/deadline/eligibility can alter owner-visible fields; readiness, material matches, industry trends and command center read mutated opportunity data; workflow, recommendations, Journal, Calendar rows, submissions and queue are not written; current invalidation is focused and non-broad. Rejected assumptions: deep parse shares the manual-parse contract; all currently invalidated keys are necessary; Operations Analytics is unaffected merely because Calendar rows are unchanged; source inspection alone proves transaction rollback; one-way visible-to-hidden evidence is enough. Unresolved gaps are limited to the named characterization suite: rollback/failed-run persistence, retry replacement, hidden-to-visible feasibility, and exact Operations/Intelligence Analytics response effects.

Implication for later work: the next prompt may add only this disposable-PostgreSQL characterization and update the ledger with its evidence. It must not type invalidation in the same step. After characterization, a fresh gate must decide whether the contract is ready.

Step 64 verification: 47 focused frontend hook/registry/viewer/hidden-review tests and 32 focused backend parsing/deadline/intelligence/classification/eligibility tests passed. Static search confirms no `opportunityDeepParse` registry entry was added, and `git diff --check` passed. Only this ledger changed for the preflight.

## 27. Step 65 — typed deep-parse implementation gate

**Gate result: stopped.** Step 64 records `DECISION B — ONE MISSING BACKEND CHARACTERIZATION`, not `DECISION A`. Therefore Step 65 did not add `opportunity.deepParse`, did not modify the hook, and made no production, backend, query, UI, callback, parsing, retry, endpoint, payload, response, request-graph, feedback, or extraction change.

The blocking prerequisite remains exactly one disposable-PostgreSQL deep-parse contract characterization suite covering section/role replacement, parse-run retry semantics, bidirectional visibility movement where possible, persisted intelligence/trust/eligibility effects, unaffected record families, response-level readiness/material/Analytics/command-center effects, and injected rollback. The suite must resolve whether `analyticsOperations` and `analyticsIntelligence` are derived or forbidden owners. It must be completed in a characterization-only step; typing invalidation in the same step remains unapproved.

Confirmed fact: the requested implementation gate explicitly required Step 64 Decision A. Rejected assumption: Step 64's provisional contract sketch or likely owner list constitutes implementation approval. Unresolved gaps and later implications remain exactly those recorded in Step 64. A fresh implementation prompt is permitted only after the characterization prerequisite is complete and a subsequent ledger gate explicitly records Decision A.

## 28. Step 66 — disposable-PostgreSQL deep-parse characterization

This characterization-only step completed the one prerequisite named by Step 64. It did not add a typed contract, change a hook or query key, alter invalidation, modify backend production behavior, change parser/history semantics, or add UI.

### Suite and controlled boundary

The suite lives in `backend/tests/contract_smoke/test_contract_smoke.py` and runs through the real HTTP endpoint, FastAPI dependency/session boundary, PostgreSQL schema, ORM relationships, service transaction, and derived read endpoints. Only `BreakdownIntelligenceEngine.parse` is replaced with deterministic parser output so no model or network result can vary. The controlled result has two ordered sections, two ordered replacement roles, a future deadline, Acting Role classification, distinct facts/inference and summaries. The rollback scenario additionally replaces `Session.commit` for one isolated request; the pre-persistence scenario replaces `run_for_opportunity` with a deterministic failure. Database persistence and downstream services are not mocked.

The baseline uses stale parser/trust metadata, facts/inference, classification, date-review ownership, demographics, scores, priority/risk, two obsolete roles and existing parse/section history. It also creates an unrelated opportunity/roles plus linked workflow, recommendation, Journal, Calendar, submission, queue, relationship, asset, reusable tape, Career task and executive brief records. IDs and update timestamps are captured before mutation.

### Persisted behavior

| Area | Characterized result |
| --- | --- |
| Authoritative opportunity | Same ID is updated; parser metadata, facts/inference, classification, deadline/date-review, demographic/eligibility, watch-list, trust, urgency/quality, priority and risk values reflect the committed enrichment result. |
| Parse history | Each successful request appends exactly one succeeded `Deep Parse` run. Identical retry appends a second run. A pre-persistence or failed-commit request appends none. |
| Parsed sections | Obsolete rows are deleted. Exactly the controlled `Roles`, `Dates` order remains. Retry deletes/recreates those rows rather than accumulating them. |
| Roles | Obsolete role rows are deleted. Exactly `New Detective`, `New Captain` remains in parsed order. Retry deletes/recreates them. Unrelated-opportunity role IDs are unchanged. A separate controlled duplicate fixture proves duplicate role names are preserved in input order on each parse, but do not accumulate across retry. |
| Character profiles | Current `CharacterIntelligenceEngine` emits SQLAlchemy relationship warnings and persists zero `CharacterProfile` rows for the replacement roles. This is characterized production behavior, not corrected here. |
| Visibility | A stale `needs_date_review` hidden row returns to the visible owner after valid controlled evidence. A visible row with an unresolved parsed deadline moves to hidden `needs_date_review`, disappears from the normal list and appears in `include_hidden`. |
| Rejected classification | Deep parse persists `Crew Job` and its rejection reason but manual-entry defaults leave `visibility_status=visible`. The normal list still excludes it through the main-classification filter; `include_hidden` returns it. Deep parse therefore changes effective list ownership without setting discarded status. |
| Travel ownership | No deterministic travel-exception transition is established by this fixture; travel ownership requires routing/travel evidence outside the controlled parser boundary. No transition was forced. |
| Atomicity | A failure at the final commit rolls back opportunity fields, visibility, parse runs, sections and roles. A parser-boundary failure before persistence changes none of them. |
| Retry | Opportunity values and list ownership remain stable under identical output; only parse history appends. Sections and roles are replaced again; unrelated records do not duplicate or change. |

The character-profile result rejects the source-level assumption that character intelligence necessarily persists a profile on this path. The rejected-classification result rejects the assumption that classification rejection and persisted discarded status are identical. Both are recorded as later correctness questions rather than compensated for in tests or production.

### Derived responses and final owner evidence

The controlled fixture compares response bodies before and after the committed mutation. The Calendar row is linked to the target opportunity so Operations can exercise its dereference path. Under that fixture, readiness, material matches, industry trends, command center and Operations dashboard materially change. Intelligence dashboard and material-performance Analytics remain byte-for-byte structurally equal. Underlying Calendar IDs/timestamps remain unchanged, so the Operations result is derived rather than a Calendar write.

| Owner | Response changes? | Frequency shown | Direct/derived | Later contract classification evidence |
| --- | --- | --- | --- | --- |
| Visible opportunities | yes | whenever classification/visibility/deadline membership changes | direct | direct |
| Hidden/review opportunities | yes | whenever rule/list membership changes | direct | direct |
| Readiness | yes | conditional on visible parsed opportunity/role state | derived | derived |
| Material matches | yes | conditional on visible text/role/archetype state | derived | derived |
| Industry trends | yes | conditional on classification/role/project inputs | derived | derived |
| Command center | yes | conditional on visible/deadline/priority inputs | derived | derived |
| Operations Analytics | yes | conditional; proven with an existing linked Calendar event | derived; Calendar row unchanged | derived |
| Intelligence Analytics | no | never for the controlled opportunity/intelligence/trust/classification changes | unaffected read owner | forbidden |
| Workflow self-tapes | no rows/values/timestamps changed | never in characterized path | unaffected persisted owner | forbidden |
| Recommendations | no rows/values/timestamps changed | never | unaffected persisted owner | forbidden |
| Journal | no rows/values/timestamps changed | never | unaffected persisted owner | forbidden |
| Persisted Calendar | no rows/values/timestamps changed | never | unaffected persisted owner | forbidden (distinct from Operations projection) |
| Submissions / queue | no rows/values/timestamps changed | never | unaffected persisted owners | forbidden |
| Relationships | no rows/values/timestamps changed | never | unaffected persisted owner | forbidden |
| Material assets / reusable tapes | no rows/values/timestamps changed | never | unaffected persisted owners | forbidden |
| Material-performance Analytics | response unchanged | never under controlled mutation | unaffected read owner | forbidden |
| Career tasks | no rows/values/timestamps changed | never | unaffected persisted owner | forbidden |
| Executive briefs | no rows/values/timestamps changed | never | unaffected persisted owner | forbidden |

The affected direct/derived responses are synchronous consequences of the single successful commit. A failed request has no successful response and leaves all characterized persistence unchanged. The suite does not prescribe frontend refetch ordering or make a successful mutation depend on background reads.

### Confirmed facts, gaps, and next gate

Confirmed: parse runs append per success; sections and roles replace; hidden-to-visible and visible-to-review movement are possible; classification filtering can change list ownership independently of `visibility_status`; readiness, material matches, industry trends, command center and conditionally Operations are affected; Intelligence and material-performance Analytics are unaffected; related persisted families remain unchanged; final-commit rollback is atomic; identical retry adds only parse history among the characterized secondary records.

Rejected assumptions: character profiles are persisted for replacement roles; a rejected classification sets discarded status for manual entries; Operations is forbidden because Calendar rows do not change; Intelligence belongs merely because the current hook invalidates it; source inspection alone was sufficient rollback evidence.

Remaining gaps: travel-exception entry/exit was not established without external routing evidence; the character-profile persistence warning is a separate production correctness concern; parse-history append-on-retry and rejected manual-entry visibility/classification semantics remain product/correctness questions. None blocks describing the observed owner set, but none is resolved here.

**Exact next gate:** a separate preflight may now decide whether the passing evidence is sufficient to approve `opportunity.deepParse`. It must independently record Decision A before implementation. If approved, that later implementation is limited to one registry entry, the canonical hook, registry/hook tests, this contract regression, and ledger; it must not include feedback, query, parser, backend or product-policy changes. This step does not record Decision A automatically.

Step 66 verification: the disposable PostgreSQL suite passed 15/15 (including the four deep-parse characterization scenarios); 42 focused parsing/deadline/classification/eligibility/character-intelligence/trust/executive-intelligence tests passed; the normal backend suite passed 166 with 15 disposable tests skipped by design. Frontend registry/hook regression passed 38/38 and the full frontend suite passed 288/288. ESLint, TypeScript no-emit, production build, static confirmation that `useDeepParseBreakdown` still uses its ad-hoc key list and no `opportunity.deepParse` registry entry exists, and `git diff --check` passed. Files changed by this step are limited to the contract-smoke test module and this ledger.

## 29. Step 67 — final deep-parse invalidation contract gate

This is a decision-only gate. It uses the Step 66 disposable-PostgreSQL persistence and response evidence rather than the provisional Step 64 sketch. No production source, hook, registry, query, backend behavior, UI, parser, retry behavior or test expectation changed.

### Step 66 evidence validation

| Required evidence | Classification | Gate consequence |
| --- | --- | --- |
| Successful parse-run persistence | proved | one committed success appends one succeeded run; opportunity owners carry parse history |
| Section replacement | proved | obsolete rows are deleted and controlled rows replace them in order; retry does not accumulate |
| Role replacement | proved | obsolete rows are deleted, current order and duplicate semantics persist, unrelated roles remain unchanged |
| Visible/hidden/other ownership transitions | proved for hidden-to-visible, visible-to-review and classification-filter ownership; travel transition unresolved | both authoritative opportunity list owners must be direct; travel evidence is not needed to distinguish another frontend cache key |
| Intelligence, trust, demographic and eligibility persistence | proved | authoritative opportunity owners change synchronously |
| Readiness response | conditionally proved | controlled role/visibility changes materially change the response; derived owner |
| Material-match response | conditionally proved | controlled parsed opportunity changes materially change the response; derived owner distinct from persisted assets |
| Industry-trend response | conditionally proved | controlled classification/role inputs materially change the response; derived owner |
| Command-center response | conditionally proved | controlled visible/deadline/priority inputs materially change the response; derived owner |
| Operations Analytics response | conditionally proved | changes with an existing linked Calendar event while that Calendar row remains unchanged; derived owner |
| Intelligence Analytics response | disproved as affected | controlled intelligence/trust/classification changes leave the response unchanged; forbidden owner |
| Unaffected record families | proved | IDs, update timestamps and counts remain stable for all characterized forbidden persisted owners |
| Complete rollback | proved | injected final-commit failure rolls back opportunity, visibility, run, section and role changes; pre-persistence failure changes nothing |
| Retry semantics | proved | identical retry appends only parse history among characterized secondary records and replaces sections/roles again |

The unresolved travel-exception fixture does not affect cache-owner classification: both normal and hidden/review data are served by the same two direct list keys already required by the proved transitions. The `CharacterProfile` persistence warning is a production correctness gap inside the authoritative opportunity domain, not evidence of a separate frontend owner. Neither requires conditional query-key selection or blocks the contract.

### Current hook comparison

`useDeepParseBreakdown` currently invalidates, in order:

1. `breakdownOpportunities`;
2. `breakdownHidden`;
3. `breakdownReadiness`;
4. `breakdownMaterialMatches`;
5. `analyticsIntelligence`;
6. `analyticsIndustryTrends`.

The first four and industry trends are evidence-supported. `commandCenter` and `analyticsOperations` are missing derived owners. `analyticsIntelligence` is unnecessary and must move to forbidden. The hook has no root, empty, broad-prefix, global-refresh or manual-refetch invalidation. It currently omits persisted Calendar, which is correct. The future hook change is only replacement of the ad-hoc spreads with `keysForContract(invalidationContracts.opportunityDeepParse)`.

### Final owner classification

| Owner | Step 66 evidence | Classification | Frequency | Exact key |
| --- | --- | --- | --- | --- |
| Visible opportunities | membership and persisted payload change | direct | always authoritative after success | `breakdownOpportunities` |
| Hidden/review opportunities | membership and persisted payload change | direct | always authoritative after success | `breakdownHidden` |
| Readiness | response changes from parsed role/visibility inputs | derived | conditional response effect; conservatively invalidate on success | `breakdownReadiness` |
| Material matches | response changes while assets remain unchanged | derived | conditional response effect; conservatively invalidate on success | `breakdownMaterialMatches` |
| Industry trends | response changes from classification/role inputs | derived | conditional response effect; conservatively invalidate on success | `analyticsIndustryTrends` |
| Command center | response changes from visible/deadline/priority inputs | derived | conditional response effect; conservatively invalidate on success | `commandCenter` |
| Operations Analytics | linked-Calendar response changes; Calendar row unchanged | derived | conditional on a linked event; conservatively invalidate on success | `analyticsOperations` |
| Intelligence Analytics | response unchanged | forbidden | never in characterized contract | `analyticsIntelligence` |
| Workflow self-tapes | rows/values/timestamps unchanged | forbidden | never | `workflowSelfTapes` |
| Recommendations | rows/values/timestamps unchanged | forbidden | never | `breakdownRecommendations` |
| Journal | rows/values/timestamps unchanged | forbidden | never | `journalEntries` |
| Persisted Calendar | rows/values/timestamps unchanged | forbidden | never; distinct from Operations projection | `calendarEvents` |
| Submissions | rows/values/timestamps unchanged | forbidden | never | `submissions` |
| Submission queue | rows/values/timestamps unchanged | forbidden | never | `breakdownQueue` |
| Relationships | rows/values/timestamps unchanged | forbidden | never | `relationships`, `relationshipAnalytics` |
| Material assets | rows/values/timestamps unchanged | forbidden | never; distinct from material-match projection | `materials`, `reusableSelfTapes` |
| Material-performance Analytics | response unchanged | forbidden | never | `analyticsMaterialPerformance` |
| Career tasks | rows/values/timestamps unchanged | forbidden | never | `careerTasks` |
| Executive briefs | rows/values/timestamps unchanged | forbidden | never | `executiveBriefs` ledger sentinel |

Callbacks, audition performance notes and dashboard preferences are also forbidden because the endpoint neither writes nor derives those owners. Parse history has no separate query key and is returned through the direct opportunity owners; no key is added for it.

### Final proposed contract — approved, not implemented

Registry property: `opportunityDeepParse`; operation: `opportunity.deepParse`; owner: `breakdowns`; timing: `synchronous`.

- Direct: `breakdownOpportunities`, `breakdownHidden`.
- Derived: `breakdownReadiness`, `breakdownMaterialMatches`, `analyticsOperations`, `analyticsIndustryTrends`, `commandCenter`.
- Forbidden: `submissions`, `workflowSelfTapes`, `callbacks`, `auditionPerformanceNotes`, `calendarEvents`, `journalEntries`, `careerTasks`, `breakdownRecommendations`, `breakdownQueue`, `relationships`, `relationshipAnalytics`, `materials`, `reusableSelfTapes`, `analyticsIntelligence`, `analyticsMaterialPerformance`, `dashboardPreferences`, `executiveBriefs`.
- Reason: deep parse synchronously replaces parse/section/role and opportunity intelligence state, can change both authoritative list memberships, and changes readiness, material-match, industry, command-center and conditionally Operations projections. It does not write Calendar or other forbidden record families, and Step 66 proves the Intelligence and material-performance responses unchanged.

No conditional registry variant is required. The registry represents conditional derived effects with one conservative exact-key set after success, as existing contracts already do. Always invalidating the exact Operations key is bounded, deterministic and safer than guessing from mutation payload or mounted Calendar state. It does not imply a persisted Calendar invalidation. Background invalidation remains isolated through `invalidateInBackground`.

### Decision and implementation gate

**DECISION A — APPROVE TYPED DEEP-PARSE INVALIDATION.** Step 66 resolves every evidence item that affects owner classification. Approve only one `opportunityDeepParse` registry entry, migration of the canonical `useDeepParseBreakdown` success invalidation to `keysForContract`, focused registry/hook tests, continued disposable-PostgreSQL regression coverage and this ledger update.

Required implementation tests:

- registry operation coverage includes `opportunity.deepParse`;
- exact direct, derived and forbidden arrays match this gate and are disjoint with no duplicate keys;
- every affected public key maps to a real production query owner;
- the canonical hook calls `keysForContract(invalidationContracts.opportunityDeepParse)` and invalidates the exact ordered keys after success;
- a failed deep parse invalidates nothing;
- rejected background refetches do not turn a successful mutation into failure;
- no root, broad feature-prefix, global refresh or manual refetch is introduced;
- forbidden owners, specifically Intelligence Analytics and persisted Calendar, are not invalidated;
- Operations Analytics is invalidated while Calendar is not;
- manual-parse and strategy contract definitions and hook behavior remain unchanged;
- all Step 66 PostgreSQL characterization, including rollback and retry, remains green;
- a deterministic mocked request graph proves one mutation request and only the contract-owned active refetches.

Forbidden adjacent work: feedback UI, parser/history/retry changes, backend changes, query keys or freshness, conditional registry redesign, `CharacterProfile` correction, travel behavior, product policy, component movement, demographic/reject invalidation, or any second mutation contract.

Stop if implementation requires a new query key, runtime payload guessing, a conditional registry redesign, backend behavior changes, or invalidating an owner outside the exact arrays above. A discrepancy must return to preflight rather than widen the contract.

**Exact next prompt scope:** implement only the approved `opportunityDeepParse` entry, canonical hook migration, specified contract/hook/request-graph tests, PostgreSQL regression confirmation and ledger implementation result. Do not combine it with feedback or any other correctness work.

Step 67 verification: Step 66 disposable PostgreSQL characterization passed 15/15; the normal backend suite passed 166 with 15 disposable tests skipped by design; all Breakdowns plus invalidation/query-policy tests passed 90/90; and the full frontend suite passed 288/288. ESLint, TypeScript no-emit, production build and `git diff --check` passed. Static search confirms no `opportunityDeepParse`/`opportunity.deepParse` registry entry exists and the canonical hook still uses its six-key ad-hoc list. This ledger is the only file changed by Step 67.

## 30. Step 68 — typed deep-parse invalidation implementation

**Gate result:** passed. Step 67 explicitly records `DECISION A — APPROVE TYPED DEEP-PARSE INVALIDATION` and defines the exact contract name, operation, owner groups, synchronous timing, conservative conditionality, canonical hook, tests, forbidden work and stop conditions. The existing registry can represent that contract without new query keys, runtime guessing or a conditional-registry redesign.

Implemented `invalidationContracts.opportunityDeepParse` with operation `opportunity.deepParse`, owner `breakdowns` and synchronous timing:

- Direct: `breakdownOpportunities`, `breakdownHidden`.
- Derived: `breakdownReadiness`, `breakdownMaterialMatches`, `analyticsOperations`, `analyticsIndustryTrends`, `commandCenter`.
- Forbidden: `submissions`, `workflowSelfTapes`, `callbacks`, `auditionPerformanceNotes`, `calendarEvents`, `journalEntries`, `careerTasks`, `breakdownRecommendations`, `breakdownQueue`, `relationships`, `relationshipAnalytics`, `materials`, `reusableSelfTapes`, `analyticsIntelligence`, `analyticsMaterialPerformance`, `dashboardPreferences`, `executiveBriefs`.

Conditional derived effects remain represented by one conservative exact-key set after every successful mutation. In particular, Operations is invalidated even when no linked Calendar event is currently mounted, but persisted Calendar is forbidden. Material matches are invalidated while persisted material assets are forbidden. Parse history has no separate key and remains available through the two direct opportunity owners.

`useDeepParseBreakdown` remains the sole canonical mutation hook and retains `deepParseBreakdown`, its endpoint, payload/response, callbacks, retry, pending/error and UI behavior. Its success path now calls `keysForContract(invalidationContracts.opportunityDeepParse)` instead of the ad-hoc `classificationKeys + opportunityAggregateKeys`. This adds the proven Operations and command-center owners and removes the disproven Intelligence owner. Failed mutations still execute no success invalidation. `invalidateInBackground` still uses `Promise.allSettled`, so a rejected background owner refetch cannot convert mutation success into failure. No query definition, key, stale time, mount policy, manual refetch, broad/root invalidation or global refresh was added.

Characterization-first tests initially failed only at the four intended seams: missing registry operation, absent exact contract, ad-hoc hook implementation and its static guard. After implementation, registry tests assert the exact contract object and ordered keys, disjointness and real public owners; hook tests assert exact typed invalidation, failure invalidating nothing and background-refetch isolation; the Breakdowns static boundary rejects ad-hoc/manual-refetch regression. Existing manual-parse and strategy contract assertions remain unchanged.

The deterministic mocked browser request graph performs exactly one `POST /opportunities/opp-1/deep-parse` and, for the active Breakdowns owners, one GET each for visible opportunities, hidden opportunities, readiness and material matches. It performs no Journal, Calendar, workflow-tape, Intelligence dashboard or global reload request, and the surrounding opportunity remains usable. The focused scenario passed three consecutive runs; the complete mocked browser suite passed 30/30.

Files changed by Step 68:

- `src/services/api/invalidationContracts.ts` and its test;
- `features/breakdowns/hooks/useBreakdownQueries.ts` and its test;
- `features/breakdowns/query-boundary.test.ts`;
- `e2e/deep-parse-invalidation.spec.ts` and the narrow deep-parse mock endpoint in `e2e/support/mockApi.ts`;
- this ledger.

The Step 66 PostgreSQL suite was not rewritten and passed 15/15, preserving replacement, ownership, rollback, retry and unaffected-family evidence. All Breakdowns plus registry/query-policy tests passed 95/95; the full frontend suite passed 293/293; the normal backend suite passed 166 with 15 disposable contract tests skipped by design. ESLint, TypeScript no-emit and production build passed.

Confirmed assumptions: the existing registry safely represents conditional derived effects conservatively; Operations and command center are real derived owners; persisted Calendar and Intelligence Analytics remain forbidden; parse history needs no new key; background invalidation remains isolated. Disproven assumptions: the old Intelligence invalidation was conservative or necessary; conditional Operations required payload logic; a manual refetch or query change was needed.

Remaining parsing debt is unchanged and outside this implementation: visible/hidden deep-parse feedback ownership, travel-exception characterization, `CharacterProfile` persistence warnings, parse-history product policy and rejected manual-entry classification/visibility semantics. Demographic invalidation, reject/archive, recommendation feedback and further extraction are also unapproved.

No next change is approved automatically. A fresh check-in is required before any deep-parse feedback, correctness repair, second invalidation contract or ownership work.

## 31. Step 69 — CharacterProfile persistence versus visible deep-parse feedback

This is an audit/prioritization step. No backend or frontend production behavior, ORM mapping, invalidation, parser, retry/history, classification, visibility, query or UI changed. One disposable-PostgreSQL characterization was added because source inspection and Step 66's warning could not by themselves distinguish transient intent from persisted-data loss.

### CharacterProfile model and ownership map

| Concern | Current behavior | Intended owner | Evidence | Risk |
| --- | --- | --- | --- | --- |
| Identity | UUID primary key; required `breakdown_id` and required unique `breakdown_role_id` | one profile per concrete `BreakdownRole` | migration 0039, ORM and schema | low ambiguity, high correctness significance |
| Role relationship | scalar `BreakdownRole.character_profile`, `uselist=False`, `all, delete-orphan`, `back_populates` | role owns lifecycle | ORM and unique FK | authoritative one-to-one child |
| Opportunity relationship | ordered `Opportunity.character_profiles`, `all, delete-orphan` | aggregate navigation/cascade | ORM and direct opportunity FK | dual relationship enrollment must share the session |
| Deletion | both FKs use database `ON DELETE CASCADE`; role/opportunity relationships use delete-orphan | replaced/deleted roles remove profiles | schema plus disposable seeded-obsolete-profile test | correctly removes obsolete rows |
| Creation | `CharacterIntelligenceEngine.run_for_opportunity` constructs a profile with child-side `breakdown` and `breakdown_role`, then assigns it to `role.character_profile`, but never adds it to the session | character-intelligence service within caller transaction | warning and zero persisted rows | confirmed data loss |
| Update | an existing persisted profile is updated field-by-field | same role-owned profile | service branch | correct when a row already exists |
| Serialization | `BreakdownRoleRead.character_profile` and frontend `BreakdownRole.character_profile` explicitly expose the persisted child | opportunity API | schemas/types/renderers | absence is user-visible |
| Orphans/duplicates | unique role FK prevents duplicate profiles per role; cascades remove seeded obsolete profile during replacement | role lifecycle | schema and disposable test | low orphan/duplicate risk after correct enrollment |

The migration creates a durable table with timestamps, two cascading FKs, a uniqueness constraint, domain checks and indexes. The Pydantic API schema embeds `CharacterProfileRead` under every role, and the frontend has a complete typed model and an “AI Character Interpretation” panel. This rules out an intentional transient object, dead relationship or derived-without-persistence contract.

### Creation, read and deletion call sites

- Create/update: `CharacterIntelligenceEngine.run_for_opportunity` is the only production constructor/updater. It is reached through opportunity create, description update, manual paste, deep parse, list-time missing-profile repair and hidden manual-role update (update followed by deep parse). Visible manual-role update uses the update enrichment path. All share the caller's session/transaction.
- Read: opportunity serializers and `BreakdownRoleDetails` expose the profile; recommendation scoring reads archetypes, traits and learning signals; readiness reads archetypes/confidence and uses them for role text/labels; industry/career intelligence reads role profiles; recommendation fit presentation reads profile archetypes. `BreakdownDetails` also selects a fitting role's profile for recommendation presentation.
- Delete: replacing `breakdown_roles` deletes obsolete role/profile rows by ORM/database cascade; opportunity deletion cascades both. No independent production delete endpoint exists or is needed.
- Tests: unit fixtures explicitly attach `CharacterProfile` to roles to prove readiness and recommendation-learning behavior, while character-engine unit tests currently test only pure `profile_for_role` output and therefore miss persistence enrollment.

Character intelligence is not duplicated in full on the role. Role columns/JSON retain source character text, fit score/explanation, compatibility inference and casting language, but profile-only archetypes, confidence evidence, traits, conflicts, arc, genre levels, requirements, recommended materials and AI summary are otherwise lost.

### Disposable PostgreSQL reproduction and fresh-session result

`test_character_profile_warning_is_persisted_data_loss` uses the real endpoint, schema, ORM and commit with only deterministic parser output stubbed. It seeds a real obsolete role/profile, deep parses into two controlled roles with character/archetype-compatible text, captures the exact SQLAlchemy `CharacterProfile ... not in session` warning, and proves:

- both new role rows persist with source description and compatibility inference;
- the mutation response contains `character_profile: null` for both roles;
- a wholly new SQLAlchemy session finds the same roles and zero profile rows;
- a fresh GET also returns both profiles as null, so the authoritative response is consistently missing rather than merely displaying an uncommitted object;
- the seeded obsolete profile is deleted with its obsolete role, leaving no orphan;
- a second identical deep parse reproduces the warning and still persists zero profiles.

The defect therefore causes cross-session persisted data loss, but not an immediate-versus-refresh mismatch: both responses consistently lack the data. Readiness falls back to text inference and cannot mark character intelligence ready; strategy/recommendation and learning paths lose profile archetypes/traits; the role viewer omits the AI interpretation. Hidden and visible contexts consume the same missing role response. Step 66 rollback remains atomic for the surrounding opportunity/role transaction; the future correction must add profile rollback assertions.

### Intended contract and existing-data risk

**Contract A — `CharacterProfile` is an authoritative persisted one-to-one child of a breakdown role.** This is established by the migration, unique non-null role FK, cascades, read schema, frontend model/UI and multiple downstream readers. Contract B is disproved by those active consumers; Contract C is disproved by the durable schema/serializer; Contract D is unnecessary.

Existing databases may contain roles with missing profiles because every creation path shares the faulty enrollment branch. Properly persisted historical profiles can exist (tests/manual rows or earlier paths) and are updateable. Database constraints make duplicate-per-role and FK-orphan rows unlikely; obsolete profiles are cascade-cleaned. The local developer database could not be counted because its PostgreSQL socket was unavailable in this environment, so exact production prevalence is unresolved. That does not block correcting future/session repair behavior.

No schema migration is required. Existing `OpportunityService.list` already detects missing role profiles and reruns character intelligence, so once enrollment is corrected, visited opportunities can repair opportunistically. A one-time administrative backfill is optional only if immediate complete historical coverage is required; no destructive cleanup is justified. The correction must not fabricate profiles for roles that no longer exist.

### Smallest backend correction sketch — not implemented

In `CharacterIntelligenceEngine.run_for_opportunity`, retain the existing generated data and relationship assignment, but explicitly enroll each newly generated `CharacterProfile` in `self.db` before flush (or the characterized equivalent assignment through the owning relationship that demonstrably enrolls it). The caller retains transaction ownership; the engine must not commit.

- Creation: one profile per persisted role, with both FKs populated.
- Existing profile: update in place, preserving its ID.
- Replacement/retry: obsolete role/profile cascade-delete; replacement roles receive exactly one new profile each; duplicate role names receive separate profiles because ownership is by role ID.
- Rollback: profile inserts/deletes roll back with role/section/opportunity changes.
- Response: immediate and fresh GET serialize equivalent non-null profiles.
- Migration: none; schema already encodes the contract.
- Invalidation: none; existing opportunity owners already refresh role/profile payloads.

Reject any implementation that commits inside the engine, changes parser output, moves authoritative data into vague role JSON, weakens uniqueness, alters cascades, adds a profile endpoint/query key, or bundles historical backfill.

### Visible deep-parse feedback ownership

| Context | Trigger owner | Hook owner | Pending shown? | Error shown? | Draft/state risk |
| --- | --- | --- | --- | --- | --- |
| Visible role fallback | `OpportunityManager` fallback action | manager's single `useDeepParseBreakdown` | no; duplicate clicks possible | no; rejected promise escapes local UI | no text draft, but expanded context should remain |
| Visible `BreakdownViewer` | viewer callback to manager `runDeepParse` | same manager hook | no | no | viewer selection/details should remain |
| Hidden details/viewer | callback to `HiddenOpportunityReview.deepParseOpportunity` | hidden review's own canonical hook | shared `role=status` shown | local `role=alert` shown | selection/details preserved |
| Hidden manual-role workflow | `HiddenOpportunityActionForm` | form update hook then its deep-parse hook | form `saving` disables submit | form-local alert | role draft preserved on failure |

Visible feedback is independently implementable in `OpportunityManager` with per-opportunity pending/error state, local status/alert and duplicate prevention; it needs no hook movement, invalidation change, hidden redesign, generic framework or route-wide state. Refreshed authoritative details are sufficient success feedback unless a later product decision requests an explicit announcement. Focus ownership needs characterization because the action exists in both fallback and viewer surfaces.

### Candidate comparison

| Criterion | CharacterProfile correction | Deep-parse feedback |
| --- | --- | --- |
| Persisted data correctness | high: confirmed missing durable child rows | none |
| User-visible silent failure | high: AI character interpretation is always absent | high: visible mutation failure is not announced |
| Cross-session inconsistency | high persisted loss, though immediate/fresh responses consistently agree on null | none |
| Historical data risk | medium: existing roles may remain unprofiled until repaired | none |
| Ownership clarity | high: schema establishes role-owned one-to-one | high: manager owns visible action |
| Product-policy blocker | none | no blocker for pending/error; success-message policy remains optional |
| Migration burden | none for correction; optional later backfill only | none |
| Regression surface | bounded backend transaction/relationship lifecycle | bounded visible UI interaction |
| Immediate testability | high in disposable PostgreSQL | high in component/browser tests |
| Unlocks later work | restores readiness/recommendation/rendering inputs | improves visible parsing usability |

Persisted correctness outranks presentation feedback because the warning is reproducible data loss across all character-intelligence creation paths and affects active downstream consumers.

### Product/data gates

1. Authoritative profile: established by code/schema — Contract A.
2. One-to-one with roles: established by unique non-null FK and `uselist=False`.
3. Obsolete profiles deleted: correctness requirement already established by cascades and reproduction.
4. Duplicate role names: established by schema; separate role IDs may each own one profile.
5. Existing-data repair: correction requires no migration; opportunistic repair is available, while complete immediate backfill is a later data-operations decision.
6. Immediate response may contain transient profiles: disproved; current response contains null, and future response must contain only committed/flush-enrolled data.
7. Visible/hidden feedback sharing: not relevant to selected backend correction; current ownership is intentionally separate.
8. Explicit deep-parse success message: later product/accessibility decision, not a blocker.
9. Disable repeat while pending: correctness/accessibility requirement for the later visible-feedback candidate, not selected now.

### Decision and next boundary

**DECISION A — CORRECT CHARACTERPROFILE PERSISTENCE.** A reproducible persisted-data correctness defect exists, and the intended Contract A is unambiguous. Approve one backend correctness boundary only: explicitly enroll newly generated profiles within `CharacterIntelligenceEngine.run_for_opportunity`, preserve caller transaction ownership and existing cascades, and add the required persistence/regression coverage. Do not add visible deep-parse feedback in the same step.

Required pre-/post-fix tests:

- reproduce and then eliminate the session warning;
- persist complete profiles for multiple roles and preserve full field values;
- immediate mutation response equals a fresh-session GET for profile payloads;
- duplicate role names receive distinct profiles keyed by distinct role IDs;
- second parse replaces roles/profiles without duplicates;
- obsolete profiles are deleted with obsolete roles;
- injected rollback restores old roles/profiles and persists no replacements;
- retry creates exactly one profile per current role and no unrelated rows;
- create, description update, manual paste, visible manual role and hidden manual-role/deep-parse paths share correct persistence where they invoke the engine;
- no orphan rows or cross-opportunity/role FK mismatch;
- readiness and recommendation consume persisted archetypes after fresh session;
- response schema and role renderer remain compatible;
- no migration is required and the Step 66/68 invalidation/request graphs remain unchanged.

Expected files: `backend/app/services/character_intelligence_engine.py`, focused character-intelligence tests, disposable contract characterization, and this ledger. A model/migration change is not expected; stop if the fix requires one. Forbidden adjacent work: feedback UI, invalidation/query changes, parser/history/retry policy, visibility/classification, backfill script/migration, generic intelligence framework, role rendering changes, travel characterization, or another correctness fix.

Stop if explicit session enrollment does not persist both FKs through replacement, changes transaction ownership, cannot preserve rollback/cascade behavior, or reveals that a schema migration/backfill is mandatory. Return to a single prerequisite rather than widening scope.

**Explicit next-step gate:** implement only the approved CharacterProfile enrollment/lifecycle correction and its characterized backend coverage. Deep-parse feedback requires a fresh check-in after that correction is complete.

Step 69 verification: disposable PostgreSQL contract smoke passed 16/16, including the new warning/data-loss/fresh-session characterization; 21 focused character intelligence, parser, readiness, recommendation, executive-intelligence and trust tests passed; the normal backend suite passed 166 with 16 disposable tests skipped by design. Role-renderer/deep-parse/Breakdowns plus invalidation/query-policy coverage passed 95/95; the relevant mocked deep-parse browser request graph passed 1/1; and the full frontend suite passed 293/293. ESLint, TypeScript no-emit, production build, architecture/import tests and `git diff --check` passed. The only files changed by this preflight are the disposable contract test module and this ledger.

## 32. Step 70 — CharacterProfile persistence correction

**Gate result:** passed. Step 69 explicitly records `DECISION A — CORRECT CHARACTERPROFILE PERSISTENCE`, an authoritative persisted one-to-one role-owned contract, the exact service seam, required characterization and stop conditions. Current code matched that diagnosis: new `CharacterProfile` instances were assigned to relationships but were not enrolled in the caller's SQLAlchemy session.

Characterization-first baseline: the disposable PostgreSQL suite passed 14 tests and failed the two new persistence assertions. Both failures found zero profile rows, null response profiles and the exact `Object of type <CharacterProfile> not in session` warnings for the opportunity and role relationships. This ruled out a fixture-only warning and confirmed the approved persisted-data defect. An older Step 66 assertion that explicitly expected zero profiles then failed after the correction; it was replaced with the authoritative one-profile-per-role, replacement and cleanup assertions rather than preserving compensating behavior.

The implementation is limited to `CharacterIntelligenceEngine.run_for_opportunity`: when no profile exists, it constructs and assigns the same derived profile as before and explicitly calls `self.db.add(profile)` when a database session is present. Existing profiles still update in place. The engine still performs only its existing flush; the caller retains commit and rollback ownership. With no database session, pure derivation behavior is unchanged. No model, relationship, cascade, schema, migration, parser, endpoint, payload, response schema, retry/history policy, visibility/classification, frontend query or invalidation behavior changed.

Disposable PostgreSQL now proves:

- complete profiles persist for multiple roles and serialize non-null in the mutation response;
- a fresh independent session and fresh GET return profile payloads equivalent to the immediate response;
- duplicate role names receive distinct profiles owned by distinct role IDs;
- replacement and retry remove obsolete role/profile rows and leave exactly one current profile per role;
- injected transaction and parser failures restore the prior role/profile set and persist no replacements;
- opportunity creation and manual text parsing return enrolled profiles through the shared engine path;
- no orphan, cross-role or duplicate profile row is introduced;
- readiness sees persisted archetypes and strategy/recommendation consumes the persisted profile;
- obsolete seeded profiles remain deleted through the established role cascade.

State and transaction ownership remain unchanged: `BreakdownRole` owns the one-to-one profile lifecycle, the opportunity service owns the surrounding transaction, and API opportunity owners remain authoritative. The correction adds no request, query key, refetch or invalidation. It changes no frontend behavior except that existing role payload fields now contain the durable data the schema already promised. Accessibility and deep-parse feedback are untouched.

Files changed by Step 70 are limited to the character-intelligence service, disposable PostgreSQL contract characterization and this ledger. Confirmed assumptions: explicit enrollment is sufficient with the existing schema and cascades; no migration is required; retry and replacement are role-ID-based; rollback remains atomic; readiness and recommendation are real consumers. Disproven assumptions: relationship assignment alone enrolled the child; the warning was harmless; replacement profiles could remain transient without user-visible loss.

Remaining debt is deliberately unchanged: existing historical rows may need opportunistic repair when read (already supported) or a separately approved backfill decision; visible deep-parse feedback, retry-history policy, travel-exception characterization and rejected manual-entry visibility semantics remain outside this boundary. No backfill, feedback work or next correction is approved automatically. A fresh check-in is required.

Step 70 verification: disposable PostgreSQL contract smoke passed 16/16 with no CharacterProfile session warning; focused character/readiness/recommendation/parser tests passed 10/10; the normal backend suite passed 166 with 16 disposable tests skipped by design. Breakdowns plus invalidation/query-policy coverage passed 95/95 and the full frontend suite passed 293/293. ESLint, TypeScript no-emit, production build, existing architecture tests/static search and `git diff --check` passed. The full mocked browser suite passed all Breakdowns and deep-parse scenarios and 29/30 overall; its sole failure was the previously documented timing-sensitive Journal immediate-return assertion observing one Journal request. That exact scenario then passed 3/3 in isolation, confirming no request-graph change from this backend-only correction.

## 33. Step 71 — final Breakdowns backend correctness sweep

This is an audit-only checkpoint. No frontend or backend production code, parser, invalidation, query, component, UI or test expectation changed.

### Ownership and transaction findings

The eight reviewed mutations use three bounded ownership patterns:

1. `OpportunityService` owns create, update, manual text parse, deep parse, visible manual-role updates, hidden-review updates/approval/rejection and the surrounding commit. Role/section replacement, demographic/eligibility, character intelligence, trust, manual-override history, self-tape projection and work-event helpers participate in that caller-owned transaction. Exceptions before commit are rolled back when the request session closes; protected deletion also handles and rolls back an integrity race explicitly.
2. `StrategyAgent.analyze` owns recommendation append and commits one newly enrolled `AgentRecommendation`. Retry appends another historical recommendation by current product behavior; it neither replaces nor transiently loses a record.
3. Recommendation feedback explicitly enrolls and flushes `RecommendationFeedback`; `LearningAgent.analyze` reads that same transaction, enrolls a new `LearningInsight`, and commits both together. Because a valid recommendation necessarily has an actor FK, the branch that invokes learning is the normal endpoint path. A pre-commit exception remains rollbackable by request-session close.

`BreakdownRoleService.sync_from_details` clears the role-owned collection and attaches new roles and casting-language children to the enrolled opportunity aggregate. Database/ORM cascades remove obsolete roles, casting-language rows and character profiles. Create, description update and deep parse can synchronize roles once before shared enrichment synchronizes them again. This is redundant and may merit later performance simplification, but disposable PostgreSQL proves the final set is unique by role ID, obsolete children are deleted, duplicate role names remain distinct records and rollback restores the prior aggregate. It is not a correctness defect.

The Step 70 profile enrollment was the only reviewed constructor that both produced an authoritative durable child and relied on relationship assignment in a way SQLAlchemy rejected. After the correction, static search found no analogous Breakdowns-owned transient child path, and both the normal and disposable suites pass with SQLAlchemy `SAWarning` promoted to an error. The remaining emitted warnings are unrelated library/datetime deprecations, not ORM ownership warnings.

### Mutation correctness matrix

| Mutation | Correctness risk | Proven | Remaining concern |
| --- | --- | --- | --- |
| Create | multi-helper atomic aggregate creation; role/profile/workflow/journal/calendar projection enrollment | disposable create contract, atomic injected failure, profile persistence, fresh reads and warning-as-error pass | role synchronization is redundant; performance only |
| Update | partial fields plus optional reparse, role replacement, manual override history and workflow projection in one commit | shared service transaction, existing update/hidden mutation contracts, profile engine/cascade coverage | no dedicated injected-failure test for every update field combination; no contradictory runtime evidence |
| Manual parse | replace parsed output/roles, preserve unrelated owners, commit once | manual-parse contract, shared engine profile assertion, focused invalidation and request-graph characterization | retry replaces parse-owned rows and appends parse history by current contract; product history policy remains separate |
| Deep parse | widest aggregate replacement and derived projection surface | Step 66 PostgreSQL characterization, Step 68 typed owner contract, rollback, retry, visibility movement, duplicate-name and Step 70 profile coverage | visible pending/error UX remains; not backend correctness |
| Manual role | update `role_details`, rebuild authoritative role children and enrich profiles | same canonical PATCH/update service for visible and hidden forms; role/profile uniqueness and cascade paths proven | visible and hidden UI choose whether deep parse follows; intentional caller behavior, not persistence divergence |
| Hidden review | uses canonical update/manual-parse/deep-parse/approve/reject endpoints rather than a hidden-only persistence path | hidden ownership/rollback/request tests and shared service inspection | product semantics for rejected manual-entry visibility remain unresolved, but no transaction defect found |
| Strategy generation | explicitly enrolled append-only recommendation committed atomically; downstream reads use persisted opportunity/profile state | disposable append/visibility/unaffected-owner test, retry count, typed invalidation and fresh profile recommendation test | retry idempotency versus append is a product-history decision, not a discovered persistence defect |
| Recommendation feedback | feedback and derived learning insight are enrolled and committed together by the invoked learning owner | source transaction trace, FK ownership, feedback-learning behavior tests and clean warning-as-error suite | lacks a dedicated disposable rollback/retry characterization; no evidence of loss, orphaning or divergence |

### Confirmed facts, rejected assumptions and gaps

Confirmed facts:

- current Breakdowns aggregate children have explicit enrollment or working aggregate cascade ownership;
- role/profile/section replacement removes obsolete children and preserves distinct duplicate-named roles;
- deep-parse rollback is complete across opportunity fields, parse runs, sections, roles and profiles;
- shared visible/hidden mutation paths converge on the same backend services;
- derived readiness, material-match, industry, command-center and Operations responses have characterized ownership, while forbidden record families remain unchanged;
- all reviewed persistence paths are clean when SQLAlchemy warnings are errors.

Rejected assumptions:

- the CharacterProfile failure indicates a general ORM enrollment pattern;
- repeated role synchronization necessarily creates duplicate persisted children;
- hidden review owns a divergent backend mutation implementation;
- strategy or feedback records rely on implicit request-end commit;
- remaining deep-parse feedback and retry-history questions are backend transaction defects.

Unresolved gaps are coverage/product gaps rather than evidence of a correctness defect: recommendation-feedback rollback/retry has no dedicated disposable test; exact prevalence of historical missing profiles remains unknown; retry-history and rejected-manual-entry semantics remain product decisions; redundant role synchronization has not been performance-measured. These do not change owner classification or invalidate the currently proven transactions.

Implication for later work: backend correctness no longer outranks the known local UX/accessibility debt. A later checkpoint may prioritize visible deep-parse feedback or another explicitly selected UX path. Historical profile repair/backfill and recommendation-history policy require separate evidence/product gates and must not be smuggled into that work.

### Decision

**DECISION A — BACKEND CORRECTNESS COMPLETE.** Within the audited Breakdowns mutation boundary, CharacterProfile was an isolated session-enrollment defect. No remaining persistence, transaction, ORM ownership, cascade, rollback, retry, projection or shared-path defect is supported by current source and disposable PostgreSQL evidence. This decision does not claim exhaustive absence of future bugs; it records that no backend correction is more important than the remaining known UX work and approves no implementation.

Step 71 verification: the 16-test disposable PostgreSQL contract suite passed with `sqlalchemy.exc.SAWarning` promoted to an error. The normal backend suite was also run with that warning category promoted to an error. No production or test file was changed; this ledger is the only Step 71 modification.

## 34. Step 72 — visible deep-parse feedback preflight

This is a decision-only preflight. No component, hook, API, invalidation, query, parser, backend, request graph, UI or test behavior changed.

### Current flow and ownership

Visible deep parse has two rendered trigger surfaces for the same expanded opportunity:

- the `OpportunityManager` role fallback shown when `breakdown_roles` is empty;
- the route-private `BreakdownViewer` missing-role fallback, whose existing callback delegates directly to the manager.

Both call `OpportunityManager.runDeepParse`, and the manager owns the one visible `useDeepParseBreakdown` hook. Current `runDeepParse` simply awaits `mutateAsync`. It has no catch, no per-ID pending guard, no local error, no status announcement and no focus policy. A rejected promise therefore escapes the local UI. Two rapid clicks, including one on each rendered surface, can send duplicate requests before either result is visible.

Hidden deep parse is not a third visible trigger owned by the manager. `HiddenOpportunityReview` owns a separate canonical hook instance, hidden-record selection, `actionError`, a section-level `role=status`, a section-level `role=alert`, and the focus destination appropriate to a record that may leave hidden ownership. `HiddenOpportunityActionForm` separately owns its update-then-deep-parse manual-role workflow with form-local saving/error state. These paths share the API/hook contract but intentionally do not share presentation state.

| Context | Trigger owner | Hook owner | Pending today | Error today | Focus today | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| Visible role fallback | manager card | manager | none | none | browser remains on button until refresh may remove it | correct locally in manager |
| Visible viewer fallback | viewer callback to manager | manager | none | none | same; button may disappear after authoritative roles arrive | use same manager per-ID state |
| Hidden viewer/details | hidden review callback | hidden review | generic hidden-section status | section alert | no explicit deep-parse return policy | retain separate; not Step 72 implementation |
| Hidden manual role | hidden action form | form update hook then form deep-parse hook | form `saving` | form-local error | form lifecycle | retain separate composite workflow |

### Exact approved visible feedback boundary

**Feedback owner:** `OpportunityManager`, because it already owns the hook, authoritative opportunity props, expansion state and both visible callbacks. Do not move the hook into `BreakdownViewer`, create another hook instance, or move state to the page/panel.

**State:** add only per-opportunity visible action state:

- `deepParsePendingById: Record<string, boolean>` for rendering;
- a synchronous pending-ID ref/set so two clicks in the same render frame cannot race the React state update;
- `deepParseErrorById: Record<string, string | null>`;
- stable expansion-toggle refs and the invoking `HTMLElement` captured from `document.activeElement` for focus return.

Do not store an `Opportunity` snapshot, mutation result or copied server state. Different opportunity IDs may remain independently usable; the duplicate guard applies only to the target ID.

**Pending placement:** render one `role="status"` per active opportunity inside that opportunity's expanded card, immediately after its summary/trust/review notices and before the detail grids. The text should identify the local action, for example `Deep parsing Spring Forward…`. Both visible triggers consume the same per-ID pending value. Extend the narrow `BreakdownViewer` contract with at most one explicit boolean such as `deepParsePending`; do not pass a mutation, state bag or generic action object.

**Duplicate prevention:** the manager's synchronous ID guard must return before calling `mutateAsync` for an already-running target. Both visible `Run deep parse` buttons must also be actually disabled while that ID is pending. A narrow optional `disabled` capability on the existing `TextAction` primitive is acceptable; a mutation-aware button, generic feedback wrapper or controller is not. Pending one opportunity must not disable another opportunity's actions or its paste/manual-role controls.

**Error placement:** render one persistent local `role="alert"` in the same expanded-card feedback area, using standardized `errorMessage(caught, "Could not deep parse this opportunity.")`. Clear only that opportunity's prior deep-parse error when it retries. The alert must not replace or collapse current details, roles, original text, parse history or other action errors. Associate both trigger surfaces with the local feedback IDs where practical; do not introduce a route-wide alert or toast-only failure.

**Focus:** capture the invoking button before awaiting the mutation. On failure, preserve the expanded card and return focus to that still-connected invoking button after the alert renders. On success, authoritative role refresh may remove either conditional trigger, so return focus to the stable expansion toggle for that opportunity. No dialog opens and no focus trap is warranted. Refocus must be scoped to the target ID and must not fire for background invalidation completion.

**Success behavior:** no separate success banner is approved. The refreshed authoritative roles, parsed sections/history and scores remain the visible success result. The pending announcement ends and the expansion toggle receives focus; no draft exists to reset.

### Request and query contract

Keep the canonical `useDeepParseBreakdown` hook, `POST /opportunities/{id}/deep-parse`, payload/response, retry behavior and typed `opportunity.deepParse` invalidation unchanged. A failed request performs no success invalidation. A successful request starts exactly one mutation and the existing contract-owned background invalidation. In the current mocked Breakdowns route, the active request graph is:

- one `POST /opportunities/{id}/deep-parse`;
- one GET each for visible opportunities, hidden opportunities, readiness and material matches;
- no Journal, persisted Calendar, workflow self-tape, Intelligence dashboard or global reload request.

Other typed derived owners may refetch only when mounted under the existing registry contract. Background refetch rejection remains isolated through `invalidateInBackground` and must not become a visible mutation failure.

### Visible versus hidden decision

**Keep the flows separate.** They share the canonical mutation hook and invalidation contract, not state ownership. Visible feedback belongs to the manager's expanded opportunity card and returns focus to its expansion toggle. Hidden feedback belongs to hidden selection/form owners and may need to return focus to the hidden disclosure or surviving list action when reclassification removes the record. Unifying them would lift route-private state, duplicate selection semantics or require a generic mutation framework. Step 72 approves no hidden-review change. A later hidden-only accessibility check may refine its generic status, duplicate prevention and focus behavior without coupling it to visible state.

### Characterization required before implementation

Add these tests against the current visible implementation first and demonstrate the expected failing feedback baseline without changing request behavior:

1. Each visible trigger sends the same one-ID deep-parse request through the manager-owned hook.
2. A deferred request announces local pending state and disables both trigger surfaces for that opportunity.
3. A second click, including cross-trigger clicking, sends no duplicate POST.
4. A different opportunity and unrelated paste/manual-role controls remain usable.
5. Failure renders the meaningful API message in a local alert, preserves expansion/details/history and invalidates nothing.
6. Failure returns focus to the initiating button and retry clears only that target's error.
7. Successful retry performs the exact typed invalidation/request graph, displays refreshed authoritative output and returns focus to the stable expansion toggle.
8. A background owner-refetch failure does not create the local mutation alert or convert success to failure.
9. Hidden review retains its own hook/state and is unchanged; no manager state or feedback props cross into it.
10. Static architecture rejects hook movement, a second visible hook, QueryClient/query-key props, generic action/feedback bags, route-wide error state and direct API calls.

Focused mocked Playwright should cover pending, cross-trigger duplicate prevention, failure, focus, retry success, surrounding-card stability and the exact request graph; run it three times. Existing deep-parse invalidation, manual-parse feedback, viewer, hidden-review, hook and registry tests must remain green.

### Decision and stop conditions

**DECISION A — APPROVE ONE VISIBLE DEEP-PARSE FEEDBACK CORRECTION.** A future implementation may add only the manager-owned per-ID pending/error/duplicate/focus behavior, the one narrow viewer pending prop, disabled `TextAction` support if needed, focused tests and this ledger update. It must not move hooks, change invalidation, add success/product semantics, alter hidden-review behavior or introduce generic mutation infrastructure.

Expected files: `BreakdownManager.tsx`, `BreakdownViewer.tsx`, the narrow `TextAction` declaration in `BreakdownDetails.tsx`, their focused tests, one focused mocked Playwright scenario and this ledger. Stop if the correction requires a second visible hook, hidden/visible shared state, a QueryClient or query-key prop, a generic feedback/controller abstraction, request/invalidation changes, component extraction, backend changes or product-policy decisions.

**Exact next prompt scope:** implement only the approved visible deep-parse local feedback boundary after the characterization-first baseline. Do not modify hidden review, deep-parse invalidation, parsing behavior or any other action feedback.

Step 72 verification: 57 focused manager/viewer/hidden-review/hook/registry tests passed, confirming current ownership and unchanged contracts. The existing deterministic deep-parse request-graph browser scenario passed 1/1 with the exact focused request set. No production or test file changed; this ledger is the only Step 72 modification.

## 35. Step 73 — visible deep-parse feedback implementation

**Gate result:** passed. Step 72 explicitly approved one manager-owned visible feedback correction with per-ID pending/error state, synchronous duplicate prevention, local status/alert, focus return, one narrow viewer pending prop, unchanged hook/invalidation/request ownership and separate hidden flows.

Characterization-first baseline: six existing manager tests passed. The two new deep-parse cases failed only at the approved seams: there was no `role="status"`, neither trigger disabled, no local `role="alert"`, no focus policy, and the rejected `mutateAsync` promise surfaced as an unhandled rejection. No existing manual-parse, form, viewer or hidden-review expectation required change.

`OpportunityManager` remains the sole visible owner of `useDeepParseBreakdown`. It now owns:

- `deepParsePendingById` and `deepParseErrorById`, keyed only by opportunity ID;
- a synchronous pending-ID set that closes the same-render-frame duplicate-click window;
- stable per-opportunity expansion-toggle refs;
- the initiating button captured at invocation for failure focus return.

`runDeepParse` clears only the target's old error, announces local pending state, invokes the unchanged canonical mutation once, catches and normalizes a meaningful API error, and always clears only the target's pending state. Failure preserves expansion, current details, roles, original text, parse history and every unrelated action. It returns focus to the still-connected initiating button. Success relies on the authoritative query refresh for visible output and returns focus to the stable expansion toggle because either conditional deep-parse trigger may disappear. No success banner, draft or copied mutation response was added.

The expanded opportunity card renders one target-local `role="status"` (`Deep parsing {project}…`) or `role="alert"` after the existing summary/trust/review notices and before the detail grids. The role fallback and `BreakdownViewer` fallback reference the same feedback ID and are both disabled for that opportunity while pending. `TextAction` gained only ordinary `disabled` and `aria-describedby` support. `BreakdownViewer` gained one optional `deepParsePending` boolean; it still owns no hook, query, mutation, feedback state or server copy. Paste and manual-role actions remain enabled, and hidden review was not modified.

Hook, endpoint, payload, response, retry policy, parser, backend and typed `opportunity.deepParse` invalidation are unchanged. Failure sends one POST and performs no success invalidation. Successful retry sends one POST and, in the active mocked route, refetches exactly visible opportunities, hidden opportunities, readiness and material matches once each. It sends no Journal, persisted Calendar, workflow self-tape, Intelligence dashboard or global reload request. Background invalidation remains isolated by the existing hook infrastructure.

Tests added:

- manager pending announcement and two-trigger disabled/duplicate behavior;
- manager local failure, surrounding-details preservation, focus return and successful retry;
- viewer pending disables only deep parse while paste/manual role remain usable;
- static ownership protection for exactly one manager hook and a query-free viewer;
- deterministic mocked browser failure/pending/focus/retry and exact request graph.

The focused browser scenario passed three consecutive runs. The complete mocked suite passed 31/31, including the unchanged focused deep-parse owner graph and manual-parse feedback regression. Breakdowns plus registry/query-policy tests passed 99/99; the full frontend suite passed 297/297; the normal backend suite passed 166 with 16 disposable tests skipped by design. ESLint, TypeScript no-emit and production build passed. The Opportunities route chunk changed from the Step 72 baseline of 118.97 kB / 28.24 kB gzip to 120.15 kB / 28.61 kB gzip; no new dependency or shared main-bundle increase was introduced.

Confirmed assumptions: the manager can own both visible trigger surfaces without hook movement; a synchronous ID guard is needed in addition to rendered disabled state; authoritative refresh remains sufficient success feedback; focus can return locally without extraction; hidden feedback remains independent. Disproven assumptions: hook-level `isPending` alone would express per-opportunity state; a generic feedback controller, toast, route-wide state or hidden-flow change was necessary.

Remaining debt is outside this boundary: hidden deep-parse status specificity/duplicate/focus behavior, strategy and demographic feedback, reject/manual-role alert semantics, retry-history product policy and other unapproved UX work. No next change is approved automatically; a fresh check-in is required.

## 36. Step 74 — recommendation-feedback contract preflight

### Frontend ownership and request map

Recommendation feedback has two independent route-private owners, not one shared form owner. `RecommendationPanel` in `BreakdownDetails.tsx` owns one `useRecommendationFeedback` mutation, selected-recommendation state, an open recommendation ID, per-ID reason drafts and one local success message. Its recommendation card and selected-detail rendering are two controls over that same owner state. `MergedAuditionReadinessPanel` in `BreakdownReadiness.tsx` owns a second hook instance and the same shape of readiness-local state. `RecommendationFeedbackControls` is a controlled renderer and owns no hook or server state.

| Concern | Current behavior | Correct owner | Defect | Risk |
| --- | --- | --- | --- | --- |
| Target | Canonical recommendation ID from authoritative props | Each panel owner | No | Low |
| Draft | Per-ID reason arrays; one form may be open per panel | The initiating panel | No copied server state | Low |
| Payload | `feedback_type`, `fit_reasons`; UI sends no notes | Feature hook/API | No | Low |
| Pending/duplicate | Hook pending state is not presented and controls remain enabled | Local panel/form | Yes | Identical append-only history can be created |
| Error/retry | `mutateAsync` rejection is not caught; no local alert; reasons survive because reset follows success | Local panel/form | Yes | Silent failure and unhandled rejected promise |
| Success/focus | Local success text, close and reason reset after the full request; no live semantics or focus restoration | Local panel/form | Accessibility gap | Medium |
| Refresh | Hook invalidates recommendations only | Canonical hook | Semantically wrong owner | Unnecessary GET and stale command center |

There is no optimistic update, manual refetch, route-wide error or durable copied recommendation state. Because each panel has one mutation instance, its pending state is shared across that panel's recommendation controls; the two panels can independently submit the same recommendation. A later UI correction can remain local: pending announcement, same-owner duplicate guard, local alert, preserved reasons, retry, success-only reset and scoped focus require no hook movement, query change, extraction or generic controller. It should follow invalidation correctness rather than bundle both changes.

### Backend persistence, transaction and retry evidence

`POST /agents/recommendations/{id}/feedback` validates `RecommendationFeedbackCreate`, loads the recommendation, constructs and flushes one `RecommendationFeedback`, then invokes `LearningAgent.analyze` in the same request `Session`. The learning agent reads all non-demo feedback for the actor, constructs one `LearningInsight`, calls `commit`, refreshes it, and returns. That commit atomically persists the already-flushed feedback and new insight; the route then refreshes and serializes the feedback as `RecommendationFeedbackRead`. It does not update the recommendation.

The Step 74 disposable-PostgreSQL test proved a successful request creates exactly one feedback and one new learning insight with the intended actor, opportunity and recommendation context. The response ID and fields match the fresh-session persisted feedback. The latest insight contains the submitted signal. An identical retry creates a distinct second feedback and a distinct second insight and increments the learned feedback counts; no row is replaced or deduplicated. A deterministic exception after insight enrollment and flush but before commit leaves neither the third feedback nor the third insight, proving request-session rollback is atomic at that boundary. The original recommendation remains present and unchanged.

| Record family | Effect | Transaction owner | Frontend read owner |
| --- | --- | --- | --- |
| Recommendation feedback | Always append one | Learning-agent commit in route session | None |
| Learning insight | Always append one for a valid recommendation actor | Learning-agent commit in route session | None; dormant server history used by later strategy/executive reads |
| Agent recommendation | Never changed | — | `breakdownRecommendations` |
| Command-center priority response | Conditionally changes because `ExecutiveAgent` reads the latest insight | Derived after commit | `commandCenter` |
| Future strategy result | May change when a later strategy mutation reads latest learning weights | Separate future transaction | No current cached response changes at feedback time |
| Opportunity, roles/profiles, readiness inputs | Unchanged | — | Breakdowns owners |
| Submissions, queue, Journal, persisted Calendar, workflow tapes | Unchanged | — | Auditions/Breakdowns/Journal/Calendar owners |
| Relationships, material assets, reusable tapes, preferences | Unchanged | — | Their feature owners |
| Analytics persisted records, Career tasks, executive briefs | Unchanged | — | Their feature owners |

The database characterization compared the recommendation response and authoritative opportunity response before/after and counted roles, character profiles, submissions, queue, Journal, Calendar, workflow tapes, relationships, assets, reusable tapes and travel preferences; all were unchanged. Source traces show readiness, material matches and all Analytics endpoints do not read feedback or learning insights. The recommendations list does not embed feedback. Dashboard recommendation widgets share `breakdownRecommendations`, so they also remain unchanged. There is no recommendation-detail query, feedback-history query or learning-insight query in the frontend.

### Derived responses and query owners

| Owner | Response changes? | Frequency | Classification | Evidence |
| --- | --- | --- | --- | --- |
| `breakdownRecommendations` and Dashboard recommendation widgets | No | Never | Forbidden | Exact before/after list equality; schema has no feedback field |
| Feedback/history | Persisted rows change | Always | No frontend owner | No GET/query exists |
| Learning insights | Persisted rows change | Always | No frontend owner | Only POST `/learning/run`; no frontend query exists |
| `commandCenter` | Yes | Conditional on the learning signal changing executive priorities | Derived | Disposable test changed `/agents/executive/priorities`; `/command-center` delegates priorities to the same `ExecutiveAgent` |
| Career intelligence | No current response owner reads latest insight | Never at feedback time | Forbidden | Career query/API inventory |
| Intelligence and industry Analytics | No | Never | Forbidden | Service dependency trace |
| Readiness and material matches | No | Never | Forbidden | Service dependency trace and unchanged opportunity/material records |
| Material-performance Analytics | No | Never | Forbidden | Recommendation row and material/submission records unchanged |
| Executive briefs and Career tasks | No | Never | Forbidden | Persisted snapshots/tasks are not regenerated |

The changed feedback and insight rows are dormant server state with no dedicated frontend query owner. This does not require inventing a query: the one existing cached response capable of changing is the exact `commandCenter` owner. Future strategy generation reads the new insight during its own request and its existing typed contract refreshes the resulting owners.

### Current invalidation and proposed contract

`useRecommendationFeedback` currently calls `invalidate(breakdownKeys.recommendations)` only after success. It has no typed registry entry, root/prefix invalidation, inline raw query array, manual refetch or duplicate invalidation. Failure runs no success invalidation. The shared invalidator uses background `Promise.allSettled`, so refetch rejection does not change mutation success. The current recommendation invalidation is unnecessary rather than compensatory: recommendation rows and responses do not embed feedback. It also misses the conditionally changed command-center response.

The current registry can express the bounded correction without runtime guesswork. Proposed, not implemented:

- Contract: `invalidationContracts.recommendationFeedbackCreate`
- Operation: `recommendation.feedbackCreate`
- Owner: `breakdowns`
- Timing: `synchronous`
- Direct owners: none, because feedback/learning history has no frontend query owner
- Derived owners: `commandCenter`
- Forbidden owners: every other public invalidation owner, explicitly including `breakdownRecommendations`, opportunities/hidden/readiness/material matches/queue, all Auditions, Journal, Calendar, relationships, Materials, all Analytics and Career tasks; also Dashboard preferences and executive briefs
- Conditionality: no runtime branch; conservatively invalidate the exact command-center key on every success because its response can conditionally change
- Canonical hook: `useRecommendationFeedback`, replacing only its recommendations-key invalidation with `keysForContract(...)`

Required implementation tests: registry identity/timing/exact groups and disjointness; public key resolution; exact hook invalidation on success; no invalidation on failure; background-refetch isolation; no root/broad key; no recommendation or other forbidden request; deterministic command-center-only request graph when mounted; existing create/update/manual-parse/deep-parse/strategy contracts unchanged; and the Step 74 PostgreSQL append/atomicity/retry characterization remaining green.

### Product gates and priority decision

Append-only feedback and learning insights, synchronous analysis, identical retry duplication and success-only draft clearing are established current behavior. Atomic feedback/insight persistence is a backend correctness requirement and is proved. Pending/error announcement and duplicate prevention are accessibility/correctness requirements for a later local UI step. Edit/delete policy, whether duplicates should eventually be prevented, and whether feedback should be embedded in recommendation responses are product decisions, but none blocks declaring current cache ownership. Feedback does not update an existing recommendation's ranking; it influences later strategy generation. The current success message can remain during the invalidation-only step.

| Criterion | Typed invalidation | Local feedback |
| --- | --- | --- |
| Authoritative stale-data risk | Removes stale conditional command-center priority and an unnecessary recommendation refetch | Does not correct cache ownership |
| Invisible failure risk | Unchanged | Corrects the primary UI defect |
| Historical duplication risk | Unchanged, but request graph becomes correct first | Can prevent concurrent duplicates locally; retry policy remains product debt |
| Ownership clarity | Exact canonical hook and public command-center key | Two clear panel-local owners |
| Backend burden | Completed PostgreSQL characterization | Low |
| Product-policy blocker | None | None for pending/error; duplicate-history policy remains separate |
| Registry/query readiness | Ready; exact key exists, empty direct set is representable | Depends on preserving the corrected contract later |
| Regression surface | Registry, hook and focused tests only | Two UI contexts and focus behavior |
| Unlocks later work | Establishes authoritative request graph before UI tests | Should follow this contract |

**DECISION A — TYPE RECOMMENDATION-FEEDBACK INVALIDATION.** Persistence, atomicity, retry behavior, response effects and query ownership are sufficient. The next boundary is exactly one `recommendation.feedbackCreate` typed contract plus the canonical `useRecommendationFeedback` migration, contract/hook/request-graph tests and ledger update. Expected implementation files are `services/api/invalidationContracts.ts` and its tests, `features/breakdowns/hooks/useBreakdownQueries.ts` and its tests, a focused mocked request-graph test if needed, and this ledger; the PostgreSQL characterization normally remains unchanged.

Forbidden adjacent work: no local feedback UI, edit/delete/deduplication policy, backend change, new query, recommendation extraction, generic feedback/invalidation framework, another contract, demographic/reject work or recommendation semantics change. Stop if the registry cannot accept an empty direct set, the canonical hook requires runtime owner guessing, or the exact command-center key cannot be exercised without broad invalidation. A fresh check-in is required after the typed contract; local recommendation-feedback UI is not automatically approved.

Confirmed facts: feedback and insight append and commit atomically; retry duplicates both; recommendations and their response are unchanged; command-center priority output can change; raw feedback/learning history has no frontend query owner; current recommendation invalidation is unnecessary. Rejected assumptions: recommendations embed latest feedback; every learning-related Analytics or Career response changes; a missing raw-history query prevents exact derived invalidation; UI and invalidation must be corrected together. Unresolved product questions are limited to feedback edit/delete/deduplication and retry-history policy; none affects this cache contract.

**Exact next prompt scope:** implement only `invalidationContracts.recommendationFeedbackCreate` and migrate only `useRecommendationFeedback` to it, preserving request, response, UI and backend semantics. Do not begin local feedback correction.

## 37. Step 75 — typed recommendation-feedback invalidation implementation

**Gate result:** passed. Step 74 explicitly approved Decision A, named `invalidationContracts.recommendationFeedbackCreate` / `recommendation.feedbackCreate`, and bounded implementation to the registry, canonical hook, focused tests and ledger. The registry supports an empty direct set and exact command-center derived ownership without a runtime condition.

Characterization-first baseline: 43 existing focused assertions passed. Three new assertions failed only at the approved seam: the registry operation and entry were absent, and the hook still invalidated unchanged recommendations. The Step 74 disposable-PostgreSQL characterization remained green before production work, proving one feedback plus one learning insight per success, atomic rollback, append-on-retry behavior, and unchanged recommendation/opportunity/unrelated records.

Implemented contract:

- owner: `breakdowns`;
- operation: `recommendation.feedbackCreate`;
- timing: `synchronous`;
- direct owners: none, because persisted feedback and learning histories have no frontend query owner;
- derived owners: `commandCenter` only;
- forbidden owners: every other public owner, including `breakdownRecommendations`, opportunities/hidden/readiness/material matches/queue, Auditions, Journal, Calendar, relationships, Materials, all Analytics and Career tasks, plus Dashboard preferences and executive briefs;
- conditional behavior: none in the registry. The exact command-center key is conservatively invalidated after every committed success because its priority response can conditionally change.

`useRecommendationFeedback` remains the sole canonical hook and now delegates only to `keysForContract(invalidationContracts.recommendationFeedbackCreate)`. The former ad-hoc recommendations invalidation was removed. Endpoint, payload, response, mutation function, callback behavior, append-only persistence, synchronous learning, retry semantics, component/form state, pending/error presentation, query keys, stale times and both panel-local UI owners are unchanged.

Failure runs no success invalidation. Successful feedback remains successful when the command-center refetch rejects because the established invalidator uses background `Promise.allSettled`. There is no root/prefix invalidation, manual refetch, duplicate invalidation or new query owner. The deterministic mounted-Breakdowns browser graph is exactly one feedback POST: recommendations do not refetch and inactive command center does not issue an immediate GET; its exact cache entry is marked stale for its next owner mount. The focused browser scenario passed three consecutive runs.

Tests added or extended cover exact contract metadata and groups, disjointness through the shared registry suite, public command-center key resolution, exact canonical-hook keys, failure invalidating nothing, background-refetch isolation, no broad/root key, no recommendation refetch, and the mocked request graph. The disposable PostgreSQL test continues to prove persistence, transaction and retry behavior without frontend mocks.

Confirmed assumptions: recommendations do not require invalidation; an empty direct owner set is valid; `commandCenter` is the only current derived response owner; inactive exact-key invalidation causes no immediate request; background failure remains isolated. Rejected assumptions: the prior recommendations refresh was necessary or compensated for missing learning history; a dedicated learning query, runtime condition, broad Analytics refresh or UI change was needed.

Remaining recommendation debt is unchanged: both local feedback owners still lack accessible pending/error handling and duplicate-submit prevention; feedback edit/delete/idempotency and retry-history policy remain product decisions. The unselected UI correction is not approved automatically. Any further change requires a fresh check-in.

## 38. Step 76 — recommendation-feedback UI preflight

### Separate ownership maps

| Concern | `RecommendationPanel` | `MergedAuditionReadinessPanel` |
| --- | --- | --- |
| Hook owner | One route-private `useRecommendationFeedback` instance | One separate route-private `useRecommendationFeedback` instance |
| Draft owner | `feedbackReasons` keyed by recommendation ID | Independent `feedbackReasons` keyed by recommendation ID |
| Target identity | Authoritative recommendation prop ID; the same ID can render in its card and selected-detail surface | Recommendation derived from authoritative opportunity/recommendation props |
| Pending exposed | No | No |
| Error exposed | No; rejected `mutateAsync` escapes the `void submitFeedback(...)` call | Same silent/unhandled rejection path |
| Draft preserved on failure | Yes accidentally, because clearing follows the awaited request | Yes for the same reason |
| Reset after success | Clears only submitted ID reasons, closes the open form, sets one panel-global message | Same |
| Duplicate risk | Rapid/same-frame clicks and the card/detail surfaces can submit the same ID concurrently | Rapid/same-frame clicks and reopen/direct-button actions can submit concurrently |
| Stable focus target | Direct action button survives; `This Fits Me` trigger survives after its Save form closes | Same within the expanded readiness row; expansion toggle is an additional stable row target |
| Surrounding UI | Remains rendered on success/failure; recommendation cannot disappear from feedback or command-center invalidation | Expanded row remains unless the user collapses it; feedback does not change recommendation/readiness ownership |

Both owners currently allow only one `feedbackOpenFor` ID at a time, but drafts for other IDs remain in their maps. In `RecommendationPanel`, card and selected-detail controls for the same recommendation both become open when that ID is selected, so “one open ID” does not mean “one rendered form.” Each panel's one TanStack mutation exposes `isPending`, variables, error and reset at mutation-instance scope, but that scope is too coarse for concurrent different recommendation IDs and cannot synchronously close the same-render-frame duplicate window. The correct future state is panel-local and keyed by recommendation ID: a rendered pending map/set, a synchronous pending-ID ref/set, per-ID error and success maps, and per-ID focus references. No recommendation object should be copied.

### Duplicate and draft lifecycle

Current buttons can issue duplicate append-only requests through rapid double click, Enter followed by click, two same-ID control surfaces in the primary panel, or another direct feedback button before React exposes mutation pending state. Native button keyboard activation works for direct feedback types, but the `This Fits Me` reason area is a `div`, not a form, so it has no native form-submit seam. A future correction should make only that existing reason area a semantic form, use a submit button, and keep Cancel/direct feedback buttons as `type="button"`.

A synchronous ID guard is required in addition to rendered disabled state. It must cover every feedback control for that ID within one owner, release in `finally`, and leave other IDs and unrelated opportunity actions usable. It must not coordinate across panels: two separately initiated submissions are valid under current append-only behavior. After completion, the same ID may intentionally submit again.

The only stored draft fields are `fit_reasons`; `feedback_type` is chosen by the invoked button, and the current UI does not expose `notes`. Reasons initialize to an empty array, are controlled per ID, have no required-field validation, and may be submitted empty. Cancel/close and switching IDs do not clear reasons. Failure preserves the complete reason list and target; retry reuses it. Success clears only that ID and closes the open reason form. Local component unmount loses drafts, which is existing route-local behavior and is not a persistence defect. Because feedback neither changes nor invalidates recommendations, authoritative rerender does not remove the target.

Future editing should clear only that ID's stale error, not its draft or another ID's state. Starting any retry should clear the target's old error and success acknowledgement. No validation rule should be invented.

### Error, accessibility, success and focus contracts

The base request layer converts network, FastAPI string detail, structured message, and validation-detail arrays into `ApiError`; `errorMessage(caught, "Could not save recommendation feedback.")` preserves the meaningful message without exposing response objects or traces. A learning-agent exception returns as the same atomic mutation failure proved by PostgreSQL. There is no special recommendation-level authentication UI contract; any server-provided permission message remains meaningful through `ApiError`. Both current owners fail to catch the rejected promise.

The shared controlled renderer already has one clear per-recommendation visual boundary, so future pending and error content belongs inside it. Use a recommendation-specific `role="status"` while pending and `role="alert"` for failure, with stable IDs and `aria-describedby` on that recommendation's controls where practical. Disable all same-ID feedback buttons across duplicate primary-panel surfaces while pending, but not other IDs or unrelated actions. Use a `fieldset`/`legend` or equivalent association for the reason checkboxes and a real form for native Enter submission. No global live region or toast is warranted.

**Success decision: Option B — retain a short explicit local acknowledgement.** No recommendation or feedback history visibly changes after success, so closure/reset alone is ambiguous. Current behavior already displays “Feedback saved. Future recommendations will learn from this.” The future correction should retain that wording, scope it by recommendation ID inside the local feedback boundary, and expose it with non-interruptive status semantics. It persists until that target starts another action, edits/reopens, or the owner unmounts; no timer/dismissal framework is approved.

Focus is independent of background command-center invalidation. Capture the initiating button before awaiting. On failure, keep the form/content and return focus to that still-connected button after the local alert renders. On success from a direct feedback button, return focus to the same surviving button. On success from `Save Feedback`, the form closes, so return focus to that recommendation's surviving `This Fits Me` trigger. If the primary card and selected-detail surfaces both exist, return to the exact initiating surface's surviving trigger, not merely the first matching ID. In readiness, preserve the expanded row and use its exact initiating/trigger control; the row is not removed by this mutation.

### Cross-panel and request ownership

The same recommendation can appear in both panels simultaneously. Submitting in one does not update the other's draft, pending, error or success state, and it should not: cross-panel suppression would require route-level coordination or a generic controller. Independent user actions may append two feedback records under established backend behavior. Accidental duplicates are prevented only within the initiating local owner.

Success remains one `POST /agents/recommendations/{id}/feedback`, followed by exact typed invalidation of the command-center cache entry. On Breakdowns that owner is inactive, so there is no immediate GET. There is no recommendation, feedback-history, learning-history, Journal, Calendar, workflow, Analytics or global-reload request. Failure is one failed POST, no success invalidation or follow-up request, and the complete local draft remains. A background command-center refetch on another mounted composition must not control local focus or error state.

### Approved implementation shape and tests

The smallest safe implementation keeps both canonical hooks where they are. In each owner add only per-ID pending/error/success state, a synchronous pending-ID guard and initiating/trigger focus refs. Extend the existing `RecommendationFeedbackControls` controlled contract narrowly with the target-local pending/error/success values, disabled/description wiring and an initiating-element-aware submit callback. Convert only the reason block to a semantic form. Small duplicated orchestration in the two owners is preferable to a shared hook/controller because their render and focus lifecycles differ. No extraction is justified.

Characterization-first implementation tests must cover, for both owners where the seam exists: complete draft payload; native form submission; local pending status; same-ID button disabling; same-frame duplicate prevention including primary card/detail cross-surface clicks; different-ID and unrelated-action usability; meaningful local alert; complete draft/target/surrounding-content preservation; failure focus; target-only stale-error clearing; retry with the same draft; target-only success reset; other draft preservation; direct-button and Save-form success focus; local success status; one POST with the typed contract unchanged; no success invalidation on failure; panel independence; no hook movement or generic infrastructure. Focused Playwright must cover failure, preserved reasons, retry, success, focus, duplicate prevention and the exact request graph, repeated three times.

Product gates:

- Append-only feedback/learning, completed identical later submissions, success-only draft clearing and form closure are established behavior.
- Same-frame duplicate prevention and failed-draft preservation are correctness requirements.
- Local pending/error and a discoverable success acknowledgement are accessibility/usability requirements.
- Success acknowledgement duration is established here as owner-local persistence until the next target action/unmount; no timed behavior.
- Cross-panel simultaneous submissions remain permitted by current ownership and append semantics.
- Edit, delete, backend idempotency and historical deduplication are deferred product decisions irrelevant to this boundary.

**DECISION A — APPROVE BOTH LOCAL OWNER CORRECTIONS.** Both panels have clear independent ownership and can receive one behavior-consistency correction through their existing shared controlled renderer without hook movement, cache/backend changes, extraction or route-wide state.

Exact approved boundary: local pending/status/error/success, synchronous same-owner per-ID duplicate prevention, draft-preserving retry, success-only target reset, native reason-form submission and scoped focus behavior in `RecommendationPanel` and `MergedAuditionReadinessPanel`. Expected files are `BreakdownDetails.tsx`, `BreakdownReadiness.tsx`, focused recommendation/readiness tests, one focused mocked Playwright scenario/support fixture if needed, and this ledger.

Forbidden adjacent work: hook or typed-contract changes, new queries, backend/persistence/retry-policy changes, cross-panel coordination, edit/delete/idempotency, recommendation extraction, a generic feedback hook/controller/live-region system, another mutation or unrelated accessibility cleanup. Stop if implementation requires route-level state, copying recommendation records, a second hook in either owner, changing the request graph, changing append semantics, or resolving edit/delete/deduplication policy.

Confirmed facts: there are two hook instances and two independent owners; the primary panel can render duplicate same-ID forms; hook-level pending is insufficient; drafts already preserve on failure; current rejection is unhandled; success needs visible acknowledgement because no rendered data changes; local focus targets survive. Rejected assumptions: the owners need centralized coordination; only one form can render per panel; recommendation refetch will signal success; disabling one submit button prevents cross-surface duplication; a generic framework or extraction is necessary. No unresolved correctness or ownership gap blocks the approved boundary.

**Exact next prompt scope:** implement only the approved local recommendation-feedback behavior in both owners and the narrow controlled renderer contract, characterization tests first. Preserve `recommendation.feedbackCreate`, backend semantics and request ownership exactly.

## 39. Step 77 — recommendation-feedback local UI implementation

**Gate result:** passed. Step 76 explicitly approved Decision A for both `RecommendationPanel` and `MergedAuditionReadinessPanel`, including per-ID pending/error/success state, a synchronous same-owner guard, native reason-form submission, local acknowledgement and scoped focus. Current code and the typed contract matched every stop condition.

Characterization-first baseline: the new owner-parameterized test reached the complete `This Fits Me` payload and demonstrated the intended defect in both owners: two same-frame Save clicks invoked `mutateAsync` twice. No existing test required silent failure or missing pending behavior to remain. After implementation, the focused owner, readiness, hook, registry and architecture suite passed 54/54.

Each owner retains exactly one `useRecommendationFeedback` instance and now independently owns `feedbackPendingById`, `feedbackErrorById`, `feedbackSuccessById` and a synchronous pending-ID set. No recommendation object, server response or route state is copied. The shared `RecommendationFeedbackControls` remains a controlled renderer; its narrow additions are target-local pending/error/success props and an initiating/success-focus-aware submit callback. No hook/controller or component extraction was introduced.

Pending begins synchronously for the recommendation ID, clears only that target's old error/success, renders local “Saving feedback…” status, sets `aria-busy`, and disables every feedback control for that ID across duplicate card/detail surfaces. The ref guard blocks same-frame click, Enter/click and cross-surface duplicates before React commits disabled state. Other recommendation IDs, opportunity actions and the other panel remain independent.

The reason area is now a labelled native form with a fieldset, submit button and button-derived submitter. Existing reason checkboxes remain controlled and accept an empty selection as before. Failure is caught locally, mapped through `errorMessage`, rendered as a target-local alert, and leaves the form, selected reasons, recommendation and surrounding content intact. The guard releases in `finally`, retry clears only that target's stale result and reuses the complete draft. Failure focuses the exact still-connected initiating button after the alert renders.

Atomic success clears only the submitted ID's reasons, closes only that ID's reason form, clears its stale error and stores the approved local status: “Feedback saved. Future recommendations will learn from this.” Other drafts and UI state remain intact. Direct-action success returns focus to its surviving initiating button. Save-form success returns focus to the exact `This Fits Me` trigger from the initiating render surface. Background command-center invalidation completion is not observed by local state or focus.

The two panels remain intentionally unsynchronized. The same recommendation may be submitted independently from both panels under established append-only behavior; only accidental duplicates inside one local owner are blocked. Hook, endpoint, payload, response, retry-history semantics, feedback/learning persistence and transaction ownership are unchanged.

Typed invalidation remains exactly `recommendationFeedbackCreate`: no direct owners, `commandCenter` derived, recommendations forbidden. Failure runs no success invalidation. Background invalidation failure remains isolated by the canonical hook. The mocked Breakdowns graph is one feedback POST per attempt, with no recommendation/history/Journal/Calendar/workflow/global request. The focused success and failure/retry scenarios passed three consecutive repetitions each (6/6).

Tests added cover both owners' complete payload, synchronous duplicate guard, local pending and disabled state, standardized alert, draft and target preservation, retry through native form submission, target-only reset, local success status, and failure/success focus. Static architecture now protects exactly one hook per owner, no QueryClient/manual invalidation in presentation, and continued canonical typed-contract use. Browser coverage proves pending, failure, preserved reasons, focus, retry success, duplicate prevention and the exact request graph.

Confirmed assumptions: both owners can remain local; the same-ID ref guard closes the pre-render duplicate window; one controlled renderer can expose semantics without owning mutation state; the success trigger survives; command-center invalidation is unrelated to focus. Rejected assumptions: hook `isPending` alone is sufficient; only one same-ID form can render in the primary panel; a route controller, global toast, recommendation refresh or cross-panel lock is necessary.

Remaining recommendation debt is product-level only: edit/delete, backend idempotency, retry-history/deduplication policy and any future feedback-history or learning-history UI. No such work is approved. A fresh check-in is required before another mutation correction or recommendation change.

## 40. Step 78 — rejected and manual-entry visibility contract preflight

This was an audit and characterization gate only. No production, schema, query, invalidation, parser, travel, or UI behavior changed.

### State model and terminology

| Field/rule | Storage / values | Writers | Readers | Contract evidence |
| --- | --- | --- | --- | --- |
| `visibility_status` | `opportunities`; `visible`, `hidden`, `discarded`, `travel_exception`; non-null default `visible` | discovery visibility, deadline validation, intelligence eligibility/travel, explicit reject/approve, manual-entry defaults | visible repository, hidden automation endpoint, materials, command center, capability counts | persisted workflow ownership, not merely a display label |
| `status` | `opportunities`; `open`, `closed`, `archived` | create/update, expired deadline, explicit reject | material matching requires `open`; normal opportunity list does not inspect it | lifecycle/archive signal independent from visibility, but currently incompletely enforced by readers |
| `breakdown_classification` | persisted constrained acting classes plus `Non-Acting Job`, `Crew Job`, `Unknown` | parser, discovery, update, explicit approval, manual default for trusted Unknown | visible, material, command-center and capability predicates | derived classification that also participates in list ownership |
| `hidden_by_rule` / `hidden_reason` | nullable rule and explanation | deadline, classification, eligibility/travel, reject/approve, manual defaults | hidden owner, trust UI, review explanations | persisted reason/precedence marker; no database enum |
| `manual_review_required` | persisted boolean | classification/date/travel/approve/reject/manual defaults | response and hidden UI | review hint, not an owner by itself |
| rejection/highlight fields | persisted text | parser and explicit reject | detail/trust UI | parser rejection and user rejection share one field, so provenance depends on `hidden_by_rule` and metadata |
| `source_metadata.user_rejected` | JSON boolean | explicit reject | not used as an ownership predicate | durable audit marker currently ignored by later automated visibility writes |
| `source_metadata.manual_entry_trusted` | JSON boolean | manual-entry defaults | descriptive only | marks trusted input, but does not define treatment of a confirmed non-acting classification |
| source type | constrained source enum including `Manual Entry` | create/update/import | manual defaults and trust | manual, agent and direct-email sources receive Unknown-classification protection |
| deadline metadata | JSON plus normalized deadline columns | parse/deadline service | deadline and intelligence visibility | `needs_date_review` and expiry have persisted ownership effects |
| demographic/eligibility/travel | persisted fields plus derived rules | demographic/intelligence services | visible/hidden/material/command-center | hard mismatch becomes discarded; travel exception and missing location become review owners |
| demo flag | persisted boolean | migration/data creation | every public list owner | independently excludes demo rows |

There is no `rejected` or `archived` visibility enum, no deleted timestamp, no opportunity restore endpoint, and no dedicated rejected/archive list endpoint. “Reject” is the user action; it writes `visibility_status=discarded`, `status=archived`, `hidden_by_rule=user_rejected`, reason/highlight metadata and an override log. “Discarded” is the persisted non-visible hard-exclusion state used for user rejection, non-acting classification, expired deadlines and hard eligibility. “Hidden” means review-required. “Travel exception” is its own persisted review category. `include_hidden=true` on `/opportunities` is a misleading name: it disables all visibility and classification predicates and returns a diagnostic superset, including discarded/archived records. It is not the frontend hidden owner. The actual hidden owner is `/automation/opportunities/hidden` and accepts only `hidden` and `travel_exception`, excluding user rejection and hard deal-breakers.

### Writer and reader maps

| Mutation | Ownership writes | Can change list membership | Transaction owner |
| --- | --- | --- | --- |
| Create/update/manual paste/deep parse | parser classification, deadline, intelligence eligibility/travel, trust; manual-source defaults may restore visible | yes, including without a final persisted visibility change for a manual non-acting classification | `OpportunityService` request transaction |
| Manual role update | opportunity update/enrichment path | conditionally | `OpportunityService.update` |
| Discovery/source ingestion | `_visibility` writes canonical hidden/discarded/travel/visible state | yes | discovery service |
| Hidden approval | acting classification, visible state, cleared review/rejection, override history | yes | `OpportunityService.approve_as_acting_breakdown` |
| Explicit reject/archive | discarded + archived + `user_rejected`, metadata and override history | yes | `OpportunityService.reject` |
| Deadline repair/list-time validation | expired -> discarded/archive; uncertain -> hidden review | yes; the list GET may commit repair | `OpportunityService.list` |
| Demographic/eligibility/travel | discarded, travel exception, hidden needs-info, or visible | yes | enclosing service request |

| Owner | Exact relevant predicate | Classification involved | Result for manual `Crew Job` |
| --- | --- | --- | --- |
| Visible opportunities | non-demo, `visibility_status=visible`, classification in main acting set | yes | excluded |
| Hidden review | non-demo, status in `hidden`/`travel_exception`, non-example source; filters hard/user rules | no acting-class predicate | excluded because status remains visible |
| Generic `include_hidden` | non-demo only (plus search/limit) | no | included diagnostically |
| Detail by ID | repository ID lookup | no | included |
| Material matches | `status=open`; normally visible + main acting classification | yes | excluded |
| Command center/capability visible counts | visible + main acting classification (+ real-data filter where applicable) | yes | excluded |
| Travel changes | `travel_exception` | no | excluded |

Two public representations overlap intentionally only in the diagnostic generic superset. Normal visible and hidden-review owners are disjoint. A persisted manual `Crew Job` with visible status belongs to neither UI owner and is reachable only by ID or the diagnostic superset. A user-rejected record is intentionally absent from both owners, but no archive owner exists.

### Disposable PostgreSQL transition evidence

| Scenario | Persisted state | Visible | Hidden review | Diagnostic superset | Finding |
| --- | --- | --- | --- | --- | --- |
| Acting/manual acting | visible + acting | yes | no | yes | coherent |
| Unknown trusted manual input with role signal | normalized to acting + visible | yes | no | yes | current manual-protection behavior |
| Unknown discovered input | hidden + classification-review rule | no | yes | yes | coherent review ownership |
| Uncertain deadline | hidden + `needs_date_review` | no | yes | yes | coherent and reversible after valid parse |
| Discovered non-acting classification | discarded + classification-rejected rule | no | no | yes | intentional hard exclusion, but no archive UI |
| Manual-entry `Crew Job` after deep parse | classification `Crew Job`, rejection reason, visibility visible, no rule | no | no | yes | orphaned from normal UI ownership |
| Explicit reject/archive | discarded + archived + `user_rejected` | no | no | yes | durable immediately; no restore endpoint |
| Reject then controlled acting deep parse | visible + archived + metadata `user_rejected=true`, rule cleared | **yes** | no | yes | proven correctness defect: parser/enrichment silently reopens archived user intent |
| Approved hidden record | acting + visible, review fields cleared | yes | no | yes | explicit approval path |
| Travel exception | deterministically covered by unit/service evidence; external routing not required for this decision | no | yes when source predicate permits | yes | separate persisted category |

The new focused PostgreSQL characterization passed and proves the reject/deep-parse contradiction after a fresh ORM expiration and HTTP owner reads. Existing controlled characterization continues to prove the manual `Crew Job` orphan state. No restore/unarchive operation exists for opportunities.

### Precedence, invariants, and frontend semantics

Schema/migration history establishes discarded ownership for `breakdown_classification_rejected` and `user_rejected`; migration 0036 explicitly normalized both from hidden to discarded. The explicit reject endpoint additionally archives, records metadata and logs a manual override. `_apply_manual_entry_defaults` names `user_rejected` as protected, but `OpportunityIntelligenceService.apply_audition_visibility` runs first and clears that rule for acting/self-tape output. Deep parse also replaces the shared rejection reason. Thus current runtime behavior contradicts the explicit durability signals rather than establishing a policy that automated parsing may undo rejection.

Final precedence supported by evidence is: explicit user reject/archive or explicit approval/override first; then deadline state; automated classification; hard eligibility/demographics; travel; manual Unknown-input protection. The exact automatic treatment of a *confirmed* non-acting manual entry is not established and remains a product gate. There is no restore precedence because restore is unsupported.

Invariant A (`visibility_status` alone owns lists) is disproved by the classification predicate. Invariant C (fully derived lists with visibility only an override) is disproved by persisted hidden/travel/discarded writers and migration history. Invariant B (persisted lifecycle/automated state plus derived classification inclusion) describes most readers, but fails because user lifecycle and automated ownership share the same mutable fields and because the manual `Crew Job` has no UI owner. Therefore the current model is **Invariant D: not fully coherent**.

Observed invalid combinations include visible+archived+user-rejected metadata after reparse and visible+non-acting with no public UI owner. Visible/hidden overlap is prevented by status predicates. Discarded rows are intentionally excluded from both active owners, but are accessible only by ID/diagnostic superset. The frontend does not show raw visibility on normal cards; hidden UI labels every returned non-travel row “Needs Review.” It has no rejected/archive owner. Consequently the manual `Crew Job` has no user-facing explanation, while a reparsed explicit rejection can incorrectly reappear as a normal visible card despite remaining archived in persisted lifecycle.

### Invalidation, data risk, and decision

Existing create/update/manual-parse/deep-parse contracts already refresh visible and hidden ownership; preserving user rejection during deep parse requires no new key. Reject/archive remains focused but ad hoc and a future typed contract is separate work. No rejected/archive query key exists. Existing databases can contain both contradictions. A read-only later diagnostic should count: visible+non-main classification; visible+archived; `source_metadata.user_rejected=true` without `visibility_status=discarded AND hidden_by_rule=user_rejected`; discarded without archived/reason; and manual non-acting rows. No schema migration is required to prevent future parser reopening, but existing contradictory rows would require a separately approved prevalence/read-only characterization before repair.

Proposed contract for the approved boundary: an explicit `user_rejected` decision is durable and has precedence over parser, deadline, classification, demographic, eligibility and travel recomputation until a future explicit restore operation exists. Automated mutations may refresh parsed/intelligence data but must preserve discarded visibility, archived status, user reason/highlight, `hidden_by_rule=user_rejected`, metadata and override history. The smallest correction belongs at the shared opportunity enrichment/visibility boundary used by parse paths, not in frontend compensation. It must cover deep parse first as the characterized mutation and must not decide automatic treatment of non-acting manual entries.

Product gates: storing non-acting records is established; discovered non-acting records are discarded by schema/service history; explicit user rejection durability is a correctness requirement; reject and archive are currently one combined action; restore is unsupported; travel is a separate review category; `visibility_status` is persisted ownership/lifecycle state combined with classification predicates. Whether confirmed non-acting manual entries should auto-discard or enter a dedicated review owner, and whether excluded/archive records need UI, remain product decisions. No schema redesign is approved.

**DECISION A — CORRECT ONE VISIBILITY-STATE DEFECT.** Approve only preservation of explicit user reject/archive across deep parse. Evidence is sufficient and independent of the unresolved manual-entry/non-acting policy. Required characterization before implementation: rejected state and override log baseline; controlled deep parse; exact preservation of discarded/archived/rule/reason/highlight/metadata; absence from visible and hidden owners; diagnostic/detail reachability; parser-derived fields may still update; rollback and retry; no unrelated writes; no restore invention; exact existing deep-parse invalidation and request graph unchanged. Expected production scope is the narrow shared backend visibility/enrichment guard plus focused PostgreSQL/service tests and this ledger. Frontend, schemas, migrations, parser output, query keys and invalidation must not change.

Stop if preservation requires deciding manual non-acting policy, introducing restore, changing enum/schema, changing parser classification, or broadening to deadline/travel/demographic behavior. Confirmed facts: `include_hidden` is not hidden-review ownership; manual `Crew Job` is ownerless in the UI; explicit rejection is reopened by deep parse; archived status and user metadata survive while visible ownership is restored; migrations treat user/classification rejection as discarded. Rejected assumptions: the Crew Job remained in hidden review; status `archived` excludes it from the normal list; `_apply_manual_entry_defaults` alone protects `user_rejected`; current lifecycle/inclusion split is coherent. Unresolved gaps: automatic policy for confirmed non-acting manual input, archive UI/restore policy, and prevalence/repair of existing contradictory rows. These do not block the one approved user-intent correction.

**Exact next-step gate:** implement only the characterized explicit-reject durability correction for deep parse, with tests first. Do not fix manual `Crew Job` ownership, add restore/archive UI, type reject invalidation, characterize demographic refresh, or repair existing data in that step.

## 41. Step 79 — explicit reject/archive durability implementation

**Gate result:** passed. Step 78 explicitly recorded Decision A, proved that deep parse reopened an explicitly rejected manual entry, established durable user intent as authoritative, selected the shared visibility/enrichment writer, required no migration or invalidation change, and prohibited the unresolved manual non-acting policy and all UI/query work.

Characterization first converted the Step 78 reproduction into the approved contract. Before production changes it failed at the exact seam: the first controlled deep parse returned `visibility_status=visible` instead of `discarded`. A second characterization covered injected pre-commit failure and the preexisting rejected aggregate. No unrelated test was rewritten to hide the defect.

The only production owner changed is `OpportunityIntelligenceService.enrich`. It now snapshots canonical `hidden_by_rule=user_rejected` state before derived deadline/classification/demographic/eligibility/travel enrichment and restores that state in a `finally` boundary after every enrichment exit. This covers successful, early-return and exceptional enrichment without adding a commit or changing transaction ownership. The preserved state is: visibility, lifecycle status, rule, hidden/user rejection reason, highlighted text and manual-review state; the durable metadata marker remains true. Parser output, roles, intelligence and trust may still refresh normally. Existing contradictory rows whose rule was already lost are not opportunistically repaired.

The initial provisional deep-parse-local guard was rejected during characterization because `CommandCenterService.refresh_signals` invokes the same enrichment writer and could reopen the record on a later read. That provisional change was removed. Central writer protection is required to satisfy the already-approved user-intent contract and does not alter any reader predicate.

Persisted/list behavior after two consecutive controlled retries is stable: discarded, archived and `user_rejected` remain; the original reason remains; the row is absent from visible opportunities, hidden review, readiness and command-center opportunity cards; it remains reachable by detail ID and the diagnostic `include_hidden` superset. This is the existing rejected/archive ownership model—no new archive owner or restore behavior was introduced. Manual acting behavior and the unresolved confirmed non-acting manual-entry `Crew Job` behavior are unchanged.

Injected commit failure leaves the rejected state and preexisting parse-run set unchanged. Retry then reaches the same authoritative rejected state. The correction adds no nested commit, history write, delete, migration, backfill, query, endpoint or request. Protected deletion and reject/archive persistence remain unchanged.

Typed `opportunity.deepParse` invalidation is unchanged and already refreshes both visible and hidden owners plus its characterized derived projections. No root/prefix invalidation, manual refetch or query-key change was added. No frontend production file changed.

Tests added/updated prove: complete rejected-state persistence, two retry successes, fresh persisted/HTTP equivalence, visible and hidden exclusion, diagnostic/detail reachability, readiness and command-center exclusion, rollback with no parse-run residue, and continued exact reject/archive semantics. The full disposable PostgreSQL suite remains the authoritative transaction check.

Confirmed assumptions: explicit reject state can be protected in one canonical enrichment writer; `finally` preserves it across all existing early returns and failures; existing keys are sufficient; reader predicates need no compensation. Rejected assumptions: a deep-parse-only guard was sufficient; archived status alone kept the row out of command center; command-center refresh was read-only; existing contradictory rows should be normalized opportunistically. Remaining visibility debt: the manual non-acting owner/product policy, archive/restore UI policy, travel-exception characterization, typed reject invalidation and read-only prevalence/data-repair planning. None is approved automatically.

Another change requires a fresh evidence gate. Do not infer approval for UI terminology, demographic refresh, travel work, repair/backfill, restore, invalidation typing or another mutation boundary.

## 42. Step 80 — reject/archive mutation-contract preflight

This is a decision-only checkpoint. No production hook, registry, query, UI, endpoint, schema, or persistence behavior changed.

### Entry points and local ownership

| Context | UI owner | Hook owner | Endpoint / payload | Current local feedback |
| --- | --- | --- | --- | --- |
| Visible opportunity list/detail | `BreakdownManager` route-private `BreakdownRejectForm` | One form-local `useRejectBreakdown` instance | `POST /opportunities/{id}/reject`; optional highlighted text and rejection reason | Local draft and raw error; pending only in button text; no alert/status semantics, synchronous duplicate guard, success acknowledgement, or focus restoration |
| Hidden review | none | none | none | Hidden review exposes approve, parse/deep-parse, role/update and protected hard delete, but no reject/archive control |
| Manual entry after creation | Same visible form when the record belongs to the visible owner | Same form-local hook | Same endpoint and payload | Same behavior |
| Bulk/admin | none found | none | none | No opportunity bulk/admin rejection route exists |

Visible and hidden UI contexts therefore do **not** currently share a rejection workflow. The backend endpoint can reject a hidden-owned ID, and that path is characterized below, but no hidden-review presentation entry point exists. Consolidating or inventing one is outside this gate. The visible form stores a durable full opportunity target snapshot rather than an ID, preserves it and its draft after failure, and closes after success. The initiating control is removed when invalidation removes the record; no stable focus target is selected.

### Backend transaction and persistence map

`OpportunityService.reject` is the single authoritative writer. The route looks up the opportunity and the service writes `visibility_status=discarded`, `status=archived`, `hidden_by_rule=user_rejected`, hidden/rejection reason, highlighted rejection text, `manual_review_required=false`, and `source_metadata.user_rejected=true`. Trust verification runs inside the same request. `ManualOverrideService.log_many` records changed visibility, rule, and rejection-reason fields. One outer `Session.commit` owns the opportunity and override rows; there is no nested commit.

| Record family | Change | Frequency | Transaction owner |
| --- | --- | --- | --- |
| Opportunity | update lifecycle, visibility, rejection and metadata fields | always on successful call | `OpportunityService.reject` request transaction |
| Manual override history | create one row per changed snapshotted field | conditional; identical values create no row | same transaction |
| Trust metadata | update through verification | synchronous | same transaction |
| Parser runs/sections, roles/profiles | unchanged | never | — |
| Recommendations/feedback | unchanged | never | — |
| Readiness/material matches/command center | no persisted rows; responses derive differently | conditional response change | reader-owned |
| Journal, Calendar, submissions, workflows, queue | unchanged | never | — |
| Relationships, Materials/reusable tapes, Career tasks, briefs/preferences | unchanged | never | — |

Disposable PostgreSQL proves visible rejection persists all canonical fields and three initial override rows; fresh-session serialization equals the committed state. Hidden-owned rejection uses the same endpoint/history path and removes the row from hidden review. An identical repeat succeeds and creates no additional override row. A repeat with a new reason succeeds, replaces the current reason, and appends exactly one reason override row. Thus identical replay is state-idempotent, but the endpoint is not an immutable append-only command: later payloads can replace the reason/history. Injected failure at the sole commit rolls back opportunity and override rows together, leaving no partial status, rule, reason, or history. Already-rejected input is accepted rather than rejected as a conflict.

Roles/profiles, parsed sections/history, recommendations/feedback, submissions, Journal, persisted Calendar, workflow tapes, queue, relationships, material assets/reusable tapes, Career tasks, executive briefs and preferences remain unchanged. Operations Analytics, Intelligence Analytics, industry trends, material-performance Analytics, and system capabilities were captured before and after and are unchanged.

### Reader responses and query owners

| Owner | Response after rejection | Classification | Public key |
| --- | --- | --- | --- |
| Visible opportunities | record removed | direct | `breakdownOpportunities` |
| Hidden review | record removed when it originated there | direct | `breakdownHidden` |
| Diagnostic `include_hidden` | record remains; lifecycle/reason fields change in place | direct response, no mounted cache owner | none |
| Detail by ID | record remains; lifecycle/reason fields change | prop/list-derived in frontend, not an independent query | none |
| Readiness | record removed | derived | `breakdownReadiness` |
| Material matches | record removed | derived | `breakdownMaterialMatches` |
| Command center | visible opportunity card/count removed | derived | `commandCenter` |
| Industry trends | unchanged; classification remains included in its non-visibility-filtered aggregate | forbidden | `analyticsIndustryTrends` |
| Operations / Intelligence / material-performance Analytics | unchanged | forbidden | corresponding Analytics keys |
| Recommendations, Journal, Calendar, workflow and queue views | unchanged | forbidden | corresponding public keys |

There is no public rejected/archive owner and none is required for cache correctness. The diagnostic superset is not mounted through React Query. `useBreakdown(id)` selects from the visible list query; there is no independent detail key or route loader. On successful rejection, authoritative list refresh removes the selected record and existing manager composition collapses it. Both active list keys can be invalidated conservatively without runtime owner guessing. System capabilities are configuration-cached, but rejection does not change their response: the apparent visible-breakdown count is not exposed in `feature_states`, and the industry threshold counts classified records irrespective of visibility.

### Current invalidation and proposed contract

The canonical `useRejectBreakdown` currently invalidates `breakdownOpportunities`, `breakdownHidden`, `breakdownReadiness`, `breakdownMaterialMatches`, `analyticsIntelligence`, and `analyticsIndustryTrends` through one ad-hoc success callback. It has no root/prefix invalidation, manual refetch, route reload, duplicate callback invalidation, or failure invalidation. The shared invalidator uses `Promise.allSettled`, so background refetch failure cannot turn mutation success into failure.

The list/readiness/material keys are correct. `commandCenter` is missing. Intelligence and industry-trend invalidations are unnecessary because their proven responses do not change. No missing detail, diagnostic, or archive key blocks a typed contract.

Proposed future registry entry:

* name: `invalidationContracts.opportunityReject`
* operation: `opportunity.reject`
* owner/timing: `breakdowns` / `synchronous`
* direct: `breakdownOpportunities`, `breakdownHidden`
* derived: `breakdownReadiness`, `breakdownMaterialMatches`, `commandCenter`
* forbidden: submissions, workflow self-tapes, callbacks, audition notes, Calendar, Journal, Career tasks, recommendations, queue, relationships and relationship Analytics, Materials and reusable tapes, all four Analytics owners, Dashboard preferences, and executive briefs
* canonical hook: the existing `useRejectBreakdown`; visible and any future hidden presentation must use the same contract without conditional owner guessing

Diagnostic and detail responses have no independent frontend cache, so they are not fabricated as contract keys. Exact invalidation of both active list owners is conservative and bounded.

### Feedback, focus, request graph, and product gates

| Concern | Visible owner | Hidden owner |
| --- | --- | --- |
| Pending shown | button text only; no live status | no reject UI |
| Error shown | raw local text, not `role=alert` or standardized | no reject UI |
| Duplicate protected | React disabled state only; same-frame gap remains | no reject UI |
| Leaves owner after success | yes | backend behavior proved, but no UI path |
| Stable focus target | none; initiating form disappears | not applicable |
| Failed target/draft preserved | yes | not applicable |
| Retry possible | yes | not applicable |

Removal from the list communicates state change visually, but a later accessibility correction should provide a short section-level acknowledgement and move focus to a stable opportunity-list heading or deterministic neighboring control because the initiating button disappears. That correction can remain in the visible form/manager composition without hook movement or generic feedback infrastructure. It must not invent hidden rejection UI. Invalidation correctness comes first because the current missing command-center refresh can leave authoritative derived state stale and UI feedback would otherwise acknowledge completion while another owner remains wrong.

Successful browser graph is one reject POST followed only by refetches for active exact affected-owner keys. Failure is one failed POST and no follow-up GET. Journal, persisted Calendar, workflow, recommendation, unrelated Analytics, global reload, and duplicate mutation requests are forbidden.

Established behavior: rejection and archive are one operation; explicit rejection is durable; no restore exists; identical repeat is state-idempotent; a later changed reason replaces current reason and appends history; visible and backend hidden-ID rejection use the same service contract. Accessibility requires meaningful local error, pending state, duplicate prevention and stable focus in a later UI step. Whether rejected records need a normal archive surface, restore support, historical reason editing policy, or existing contradictory-data repair remains a product/data-operations decision. None blocks typed invalidation.

### Priority and decision

| Criterion | Typed invalidation | Local UI feedback |
| --- | --- | --- |
| Authoritative stale-data risk | high: command center is currently missed | none directly |
| Invisible failure risk | unchanged | high and correctable locally |
| Focus/selection risk | unchanged | high after removal |
| Query-owner clarity | complete; all changed mounted owners have exact public keys | local visible owner clear; hidden owner absent |
| Backend characterization | complete for persistence, repeat, rollback and readers | backend-independent after contract is correct |
| Product-policy blocker | none | acknowledgement wording/focus can be bounded, but hidden UI must not be invented |
| Regression surface | small canonical registry/hook change | larger interaction surface |
| Unlocks later work | makes later success/failure UI truthful across owners | does not repair stale command center |

**DECISION A — TYPE REJECT/ARCHIVE INVALIDATION.** Persistence, response ownership, rollback/repeat behavior and all required public keys are sufficiently established. Approve only `opportunityReject` plus migration of the existing canonical `useRejectBreakdown` success callback. Required implementation tests: exact registry operation/owner/timing and direct/derived/forbidden arrays; group disjointness and public-key validity; exact hook invalidation on success; zero invalidation on failure; background-refetch isolation; no root/prefix/manual/duplicate invalidation; unchanged create/update/manual-parse/deep-parse/strategy contracts; deterministic one-POST browser graph; visible and hidden PostgreSQL persistence; rollback; identical and changed-reason repeats; deep-parse rejection durability regression.

Expected implementation files are the invalidation registry, canonical hook, registry/hook/static tests, focused mocked request-graph coverage if needed, disposable PostgreSQL regression only if the existing characterization exposes a missing assertion, and this ledger. Forbidden adjacent work: UI pending/error/focus/labels, hidden reject entry point, archive/restore/history query, backend semantics, repeat/idempotency policy, parser/enrichment, visibility enums, migration/backfill, manual `Crew Job`, demographic/travel work, component movement, and any second contract.

Stop if current registry cannot express the exact five affected keys, a changed mounted response lacks a public key, the canonical hook is not unique, or implementation would require runtime owner guessing. Confirmed facts: one endpoint/service/hook exists; no hidden UI reject exists; repeat semantics are deterministic; rollback is atomic; command center changes; Analytics and system capabilities do not. Rejected assumptions: hidden review already exposes reject; detail has an independent cache; diagnostic inclusion needs a fabricated key; Analytics invalidation is conservatively necessary; an archive query owner is required. Unresolved gaps: restore/archive product ownership, historical reason policy, local accessible feedback/focus, and existing contradictory-data repair. They are not part of the approved boundary.

**Exact next-step gate:** implement only the typed `opportunity.reject` invalidation contract and canonical-hook migration with the listed tests. Do not add reject/archive UI feedback or any other production change.

## 43. Step 81 — typed reject/archive invalidation implementation

**Gate result: passed.** Step 80 explicitly recorded Decision A, one exact `opportunityReject` contract, the sole canonical `useRejectBreakdown` hook, complete PostgreSQL persistence/rollback/repeat evidence, exact owner groups, expected files and stop conditions. Current code confirmed one hook, all five affected public keys, no independent detail/diagnostic/archive query, and no need for runtime owner guessing.

Characterization tests were added before production changes. The baseline produced exactly three failures: the review-critical operation inventory lacked `opportunity.reject`, the exact contract was undefined, and the typed-hook case could not resolve it. The other 47 focused tests passed. No persistence, UI, or unrelated expectation was rewritten.

Implemented `invalidationContracts.opportunityReject` with operation `opportunity.reject`, owner `breakdowns`, timing `synchronous`, direct owners `breakdownOpportunities` and `breakdownHidden`, and derived owners `breakdownReadiness`, `breakdownMaterialMatches`, and `commandCenter`. Its forbidden set is submissions, workflow self-tapes, callbacks, audition notes, Calendar, Journal, Career tasks, recommendations, queue, relationships and relationship Analytics, Materials and reusable tapes, Operations/Intelligence/industry-trend/material-performance Analytics, Dashboard preferences, and executive briefs. Direct, derived and forbidden groups are disjoint and all affected names resolve to existing public query owners.

The sole production hook migration replaced only `useRejectBreakdown`'s ad-hoc `classificationKeys + opportunityAggregateKeys` callback with `keysForContract(invalidationContracts.opportunityReject)`. This removes unnecessary Intelligence and industry-trend invalidation and adds the proven command-center owner. No query key, detail/archive query, prefix invalidation, manual refetch, duplicate invalidation, endpoint, payload, response, mutation callback, retry, pending/error/focus, selection, or component ownership changed.

Backend evidence remains authoritative: one `OpportunityService.reject` transaction persists discarded/archived/user-rejected fields, rejection/trust metadata and conditional override rows. Identical replay adds no history; a changed reason replaces the current reason and appends one override row. Injected commit failure rolls back opportunity and history together. Step 79 deep-parse durability remains unchanged.

Success invalidates the exact five keys through the established background invalidator. Failure runs no success invalidation. `Promise.allSettled` keeps a committed mutation successful when an owner refetch rejects. A deterministic mocked browser graph repeated three times proves one reject POST, one active refetch each for visible opportunities, hidden opportunities, readiness and material matches, no inactive command-center GET on the Breakdowns route, and no Journal, Calendar, workflow, recommendation or Analytics request. No global reload or duplicate POST occurs.

Tests added: exact registry metadata/arrays/key resolution and operation coverage; canonical hook exact success keys, zero failure invalidation and background-refetch isolation; static typed-hook/no-ad-hoc/no-archive-query protection; and the focused mocked request graph. Existing disposable PostgreSQL visible/hidden persistence, repeat, rollback and unaffected-owner characterization remains unchanged and green.

Confirmed assumptions: the registry represents the contract without conditions; both active list owners can be invalidated conservatively; command center has an exact public key; diagnostic/detail responses need no fabricated keys; one canonical hook is sufficient. Rejected assumptions: Analytics invalidation was harmless necessary conservatism; a rejected/archive cache owner was required; the hidden review had a second hook to migrate; UI feedback had to be combined for authoritative removal.

Remaining reject/archive debt is local visible pending/error/duplicate/focus/accessibility behavior, inaccurate product language, archive/restore product ownership, historical reason policy, and existing contradictory-data repair. None is approved automatically. Another change requires a fresh evidence gate; do not infer approval for the UI candidate, restore/archive surfaces, backend idempotency, data repair, manual non-acting policy, demographic/travel work, or another mutation contract.

Final verification: focused registry/hook/static tests passed 56; focused mocked request graph passed three consecutive runs; all Breakdowns and frontend tests passed within 309 total; disposable PostgreSQL passed 21; normal backend passed 166 with 21 guarded contract skips; ESLint, TypeScript no-emit, production build, static architecture searches and `git diff --check` passed. Full mocked Playwright passed the new reject scenario and 32/34 overall; the two failures were pre-existing timing-sensitive immediate-return policy assertions (one missed command-center refetch and one unexpected Journal refetch), outside the changed request graph and reproducible category from Step 80. No production behavior was altered to compensate for them.

## 44. Step 82 — non-acting source-exclusion contract preflight

This is an audit and product-contract decision only. No model, migration, discovery code, parser, Opportunity lifecycle, query, invalidation, UI, or existing data changed.

### Source identity inventory

| Source / ingestion path | Stable external ID | Canonical URL | Minimum fingerprint available before detail work | Repost/revision behavior |
| --- | --- | --- | --- | --- |
| Playbill public jobs plugin | No explicit field; a source-scoped ID can be derived only when the `/job/...` path exposes one | Specific job URL is available in listing metadata and is stable enough for a source-scoped URL identity; fragments/query noise still need canonicalization | normalized listing title + canonical path; the current `discovered_on` is run date and must not be a version field | Same URL can be edited; a changed listing-title/version token must bypass an old exclusion and be reclassified |
| Parallel public web search | Provider returns no guaranteed posting ID | URL is normalized by removing fragments and repeated result URLs are collapsed | canonical URL + returned page title before page fetch | Arbitrary public pages can change or redirect; URL-only exclusions require a version check and expiry |
| Supervised protected-platform import | Platform posting ID is not extracted | User-opened current page URL is captured, but stability/session parameters are platform-specific | platform name + safely canonicalized URL when available | This is a user-created draft, not a crawler; it must not auto-create an exclusion before user confirmation |
| Manual Opportunity / manual paste | Usually none; optional original URL may exist | Optional and not guaranteed authoritative | none for text-only records | Test/example text and reused titles must never create automatic source suppression |
| Registered placeholder providers | No live candidate contract yet | Not established | none | Must adopt the same identity contract when an implementation becomes active; they do not block the two active automated paths |

The same notice can arrive through Playbill and Parallel, through different tracking URLs, or later through supervised/manual import. Identity must therefore be source-scoped by default. Cross-source content matching is unsafe because syndicated crew and cast notices can share project/title text. URL canonicalization must normalize scheme/host case, default ports, fragments, trailing slash and only known tracking parameters; it must not erase source-significant path or query IDs.

### Current deduplication and why repeated work occurs

| Stage | Current check | Persisted owner | Weakness |
| --- | --- | --- | --- |
| Provider result extraction | Parallel canonicalizes URLs and removes duplicates in one response | none | forgotten after the run; the same URL is fetched next run |
| Plugin normalization | `DiscoveryProvider.deduplicate` uses lowercased project + role + location in one batch | none | no source identity/version, no persistence, and false collisions for generic roles/locations |
| Playbill listing classification | crew/non-acting listing titles are skipped before detail fetch | none | efficient for that run, but the exclusion is forgotten and reconsidered every crawl |
| Parallel page classification | fetches visible page text, then drops Crew/Non-Acting/Unknown | candidate report in run payload/result only, not a durable candidate record | repeated URL fetch and classification; no early persisted lookup |
| Discovery persistence | `_create_opportunity` queries a full Opportunity by `normalized_key` | `Opportunity` | key uses project/role/location/source host/date hints, excludes URL path/external ID, is indexed but not unique, and is checked only after provider detail normalization |
| Discarded Opportunity | still matches `normalized_key` and prevents another aggregate in ordinary sequential runs | full Opportunity aggregate | retains excessive data, can be re-enriched/read, does not prevent provider detail fetch, and concurrent runs can insert duplicates |
| Manual/supervised paths | no source-exclusion lookup | Opportunity or supervised draft | deliberately user-controlled; text-only identity is unsafe for automatic suppression |

A discovered normalized non-acting item can currently create a discarded full Opportunity through the general discovery service. Public Playbill and Parallel happen to filter their known non-acting candidates earlier, so they retain no durable identity at all. A retained discarded Opportunity prevents only later aggregate creation when its approximate key matches; it does not prevent listing/detail collection and parsing work. The database has no uniqueness constraint on `normalized_key`, so application check-then-insert is also not concurrency-safe.

### Full-aggregate cost

One non-acting Opportunity has roughly seventy scalar/JSON/array fields plus the normalized-key index and foreign-key/index participation. Discovery calls `_ensure_details`, flushes the row, creates a `BreakdownParseRun` and parsed sections through `BreakdownIntelligenceEngine`, may create roles, casting-language and CharacterProfile rows, then runs deadline, role, watch-list, intelligence, demographic/eligibility/travel and trust enrichment. Later strategy/manual actions can add recommendations and override history. None of those aggregates is needed merely to remember that one source posting was confirmed crew/non-acting. Acting opportunities retain the full aggregate unchanged.

### Option comparison

| Criterion | Retain discarded Opportunity | Dedicated tombstone | General discovery ledger | Source-specific ignore |
| --- | --- | --- | --- | --- |
| Storage efficiency | poor | high | high but broader | variable |
| Duplicate prevention | late and approximate | exact source-scoped identities with database uniqueness | exact | fragmented by adapter |
| False-positive risk | approximate normalized-key collisions | bounded by identity + version + expiry rules | bounded but more policy states | inconsistent |
| Source portability | coupled to Opportunity | shared contract for every active/future provider | shared | poor |
| Query complexity | pollutes active aggregate and readers | one early existence/upsert lookup | more statuses/transitions | multiple implementations |
| Migration size | none, but requires special minimal aggregate behavior | one small table plus indexes | larger table/service redesign | adapter-specific storage changes |
| Operational diagnostics | misleading Opportunity counts | minimal reason/seen counters | rich | fragmented |
| Scope | preserves current coupling | exactly confirmed exclusions | unnecessarily covers accepted/failed/duplicate history | duplicates logic |

Option A cannot be made deliberately minimal without bypassing required Opportunity fields and guarding numerous existing readers/enrichers; it would remain an Opportunity-shaped tombstone. Option C is not justified: accepted Opportunities and `DiscoveryRun` already own their histories, and no evidence requires one generalized accepted/rejected/failed ledger. Option D makes identity policy inconsistent and cannot suppress the same provider implementation through multiple ingestion services. Option B is the smallest durable boundary.

### Proposed minimum source-exclusion record

| Field | Classification | Contract |
| --- | --- | --- |
| `id` | required | UUID primary key |
| `source_name` / provider key | required | stable scoped namespace, preferably implementation key rather than display label |
| `external_source_id` | optional | stored only when the provider contract supplies a documented stable posting ID |
| `canonical_url_hash` | optional but required for current automated sources | keyed hash of canonical URL; raw URL is unnecessary for suppression |
| `canonical_url` | unnecessary by default | retain only if a later diagnostic requirement proves hash-only operation insufficient |
| `content_fingerprint` | optional | source-scoped normalized detail fingerprint used only after a page must already be fetched; never a cross-source identity |
| `content_version_hash` | required for URL/ID matching when version metadata exists | hash of safe listing metadata such as normalized title + provider publication/update token; changed value forces reconsideration |
| `exclusion_type` | required | narrow value such as `confirmed_non_acting`; do not generalize to all discovery outcomes |
| `classification` | required | `Crew Job` or `Non-Acting Job` only |
| `reason_code` | required | bounded operational code, not copied posting text |
| `first_seen_at`, `last_seen_at`, `times_seen` | required | audit/suppression counters |
| `expires_at` | required for URL/fingerprint-only identities; optional for documented stable IDs | bounds stale-URL false positives |
| `source_metadata` | unnecessary | do not add a generic JSON dumping ground; add a future scalar only if a provider proves it necessary |

No title, project/company/location, role description, contact, attachment, full page text, parser output, AI summary, demographic data or personal information belongs in the record. A short non-user-authored reason code is sufficient.

### Matching, false-positive protection, and confidence

Deterministic lookup order is: (1) source/provider + documented external posting ID + compatible content-version hash; (2) source/provider + canonical URL hash + compatible listing-version hash and unexpired tombstone; (3) source/provider + detail content fingerprint + version hash after fetching when earlier identity is unavailable; (4) no safe match, process normally. A match with a materially different observed version must not suppress: it is re-fetched/reclassified, then the exclusion is replaced/refreshed only if it remains confirmed non-acting.

Safeguards are source scoping, version compatibility, expiry for URL/fingerprint-only records, no title-only identity, no cross-source content suppression, and no automatic manual-text tombstone. Reused project names, “Open Call,” shared project pages, crew/cast notices on one page, redirects and reused source IDs therefore fall through to review when version evidence is absent or changed. A source ID documented as reused must be treated like URL identity rather than permanent identity.

Automatic creation is permitted only for an automated discovered candidate deterministically classified `Crew Job` or `Non-Acting Job` with no acting signal and at least one authoritative source identity. `Unknown`, mixed acting/non-acting signals, parser failure, fetch failure, ordinary duplicate and low-confidence classifications remain reviewable or retryable and must not create this tombstone. The current deterministic classifier has no numeric confidence; its explicit rejected classification plus absence of acting signals is the narrow established confirmation boundary. A future probabilistic classifier would require its own confidence product gate.

Manual policy: automated discovered confirmed non-acting candidates create/update automatically. A manual paste with a real source identity may offer a future explicit “exclude this source posting” choice but must not auto-exclude. A text-only manual/test/example record is forbidden from creating an exclusion. A manually created acting Opportunity later classified non-acting remains an Opportunity lifecycle/product decision; it must not silently create source suppression. Supervised drafts remain reviewable and user rejection of an import is not equivalent to confirmed non-acting classification.

### Early skip, lifecycle, ownership, and concurrency

The earliest safe boundary is after listing/search metadata yields a canonical identity and version token, before detail fetch. Playbill and Parallel both expose URL and title at this point, so no discovery-identity prerequisite blocks the design. On a compatible unexpired match, the run updates only `last_seen_at`/`times_seen` and records an exclusion metric, skipping detail fetch, deep parsing, enrichment, AI and Opportunity creation. When only a detail fingerprint is safe, the lookup occurs after fetch but still before Opportunity parsing/enrichment.

Documented stable-ID exclusions may remain until the provider shows a changed version; URL-only tombstones need bounded expiry (proposed implementation preflight must select and test one duration, initially 180 days) and fingerprint-only tombstones a shorter expiry (initially 90 days). Seeing the same compatible version extends `last_seen_at` and increments `times_seen` but must not silently make a weak identity permanent. No restore/management UI is required. A changed version, expiry, or explicit future administrative removal permits reconsideration.

Tombstones have no normal frontend query owner: not visible, hidden review, command center, readiness, material matches or Analytics. Discovery-run metrics may report a `source_excluded` count using existing run/report ownership; creating/updating a tombstone publishes no Opportunity and triggers no Breakdowns invalidation.

A new table and migration are required. Existing discarded/non-acting or contradictory Opportunities remain untouched; no conversion, deletion, backfill or read-time normalization is approved. A later read-only prevalence audit can estimate repair/conversion value. The future implementation must use database-enforced partial unique constraints for non-null `(source_name, external_source_id)` and `(source_name, canonical_url_hash)` identities, with the version policy handled atomically, plus an indexed source-scoped fingerprint identity. PostgreSQL upsert/unique-conflict handling, not an application-memory lock, must make concurrent discovery converge on one record and one set of counters.

Future request/side-effect contract: confirmed classification upserts the compact exclusion in the same discovery-run transaction, does not create/delete an Opportunity, increments rejected/source-excluded metrics, and performs no downstream enrichment or frontend invalidation. Transaction failure rolls back both run counters and tombstone; retry converges through uniqueness and increments sighting state once per committed run. No backend implementation is approved here.

### Decision and next gate

**DECISION A — APPROVE DEDICATED SOURCE-EXCLUSION TOMBSTONE.** The two active automated discovery paths expose source-scoped URL/title identity early enough, a narrow confirmation boundary already exists, and a compact record avoids the full aggregate and repeated expensive work without requiring an archive UI or general discovery ledger.

The exact next boundary is a separate schema-and-service implementation preflight for one `source_exclusions` model/migration, one source-identity canonicalizer, one atomic lookup/upsert service, and integration only into the active Playbill and Parallel discovery paths at the proved early boundaries. Required characterization before implementation: URL normalization and tracking parameters; same-run and cross-run matches; Playbill and Parallel early skip before detail fetch; changed-title/version reconsideration; expiry; cross-source syndication; same project/generic title non-collision; mixed/Unknown remains reviewable; manual text creates nothing; supervised rejection creates nothing; concurrent PostgreSQL upsert; rollback/retry; no Opportunity/children; exact discovery metrics; no frontend invalidation/query owner; no stored full text or PII.

Expected future files: one backend model and model export, one Alembic migration, a narrowly named source-exclusion identity/service module, focused adapter/discovery tests, disposable PostgreSQL contract tests, and this ledger. Forbidden adjacent work: existing-data conversion/cleanup, Opportunity deletion or visibility changes, parser/classifier changes, crawler expansion, generalized discovery ledger, source-management UI, restore, query keys/invalidation, manual `Crew Job` ownership, travel/demographic work, or acting Opportunity storage changes.

Stop if an active adapter cannot expose a safe source-scoped identity before expensive work, version compatibility cannot prevent revised acting postings from suppression, uniqueness would require broad content matching, uncertain classifications would be excluded, manual text would create automatic tombstones, or implementation requires changing Opportunity lifecycle. Confirmed facts: current persisted dedup is full-Opportunity and non-unique; discarded aggregates suppress only late aggregate creation; Playbill and Parallel already have pre-detail URLs/titles; current non-acting filters are forgotten; no frontend owner is needed. Rejected assumptions: retaining a discarded Opportunity is storage-minimal; `normalized_key` includes stable posting identity; discarded records prevent network/detail work; a general ledger is necessary; title/content matching can safely cross sources. Unresolved gaps for implementation preflight: exact provider-specific URL parameter allowlists and final expiry durations. They do not block choosing the storage boundary but must be fixed before production implementation.

Verification for this audit: 39 focused discovery/source/classification tests passed; all 97 Breakdowns tests passed; full frontend passed 309; normal backend passed 166 with 21 guarded disposable-contract skips; ESLint and existing architecture/static tests passed; static search confirms no tombstone model, migration, query or production implementation was added; `git diff --check` passed. New disposable PostgreSQL characterization was not necessary for this decision because no schema exists yet and the concurrency/rollback cases are explicitly required before the future schema implementation rather than simulated against the Opportunity table.

## 45. Step 83 — source-exclusion schema/service implementation preflight

This remains decision-only. No migration, model, service, provider integration, discovery behavior, parser behavior, API, frontend code, query key, invalidation, cleanup or data conversion was added.

### Repository schema and transaction conventions

| Concern | Repository convention | Tombstone foundation choice | Evidence |
| --- | --- | --- | --- |
| Primary key | UUID mixin, Python UUID default and PostgreSQL `gen_random_uuid()` server default | `UUIDPrimaryKeyMixin` | all modern models/migrations |
| Timestamps | timezone-aware `created_at`/`updated_at`, `now()` server defaults | retain mixin plus domain `first_seen_at`/`last_seen_at` | `TimestampMixin`, migration 0051 |
| Enums | constrained strings rather than PostgreSQL enum types | bounded `String` plus check constraints | Opportunity/discovery models |
| Checks | named table check constraints | named identity, vocabulary, counter, timestamp and expiry checks | Opportunity and automation models |
| Indexes | model `Index` plus explicit Alembic create/drop | two PostgreSQL partial unique indexes | migration/model parity |
| Nullable unique data | no current partial-index example, but Alembic/SQLAlchemy target PostgreSQL directly | `postgresql_where` partial unique indexes; no SQLite weakening | PostgreSQL-only configuration/dependencies |
| JSON | PostgreSQL JSONB only for real structured payloads | none | arbitrary metadata is forbidden |
| Strings | explicit bounded lengths | provider 160, external ID 255, hashes 64, vocabularies 40/80 | repository field conventions |
| Model exports | explicit import and `__all__` in `app.db.models` | internal model export only | model package convention |
| Data access | services commonly query/execute directly on a supplied Session | one focused service; no new repository layer | discovery/opportunity services |
| Commit ownership | outer request/job service commits; helpers flush/execute | exclusion service never commits | discovery run already owns one transaction |
| Migration tests | disposable PostgreSQL initializes empty cluster and upgrades Alembic to head | migration/constraint/concurrency tests use that runner | `scripts/run_contract_smoke.py` |

The supported application and normal test database is PostgreSQL/psycopg. The model already depends on PostgreSQL UUID, JSONB and ARRAY types; there is no supported SQLite development/test path requiring fallback. Production partial uniqueness must not be weakened for an unconfigured dialect.

### Exact table proposal

Table: `source_exclusions`. It is an internal operational identity table with no foreign key to Opportunity and no relationship from Opportunity.

| Column | SQLAlchemy / SQL type | Required/default | Mutable | Index/constraint | Retention justification |
| --- | --- | --- | --- | --- | --- |
| `id` | PostgreSQL UUID | required; UUID mixin defaults | immutable | primary key | row identity |
| `source_name` | `String(160)` | required | immutable after creation | participates in both unique indexes | stable provider implementation key, not display label |
| `external_source_id` | `String(255)` | optional | may be filled when the same URL identity later supplies it; otherwise immutable | partial unique with source | minimal documented provider identity; not a title |
| `canonical_url_hash` | `String(64)` | optional | immutable for a logical source identity | partial unique with source | SHA-256 identity without retaining URL |
| `content_version_hash` | `String(64)` | required | replaced only after a newly processed version is reconfirmed non-acting | ordinary index unnecessary | explicit changed-content safety |
| `exclusion_type` | `String(40)` | required; application value `confirmed_non_acting` | immutable | check | prevents generic rejection-ledger growth |
| `classification` | `String(80)` | required | mutable when a newly confirmed version changes between the two allowed classes | check | `Crew Job` or `Non-Acting Job` |
| `reason_code` | `String(80)` | required | mutable on reconfirmed version | check | bounded operational evidence |
| `first_seen_at` | timezone-aware `DateTime` | required; application `now` and server `now()` | reset when a newly confirmed version supersedes current version | timestamp check | first sighting of current excluded version |
| `last_seen_at` | timezone-aware `DateTime` | required; application `now` and server `now()` | updated per compatible committed sighting | timestamp check | current-version activity |
| `times_seen` | `Integer` | required; default/server default 1 | atomic increment; reset to 1 on version supersession/reactivation | `>= 1` check | compact diagnostics/concurrency proof |
| `expires_at` | timezone-aware `DateTime` | conditional | reset on reconfirmation; otherwise immutable per current version | weak-identity expiry check | bounds URL-only suppression |
| `created_at`, `updated_at` | timestamp mixin | required/server defaults | framework-managed | none | row lifecycle distinct from version lifecycle |

`content_fingerprint` is deliberately omitted from the initial foundation. Both active automated providers have pre-detail URLs, and adding a third identity mode would broaden matching, expiry and uniqueness without a current consumer. Full canonical URL, posting text, HTML, title, project/company/location, role/contact data, parser/AI output, notes, JSON metadata, soft delete and Opportunity foreign keys are forbidden.

### Identity invariants and PostgreSQL constraints

One row may contain both external ID and URL hash so later runs can enrich the same logical identity and avoid parallel tombstones. It must contain at least one:

* `ck_source_exclusions_identity`: `external_source_id IS NOT NULL OR canonical_url_hash IS NOT NULL`.
* `ck_source_exclusions_weak_expiry`: `external_source_id IS NOT NULL OR expires_at IS NOT NULL`. A URL-only identity always expires; an external-ID row may still receive expiry by provider policy.
* `ck_source_exclusions_times_seen`: `times_seen >= 1`.
* `ck_source_exclusions_seen_order`: `last_seen_at >= first_seen_at`.
* `ck_source_exclusions_expiry_order`: `expires_at IS NULL OR expires_at > first_seen_at`.
* exclusion type limited to `confirmed_non_acting`.
* classification limited to `Crew Job`, `Non-Acting Job`.
* reason code limited initially to `provider_listing_rule`, `deterministic_classification`.

Partial unique indexes:

* `uq_source_exclusions_source_external_id` on `(source_name, external_source_id)` where external ID is not null.
* `uq_source_exclusions_source_url_hash` on `(source_name, canonical_url_hash)` where URL hash is not null.

`content_version_hash` does not participate in identity uniqueness. A materially changed posting is a new version of the same source identity, not a second logical tombstone. The database retains one current excluded version. A service query matching both available identities must resolve to zero or one row; two different rows matching external ID and URL is an integrity conflict and must stop rather than guess or merge silently.

### Version-model decision

| Criterion | Current-version row | Immutable version rows |
| --- | --- | --- |
| Storage growth | bounded one row per identity | unbounded repost/version history |
| Concurrency | one unique identity target | composite identity/version conflicts |
| Revised acting safety | version mismatch bypasses without mutating row | new acting version absent, also bypasses |
| Diagnostics | current exclusion plus counters | detailed history not currently required |
| Upsert | update current version only after reconfirmation | insert each confirmed version |
| Cleanup | expired rows may remain; no required job | eventual history cleanup required |

Select **current-version Model A**. Same identity + same version + active expiry suppresses and atomically records a sighting. Same identity + different version never suppresses and does not mutate the tombstone before classification. If the new version is confirmed acting/uncertain, the old row remains as evidence for the old hash but cannot suppress the new hash. If the new version is reconfirmed non-acting, the same row receives the new version/classification/reason, resets current-version first/last seen and count to one, and receives a fresh expiry. An expired same-version row does not suppress; later confirmed non-acting processing reactivates that row rather than creating another.

`content_version_hash` is mandatory for every identity, including external IDs. This is the explicit safeguard against reused IDs and revised source pages. Missing version evidence means no tombstone lookup can suppress and no exclusion can be recorded.

### Canonical identity service

Create one pure `SourceIdentityService` (repository-conventional static/pure methods, no Session) returning an immutable internal `SourceIdentity` dataclass. Its bounded input is provider implementation key, optional documented external ID, optional absolute raw URL, and a mapping of pre-detail version fields. It owns normalization and SHA-256 hashing; it does not own database access, classification or provider fetching.

Canonical URL v1 rules:

* accept absolute HTTP/HTTPS only; reject credentials, relative URLs and missing host;
* lowercase scheme and IDNA-normalized hostname; remove default ports;
* remove fragment; normalize empty path to `/`; preserve path case and percent-encoded semantics rather than guessing server behavior;
* parse query pairs with blank values, remove only universal marketing keys (`utm_*`, `fbclid`, `gclid`, `msclkid`), sort remaining key/value pairs deterministically, and preserve every unknown parameter;
* never strip a provider-specific parameter in the shared service;
* provider hostname aliases and additional removable parameters are explicit adapter-supplied policy, not hidden global behavior.

Playbill foundation policy may alias `www.playbill.com` to `playbill.com`, preserves the entire `/job/...` path and all non-marketing query parameters, and uses normalized listing title as the currently proved pre-detail version field. No external ID is claimed until the adapter proves a documented path identifier. Known ambiguity: current fixtures do not prove whether Playbill reuses a job URL, which is why version hash and 180-day URL expiry remain mandatory.

Parallel is a search provider over arbitrary target domains, so it has no hostname aliases or provider-specific query stripping. It preserves target hostname/path and every non-marketing query parameter and uses returned page title as the pre-fetch version field. Redirect targets are not available until fetch; a future integration may build the identity from final URL only if it retains the original source-scoped lookup safely. Known ambiguity: search result titles can be missing; such candidates cannot be early-suppressed and must proceed normally.

Provider-specific parameter rules belong in adapter-owned explicit `SourceUrlPolicy` inputs. This conservative default may miss suppression for unknown trackers, but it cannot erase source-significant IDs. That tradeoff is correct for the foundation.

Hash contract:

* SHA-256 from Python `hashlib`, lowercase 64-character hexadecimal storage;
* Unicode NFKC and whitespace collapse for source name, external ID and version scalar values;
* canonical JSON serialization with sorted keys, UTF-8, explicit schema prefix (`source-identity:v1` or `source-version:v1`) and provider scope;
* ordered/version-field names are retained; null and blank normalize to omission, and an empty version mapping is rejected;
* canonical URL hash input is the complete canonical URL under the identity prefix;
* version hash input is provider plus normalized sorted field mapping;
* runtime `hash()` and ambiguous string concatenation are forbidden.

Cryptographic collision risk is negligible; without raw identity data a collision cannot be resolved from the table, so any future hash-version change requires a new schema prefix and migration/preflight rather than silent reinterpretation.

### Vocabulary and service ownership

The bounded vocabulary is one exclusion type, two classifications and two reason codes:

* `confirmed_non_acting`;
* `Crew Job`, `Non-Acting Job`;
* `provider_listing_rule` for deterministic provider-listing classification and `deterministic_classification` for confirmed parsed classification.

Constrained strings match repository conventions and avoid PostgreSQL enum migration coupling. Arbitrary parser prose is not stored.

One `SourceExclusionService` receives the existing SQLAlchemy Session and owns:

| Responsibility | Contract |
| --- | --- |
| `record_compatible_sighting(identity, now)` | atomically find active same-version row, increment counter/update last seen, return excluded result; mismatch/expiry returns not excluded without mutation |
| `record_confirmed_exclusion(identity, classification, reason_code, expires_at, now)` | validate vocabulary/identity, insert one row or reconfirm/reactivate the matching current-version row |
| identity reconciliation | find by all supplied identities; fill a missing secondary identity only when exactly one existing row matches; reject conflicting rows |
| transaction behavior | execute/flush only; never commit, rollback globally, fetch, classify, create Opportunity or update DiscoveryRun |

Lookup and sighting update are one atomic service method so adapters cannot perform race-prone select-then-increment. Every compatible committed run increments exactly once; throttling is not approved.

For atomic sighting, use one PostgreSQL `UPDATE ... WHERE` matching source plus strongest supplied identity, exact version, and active expiry, with `times_seen = times_seen + 1`, `last_seen_at = now`, returning the row. This is atomic without a preliminary lock.

For confirmed exclusion, use PostgreSQL `INSERT ... ON CONFLICT DO NOTHING` without a conflict target so either partial unique index is respected, then select the row by the supplied identity set and lock/update it in the caller transaction. A newly inserted row starts at one. A conflict reload updates the same-version sighting atomically or supersedes/reactivates the current version only after confirmed classification. If external ID and URL resolve to different rows, raise an integrity error. No application-memory lock, nested commit or independent transaction is allowed. Implementation tests must prove the exact two-worker outcome; if `DO NOTHING` plus reload cannot preserve one increment per committed confirmation under the test barrier, the implementation must stop rather than add a nested commit.

The outer discovery run/request remains transaction owner. Tombstone creation/sighting and future `DiscoveryRun` counters commit or roll back together. A failed sighting, insert, conflict resolution or later surrounding bookkeeping leaves no partial tombstone/counter change. Foundation tests can explicitly begin/rollback Session transactions without provider integration.

### Discovery bookkeeping, expiry, API and existing data

No DiscoveryRun schema change is required. Existing `total_found`, `total_rejected`, notes and `rejection_reasons_summary` can later report `source_excluded` in provider integration, but foundation-only code does not touch them. Tombstone and run updates must be atomic once integration occurs.

Initial configuration is code constants in the exclusion domain, not database defaults or Settings fields: URL-only 180 days. Fingerprint TTL is removed because fingerprint identity is not in the foundation. External-ID rows may omit expiry only while every lookup still requires exact version compatibility; a provider may pass a shorter expiry later. Expired rows remain stored but inactive; confirmed reclassification reactivates the same row. No scheduler or cleanup is required.

No Pydantic schema, API/admin endpoint, serialization, frontend type, React Query owner, invalidation contract, navigation or archive view exists. Skipping an Opportunity later produces no Breakdowns refetch. The empty-table migration is deployable without touching existing Opportunities. No conversion, deletion, cleanup, backfill or read-time normalization is approved; later prevalence/repair remains a data-operations decision.

### Test architecture and implementation boundary

Mandatory tests before production implementation:

* migration upgrade from 0054, exact columns/checks/partial indexes, clean downgrade to 0054 and re-upgrade;
* PostgreSQL check violations for missing identity, URL-only missing expiry, invalid vocabularies, counter and timestamp order;
* uniqueness for external and URL identities and allowance for null optional identities;
* URL normalization: scheme/host/default port, fragment, trailing/empty path, marketing removal, unknown/significant query preservation, deterministic query ordering, Unicode/IDNA, invalid/relative/credential URLs, Playbill alias policy;
* deterministic provider-scoped URL/version hashes, field ordering/null handling, changed version, generic title not becoming identity, and no cross-source equality;
* first exclusion, same-version active sighting, expired/mismatched version bypass without mutation, reconfirmed version supersession, expired reactivation, secondary identity enrichment and identity conflict rejection;
* two real PostgreSQL Sessions/workers racing first insert and sighting, one row, correct counters, no nested commit;
* rollback at creation, sighting, supersession and surrounding transaction; no Opportunity or child rows;
* rejection of text-only/manual identity, missing version, Unknown/mixed/invalid classifications and arbitrary reason codes;
* static absence of API, frontend query/invalidation, Opportunity relationship/full-content fields and provider imports/integration.

| Criterion | Foundation only | + Playbill | + both providers |
| --- | --- | --- | --- |
| Schema/concurrency proof | complete | complete | complete |
| Real behavior proof | service boundary only | one early-skip path | all current paths |
| Scope | smallest | schema plus crawler behavior | two distinct pipelines |
| Rollback complexity | isolated caller transaction | discovery-run integration | discovery plus Parallel search lifecycle |
| Regression surface | model/service only | listing behavior | listing and fetched public web behavior |
| Dead-code risk | temporary, bounded by explicit next integration gate | none | none |
| Ease of review | highest | medium | lowest |

**DECISION A — IMPLEMENT TOMBSTONE FOUNDATION ONLY.** The service is meaningfully testable against disposable PostgreSQL without a provider: schema constraints, version safety, expiry, atomic counters, two-session upsert and rollback are the highest-risk foundation. Combining Playbill would change discovery behavior and obscure whether failures come from schema/concurrency or adapter identity. Temporary unused internal code is bounded and must be followed by a separate Playbill integration gate before Parallel.

Product gates: current-version rows, changed-version reconsideration, per-run sighting updates and expired-row reactivation are correctness/implementation choices established here; URL-only 180 days is an initial configuration choice; fingerprint expiry is irrelevant because fingerprint mode is omitted; external IDs may omit expiry only with mandatory version matching; admin visibility and existing-data conversion are deferred product/data-operations decisions; exclusion metrics are deferred to provider integration.

Exact approved future boundary: one migration, one `SourceExclusion` model/export, one pure source identity module, one session-owned exclusion service, and focused unit/disposable-PostgreSQL/static tests. No provider consumes it. Expected files are `alembic/versions/0055_source_exclusions.py`, one narrowly named model module plus model export, one identity/service module (or two small cohesive modules if repository naming requires), focused identity/service tests, disposable contract tests and this ledger.

Forbidden adjacent work: Playbill/Parallel or placeholder integration, discovery metrics changes, Opportunity lifecycle/storage, classifier/parser/crawler changes, API/frontend/query/invalidation, cleanup scheduler, conversion/backfill/deletion, admin UI, fingerprint mode, generalized discovery ledger, manual Crew Job policy, demographic/travel work. Stop if migration constraints differ from the model, versionless identities can suppress, URL normalization strips unknown parameters, concurrent sessions create two rows/lose committed sightings, conflict handling requires nested commits, rollback leaves a row, or tests cannot run against real PostgreSQL.

Confirmed facts: PostgreSQL is the supported database; partial indexes and dialect upserts are available; outer Session ownership fits a no-commit helper; both risky service paths are testable without providers; current active providers make fingerprint mode unnecessary. Rejected assumptions: immutable version history is operationally required; version belongs in uniqueness; an identity-type column is needed; raw URLs or generic JSON are necessary; provider integration is required to validate concurrency; SQLite compatibility should weaken constraints. Unresolved gaps: the real two-session test may disprove the provisional `ON CONFLICT DO NOTHING` conflict-resolution sequence, and Playbill/Parallel redirect/parameter policies still require provider-integration characterization. The first is an implementation stop condition inside the approved foundation; the second does not affect a foundation that preserves every unknown query parameter and integrates no provider.

**Exact next-step gate:** implement and verify only the tombstone foundation above. Do not integrate Playbill or Parallel in that step.

Step 83 verification: focused discovery/source/parser tests passed (39); the full backend suite passed (166 passed, 21 skipped); the disposable PostgreSQL contract suite passed (21 passed, 166 deselected); the full frontend suite passed (309); ESLint and TypeScript no-emit passed; `git diff --check` passed; and static searches confirmed that no `SourceExclusion` model/service, `source_exclusions` table, query owner, or provider integration was introduced.

## 46. Step 84 — source-exclusion foundation implementation

The mandatory gate passed: Step 83 recorded **DECISION A — IMPLEMENT TOMBSTONE FOUNDATION ONLY**, and the current repository supported every approved constraint without provider integration, nested commits, weakened PostgreSQL uniqueness, or Opportunity creation. The pre-production characterization baseline failed at the intended missing-module seam (`app.services.source_identity` did not exist); no existing Opportunity/deduplication behavior was rewritten to compensate.

Implemented exactly the approved foundation:

* migration `0055_source_exclusions` creates and cleanly drops the empty `source_exclusions` table, eight named checks, and the two source-scoped partial unique indexes; it does not touch Opportunity or existing rows;
* `SourceExclusion` mirrors the migration with UUID/timestamp mixins and no relationships, JSON, raw URL, content, parser, AI, or user-facing fields;
* immutable `SourceIdentity` and explicit `SourceUrlPolicy` carry only normalized provider identity hashes and version hash;
* pure `SourceIdentityService` implements absolute credential-free HTTP(S), lowercase/IDNA hostname, default-port removal, fragment removal, empty-path normalization, conservative marketing-parameter removal, preservation/sorting of all unknown query pairs, optional explicit hostname aliases, NFKC/whitespace scalar normalization, canonical sorted JSON and provider-scoped SHA-256 hex hashes;
* `SourceExclusionService` accepts the caller Session, never commits, validates the bounded confirmed-non-acting vocabulary, performs atomic exact-version active sighting increments with `UPDATE ... RETURNING`, and uses PostgreSQL `INSERT ... ON CONFLICT DO NOTHING` plus locked identity reconciliation for concurrent confirmation;
* URL-only exclusions receive the approved 180-day expiry; external-ID identities may remain unexpired but still require exact version compatibility; changed versions bypass suppression and are installed only after reconfirmed non-acting classification; reactivation/version supersession resets current-version timestamps and count;
* conflict between supplied external-ID and URL identities is rejected rather than merged; missing identity, missing version, Unknown/mixed classifications, arbitrary reasons, title-only/manual text, user rejection alone, and unsafe URLs cannot create a tombstone.

Transaction ownership remains the future outer discovery transaction. Insert, compatible sighting, version replacement and identity reconciliation only execute/flush. Caller rollback removes or restores every change. No DiscoveryRun field/status/metric was added. No Playbill or Parallel production code consumes the foundation.

The real two-session PostgreSQL test resolved Step 83's principal uncertainty: simultaneous confirmation converged through the partial unique constraint to one logical row, both callers received coherent excluded results, `times_seen` became two, and both Sessions remained usable. No application lock, nested commit, swallowed integrity error, or weakened constraint was required. Model/migration inspection proved exact columns/check names/indexes; partial external-ID and URL uniqueness and weak-identity expiry fail at PostgreSQL; downgrade to 0054 removes the table and re-upgrade restores it.

Frontend and invalidation remain absent: no API/schema, React Query key, invalidation contract, frontend type/hook/UI, hidden-review owner, command-center/readiness/material owner, manual refetch, or Breakdowns request was added. Existing Opportunities and child aggregates are not read or written by the service, and no conversion, deletion, relabel, normalization, backfill, cleanup, or provider behavior occurred.

Tests added:

* six pure identity tests covering normalization, significant-parameter preservation, deterministic/source-scoped hashes, reordered/null version fields, changed versions, title-only rejection and unsafe URLs;
* one static architecture test covering no Opportunity relationship/write surface, commit, discovery-provider dependency, network use, frontend key/invalidation, or unapproved production consumer;
* eight disposable PostgreSQL tests covering creation, compatible sighting, version mismatch and confirmed supersession, expiry/reactivation rollback, sighting rollback, database checks, bounded classification, zero Opportunity writes, genuine concurrent convergence, schema parity, partial uniqueness, weak expiry and migration downgrade/re-upgrade.

Verification: focused unit/static tests passed (7); focused PostgreSQL passed (8); the complete disposable PostgreSQL suite passed (29, 7 existing warnings); the normal backend suite passed (173, 29 skipped); frontend passed (309); ESLint, TypeScript no-emit, production build, Ruff, migration-head audit (`0055_source_exclusions`), architecture/static checks and `git diff --check` passed. The first full mocked Playwright run had one pre-existing Journal immediate-return timing failure; that scenario then passed three consecutive isolated runs and the complete mocked suite passed on rerun (34/34), confirming no source-exclusion request-graph change.

Confirmed assumptions: PostgreSQL partial indexes and dialect conflict handling express the contract; caller-owned transaction boundaries are sufficient; a foundation-only service is testable; current-version rows safely reconsider changed versions; conservative URL handling need not know provider-specific significant parameters. Rejected assumptions: concurrency requires nested commits or memory locks; provider integration is required now; an archive/query owner, DiscoveryRun schema, fingerprint mode, raw URL, JSON metadata, Opportunity relationship, frontend invalidation, or existing-data migration is necessary.

Remaining tombstone debt is intentionally outside Step 84: no active provider invokes the foundation, provider redirect/external-ID facts remain uncharacterized, no discovery exclusion metric exists, expired-row cleanup/admin visibility is undecided, and existing non-acting Opportunities remain untouched. A fresh check-in must preflight Playbill integration as the next bounded step; it must not infer approval for Parallel, manual-source controls, cleanup, data conversion, admin UI, or historical tombstone management.

## 47. Step 85 — Playbill source-exclusion integration preflight

This step is audit-only. No provider, foundation service/model/migration, discovery behavior, frontend, invalidation, Opportunity, metric, API, cleanup or existing-data code changed.

### Pipeline, rule and ownership map

| Stage | Production owner | Input | Output | Caller Session available? | Expensive? |
| --- | --- | --- | --- | --- | --- |
| create run/transaction | `DiscoveryAutomationService.run_provider` | provider key/mode | flushed `DiscoveryRun` | yes, `self.db` | no |
| listing request | `PublicPlaybillJobsSource.discover` | `https://playbill.com/jobs` | jobs-page HTML | no provider access to Session | one network request |
| listing extraction | `discover`, anchor regex | anchors containing `/job/` | cleaned title plus `urljoin` URL | no | no |
| pre-detail classification | `discover` → `classify_breakdown_text(title)` | anchor title only | classification/reason | no | deterministic local work |
| listing rejection/review gate | `discover` | classification/title terms | crew/non-acting silently omitted; unhelpful Unknown omitted; acting/review candidate retained | no | no |
| detail request/parse | `normalize` → `_normalize_item` → `_detail_text` | retained item URL/title | visible detail text or title fallback | no | per-candidate network/HTML parsing |
| post-detail classification | `_normalize_item` | title plus detail text | normalized classification/reason | no | deterministic local work |
| domain normalization | `_normalize_item`, `BreakdownDetailsService` | detail fields | `NormalizedOpportunity` | no | formatting/derivation |
| in-run dedup/validation | provider base plus orchestration | normalized records | valid unique candidates | yes only in orchestrator | no DB lookup yet |
| persistence dedup/create | `_create_opportunity` | normalized item | existing/new full Opportunity | yes | Opportunity/source lookup and writes |
| run bookkeeping/commit | `run_provider` | counts/results | succeeded `DiscoveryRun` and response | yes | commit |

The earliest data-complete pre-detail point is immediately after lines 43–48 of `public_sources.py`: href has been joined, anchor label cleaned, and the existing deterministic classifier has run. It is before `_detail_text`, normalization, Opportunity lookup/create and all downstream work. However, `DiscoveryProvider.discover()` has no arguments and `PublicPlaybillJobsSource` has no Session/service reference. The outer Session exists and has already flushed the run, but cannot currently be used at that boundary without a new caller-owned integration seam. Creating a Session inside the provider is forbidden.

The current pre-detail rule is exactly `classify_breakdown_text(clean_anchor_title)`. Crew signals (`production assistant`, `crew`, `gaffer`, `grip`, `editor`, `camera operator`, `sound mixer`, `wardrobe supervisor`, `stage manager`, `props`, `lighting designer`) produce `Crew Job` only when no acting signal exists. Bounded employment signals similarly produce `Non-Acting Job` only without an acting signal. Both are silently omitted before detail fetch and are not persisted, counted in `raw_items`, or reconsidered except by re-running the same title rule. Unknown titles survive only when they contain an explicit review term; short Playbill branding anchors are also omitted. Mixed cast/crew text containing an acting signal is not crew-classified and therefore is not eligible for a tombstone.

This existing crew/non-acting result maps semantically to `confirmed_non_acting`, its returned `Crew Job`/`Non-Acting Job`, and `provider_listing_rule`; no broader keyword rule is approved. The classifier itself is unchanged and deterministic, but its evidence is limited to the anchor title.

### URL, source and version evidence

Repository examples are sparse:

| Example | Foundation canonical result | Identity-safe? | Early version evidence | Finding |
| --- | --- | --- | --- | --- |
| `https://playbill.com/jobs` | listing index | no | none | pagination/index, never a posting identity |
| `/job/...` relative anchor | joined to jobs-page origin | provisionally job-level | cleaned anchor title | actual production extraction shape |
| `https://playbill.com/job/specific-role/abc123` | same path, fragment removed | structurally job-level | test fixture title only | proves path recognition, not identifier semantics |
| `https://playbill.com/job/example` | same path | fixture only | fixture title | no reuse/revision evidence |
| `www`/marketing/significant-query example | `www.playbill.com` aliased to `playbill.com`; marketing removed; unknown query preserved/sorted | normalization tested | title | synthetic foundation fixture, not Playbill response evidence |

Stable source name must be the implementation key `playbill_public_jobs`, not display copy `Playbill Public Jobs`, alias `playbill`, SourceResearch labels, or hostname. No documented external ID is currently extracted. The provisional identity would therefore be:

```text
source_name: playbill_public_jobs
external_source_id: none
raw_url: urljoin(listing_url, href)
version fields: normalized anchor title only
URL policy: alias www.playbill.com → playbill.com; remove universal marketing keys only; preserve every other query parameter
```

The URL hash is an acceptable source-scoped posting locator only if `/job/...` is not page-level/reused incompatibly. Title is stable for unchanged fixtures and a changed title changes the version hash. `discovered_on` is volatile and must not participate. No category, publication date, update date, revision token, employer, location or listing type is extracted at the early boundary.

Critical evidence is absent: the repository does not prove whether Playbill reuses a job URL while retaining the same anchor title, nor expose an early revision timestamp/version marker. Consequently the provisional title-only version cannot prove the required scenario where version A is a crew notice and the same URL/title later contains acting detail as version B. Both would hash identically and an active tombstone would suppress B before detail fetch. Existing code also misses that revision because its title-only rule skips before detail, but preserving that behavior would be a compensating correctness defect, not evidence that durable suppression is safe.

### Proposed behavior after the identity prerequisite

If safe early version evidence is established, the bounded order remains:

1. extract/join URL and cleaned title;
2. build `SourceIdentity` with `playbill_public_jobs` and explicit Playbill `SourceUrlPolicy`;
3. caller-owned `SourceExclusionService.record_compatible_sighting(identity)`;
4. on hit, omit internally, skip detail/normalization/Opportunity work and retain no frontend owner;
5. on miss, run the existing title classifier;
6. for its existing confirmed crew/non-acting result, call `record_confirmed_exclusion(..., reason_code="provider_listing_rule")`, omit the item and continue;
7. otherwise preserve current detail, classification, deduplication and Opportunity flow.

Unsafe URL, missing identity or missing version must fail open into current processing and create no tombstone. Acting, mixed, useful Unknown, malformed-identity, detail-failure, parser-failure, duplicate and existing acting Opportunity behavior remains unchanged. Expired URL-only rows do not suppress; the existing deterministic rule reconfirms/reactivates the same row. A changed compatible source version bypasses the old row; if it is later confirmed non-acting, the current-version service safely replaces the row. No shared service change is indicated.

An exclusion hit should use silent internal omission (Option A), matching current Playbill behavior. Existing `DiscoveryRun` has no accurate pre-normalization skip item and raw totals already exclude crew titles; Step 85 does not approve a metric/status/schema change. The avoided work is one detail request, visible-page parsing, post-detail classification, BreakdownDetails normalization, in-run/persisted dedup, Opportunity/source writes and downstream processing. First crew confirmation and later sightings each retain only the jobs-page request; acting listings retain the current jobs-page plus detail request graph.

The current transaction commits once per provider run. Network requests already occur after the run flush within that transaction. Normal success commits run and Opportunity writes together. The exception path marks the run failed and commits without first rolling back; an unexpected SQL failure can leave the Session aborted, so future integration must characterize/repair the run-level database-failure path without adding a provider commit or independent Session. This is a later transaction constraint, not the selected Step 85 prerequisite because safe version identity fails first.

Future concurrency coverage must use two orchestration Sessions: simultaneous first confirmation converges to one tombstone/no Opportunity; a later committed run records one sighting and skips detail. The foundation has proved service convergence but not adapter HTTP behavior. Tombstone failure must follow one proved run policy, rollback all caller-owned writes, and never be hidden by frontend invalidation. No savepoint is approved by this preflight.

### Product gates, tests and decision

| Gate | Classification |
| --- | --- |
| source name `playbill_public_jobs` | established implementation fact |
| conservative `www` alias/marketing-only URL policy | implementation choice supported by foundation |
| exact early version fields | **correctness prerequisite unresolved** |
| current title crew rule | established deterministic behavior; do not broaden |
| exclusion skip bookkeeping | implementation choice: silent omission, no schema/metric |
| tombstone DB failure policy | later transaction prerequisite after identity is safe |
| expired exclusion reconfirmation | established service behavior |
| revised acting bypass | correctness requirement not proved with title only |
| redirects/final URL updates | deferred provider fact; fail-open required |
| historical conversion | separate data-operations decision; forbidden here |

Required characterization before integration:

* capture representative Playbill listing fixtures proving whether each `/job/...` URL is immutable per notice or identifying an early source-provided update/publication/revision value;
* prove unchanged metadata hashes identically and a materially revised same-URL notice hashes differently without volatile per-run fields;
* prove marketing changes retain identity, unknown/significant query values remain, relative URL joins safely, unsafe/missing identity fails open, and title alone is never identity;
* only after that gate: active hit skips detail/increments once; first crew creates one tombstone/no Opportunity or children; acting/mixed/Unknown paths remain; expiry/reactivation and changed acting revision work; caller rollback and two-worker adapter concurrency; exact request counts; no Parallel/frontend/query/invalidation/model/migration/API/cleanup/existing-data changes.

**DECISION C — ONE PLAYBILL IDENTITY PREREQUISITE.** Establish exactly one missing provider fact: **does Playbill guarantee a `/job/...` URL is immutable for one posting, or expose a stable pre-detail revision/publication marker that changes whenever the posting content is materially revised?** Until one side is proved with representative fixtures/provider evidence, title-only versioning can suppress a revised acting notice and Playbill integration is not approved.

Expected prerequisite files are Playbill listing fixtures and narrowly scoped URL/version characterization tests plus this ledger. Production provider/foundation/discovery files remain forbidden. Stop if the URL is reused without an early revision signal, if the only change signal requires detail fetch, or if significant query parameters cannot be conservatively preserved. In the latter cases a fresh preflight must choose post-detail exclusion rather than weaken version safety.

Confirmed facts: Playbill crew filtering is pre-detail, deterministic and acting-signal guarded; candidate URLs are job-path anchors joined against the listing page; detail fetch begins only in normalization; the outer run owns one Session and commit; no Opportunity exists at the desired early boundary; the foundation already provides exact-version expiry/reactivation and concurrency semantics. Rejected assumptions: display name is a stable source key; the path suffix is a documented external ID; `date.today()` is a version signal; title change detects every material revision; current silent skipping proves durable suppression safe; the adapter may open its own Session; a metric, frontend invalidation or archive owner is needed. Unresolved gap: the one provider identity/version fact named in Decision C. Implication: transaction seam and database-failure handling must be re-audited only after safe version evidence exists.

**Exact next-step gate:** add audit fixtures/characterization proving immutable job URLs or a reliable early revision signal. Do not integrate Playbill, modify the foundation, or begin transaction-seam implementation in that step.

Step 85 verification: focused Playbill-adjacent discovery/classification/identity/static tests passed (30); the disposable PostgreSQL source-exclusion suite passed (8); the normal backend suite passed (173, 29 skipped); frontend passed (309); mocked Playwright passed (34); ESLint, TypeScript no-emit, production build, static no-provider-integration searches and `git diff --check` passed. No characterization fixture was added because the repository contains no captured Playbill listing response capable of proving the missing provider fact; inventing one would not establish external behavior.

## 48. Step 86 — correction of the Playbill-specific architectural path

### Product correction and workspace audit

The product boundary is corrected: Playbill is one trusted discovery adapter among several, not a source-exclusion subsystem. Provider adapters translate source-specific data into a future shared candidate contract; the session-owning discovery orchestration layer applies generic identity, exclusion, classification, routing, deduplication and persistence policy.

The workspace verifies that this correction is documentation-only:

| File/change | Classification | Disposition | Evidence |
| --- | --- | --- | --- |
| `0055_source_exclusions.py` | valid generic foundation | keep unchanged | provider-neutral table/checks/indexes; no provider or Opportunity reference |
| `app/db/models/source_exclusion.py` and model export | valid generic foundation | keep unchanged | compact model, no provider/Opportunity relationship |
| `app/services/source_identity.py` | valid generic foundation | keep unchanged | pure source-scoped identity/version primitives and explicit URL policy input |
| `app/services/source_exclusion_service.py` | valid generic foundation | keep unchanged | supplied-Session service, no adapter/import/commit/routing behavior |
| source identity, architecture and disposable PostgreSQL tests | valid generic foundation tests | keep unchanged | generic normalization, persistence, expiry, rollback and concurrency contracts |
| `app/automation/discovery/public_sources.py` | ordinary Playbill adapter behavior predating Step 85 | keep unchanged | no identity/exclusion service import, Session, database write, commit or invalidation |
| `app/automation/discovery/service.py`, contracts and public-web work | unrelated pre-existing dirty workspace work | preserve; do not reinterpret or revert | no Step 85 source-exclusion integration; current generic run ownership remains factual context |
| Step 85 ledger section | documentation-only roadmap entry | retain factual audit, supersede future direction | no production/test/fixture file accompanied it |
| generated `__pycache__`, frontend build output and other dirty/untracked files | generated or unrelated existing state | preserve/ignore | outside corrective boundary |

Static searches found no Playbill/provider import of `SourceExclusionService`, `SourceIdentityService` or `SourceExclusion`; no adapter Session injection or commit; no provider-specific tombstone service/write; no source-exclusion call inside an adapter; no provider-specific query key, invalidation or frontend owner; and no test asserting provider-owned persistence or concurrency. The only production `playbill_public_jobs` business reference remains ordinary provider/source metadata and existing source-research aliasing, not tombstone lifecycle policy.

Therefore no production rollback and no test rollback are required. Removing code would damage valid generic infrastructure or unrelated existing work. No Step 85 fixture exists to remove.

### Work retained and direction superseded

All Step 84 generic work remains authoritative: `source_exclusions`, `SourceExclusion`, `SourceIdentity`, `SourceUrlPolicy`, `SourceIdentityService`, `SourceExclusionService`, PostgreSQL partial uniqueness, current-version compatibility, weak-identity expiration, atomic sighting/upsert, caller rollback and generic concurrency coverage.

Useful Step 85 facts remain recorded:

* the current Playbill adapter owns no Session;
* `DiscoveryAutomationService` owns the current Session and provider-run transaction;
* Playbill currently extracts `/job/` anchors and applies its existing title classifier before detail fetch;
* available repository fixtures do not prove Playbill URL immutability;
* title-only version evidence cannot safely distinguish every materially revised notice;
* the adapter must not open an independent Session or own frontend invalidation.

The following Step 85 framing is now explicitly **superseded and grants no implementation approval**:

* treating “Playbill early exclusion” as the next application architecture;
* designing a direct Playbill-to-`SourceExclusionService` call path;
* giving Playbill adapter code sighting, tombstone, transaction, Opportunity-suppression or concurrency ownership;
* making Playbill URL/version uncertainty a blocker to designing the generic orchestration boundary;
* making Playbill the first provider-specific persistence subsystem merely because its current filter is pre-detail.

The factual Decision C about unproved Playbill version evidence remains a constraint on any eventual Playbill adapter mapping, but its Playbill-specific integration roadmap is obsolete. It must be resolved as provider metadata feeding the generic candidate contract, not as authorization for provider-owned persistence.

### Corrected ownership and trusted-source semantics

```text
Source adapter
    ↓
Generic source candidate
    ↓
Session-owning discovery orchestration
    ↓
Identity and version evaluation
    ↓
Source exclusion lookup
    ↓
Classification and routing
    ↓
Opportunity, review, or compact exclusion
```

Source adapters own only source-specific HTTP collection/parsing, source URL and item-ID extraction, source-specific version evidence, raw category extraction and translation into the future generic source-candidate contract. Small provider configuration remains valid: stable source name, trust level, URL normalization policy, external-ID/version-field extraction and parser strategy. Such configuration describes source data; it must not implement application lifecycle policy.

Discovery orchestration owns the SQLAlchemy Session and transaction, identity/version evaluation, exclusion lookup, compatible sighting, exclusion creation, classification policy, uncertainty/review routing, Opportunity deduplication and persistence, parser/enrichment invocation and DiscoveryRun results. Generic exclusion policy may consume adapter-provided normalized identity inputs, but an adapter must not call the exclusion service, commit, suppress Opportunities as persisted policy, coordinate database concurrency, or trigger frontend invalidation.

Frontend owns nothing new. Source exclusions have no React Query owner, invalidation contract, UI route, hidden-review record or acknowledgement.

“Trusted source” means approved provenance, enabled discovery, no source-approval queue, expected parser structure and permitted automated ingestion. It does **not** mean that every item becomes an Opportunity or bypasses classification, uncertainty, demographics, travel, deduplication, exclusions, generic routing or transaction ownership. Trust does not create a provider-specific application lifecycle.

### Decision and next gate

**DECISION A — DOCUMENTATION CORRECTION ONLY.** Step 85 introduced no incorrect Playbill-specific production code, test, fixture, Session injection, persistence, invalidation or query ownership. Only the ledger's provider-specific next-step framing required correction. No production or test file should be removed or revised.

The exact next preflight is generic and decision-only: inventory every current provider output and orchestration seam, then define the smallest shared source-candidate contract that can carry source key, raw item identity, version evidence, raw category, source URL and source payload/reference into session-owning orchestration without moving business persistence into adapters. It must compare how Playbill and public-web/Parallel-shaped results map to one contract without implementing `SourceCandidate`, changing providers, or altering discovery behavior.

Stop if the generic contract would require removing valid adapter parsing, copying full copyrighted content unnecessarily, moving Session ownership out of orchestration, embedding provider-specific lifecycle flags, changing the tombstone foundation, or redesigning all providers in one step. Remaining unresolved issues include Playbill URL/revision evidence, equivalent identity/version evidence for other sources, the exact generic candidate payload and fail-open behavior, current pre-normalization filtering ownership, and rollback semantics for a database error during a provider run. These are inputs to later generic preflights, not approval for Playbill-specific code.

Step 86 verification: static searches confirmed no provider source-exclusion/identity-service imports, no Playbill Session/commit/rollback ownership and no frontend source-exclusion owner; focused generic-foundation and Playbill-adjacent discovery tests passed (26); disposable PostgreSQL foundation tests passed (8); the normal backend suite passed (173, 29 skipped); frontend passed (309); ESLint, TypeScript no-emit, production build, Ruff, migration-head audit (`0055_source_exclusions`), architecture/static audits and `git diff --check` passed. No test or production rollback was performed because none was warranted.

## 49. Step 87 — generic source-candidate contract and orchestration preflight

This step is decision-only. No production contract, processor, provider migration, tombstone change, frontend code, invalidation, API, metric or historical data operation was added.

### Provider and entry-point inventory

| Source/path | Entry point | Current return type | Detail owner | Classification owner | Session access | Opportunity owner |
| --- | --- | --- | --- | --- | --- | --- |
| Playbill public jobs | registry → `run_source` → `PublicPlaybillJobsSource.discover` | listing `list[dict]`, then `list[NormalizedOpportunity]` from `normalize` | Playbill `_detail_text` during normalize | shared deterministic classifier, invoked by adapter pre- and post-detail | adapter none; orchestration yes | `DiscoveryAutomationService._create_opportunity` |
| Parallel public search | `run_all` → `_run_public_web_search` → `PublicWebBreakdownSearch.search` | `PublicWebSearchResult` containing URL/report dicts and normalized opportunities | `PublicWebBreakdownSearch._fetch_visible_text` | shared classifier invoked post-detail inside public-web search | search object none; orchestration yes after result | `_process_public_web_search_result` → `_create_opportunity` |
| supervised platform import | separate API/service, not discovery registry runtime | captured dict → persisted `SupervisedBreakdownImport`; approval builds `OpportunityCreate` | supervised browser controller | import parser/confidence plus explicit user approval | service owns request Session | `OpportunityService.create` only after approval |
| manual create/paste | Opportunities API and `OpportunityService` | typed `OpportunityCreate` or text payload | user input/current Opportunity | manual defaults plus explicit parse endpoints | request service owns Session | `OpportunityService` |
| placeholder providers | discovery registry | empty `list[dict]` and normalized list | none | none | adapter none | none |
| discovery plugin interface | `DiscoveryProvider.discover/normalize` | raw dictionaries then `NormalizedOpportunity` | provider-defined | currently provider-defined/shared calls | provider none | generic orchestration after normalize |

No provider returns an ORM Opportunity, iterator or async generator. The narrowest existing shared seam is `NormalizedOpportunity`, but it occurs after provider-specific detail fetching and after Playbill/Parallel have already discarded non-acting or Unknown records. The earlier shared shape is only untyped `dict`, so it cannot safely carry identity/version authority.

### Current orchestration and transaction map

| Stage | Owner | Input | Output | Session available? |
| --- | --- | --- | --- | --- |
| registry/settings/approval | `DiscoveryAutomationService` | provider key | enabled approved plugin | yes |
| run creation | `run_source` | plugin/mode | flushed `DiscoveryRun(status=running)` | yes |
| listing collection | provider `discover` | provider network/source | raw dictionaries | not inside adapter |
| provider detail/normalize | provider `normalize` | raw items | `NormalizedOpportunity` | not inside adapter |
| provider-local dedup | `DiscoveryProvider.deduplicate` | normalized opportunities | project/role/location unique list | no adapter Session |
| validate/mode/intent/deadline | orchestration | normalized item | accepted/rejected item | yes |
| persistence dedup | `_create_opportunity` | normalized item | existing/new Opportunity | yes |
| enrichment | role sync, watch list, intelligence, trust | new Opportunity | derived rows/fields | yes |
| success bookkeeping | `run_source` | counters | succeeded run | yes; commits once |
| provider failure | `run_source` exception block | exception | attempts failed run update | yes, but no rollback first |
| Parallel collection | separate `_run_public_web_search` after provider runs | actor/mode | normalized result/report | search has none; orchestration has Session |
| Parallel persistence | `_process_public_web_search_result` | normalized public-web items | Opportunities/report | yes, but no dedicated `DiscoveryRun` transaction boundary here |

The earliest *generic* exclusion point would be after a typed listing candidate reaches orchestration and before an optional provider detail call. A second generic point is after detail normalization when safe version evidence is detail-derived. Current adapters do not expose either as a typed orchestration callback; Playbill and Parallel both fetch/filter internally.

### Selected contract design sketch

Choose **two-stage types (Option B)** for later implementation because it matches the existing discover/normalize split, permits early lookup only when evidence is sufficient, and lets Parallel defer versioning until fetched detail. One all-purpose object would mix unavailable listing/detail fields and encourage unsafe early suppression. An envelope with arbitrary provider payload would weaken type safety and risk logging full HTML or copyrighted text.

Proposed immutable `SourceListingCandidate` fields:

| Field | Requirement/owner | Persistence/logging | Role |
| --- | --- | --- | --- |
| `source_key: str` | required; adapter definition | transient; safe bounded key | stable provider scope |
| `source_url: str | None` | optional adapter evidence | transient; redact query in logs | raw input to identity service, never sole identity without authority/version |
| `external_source_id: str | None` | optional adapter evidence | transient until hashed/service use | strongest provider identity when documented |
| `version_fields: tuple[(str, str), ...]` | required for exclusion eligibility; adapter extracts, orchestration validates/hashes | transient, bounded non-content scalars | canonical version-service input |
| `title: str | None` | optional extraction | transient/log length bounded | display/classification/version evidence when approved |
| `raw_category: str | None` | optional source-native value | transient/log bounded | classification evidence, not final routing |
| `identity_authority` | required enum: `provider`, `user_supplied_url`, `none` | transient | prevents text/manual/test tombstones |
| `classification_evidence` | optional immutable bounded object: source rule key, suggested generic class, acting-signal boolean | transient | provider evidence only; core validates final eligibility |

Proposed immutable detail-stage `SourceCandidate` composes the listing candidate with the existing `NormalizedOpportunity` and optional additional bounded `detail_version_fields`. It does not repeat identity hashes or final persistence decisions. Orchestration calls the existing `SourceIdentityService`; adapters never implement hashing. Detail acquisition remains adapter-owned through a later narrow method boundary, but database policy remains central.

Rejected candidate fields: precomputed identity/version hash (central consistency risk), canonical URL duplicate, arbitrary `identity_fields`, summary, raw/normalized page text on the listing type, confidence float without a defined scale, duplicated acting/non-acting flags outside the evidence object, publication/location fields as universal requirements, `detail_fetched` boolean in place of types, arbitrary `provider_metadata`, ORM objects, Session, query keys, lifecycle actions and full provider payload/HTML. Transient normalized detail text remains inside `NormalizedOpportunity.description` only as currently required for Opportunity normalization; it must not be logged or persisted in tombstones.

Identity ownership is Model A: adapters emit raw source evidence and an explicit small `SourceUrlPolicy`/provider strategy reference; orchestration calls `SourceIdentityService`. This preserves one normalization/hash implementation while allowing provider-specific URL aliases and version extraction. `version_fields`, not hashes, cross the boundary. Missing/blank version fields make exclusion ineligible and fail open.

Classification ownership is central. Adapters may emit source-native category and bounded deterministic evidence such as `suggested_classification=crew_job`, `rule_key=playbill_title_rule`, `acting_signal=false`; they never create a tombstone or decide Opportunity lifecycle. The orchestration classifier validates provider evidence alongside shared classification. No Playbill terminology is required by other providers.

### Trusted, manual and exclusion policy

Existing provider class attributes plus `DiscoveryProviderSettings` are sufficient for the future trusted-source definition; no database registry is needed. Later code may add bounded class/definition capabilities (`trust_level`, pre-detail identity/version support, URL policy), but Step 87 adds none. Trust affects approved provenance, enablement and permission for automated ingestion, never application classification.

Manual Opportunity creation/text parsing remains outside automated candidate ingestion and has `identity_authority=none` conceptually. Supervised captures remain their existing Draft/Needs Review records; a user-supplied URL is not provider-authoritative and explicit rejection cannot create a tombstone. Placeholder/test candidates cannot be exclusion-eligible. No text-only or fixture identity may be upgraded from title/content similarity.

Central automatic exclusion eligibility requires all of: provider-authoritative identity, exact non-empty version evidence, source policy allowing automated exclusion, deterministic confirmed `Crew Job`/`Non-Acting Job`, no acting signal, and non-manual/non-test origin. Provider evidence is necessary but not persistence authority.

Early lookup is allowed only for a listing-stage candidate with authoritative identity and a provider-declared safe pre-detail version strategy. Otherwise detail is fetched and a detail-stage candidate is evaluated. Separate types, rather than a stage string, make unavailable evidence explicit. Unsafe/missing identity/version fails open into existing classification/review behavior and never creates a tombstone.

### Future processor, ordering and side effects

The eventual narrow owner should be a `DiscoveryCandidateProcessor` (name provisional) receiving the caller Session and collaborating with existing identity, exclusion and Opportunity services. It should own candidate validation, identity construction, exclusion lookup/sighting and central exclusion eligibility/routing. It should delegate existing normalized Opportunity dedup/create/enrichment rather than reimplement all ten responsibilities or become a general event framework. Provider collection/detail remains outside it; `DiscoveryAutomationService` sequences it and owns DiscoveryRun counters/commit.

Future order:

1. validate listing contract and authority;
2. build identity when version evidence is sufficient;
3. compatible active exclusion → atomic sighting and stop;
4. changed/expired/no exclusion → classify at the safe stage;
5. confirmed eligible non-acting → record/update compact exclusion and stop;
6. Unknown/mixed/low-confidence/incomplete identity → preserve existing provider-specific review/fail-open path until a shared review owner is separately approved;
7. acting detail candidate → current normalized-key dedup, then Opportunity creation and downstream role/watch-list/intelligence/trust work.

Existing Opportunity normalized-key dedup remains unchanged. Source identity may later avoid repeated fetches but must not silently merge or replace acting Opportunities without a separate deduplication decision. A changed acting version leaves the old tombstone inactive for that hash and proceeds; confirmed non-acting changed version updates the current row; expired rows require reconfirmation.

No tombstone hit/create has a frontend query owner or invalidation. Acting Opportunity creation retains existing discovery response behavior. No new frontend behavior is approved.

### Transaction and failure prerequisite

The generic processor must use the caller Session, never commit/open a Session/use nested commits, and participate atomically with Opportunity and DiscoveryRun writes. Current success behavior meets that shape for registry providers. Current failure behavior does not:

```text
run_source creates and flushes running DiscoveryRun
try performs provider and database work
except marks the same run failed
except calls db.commit() without db.rollback()
```

After an integrity/database exception, SQLAlchemy leaves the transaction failed; assigning fields does not repair it and the attempted commit raises `PendingRollbackError` or the original transactional failure. A generic processor would add expected exclusion insert/update and Opportunity failure seams to this unsafe path. There are no candidate savepoints; provider errors abort the whole source run. Parallel additionally lacks a matching dedicated run transaction in `_run_public_web_search`, but its migration is separate and must not broaden the first correction.

Rollback expectation after repair: rollback the failed provider-run transaction, then record failed-run status in a clean caller-owned transaction using the existing run identity or a safely reconstructed run record; do not partially retain sightings, exclusions, Opportunities or enrichment. Whether one candidate may fail independently is deferred—current convention aborts the whole provider run, so no savepoint is approved.

### Migration comparison, tests and gates

| Strategy | Value | Risk | Decision |
| --- | --- | --- | --- |
| A: contract+processor, no provider | proves generic policy | dead abstraction; unsafe failure owner | reject now |
| B: contract+processor with compatibility adapters | runtime proof | effectively migrates several providers and preserves untyped shapes | reject |
| C: contract types only | type review | unused types before transaction semantics; detail callback still unresolved | defer |
| D: refactor orchestration with all compatibility paths | immediate adoption | broad provider/Parallel regression surface | reject |

Required transaction-prerequisite tests before any contract implementation:

* inject a SQLAlchemy failure after `DiscoveryRun` flush and after a candidate database write;
* prove the original transaction rolls back run, exclusion, Opportunity and derived writes;
* prove failed status/error is persisted from a clean usable Session transaction;
* prove provider network/classification exception follows the same one-run failure policy;
* prove the Session remains usable and no nested commit/savepoint/provider Session is introduced;
* keep success counters/commit, generic tombstone rollback/concurrency, Playbill/Parallel behavior and frontend request graphs unchanged.

Later contract/processor tests remain as scoped in the prompt: immutable required source key; authority/version constraints; no arbitrary metadata; compatible skip/sighting; changed version continuation; non-acting tombstone; acting Opportunity delegation; uncertain current routing; manual/test prohibition; rollback; provider independence; and static no-provider Session/commit/exclusion persistence.

Product gates: two-stage types, raw evidence, version fields, orchestration identity service and central classification are correctness/implementation choices; trusted capabilities are small code configuration; manual authority is a correctness guard; early/post-detail support is required; compatibility strategy is deferred until one provider migration; candidate-level failure is deferred product/operational policy; current failed-transaction handling is a prerequisite.

**DECISION D — ONE TRANSACTION PREREQUISITE.** Correct exactly the `DiscoveryAutomationService.run_source` failed-transaction path so it rolls back the failed provider-run unit before persisting a failed `DiscoveryRun` from a clean usable transaction. Do not add candidate types, processor, exclusions, provider migrations, Parallel changes or savepoints in that correction.

Expected prerequisite files: `app/automation/discovery/service.py`, narrowly focused orchestration transaction tests (including disposable PostgreSQL where required), and this ledger. Forbidden adjacent work: `SourceListingCandidate`/`SourceCandidate`, processor, provider interface changes, Playbill/Parallel migrations, tombstone/schema/service changes, candidate-level savepoints, dedup redesign, review queue, metrics/API/frontend/invalidation/history. Stop if failed status cannot be preserved without a new Session/transaction owner, if rollback would erase unrelated already-committed provider runs, or if the correction requires changing Parallel/public-web behavior.

Confirmed facts: providers currently return raw dicts then normalized opportunities; both active automated paths fetch/filter before orchestration policy; providers own no Session; registry provider success commits per run; normalized-key dedup and downstream enrichment are central; manual/supervised flows are separate and must not tombstone; the foundation accepts raw version mappings centrally. Rejected assumptions: `NormalizedOpportunity` is early enough; one all-purpose candidate is simpler safely; adapters should form hashes; trusted means bypass; arbitrary metadata is needed; all providers must migrate together; a contract-only production type is useful before transaction safety. Unresolved gaps after the prerequisite: precise detail-fetch callback interface, current uncertain records discarded inside Playbill/Parallel before orchestration, Parallel run transaction boundary, first provider compatibility strategy and source-specific version facts.

**Exact next-step gate:** implement and characterize only the `run_source` rollback/failed-run persistence correction. Do not create the generic candidate contract or migrate any provider in that step.

Step 87 verification: focused provider/orchestration/identity/classification tests passed (44); the normal backend suite passed (173, 29 skipped); the complete disposable PostgreSQL suite passed (29, 7 existing warnings); frontend passed (309); ESLint, TypeScript no-emit, production build, Ruff, architecture/static searches and `git diff --check` passed. The mocked Playwright suite had two unrelated request-timing policy failures in `request-graphs.spec.ts` (Calendar live-refetch observation and Journal immediate-return freshness); a three-repeat focused rerun remained nondeterministic (2 passed, 4 failed). No frontend or query-policy file changed in Step 87, so this preflight did not rewrite those assertions or expand into existing timing debt.

## 50. Step 88 — `run_source` rollback and failed-run persistence correction

Step 87's sole approved prerequisite was implemented: `DiscoveryAutomationService.run_source` now rolls back the complete failed provider-run transaction before recording failure from a clean transaction. The request dependency remains the Session owner; `run_source` remains the transaction/commit owner for one registry-provider run. Providers still receive no Session and own no commit.

### Transaction evidence and corrected sequence

The old sequence was `add running run → flush → provider/normalization/persistence/derived writes → exception → mutate the same run → commit without rollback`. An ordinary Python/provider exception therefore committed partial writes, while a failed PostgreSQL flush left the Session deactivated and caused the exception handler's commit to raise `PendingRollbackError`, masking the original database error. The initial `DiscoveryRun` row was not independently committed and therefore could not survive a correct rollback.

The new sequence is:

```text
allocate application UUID and bounded run metadata
→ add/flush running DiscoveryRun inside try
→ provider, normalization, deduplication, Opportunity and derived work
→ success: mark succeeded and commit once (unchanged)
→ any failure: rollback whole run transaction
→ construct a fresh failed DiscoveryRun with the same UUID
→ add/commit failed run from the clean Session
→ re-raise the original failure
```

The flush is now inside the protected transaction boundary. The UUID is explicitly application-generated before flush, matching the model's existing Python UUID default while making identity available even if flush fails. Rollback removes the uncommitted running row and all partial source, Opportunity and child writes. The original ORM instance and its in-memory counters are not reused; a fresh instance is constructed from `run_id`, plugin ID, mode, original start time and immutable run payload.

### Failed-run and exception contract

The failed row preserves the one logical run ID, provider foreign key, mode, start time and run payload. It records `status=failed`, the existing `str(exc)` error representation, and one shared `finished_at`/`completed_at` value. All persisted-work counters are explicitly zero because the transaction that could have produced those rows was rolled back; the service does not claim rolled-back Opportunities as found, created, hidden, saved or rejected. No schema or error-format change was introduced.

Provider/network/parser/normalization Python exceptions and SQLAlchemy/database exceptions use the same whole-run rollback path. The caller contract remains re-raising the original exception. If the clean failed-row commit itself fails, `run_source` rolls that secondary transaction back, logs the secondary persistence failure once, and then re-raises the original failure; it does not loop, reuse an aborted transaction or mask the primary error. The same Session is queryable after both the ordinary failure path and the secondary-persistence-failure path.

Commit-time failure was characterized at the closest deterministic seam: the first (success) commit was forced to fail and the second clean failed-row commit was allowed to complete. The original commit exception remained primary and exactly one failed logical run persisted. No early running-run commit was added. Successful empty-provider characterization still returns the existing result shape and performs exactly one commit.

### Characterization baseline and proof

Tests were written before production behavior changed. The old implementation failed three focused assertions: a provider exception committed a partial `OpportunitySource`; a real PostgreSQL not-null failure after flushed Opportunity and role writes surfaced `PendingRollbackError`; and failed-status commit failure masked the original provider error. Two baseline assertions already passed: recoverable commit-time sequencing and the one-commit success shape.

After the correction, disposable PostgreSQL tests prove:

* provider exception rolls back a flushed partial write and persists one failed run;
* a real PostgreSQL constraint failure rolls back Opportunity, BreakdownRole and their new source;
* failed counters are zero, completion/error fields persist and no second run is created;
* the Session accepts a subsequent query with no `PendingRollbackError`;
* a forced final commit failure is rolled back and recorded under the original run UUID;
* a forced failed-status commit failure does not mask the provider exception;
* success still commits once and returns the unchanged response.

Static protection confirms no `begin_nested`/savepoint, candidate contract, exclusion orchestration, provider Session/commit, new frontend ownership or migration was introduced. Playbill, Parallel, source identity/exclusion, query keys and invalidation remain unchanged.

Confirmed facts: the running row is uncommitted; its application UUID can be fixed before flush; rollback makes a fresh transaction available on the same caller-owned Session; fresh reconstruction is safer than reusing rolled-back ORM state; one provider failure continues to abort the whole source run. Rejected assumptions: a Python exception may safely retain partial writes; mutating the old run after rollback is authoritative; `commit()` repairs an aborted Session; failed in-memory created counters should survive rollback; a second Session or savepoint is required. Unresolved gap: candidate-level partial success remains an unapproved product/transaction policy and Parallel's separate public-web transaction boundary remains outside this correction.

**RESULT A — TRANSACTION PREREQUISITE IMPLEMENTED.** The Step 87 generic source-candidate architecture preflight may resume from current code evidence. This result does not approve candidate types, a processor, provider migrations, source-exclusion orchestration, savepoints or any frontend work. A fresh check-in is required before implementing those boundaries.

Step 88 files: `backend/app/automation/discovery/service.py`, `backend/tests/contract_smoke/test_discovery_run_transactions.py`, `backend/tests/test_source_exclusion_architecture.py`, and this ledger. Stop condition satisfied: transaction correction only; no generic source candidate work began.

Step 88 verification: the focused real-PostgreSQL transaction suite passed (5); the complete disposable PostgreSQL suite passed (34, 18 warnings); focused discovery/provider/identity/static tests passed (27); the normal backend suite passed (174, 34 contract skips); frontend unit tests passed (309); mocked Playwright passed (34); ESLint, TypeScript no-emit, production build, changed-file Ruff, architecture/static searches, migration-head audit (`0055_source_exclusions`) and `git diff --check` passed. Repository-wide Ruff remains red on 15 unrelated pre-existing findings outside Step 88; those files were not changed. Direct `alembic current` could not connect to the developer database in the sandbox, while the guarded disposable runner successfully upgraded a clean database through head and ran the migration/contract suite.

## 51. Step 89 — renewed generic source-evidence and exclusion-gate preflight

### Step 88 gate and corrected transaction lifecycle

Step 88 records `RESULT A — TRANSACTION PREREQUISITE IMPLEMENTED`, and current code plus its disposable-PostgreSQL suite confirms every gate condition. `run_source` allocates and flushes one running `DiscoveryRun`, executes provider/normalization/deduplication/Opportunity/derived writes in the same caller-owned Session transaction, commits once on success, and on any failure rolls back all partial writes before reconstructing the same logical failed run ID in a clean transaction. The Session remains usable, success behavior is unchanged, and neither savepoints nor provider Sessions were added.

This repair removes the transaction blocker but does not automatically validate Step 87's proposed two-stage domain model. A future central exclusion write may participate safely in the whole provider-run transaction; an exclusion failure must continue to fail and roll back the whole run. Candidate-level partial success, nested commits and savepoints remain unapproved.

### Revalidated provider and orchestration inventory

| Source | Current shape | Detail/classification owner | Session/Opportunity owner | Step 89 implication |
| --- | --- | --- | --- | --- |
| Playbill public jobs | `discover()` emits listing dictionaries; `normalize()` emits `NormalizedOpportunity` | adapter filters deterministic non-acting/irrelevant listing text before detail; adapter fetches detail and classifies again | adapter has no Session; `run_source` owns persistence | can later emit generic evidence, but current listing URL/version durability is still unproved |
| Parallel public search | `PublicWebSearchResult` with reports and normalized opportunities | search helper fetches each candidate page and discards Crew/Non-Acting/Unknown after detail classification | helper has no Session; `_process_public_web_search_result` owns Opportunity writes, outside registry-provider `DiscoveryRun` | compatible with the evidence vocabulary later, but its separate transaction/run boundary excludes it from the first migration |
| supervised platform import | persisted Draft/Needs Review `SupervisedBreakdownImport`, then user approval creates an Opportunity | supervised import service parses; user approval is lifecycle authority | request service owns Session and commits separately | stays outside automatic exclusions; user rejection is not provider-authoritative evidence |
| manual create/paste | `OpportunityCreate` or pasted text against an existing Opportunity | Opportunity service/parser | request service owns Session | text-only/manual evidence remains ineligible for tombstones |
| placeholder providers | empty raw lists and empty normalized lists | none | no adapter Session; generic orchestration if implemented later | need no migration or Playbill-specific fields |

No active provider returns ORM objects. Registry providers still share only raw dictionaries followed by `NormalizedOpportunity`; Parallel is a separate public-web result path. `run_source` remains the narrow session-owned orchestration seam: provider call → normalize/deduplicate/validate → mode/intent/deadline policy → normalized-key dedup and Opportunity creation → role/watch-list/intelligence/trust writes → run counters → one commit. The future exclusion gate may be invoked at the first point where a provider-neutral evidence value exists, but Step 89 does not insert that call.

### Contract comparison and selected shape

| Criterion | Two-stage candidates | One detail-ready candidate | Listing envelope + normalized | Evidence companion |
| --- | --- | --- | --- | --- |
| provider neutrality | good | good | envelope risks provider payload | best; identity evidence is independent |
| early exclusion | yes | no | yes | yes, whenever exact listing evidence exists |
| existing-code reuse | duplicates normalized lifecycle | duplicates normalized fields | reuses normalized value | reuses `NormalizedOpportunity` unchanged |
| Playbill fit | good but premature callback redesign | loses early skip | workable | workable after identity facts are established |
| Parallel fit | forces listing/detail types | post-detail only | workable | post-detail evidence works without Playbill fields |
| migration scope | high | medium | medium | low |
| testability | high | high | payload boundary is weaker | high; pure validation plus service orchestration |

Select **Option D: an immutable source-evidence companion**, not `SourceListingCandidate → SourceCandidate`. Two full candidate types are rejected because they duplicate the already-established normalized acting contract and require an optional-detail-fetch framework before one provider proves it. A generic envelope is rejected because it invites arbitrary provider payloads. A detail-only candidate is rejected because it cannot support safe early exclusion.

The evidence companion is valid at either listing or detail time. It carries no stage flag: presence of authoritative identity plus exact bounded version evidence determines whether the gate can run. Existing `NormalizedOpportunity` remains the acting-detail value and is passed separately only in later orchestration/provider work.

### Exact approved contract sketch

Approve these provider-neutral immutable values for the next implementation:

`SourceVersionField(name: str, value: str)` — name required, normalized and bounded to 80 characters; value required, normalized and bounded to 500 characters. A `tuple[SourceVersionField, ...]` is ordered canonically by name, has 1–16 unique names, is transient, and is the sole version input to `SourceIdentityService`. Values must be bounded scalar source evidence, never full text/HTML. The central layer converts the tuple to the existing mapping only after duplicate-name validation.

`SourceEvidence` fields:

| Field | Contract | Ownership/use |
| --- | --- | --- |
| `source_key` | required normalized string, 1–160 | adapter definition supplies stable key; identity scope; safe to log |
| `source_url` | optional absolute URL, max 1000 | adapter evidence; identity input; log only redacted/canonical host/path, not raw query |
| `external_source_id` | optional string, max 255 | provider-authoritative identifier; identity input; log only bounded/redacted value |
| `identity_authority` | required enum `provider`, `user_supplied_url`, `none` | central exclusion eligibility; only `provider` may auto-exclude |
| `version_fields` | immutable tuple described above | exact-version input; required for exclusion, never persisted raw |

At least one of URL/external ID is required to build identity, but an evidence object may be representable without either so unsafe/manual input can fail open through an explicit validation result rather than raising a provider-wide error. The gate, not the provider, decides eligibility. `title` and `raw_category` are rejected as universal fields: they may be source-specific inputs to a version extractor or classification evidence but are not universally authoritative identity. Canonical URL, hashes, raw content, metadata dictionaries, ORM models, Session, persistence actions and Opportunity fields are forbidden.

`SourceClassificationEvidence` fields:

| Field | Contract | Meaning |
| --- | --- | --- |
| `rule_key` | required bounded identifier, 1–120 | source/shared deterministic rule provenance; no prose |
| `suggested_classification` | enum `Acting Role`, `Crew Job`, `Non-Acting Job`, `Unknown` | evidence, never final persistence authority |
| `confidence_kind` | enum `deterministic`, `probabilistic`, `unknown` | only deterministic may qualify |
| `acting_signal_present` | boolean | blocks exclusion when true |
| `non_acting_signal_present` | boolean | required for exclusion |

Mixed evidence is both booleans true and is ineligible. Unknown uses the Unknown classification and/or unknown confidence. The gate accepts only deterministic Crew/Non-Acting evidence with non-acting true and acting false, then centrally maps approved source-rule evidence to the existing `provider_listing_rule` or shared deterministic evidence to `deterministic_classification`. Providers cannot authorize or persist a tombstone.

### Identity, version, trust and processor ownership

Adapters provide raw evidence; the central gate calls the existing pure `SourceIdentityService`. Providers do not precompute hashes or import `SourceExclusionService`. Source-specific URL policy and extraction remain small code-owned strategy/configuration, but normalization/hashing remains singular. Exact non-empty version fields are mandatory; title-only universal versioning, full HTML and arbitrary payload persistence are forbidden.

Approve one small immutable `SourceCapabilities` value in code, attached through the existing provider definition/class mechanism:

* `trusted_source: bool` — approved provenance/automated collection, never classification bypass;
* `automatic_non_acting_exclusion: bool` — explicit permission for the central gate;
* `url_policy: SourceUrlPolicy` — provider-specific safe canonicalization rules.

Existing `DiscoveryProviderSettings.enabled` and researched-source approval remain operational enablement/approval owners, so duplicate `enabled`, approval, external-ID and stage-support flags are rejected. Early versus post-detail support is evidenced by when the adapter can emit exact version fields, not a promise flag. Trusted never bypasses classification, demographic/travel policy, deduplication, exclusion checks or review.

Select **Processor A: a session-owned exclusion gate only**. It validates evidence/capabilities, builds identity, records compatible sightings, validates automatic-exclusion eligibility, and records confirmed exclusions through `SourceExclusionService`. It receives the caller Session or existing service collaborators and never commits, opens a Session, invokes a provider, creates an Opportunity, routes uncertainty, performs normalized-key deduplication or owns downstream parsing. A full candidate router is rejected as premature; helpers embedded in the already-large `DiscoveryAutomationService` would blur policy and test ownership.

Approved conceptual operations are `check_compatible(evidence, capabilities) -> gate result` and `record_confirmed(evidence, classification_evidence, capabilities) -> gate result`, with explicit outcomes such as excluded/not-eligible/version-changed. Names remain subject to repository conventions, but no provider-specific method is allowed. A compatible exclusion updates the sighting and stops later processing when orchestration eventually calls it. Changed/expired/unsafe evidence returns continue/fail-open. Confirmed eligible non-acting records the compact tombstone. Acting, Unknown, probabilistic and mixed evidence never record.

### Behavior, transactions and migration boundary

Acting behavior remains the existing `NormalizedOpportunity` validation, normalized-key deduplication, `_create_opportunity`, and derived writes. Uncertain behavior remains exactly where each current source leaves it; the foundation does not invent a review queue or correct Playbill/Parallel's current filtering. Manual text/paste and supervised imports are not wired to the gate. User rejection, supplied URL alone and test/example text cannot create tombstones.

The gate participates in the corrected Step 88 caller transaction. It performs no commit and uses no savepoint. Any identity/exclusion database failure propagates, causing the whole registry-provider run to roll back and persist one clean failed `DiscoveryRun`. This is the existing failure policy and is preserved. Parallel's separate path is deferred.

Migration-boundary comparison:

| Boundary | Value | Risk | Decision |
| --- | --- | --- | --- |
| contract/validation only | proves types | unused and no persistence-policy proof | reject |
| contract + central exclusion gate, no provider | proves complete provider-neutral policy against real PostgreSQL | temporarily unused by production provider | **approve**; smallest independently testable foundation |
| plus behavior-preserving compatibility | no provider can emit evidence yet, so compatibility is artificial | widens orchestration without behavior | reject |
| plus thin Playbill | real vertical slice | Playbill URL reuse/version durability remains unproved; would force policy guessing | defer |
| full provider refactor | broad adoption | changes Playbill and Parallel together | reject |

The approved foundation has bounded temporary dead-code risk, like the already-approved tombstone foundation, but can be exhaustively validated without falsely establishing Playbill identity. Parallel can later provide the same `SourceEvidence` after detail fetch using its own source key, URL policy and version extractor; it needs no Playbill fields and no migration now.

No frontend query owner, invalidation, UI, API, schema, migration, historical conversion, cleanup or metrics are approved. Exclusion hits publish no Opportunity and therefore trigger no Breakdowns invalidation. Acting Opportunity behavior remains unchanged.

### Implementation tests and gates

Required next-step tests:

1. immutable provider-neutral values; required/bounded source key and version fields; unique canonical field order;
2. authority enum and unsafe/manual evidence validation; no arbitrary metadata, ORM or Session in contracts;
3. URL/external-ID validation delegates to `SourceIdentityService`; exact version is required; no title-only identity;
4. bounded deterministic/probabilistic/Unknown/mixed classification vocabulary;
5. compatible exclusion updates one sighting and returns stop;
6. changed or expired version continues without sighting;
7. deterministic Crew/Non-Acting evidence records one tombstone;
8. acting, Unknown, probabilistic, mixed, untrusted, disabled-capability and user/manual evidence record nothing;
9. gate never commits and a caller rollback removes sighting/insert;
10. a gate database failure participates in the Step 88 whole-run rollback test seam without provider Session/savepoint;
11. generic source key scoping and no cross-source match;
12. existing source-exclusion concurrency/rollback suite remains green;
13. existing normalized-key dedup, `_create_opportunity`, current uncertain behavior and discovery success/failure behavior remain unchanged;
14. static providers import neither Session nor exclusion persistence; no provider commit;
15. no schema/frontend/query/invalidation/API/history/cleanup/metrics/Parallel/Playbill production changes.

Product gates: contract shape, bounded evidence, central identity/version ownership, deterministic classification requirements, provider authority, no Session/commit and whole-run rollback are correctness requirements; exact dataclass/module/method names and `SourceCapabilities` attachment are implementation choices; provider URL/version extractors are source configuration; first Playbill and Parallel migrations are deferred until source-specific evidence is characterized; manual/supervised exclusion remains prohibited by current product contract.

**DECISION A — IMPLEMENT GENERIC CONTRACT AND EXCLUSION GATE FOUNDATION.** Approve only the immutable provider-neutral evidence/classification/capability contract, one caller-Session-owned central exclusion gate, and focused pure/PostgreSQL/static tests. Do not migrate Playbill, Parallel, supervised imports, manual entry or placeholders; do not change current orchestration calls or production behavior.

Expected next-step files: one narrow discovery contract module (or bounded additions to the existing contract module), one generic exclusion-gate module, focused unit tests, focused disposable-PostgreSQL tests, static architecture tests, and this ledger. `SourceExclusion`, its migration, `SourceIdentityService`, `SourceExclusionService`, provider adapters, `DiscoveryAutomationService`, Opportunity services, frontend and query/invalidation files should remain unchanged unless the implementation gate finds a direct contradiction and stops.

Forbidden adjacent work: provider migration, detail-fetch callbacks, candidate router, Opportunity routing/dedup refactor, uncertain-review redesign, source-specific version policy, Parallel transaction work, savepoints, commits/new Sessions, schemas/migrations/APIs/frontend/invalidation, historical conversion, cleanup or metrics. Stop if the gate cannot validate without provider-specific fields, must commit/open a Session, needs orchestration integration for correctness, weakens exact-version matching, permits manual/test tombstones, or requires changing the Step 88 success/failure contract.

Confirmed facts: Step 88 transaction behavior is safe for a future gate; providers own no Session; Playbill and Parallel currently discard non-acting evidence before central policy; `NormalizedOpportunity` remains a useful acting-detail contract; the identity service already accepts raw source/URL/external-ID/version mappings; the exclusion service is caller-transaction-owned. Rejected assumptions: two full candidate stages are required; Playbill is ready as the first consumer; a generic provider payload is necessary; title/category belong universally in identity; a full router is needed to centralize exclusions; compatibility shims add value before evidence exists. Unresolved gaps for provider migration: Playbill's durable job identity and safe version extractor, a generic optional-detail callback shape, preservation/improvement of uncertain Playbill/Parallel records, and Parallel's separate run transaction owner.

**Exact next-step scope:** implement Decision A only—the generic immutable evidence/capability/classification contracts and central exclusion gate foundation with tests. Do not integrate any provider or call the gate from `run_source` yet.

Step 89 verification: focused transaction/provider/identity/exclusion/static tests passed (27, with 5 PostgreSQL tests skipped outside the guarded runner); the complete disposable PostgreSQL suite passed (34, 18 warnings); the normal backend suite passed (174, 34 contract skips); frontend unit tests passed (309); mocked Playwright passed (34); ESLint, TypeScript no-emit, production build, scoped Ruff, provider Session/commit searches, source-exclusion integration searches, frontend ownership searches and `git diff --check` passed. Repository-wide Ruff continues to report the same 15 unrelated pre-existing findings recorded in Step 88; this audit changed none of those files.

## 52. Step 90 mandatory implementation gate — runtime-consumer contradiction

Step 90 passed the decision-name gate because Step 89 records `DECISION A — IMPLEMENT GENERIC CONTRACT AND EXCLUSION GATE FOUNDATION`, and Step 88's transaction proof remains valid. Production implementation did not begin because the mandatory current-code gate exposed a contradiction between the approved Step 89 boundary and Step 90's additional runtime-use requirement.

Step 89 deliberately approved a provider-neutral contract and exclusion-gate foundation with bounded temporary dead-code risk. It explicitly prohibited provider migration, prohibited changing current orchestration calls, and listed `DiscoveryAutomationService` and all provider adapters among files expected to remain unchanged. Current code still matches that evidence: Playbill emits raw listing dictionaries and then `NormalizedOpportunity` while discarding non-acting listings inside the adapter; Parallel emits its separate `PublicWebSearchResult`/normalized path while discarding non-acting and Unknown results; placeholder providers emit nothing; supervised and manual paths remain outside automated discovery. No live path emits the approved `SourceEvidence` companion.

Step 90 adds a stricter requirement: Decision A must include an orchestration seam that invokes the gate, and if no live provider consumes it the implementation must nevertheless have a bounded internal integration path that is not dead/unused. Under current code, no truthful invocation exists without one of:

1. migrating Playbill or Parallel to emit evidence, which Step 89 Decision A and Step 90's provider limits forbid;
2. fabricating evidence from `NormalizedOpportunity.source_metadata`, which violates the authoritative-identity/exact-version contract and risks title/metadata-derived tombstones;
3. adding an uncalled/no-op orchestration helper, which remains dead code and fails Step 90's explicit runtime-use requirement;
4. changing acting/uncertain behavior or provider return shapes, which exceeds Decision A and requires a fresh provider-specific preflight.

Therefore the approved contract/gate cannot be implemented faithfully under all Step 90 constraints. This is not a transaction, schema, Session or persistence blocker. It is one exact implementation-boundary blocker: **Decision A must either permit a foundation with no live consumer, as Step 89 recorded, or be replaced by a separately approved thin provider migration that supplies authoritative identity and exact version evidence.** Playbill cannot be selected implicitly because its durable job identity/version facts remain unresolved; Parallel cannot be selected because it is expressly deferred and has a separate run boundary.

Mandatory pre-implementation gate result:

* Step 89 decision: Decision A.
* Approved types/fields: immutable `SourceVersionField`, `SourceEvidence`, `SourceClassificationEvidence`, and `SourceCapabilities` as recorded in Step 89.
* Identity/version owner: central identity service consuming adapter-provided raw authoritative evidence and exact bounded version fields.
* Gate/transaction owner: generic caller-Session-owned exclusion gate with no commit/savepoint; Step 88 whole-run rollback when eventually invoked by `run_source`.
* Acting/uncertain owner: existing orchestration/provider behavior, unchanged.
* Manual/supervised restriction: no automatic exclusion.
* Playbill/Parallel scope: no migration under Decision A.
* Missing required item: a permitted live producer and call site for `SourceEvidence`.

No characterization tests were added because expected failures could not be limited to the approved missing foundation: any runtime test would necessarily encode an unapproved provider migration, fabricated evidence, or a behavior-changing orchestration adapter. No production, test, schema, provider, query, invalidation or frontend file changed in this stopped implementation step. The only change is this discrepancy record.

**STEP 90 RESULT — IMPLEMENTATION BLOCKED AT MANDATORY GATE.** A fresh decision is required. The narrow choices are: (A) explicitly reaffirm foundation-only implementation and waive the live-consumer requirement, or (B) preflight one thin provider evidence mapping after proving that provider's authoritative identity and exact version contract. Do not implement generic contracts, the gate, Playbill, Parallel or an artificial compatibility seam until that choice is recorded.

## 53. Step 91 — foundation-only policy reconciliation

### Conflict resolution and repository precedent

Step 89 approved `DECISION A — IMPLEMENT GENERIC CONTRACT AND EXCLUSION GATE FOUNDATION`: immutable provider-neutral evidence/classification/capability contracts, validation, one caller-Session-owned gate, typed results and direct tests, with no provider migration or orchestration invocation. Step 90 correctly stopped because its new live-consumer requirement contradicted that approval. The contradiction was procedural, not evidence that the contract or transaction design was unsafe.

Repository evidence supports intentionally staged foundations. Step 83/84 deliberately introduced `0055_source_exclusions`, `SourceExclusion`, `SourceIdentity`, `SourceUrlPolicy`, `SourceIdentityService` and `SourceExclusionService` before any provider consumed them. The implementation had no API/frontend/query/invalidation owner and no discovery call site, yet it provided independently executable persistence, normalization, exact-version, expiry, concurrency and rollback behavior. Direct pure and real-PostgreSQL tests proved those invariants. Current static searches still show that production consumers of the identity/exclusion services are limited to their own generic modules; provider adapters import neither service nor Session.

Other staged repository patterns exist—placeholder provider definitions precede implementations, internal parsers/services are directly testable before every route/UI owner exists, and dormant server histories may precede a frontend query owner—but Step 84 is the controlling like-for-like precedent.

| Concern | Step 84 foundation | Proposed generic contract/gate |
| --- | --- | --- |
| immediate live consumer | no provider integration | no provider/orchestration integration |
| bounded independent behavior | identity/version normalization plus atomic tombstone persistence | evidence/capability/classification validation plus central exclusion eligibility/outcome |
| direct tests | pure, schema, PostgreSQL, concurrency, rollback, static | pure contract, PostgreSQL gate, rollback, Step 88 integration seam, static |
| database effects when called | insert/update through caller Session, no commit | delegates insert/update to existing service through caller Session, no commit |
| provider-neutral | yes | yes; provider keys/policies are inputs, never branches |
| speculative fields | deliberately minimized | bounded fields fixed by current identity/exclusion contracts; arbitrary payload rejected |
| safe removal/revision | model removal would require migration once deployed | no schema/data/API/provider consumer; removable without data migration or compatibility break |

The proposed foundation is therefore less costly to revise than Step 84, not more. It adds no persistence shape and exposes no public route or frontend contract.

### Independent value and exact responsibility

The gate is not an alias over `SourceExclusionService`. Existing services prove how to hash identity and persist exact-version exclusions, but they intentionally accept already-authorized calls. The missing independent invariant is whether source evidence is eligible to reach persistence at all. The approved foundation centralizes that decision so a future adapter cannot accidentally turn a user URL, probabilistic classification, mixed acting signal or versionless item into a tombstone.

Its complete bounded responsibility is exactly:

1. validate immutable source evidence and bounded version fields;
2. validate code-owned source capabilities;
3. return ineligible without database mutation for insufficient/untrusted/manual evidence;
4. delegate identity construction to `SourceIdentityService`;
5. delegate exact compatible lookup/sighting to `SourceExclusionService`;
6. return a typed existing-exclusion outcome on a compatible hit;
7. validate deterministic confirmed Crew/Non-Acting evidence with no acting signal;
8. delegate confirmed exclusion persistence and return a typed new-exclusion outcome;
9. return continue/ineligible for changed, acting, Unknown, mixed or probabilistic evidence;
10. never commit, open a Session, use a savepoint, create an Opportunity, invoke a provider, fetch, classify with AI, route acting/uncertain data, invalidate frontend data, or own metrics.

This responsibility is fully definable without source-specific behavior. Direct tests may invoke it using synthetic **field-level** evidence such as `source_key=contract_test_source`, an external ID or absolute example URL, explicit version scalars, and deterministic/mixed/acting classification flags. Those fixtures test generic invariants only. They must not use Playbill/Parallel names, URLs, response copies or undocumented semantics and must not claim network savings or live suppression.

### Direct invocation, dormancy and anti-speculation safeguards

Direct service invocation in unit/PostgreSQL tests is sufficient proof for this one staged boundary. It is not a runtime consumer and must not be described as active product behavior. Until a separately approved provider migration supplies authoritative evidence, the feature is dormant: no discovery request calls the gate, no live item is suppressed, no detail request is avoided, and no live Opportunity path changes.

The Step 90 live-consumer requirement is explicitly waived for the next foundation-only implementation. This waiver does not permit fake integration. The implementation must not:

* call the gate from `run_source` with `None`, empty, inferred or discarded evidence;
* wrap `NormalizedOpportunity`/`source_metadata` into synthetic authority;
* add unreachable/no-op branches, hidden flags, fake adapters, placeholder production records or an unused provider registry entry;
* add Playbill/Parallel conditionals, fields, policies or fixtures to the generic gate;
* widen a public barrel, API/schema or frontend type surface;
* claim active request savings, suppression or Opportunity avoidance.

Speculative architecture is further bounded by requiring frozen validated data classes/enums only for the Step 89 fields, one typed outcome vocabulary, composition of the two existing services, and no generic processor/router/framework. No title, raw category, HTML, payload dictionary, ORM object, Session field, callback, Opportunity or stage abstraction may be added. Contract/gate modules remain internal to backend discovery and may be renamed/revised before first provider use.

The typed gate tests must cover authoritative identity, exact version, compatible sighting, changed/expired version, deterministic non-acting, acting conflict, mixed/Unknown/probabilistic, manual/user-supplied authority, untrusted capability and caller rollback. Test data is invented bounded scalar evidence and contains no copyrighted provider content.

### Removability, persistence and follow-up

Because no consumer imports the foundation, it may be revised or removed without schema migration, historical transformation, provider behavior change, frontend/API compatibility break, query/invalidation change or data cleanup. The existing `source_exclusions` table, identity service and exclusion service remain the only persistence layer. The gate adds no model, migration, API, frontend type, query key, invalidation, UI, history conversion, cleanup or metrics.

After implementation, the next step is a source-selection preflight—not an automatic Playbill migration. It must compare real source paths using authoritative identity, exact version evidence, deterministic classification evidence, stage availability, corrected transaction fit, access constraints, migration scope, provider neutrality and deterministic testability. Playbill, Parallel or another real supported public source may be selected; selecting none remains valid. Manual text/test entries and supervised user rejection stay ineligible.

### Decision and exact next boundary

**DECISION A — REAFFIRM FOUNDATION-ONLY IMPLEMENTATION.** The generic contracts and central exclusion gate have bounded independent value and may be implemented without a current provider consumer. Step 90's live-consumer requirement is explicitly waived for this single implementation boundary.

Approve only:

* immutable `SourceVersionField`, `SourceEvidence`, `SourceClassificationEvidence` and `SourceCapabilities` contracts with the exact Step 89 bounds/vocabularies;
* validation and central conversion of bounded version fields into the existing `SourceIdentityService` input;
* one typed gate outcome vocabulary (`excluded_existing`, `excluded_new`, `continue_processing`, `ineligible_for_exclusion` or repository-equivalent exact names);
* one caller-Session-owned gate composing existing identity/exclusion services;
* direct pure, real-PostgreSQL, rollback and static architecture tests;
* ledger update.

Expected production files: one narrow internal discovery contract module (or bounded additions to `contracts.py`) and one narrow internal exclusion-gate module. Expected tests: focused contract/validation tests, focused disposable-PostgreSQL gate tests, Step 88 rollback regressions and static ownership tests. `DiscoveryAutomationService`, all providers, `SourceExclusion`/migration, existing identity/exclusion services, Opportunity services, APIs and frontend production files remain unchanged.

Forbidden adjacent work: any runtime call site, provider mapping/migration, compatibility adapter, generic router/processor, detail callback, fabricated evidence, Playbill/Parallel policy, manual/supervised integration, Session/commit/savepoint ownership change, schema/API/frontend/query/invalidation/history, metrics, cleanup or conversion. Stop if implementation requires provider-specific data, changes existing service semantics, cannot remain no-commit, permits versionless/manual/mixed evidence, needs orchestration wiring for correctness, or introduces a public compatibility surface.

Required next-step tests are the Step 89 contract/gate list plus explicit proof that no production consumer imports the new gate, direct test fixtures use generic names only, modules expose no ORM/Session in contract values, rollback removes both new exclusion and sighting changes, Step 88 transaction tests remain green, and no live request/provider/Opportunity/frontend graph changes.

Confirmed facts: Step 84 establishes like-for-like precedent; existing services lack central eligibility policy; the gate responsibility is independently executable; Step 88 makes eventual caller transaction integration safe; no current provider can truthfully consume the contract. Contradictory instructions resolved: Step 89 allowed dormancy while Step 90 demanded a live seam; Step 91 retains the approved bounded dormancy and rejects fake wiring. Rejected assumptions: every production-domain module must have an immediate runtime consumer; test-only evidence is a fake provider; the gate is merely a wrapper; Playbill must be selected next; a registry/no-op call makes architecture more real.

**Exact next prompt scope:** implement only this reaffirmed dormant foundation and its direct tests. Do not add an orchestration invocation. After it is green, run a fresh provider-selection evidence preflight.

Step 91 verification: focused source-identity/source-exclusion/static and Step 88 transaction tests passed (8, with 5 guarded PostgreSQL tests skipped outside the disposable runner); the normal backend suite passed (174, 34 contract skips); frontend unit tests passed (309); ESLint, TypeScript no-emit, production build, scoped Ruff, provider Session/commit/persistence searches and `git diff --check` passed. No production or test file changed in this reconciliation step, so the already-green complete disposable PostgreSQL and mocked Playwright results from Step 89 remain the current behavior evidence rather than being rerun for a documentation-only policy correction.

## 54. Step 92 — dormant generic source-evidence and exclusion-gate foundation

### Gate and characterization baseline

Step 91 records `DECISION A — REAFFIRM FOUNDATION-ONLY IMPLEMENTATION` and explicitly waives Step 90's live-consumer requirement. The mandatory gate therefore approved only immutable provider-neutral evidence/capability/classification contracts, a caller-Session-owned exclusion gate, typed outcomes, direct tests and this ledger update. `DiscoveryAutomationService.run_source`, providers, Opportunity services, APIs, migrations, ORM schema and frontend production code remained outside the boundary.

Tests were added before production modules. The pure contract baseline failed only because `app.automation.discovery.source_evidence` did not exist. No existing test encoded the proposed behavior and no compensating runtime seam existed. The disposable PostgreSQL baseline later exposed one invalid test setup—an expiry earlier than `first_seen_at`—and thereby confirmed the existing `ck_source_exclusions_expiry_order` constraint; the fixture was corrected to evaluate after a valid future expiry, with no production change.

### Contracts, validation and immutability

The internal provider-neutral contract lives in `backend/app/automation/discovery/source_evidence.py`. It contains frozen dataclasses and bounded string enums only:

* `SourceVersionField(name, value)`: NFKC/whitespace canonicalization; non-empty name/value; maximum lengths 80/500.
* `SourceEvidence(source_key, source_url, external_source_id, identity_authority, version_fields)`: source key required and bounded to 160; optional URL/external ID bounded to 1000/255; at most 16 immutable version fields; stable name sorting; duplicate names rejected. Incomplete ordinary evidence remains representable so the gate can fail open.
* `SourceClassificationEvidence(rule_key, suggested_classification, confidence_kind, acting_signal_present, non_acting_signal_present)`: rule key required/bounded to 120; classifications are `Acting Role`, `Crew Job`, `Non-Acting Job`, or `Unknown`; confidence is deterministic, probabilistic, or unknown; conflicting signals remain representable.
* `SourceCapabilities(trusted_source, automatic_non_acting_exclusion, url_policy)`: code-owned booleans plus the existing immutable `SourceUrlPolicy`; no registry or persistence.
* `IdentityAuthority`: `provider`, `user_supplied_url`, or `none`. Only provider authority is eligible for automatic exclusion.

The contracts contain no Session, ORM row, Opportunity, raw HTML, arbitrary metadata/payload, precomputed hash, provider-specific field, callback or frontend instruction. Trusted status alone grants nothing: automatic exclusion also requires the explicit capability, provider authority, usable URL or external ID, at least one exact version field, deterministic Crew/Non-Acting classification, a non-acting signal and no acting signal.

### Gate, outcomes and service delegation

`backend/app/automation/discovery/source_exclusion_gate.py` adds one narrow `SourceExclusionGate` and frozen `SourceExclusionGateResult`. Outcomes are exactly `excluded_existing`, `excluded_new`, `continue_processing`, and `ineligible_for_exclusion`.

The caller supplies the SQLAlchemy Session. The gate constructs identity only through `SourceIdentityService.build_identity`, passing the source key, raw URL, external ID, canonically ordered version mapping and existing URL policy. It does not reproduce URL/version hashing, source scoping or expiration. It delegates compatible lookup/sighting and confirmed exclusion writes only to `SourceExclusionService`.

Eligibility is evaluated before persistence. Insufficient authority/capability/identity/version evidence returns `ineligible_for_exclusion` with zero writes. Unsafe identity normalization also fails open through that result. With eligible identity, an exact active match records one sighting and returns `excluded_existing`. No match and no classification returns `continue_processing`. Only deterministic Crew/Non-Acting evidence with a non-acting signal and no acting signal records `confirmed_non_acting` through the established `provider_listing_rule` vocabulary and returns `excluded_new`; acting, Unknown, probabilistic or mixed evidence is ineligible.

Changed versions are not compatible hits. Eligible changed non-acting evidence uses the existing current-version-row update; acting/uncertain evidence does not overwrite the old tombstone. Expired weak identities do not suppress, while eligible reconfirmation reactivates through the existing service. The gate exposes no additional lifecycle detail because the persistence service already abstracts insert, current-version replacement and reactivation.

### Transaction, persistence and neutrality proof

The gate never commits, rolls back, opens a Session, uses a savepoint or starts a nested transaction. SQL failures propagate. Disposable PostgreSQL tests prove caller rollback removes a new exclusion, restores a sighting counter, restores a changed-version update and leaves the Session usable. The combined Step 84 foundation and Step 88 transaction suite proves that this ownership is compatible with whole-run rollback and clean failed-`DiscoveryRun` persistence without modifying `run_source`.

Direct PostgreSQL tests also prove exact compatible hits, one-row sighting updates, changed-version continuation/update, valid-expiry behavior and zero Opportunity/role/parse-run creation. Static tests prove the gate has no Playbill or Parallel branch, contracts have no provider-specific fields, providers import neither gate nor persistence, orchestration never invokes the gate, APIs/frontend never expose `SourceEvidence`, and no fake runtime seam exists.

### Dormant status, assumptions and next gate

This foundation is intentionally dormant. No provider emits `SourceEvidence`; no discovery/orchestration path invokes `SourceExclusionGate`; no live source is suppressed; no network request, Opportunity flow, review flow, query, invalidation or user-visible behavior changed. No schema, migration, historical record, cleanup job, metric, API or frontend owner was added.

Confirmed assumptions: Step 84 services support central typed outcomes without semantic changes; incomplete evidence can fail open; the caller Session provides complete transaction control; current-version and expiry behavior can be reused exactly; provider neutrality is statically enforceable. Rejected assumptions: a live/no-op consumer is needed; trusted alone permits persistence; title-only or user-supplied identity is authoritative; the gate should route acting/uncertain candidates; changed evidence should overwrite a tombstone before deterministic reconfirmation; direct tests activate product behavior.

Remaining work is deliberately limited to a fresh first-provider selection preflight comparing authoritative identity, exact version evidence, deterministic classification, request-stage availability, transaction fit and testability. It must not assume Playbill, Parallel or any other source is suitable, and it must not modify this foundation unless evidence identifies a concrete compatibility defect.

**STEP 92 RESULT — DORMANT GENERIC FOUNDATION IMPLEMENTED.** The exact next scope is a first-provider selection audit only. Do not migrate a provider, change orchestration, add a compatibility adapter, or activate exclusion behavior without that new decision.

Step 92 verification: pure contract/identity/static tests passed (17); focused gate PostgreSQL tests passed (13); combined source-exclusion, gate and Step 88 transaction PostgreSQL tests passed (26, 13 pre-existing deprecation warnings); the complete disposable PostgreSQL suite passed (47, 18 warnings); the normal full backend passed (183, 47 guarded contract skips); frontend unit tests passed (309); ESLint, TypeScript no-emit, production build, scoped Ruff, migration-head, runtime-consumer, provider-ownership, frontend-ownership and `git diff --check` audits passed. Mocked Playwright passed 33/34; the unrelated pre-existing Category-B immediate-return timing assertion failed because Journal refetched once. A focused three-run repetition reproduced the known nondeterminism (two passes, one failure). Per the explicit Step 92 instruction, no unrelated flaky frontend timing assertion was changed.

## 55. Step 93 — first source-consumer selection preflight

### Foundation gate and source inventory

Step 92 is complete and dormant: `SourceEvidence`, `SourceCapabilities`, `SourceClassificationEvidence`, `SourceExclusionGate` and typed outcomes exist; no provider or orchestration path imports the gate; no live request, persistence, Opportunity, frontend or invalidation behavior changed. The Step 93 gate therefore passed. This step changed no production or test code.

Only two automated source paths are real candidates. `PublicPlaybillJobsSource` performs public Playbill listing/detail HTTP extraction and returns `NormalizedOpportunity`; `PublicWebBreakdownSearch` uses Parallel to discover third-party URLs, fetches each public page itself and returns a separate `PublicWebSearchResult` containing accepted normalized acting records plus lossy rejection reports. Backstage, Mandy, Project Casting, NYCastings, casting-office, film-commission and social definitions are registered placeholders whose `discover()` and `normalize()` return empty lists. Actors Access, Casting Networks and Casting Frontier registry entries are placeholders; their real supervised import path is separate and user controlled. Manual input is not an automated source.

| Source | Real implementation? | Authoritative identity | Exact version evidence | Deterministic non-acting evidence | Stage available | Session owner | Migration size |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Playbill public jobs | yes | job URL; live paths contain a per-job UUID, but repository extraction does not expose it separately | no proven revision token or bounded semantic-version extractor | source-native category is visible live; current code instead applies deterministic shared signals to listing title and then detail text | listing and post-detail | `DiscoveryAutomationService.run_source` | medium; evidence companion plus orchestration seam |
| Parallel public search | yes | fetched third-party public URL, not a Parallel-owned source item ID | official search result may include publish date/excerpts, but no revision marker; repository discards publish date/excerpts and has no semantic-version extractor | deterministic shared classifier on fetched visible text; rejected classification evidence is discarded | post-detail page fetch | `DiscoveryAutomationService` public-web path | medium/large; retain per-candidate evidence and central processing seam |
| Other public/casting/office/social/film-commission definitions | no; placeholders | none in production output | none | none | none | generic run owner exists but no items | unsafe/not a migration |
| Supervised platform import | yes, user-triggered comparison only | user-opened URL, not automatically provider-authoritative | capture timestamp and mutable visible text; no provider revision contract | user approval/rejection owns lifecycle | captured detail page | `SupervisedBreakdownImportService` | ineligible by product contract |
| Manual create/paste | yes, comparison only | none or user-supplied URL | none authoritative | user/manual parse, not source-native authority | manual input | Opportunity service/request Session | ineligible by product contract |

Eligibility requires all twelve Step 93 facts together: stable source key, authoritative identity, exact non-empty material version, version change on acting/non-acting revision, deterministic non-acting evidence with acting override, adapter translation without Session, a session-owned pre-Opportunity gate seam, unchanged acting/uncertain flow, deterministic request/write tests, no schema/frontend change and no second provider migration. Neither real automated path currently proves the exact-version requirement, so neither is eligible.

### Playbill evidence and safety

Repository facts: source key `playbill_public_jobs` and display name `Playbill Public Jobs` are stable; the adapter owns no Session; listing anchors containing `/job/` are normalized with `urljoin`; a deterministic shared classifier skips Crew/Non-Acting titles before detail fetch and drops Unknown titles lacking review terms; accepted records then fetch and normalize detail text and are handed to session-owning `run_source`. The adapter currently discards the rejected listing and its classification evidence, so a future mapping must preserve evidence rather than directly persist.

Live public inspection on 2026-07-18 adds two useful facts. Playbill exposes source-native categories such as Performer, Technical, Administrative and Non-Theatrical, and individual job paths have the shape `/job/<slug>/<uuid>`. A detail page can explicitly say `Revised`, and the listing supplies a posting date. This supports authoritative job identity and deterministic provider-category evidence. It does **not** prove URL immutability, document that the UUID survives revisions, provide a revision ID/updated timestamp, or establish that posting date changes on every material revision. The visible `Revised` flag is a state label, not a version value.

Pre-detail versioning remains unsafe: title alone is forbidden; title plus category/posting date can miss a same-day or in-place change. Post-detail versioning is potentially feasible but not implemented or characterized. The adapter's cleaned page is capped at 12,000 characters and includes page chrome; no bounded normalized semantic-field extractor currently proves that every acting/non-acting material change changes the version while irrelevant chrome does not. `BreakdownDetailsService` output is an acting aggregate projection, not an approved source-version contract.

The shared classifier is deterministic and correctly gives acting signals precedence over crew/employment signals. A future Playbill mapper could emit the generic classification vocabulary without changing the contract, but only after a source-version research/characterization step establishes either a documented revision marker or an exact bounded semantic payload. Playbill is therefore not approved now.

### Parallel evidence and safety

Parallel is an aggregator/search provider, not the authoritative publisher of candidate pages. Its official Search response contains URL, title, optional publish date and excerpts. Current code extracts only normalized URL/title, removes fragments, fetches the third-party page, cleans visible text, classifies it and emits only acting `NormalizedOpportunity` values. Non-Acting, Crew and Unknown results become generic rejection reports and lose their classification signals and page text before session-owned `_process_public_web_search_result` runs.

The fetched absolute third-party URL is authoritative enough to locate the observed public page, but the repository has no provider/source-policy identity for arbitrary hosts, no external item ID and no proof that a URL is not reused. Parallel `search_id`/`session_id` identify the search, not the source item. `publish_date` is not an update token and current extraction drops it. Excerpts are incomplete/LLM-optimized, raw page text is volatile, and neither is a proven exact semantic version. Using `parallel` as the source key would also scope tombstones to the aggregator rather than the underlying publisher; changing that safely requires bounded host/source capability selection, not a provider-specific field in `SourceEvidence`.

Classification is deterministic only after the direct page fetch through the shared classifier; acting signals already override non-acting signals. A future post-detail mapping is conceptually possible, but it must retain a typed rejected candidate/evidence companion instead of the current lossy report and must establish a safe version/source-policy strategy for arbitrary third-party hosts. That is a larger and less neutral first migration than Playbill, and it remains ineligible.

### Other sources, supervised/manual rejection and version comparison

No other public provider exists in production code; registry metadata and source-research rows are not adapters and must not be treated as evidence. Placeholder sources cannot be selected. Supervised imports intentionally require user approval, commit in their own service, may contain protected/private page data and treat rejection as user intent. Manual text/URL inputs have authority `none` or `user_supplied_url`. Neither may create source tombstones.

| Source | Pre-detail safe? | Post-detail safe? | Authoritative marker? | Best available version |
| --- | --- | --- | --- | --- |
| Playbill | no; category/title/date insufficient | potentially, but no bounded semantic extractor is proven | UUID-like job path proves identity, not revision; `Revised` has no token | none currently safe |
| Parallel-discovered page | no; title/publish date/excerpts insufficient | potentially per underlying host, but no generic stable extractor/policy | no; URL only, Parallel IDs identify searches | none currently safe |
| Placeholders | no | no | no | none |
| Supervised/manual | forbidden | forbidden | user-controlled only | ineligible |

Classification comparison: Playbill offers the strongest evidence because live source-native categories can distinguish Performer from Technical/Administrative/Non-Theatrical, while the existing shared classifier also supplies deterministic Crew/Non-Acting and acting override. Parallel has only fetched-page shared-classifier evidence. Both currently discard rejected evidence before central orchestration. Neither uses probabilistic AI as the deterministic rule, and neither requires a Step 92 contract change.

### Mapping boundaries, request graphs and transaction fit

The smallest eventual Playbill boundary would be: extracted listing/detail evidence -> generic evidence/classification values -> session-owned gate inside `run_source` before `_create_opportunity` -> existing acting/uncertain continuation. The adapter would still own HTTP/parsing only. Because current `discover()` drops non-acting items and `normalize()` fetches details internally, this needs one bounded evidence-carrying interface extension plus the orchestration call; it is medium scope, not a one-line mapping.

The smallest eventual Parallel boundary would be: fetched third-party candidate/page evidence -> typed generic evidence/classification retained in `PublicWebSearchResult` -> gate in `_process_public_web_search_result` before `_create_opportunity` -> unchanged acting continuation. It would require preserving rejected candidate evidence and selecting source-specific URL policy/capabilities for arbitrary hosts, making it medium/large.

For a compatible Playbill tombstone, a safe post-detail design would still perform the listing and detail requests, then one sighting update and no Opportunity lookup/insert, parse run, roles, intelligence/trust/enrichment or frontend invalidation. A new confirmed non-acting result would perform the same source requests and one tombstone write. Acting/uncertain processing would remain current. Parallel would likewise still perform its search and candidate-page fetch, avoiding only Opportunity/downstream work. No candidate currently proves safe pre-detail versioning, so no network saving is claimed.

Both potential seams have the correct transaction owner available: `run_source` owns the Playbill Session/whole-run commit and Step 88 rollback; `_process_public_web_search_result` is invoked by the same discovery service with its Session. Providers need no Session, commit or savepoint. A gate SQL failure would follow whole-run rollback where the call is inside `run_source`; however the public-web wrapper currently catches search errors before processing, so exact failure propagation must be characterized during a later Parallel-specific preflight. No frontend query, tombstone owner, invalidation or UI is needed; acting Opportunity behavior retains existing invalidation semantics.

The Step 92 contract fits both candidates: source key, URL/external ID, authority, ordered version fields, classification evidence and URL policy are sufficient. The blocker is absent provider evidence/extraction, not a generic contract defect. No contract prerequisite is selected.

### Comparison and decision

| Criterion | Playbill | Parallel | Other eligible source |
| --- | --- | --- | --- |
| Identity authority | strongest: Playbill job URL with UUID-like component | mixed: third-party URL found by aggregator | none exists |
| Version safety | unproven | unproven and host-variable | none |
| Classification determinism | strong source category plus deterministic shared rule | deterministic shared rule after fetch | none |
| Contract fit | fits without new generic fields | fields fit, but dynamic source policy unresolved | n/a |
| Orchestration fit | caller Session in `run_source` | caller Session in public-web processing | n/a |
| Migration scope | medium | medium/large | unsafe |
| Testability | strong fixtures/request seams, missing version fixtures | strong mock seams, heterogeneous-host version risk | none |
| Acting-flow preservation | plausible with evidence companion | plausible but current Unknown/rejections are lossy | n/a |
| Provider neutrality | achievable | harder due aggregator/underlying-source distinction | n/a |
| Remaining uncertainty | exact material revision/version contract | source authority, per-host policy and exact version | no implementation |

**DECISION E — NO CURRENT SOURCE IS SAFE TO MIGRATE.** Keep the generic foundation dormant. Playbill now has the clearest identity and classification evidence but lacks one exact safe version contract. Parallel lacks both a safe exact version contract and a resolved underlying-source identity/policy boundary. Placeholders are not real sources; supervised/manual paths are product-ineligible.

The exact next boundary is a Playbill source-version evidence research preflight—not a migration. It should characterize multiple unchanged and revised job pages, determine whether the UUID is stable across revisions, identify any documented `updated_at`/revision field in HTML or source data, and, only if none exists, design and test a bounded normalized semantic version payload that changes for material acting/non-acting edits while ignoring chrome. It must not integrate the gate or alter provider behavior.

Required future migration tests remain gated on that evidence: unchanged/revised identity/version fixtures; source category and acting-override mapping; retained uncertain behavior; exact request graph; no provider Session/commit; session-owned gate insertion; compatible/new exclusion with no Opportunity/children/invalidation; acting flow unchanged; Step 88 rollback; and static proof that Parallel remains untouched.

Expected next-preflight files: architecture ledger and narrowly necessary Playbill HTML/identity/version characterization fixtures/tests only. Forbidden adjacent work: provider migration, gate/contract changes, Parallel changes, live persistence, Opportunity changes, schemas/migrations, frontend/query/invalidation, historical conversion, cleanup or metrics. Stop if Playbill revision identity remains undocumented, semantic versioning requires raw full HTML/title-only/time-based data, or preserving acting/uncertain flow requires a broad provider redesign.

Step 93 verification: focused generic contract/gate/provider/classification/orchestration tests passed (41); the normal full backend passed (183, 47 guarded contract skips); frontend unit tests passed (309); ESLint, TypeScript no-emit, production build, scoped Ruff, provider Session/commit searches, runtime-consumer absence, frontend/query/invalidation ownership and `git diff --check` passed. The complete disposable PostgreSQL run passed 46/47 but its pre-existing concurrency characterization intermittently violated `last_seen_at >= first_seen_at` when the conflict winner's later `first_seen_at` was combined with the earlier caller timestamp; an immediate focused rerun passed (1). No Step 93 code touched that service or test. Mocked Playwright passed 32/34; both failures were the existing immediate-return request-timing assertions (`Calendar` refetch absent and Journal refetch present), unrelated to this documentation-only audit, and were not changed.

## 56. Step 94 — generic provider version-evidence strategy preflight

### Step 93 result and current version flow

Step 93 selected `DECISION E — NO CURRENT SOURCE IS SAFE TO MIGRATE`; the shared provider blocker is unproven exact material-version evidence, not a defect in `SourceEvidence`. Step 92 remains dormant and no production consumer exists.

The current generic flow is already complete from canonical fields onward:

| Stage | Current owner | Input | Output | Pure? | Provider-specific? |
| --- | --- | --- | --- | --- | --- |
| source extraction | future provider adapter/helper | source-native revision/content evidence | bounded source-owned scalars | expected yes after HTTP | yes |
| field canonicalization | `SourceVersionField` and `SourceEvidence` | named scalar fields | immutable, bounded, NFKC/whitespace-normalized, name-sorted unique tuple | yes | no |
| mapping boundary | `SourceEvidence.version_mapping()` | canonical tuple | deterministic mapping | yes | no |
| identity normalization/hash | `SourceIdentityService` | source key, identity and version mapping | source-scoped SHA-256 content-version hash | yes | no |
| eligibility/compatibility | `SourceExclusionGate` plus `SourceExclusionService` | typed evidence/identity | ineligible, continue, existing or new exclusion result | gate policy plus database service | no provider branches |

Canonical field ordering and hashing are already centralized. `SourceEvidence` sorts by normalized field name and rejects duplicate names; the identity service removes empty mapping entries, serializes `schema`, normalized source and normalized values with deterministic JSON `sort_keys=True`, and hashes with SHA-256 under `source-version:v1`. Runtime `hash()`, mapping insertion order and a second digest are absent.

### Evidence taxonomy and exactness

The provider-neutral evidence taxonomy is documentation and acceptance vocabulary, not a set of runtime strategy classes:

1. **Authoritative revision token** — exact only when provider documentation or repeatable fixtures prove it identifies material revisions.
2. **Authoritative updated timestamp** — exact only when its provider contract guarantees relevant changes update it; publication/crawl/search time is insufficient.
3. **Bounded semantic content** — exact for exclusion compatibility only when provider fixtures prove the selected normalized fields include every source change capable of turning the excluded item into an acting opportunity and ignore only irrelevant volatility.
4. **Composite evidence** — two or more of the above canonical fields when no single field establishes the contract; it inherits the weakest unproven assumption and is not automatically exact.
5. **Unsupported** — no non-empty `version_fields`; the existing gate fails open as ineligible and writes nothing.

No numeric confidence or strategy enum is justified. Evidence is either **exact for exclusion compatibility** or **unsupported**. Audit labels may distinguish provider-authoritative and characterized-semantic evidence, but those labels do not belong in the current persistence/gate contract and must not authorize suppression by themselves.

### Material-change and exclusion-specific scope

`material for exclusion compatibility` is deliberately narrower than `material for general Opportunity updates`. A new version is mandatory when the same source identity can change between acting, crew and other non-acting meaning; is replaced by an unrelated posting; or changes title/category/role/description/acting-signal content in a way that can alter that classification. A provider correction that changes those semantics is material.

Demographics, union, compensation, location, audition format and deadline belong in the exclusion version only when that provider can use them to change whether the posting is acting versus non-acting, or when omission could hide replacement by an acting notice. They are not universally required merely because they matter to an acting Opportunity after it is admitted. Cosmetic punctuation, whitespace, Unicode presentation, equivalent field reordering, navigation, advertisements, tracking data and page chrome are not material. The provider's characterization burden is to prove the normalization distinction rather than have a generic builder guess it.

### Canonicalization and field-schema ownership

Existing generic rules are sufficient:

* NFKC normalize and collapse whitespace for names and values.
* Reject empty canonical field names/values, duplicates, more than 16 fields, names over 80 characters and values over 500 characters; the resulting maximum scalar payload is bounded.
* Preserve case and punctuation because no cross-provider evidence proves they are universally cosmetic.
* Sort fields by canonical name; deterministic JSON sorting makes mapping order irrelevant.
* Providers must emit explicit non-empty values; missing is omission, not an invented null marker.
* Provider extractors must canonicalize booleans/enums and documented dates into stable strings (prefer explicit enum values and timezone-qualified ISO-8601 when a timestamp contract exists) before `SourceVersionField` construction.
* URL identity continues through `SourceUrlPolicy`; a URL is not a semantic version field unless the provider proves it is a revision value.
* HTML/entity decoding, chrome removal and repeated-section interpretation remain source extraction concerns because generic code cannot distinguish meaningful markup from volatility.

Forbidden evidence remains: runtime `hash()`, current/discovery time, random UUID, unordered serialization, raw full HTML, arbitrary provider JSON, volatile search ranking, tracking/query chrome, credentials and advertisements.

Use **source-scoped canonical keys** (Model C): short documented semantic/source-contract keys such as `revision_token`, `updated_at`, `category`, `posting_title` or `role_section`. Do not prefix them with provider names because `source_key` already scopes the digest, and do not impose one universal semantic schema on heterogeneous providers. Each provider must document what every emitted key means and why the complete set is exact for exclusion compatibility.

### Strategy comparison and boundary

| Concern | Protocol | Pure functions | Enum builder | No abstraction |
| --- | --- | --- | --- | --- |
| simplicity | low | medium | medium | highest |
| provider neutrality | apparent, but raw type becomes speculative | good only after repeated proven shapes | risks central branching | strong through canonical output |
| type safety | interface-level | per-builder | discriminated input | existing frozen bounded fields |
| testability | good but unused | good | good | already directly tested |
| avoids branching | yes | caller-selected | no | yes |
| future extensibility | high but hypothetical | incremental | centralized edits | provider helper can be added when proven |
| premature abstraction risk | highest | medium | high | lowest |
| repository fit | no protocol precedent needed here | possible later | unnecessary capability coupling | matches Step 92 design |

Selected shape: no shared strategy object or builder now. Providers eventually own pure source-specific extraction helpers and emit final canonical `SourceVersionField` values. Existing generic construction supplies the canonicalizer. If two proven providers later share an identical authoritative input shape, a small pure builder may be extracted from evidence then; it must not be anticipated now.

No registration mechanism is needed. `SourceCapabilities` should not gain a strategy kind: capabilities authorize use and supply URL policy, while a version strategy label would neither prove exactness nor be required by the gate. Providers choose their own pure extractor in code and orchestration consumes only the resulting generic evidence.

No generic raw-version input type is needed. `revision_token`, timestamps and semantic fields have different provider contracts; a universal dictionary or discriminated union would merely move arbitrary/provider-specific data behind a generic name. Provider-local typed inputs/fixtures are appropriate when Step 95 proves a shape, and their output remains the existing bounded tuple.

### Identity boundary, provider responsibility and hypothetical fit

Strategy/extraction output remains `tuple[SourceVersionField, ...]`, passed via `SourceEvidence` to the unchanged `SourceIdentityService`. Extractors must not build hashes, source identities, expiry, database comparisons or rows. The identity service remains the sole owner of source scoping, deterministic serialization and SHA-256 collision assumptions; empty version payloads remain invalid/ineligible.

An eventual provider owns locating/documenting source-native evidence, extracting and normalizing source content, mapping it into source-scoped canonical keys and provider fixtures. It does not own database lookup, persistence, Session/commit/rollback, generic eligibility, acting/uncertain routing or frontend behavior.

Playbill could hypothetically use, in order of preference: a documented revision token; a documented material-update timestamp; a composite with its job UUID plus such a marker; or a characterized bounded semantic field set. Current `Revised` text/posting date is not enough, and Step 95 must prove unchanged stability, material revision sensitivity, chrome exclusion, UUID behavior and completeness before choosing one. Playbill remains unsupported until then.

Parallel could hypothetically use publisher-scoped revision evidence or a characterized bounded semantic payload from the fetched third-party page. Its search publication date is not a revision timestamp; excerpts are incomplete; publisher/source scoping remains unresolved. No Parallel strategy is approved.

Future providers can use the same output invariants without generic branches. No behavior is invented for current placeholders.

### Tests, product gates and decision

Required generic tests already cover stable ordering, NFKC/whitespace normalization, key/value/count bounds, duplicate rejection, deterministic source-scoped/version-sensitive SHA-256, empty rejection, no arbitrary payload and architecture isolation. A provider implementation must add fixtures proving unchanged content stability, acting/non-acting material sensitivity, field-key sensitivity, explicit missing/empty handling, volatile chrome removal, title-only rejection, and provider-local absence of database/Session/commit/HTTP in any pure extractor. Timestamp/token/composite tests are required only if that provider actually selects those evidence forms.

Product-gate classification:

* correctness requirements: exact-or-unsupported evidence, exclusion-specific material-change coverage, deterministic bounded canonical output, existing identity-service boundary, fail-open behavior;
* implementation choices established: source-scoped canonical keys, provider-local pure extraction, no registration/raw generic input, current `SourceVersionField` output;
* deferred provider decisions: exact Playbill/Parallel evidence form and field set;
* configuration: provider URL policy only, not version strategy;
* no product decision or persistence/frontend work is required for this preflight.

**DECISION A — EXISTING VERSION-FIELD CONTRACT IS SUFFICIENT.** No generic strategy production code, builder, capability extension or contract revision is approved. Providers extract source-specific evidence, map it to bounded canonical `SourceVersionField` values under the rules above, and delegate ordering/identity hashing to existing code.

Exact next boundary: Step 95 is a Playbill version-evidence characterization preflight only. It may add narrowly scoped HTML/source-data fixtures and provider-local test helpers to compare unchanged/revised pages, but it must not migrate Playbill, invoke the gate, modify generic contracts, introduce a shared strategy abstraction, or change production behavior.

Expected Step 95 files: architecture ledger and narrowly necessary Playbill characterization fixtures/tests; a provider-local pure extractor is not approved for production until the preflight selects and proves its exact field contract. Forbidden adjacent work: provider/gate/orchestration integration, Parallel changes, generic builders/protocols/enums, capability changes, identity hashing changes, Session/database work, schema/API/frontend/query/invalidation/history, cleanup or metrics. Stop if exactness requires title-only/current-time/raw-HTML evidence, UUID/revision semantics remain ambiguous, material changes cannot be captured in bounded fields, or a generic contract change appears necessary.

Step 94 verification: focused source-evidence/identity/gate/provider/classification/orchestration tests passed (41); the complete disposable PostgreSQL suite passed (47, 18 pre-existing warnings); the normal full backend passed (183, 47 guarded contract skips); frontend unit tests passed (309); ESLint, TypeScript no-emit, production build, scoped Ruff, strategy-absence, provider Session/commit, frontend/query/invalidation, migration-head (`0055_source_exclusions`) and `git diff --check` audits passed. Mocked Playwright passed 32/34; the two failures were the same unrelated immediate-return timing assertions recorded in Step 93 (Calendar refetch absent, Journal refetch present). No timing assertion or unrelated code was changed.
