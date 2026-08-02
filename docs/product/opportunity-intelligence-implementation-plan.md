# Opportunity Intelligence Phase 1 Implementation Plan

This plan implements the deterministic design in small, reviewable commits. It does not change discovery, persistence, APIs, frontend behavior, deployment, or dependencies.

## Task 1 — Characterize existing intelligence boundaries

Add focused tests that lock current `OpportunityIntelligenceService.enrich`, existing `Opportunity.urgency_score`/`quality_score`, and Strategy Agent behavior. Add test builders for fixed actors, opportunities, context, UUIDs, and timezone-aware `as_of` values.

Acceptance criteria:

- Existing mutable enrichment behavior is unchanged.
- Tests prove the new scorer will not overwrite existing score fields.
- No production change beyond test-enabling typing, if strictly necessary.

Suggested commit: `test(intelligence): characterize opportunity scoring boundaries`

## Task 2 — Add the pure versioned score contract

Add immutable `ScoreFactor`, `CategoryScore`, `OpportunityScore`, and a small explicit scoring-context type. Add constants for version, baseline, category caps, critical fields, and fixed ordering. Expose a read-only `OpportunityIntelligenceService.score(..., as_of=...)` skeleton with normalization and hard overrides.

Acceptance criteria:

- Score is bounded 0–100.
- Every factor has ID, category, points, explanation, and priority.
- `as_of` is required and timezone-aware.
- Scoring mutates no ORM object and performs no transaction or network work.

Suggested commit: `feat(intelligence): add deterministic scoring contract`

## Task 3 — Implement fit and career-value factors

Implement mutually exclusive role fit, demographic, role-type, language, and explicit union compatibility factors. Add best-only active goal, dream target, strategic stretch, and watch-list career factors using normalized structured data.

Acceptance criteria:

- Missing data is neutral unless documented otherwise.
- No identity or preference is inferred.
- Repeated goals/roles/terms cannot inflate totals.
- Perfect-match, stretch, dream-project, and conflicting-factor tests assert exact results.

Suggested commit: `feat(intelligence): score opportunity fit and career value`

## Task 4 — Implement practicality, confidence, and interest factors

Add deadline, audition mode, travel, housing, compensation, parse, trust, source, completeness, submission, and feedback factors. Build deterministic confidence text from fixed templates.

Acceptance criteria:

- Fixed-time deadline tests cover tomorrow, seven-day boundaries, missing dates, and expiration.
- Hard eligibility remains authoritative.
- Travel exception and travel dealbreaker remain distinct.
- Low-confidence and incomplete-data output is fully explained.

Suggested commit: `feat(intelligence): score practicality confidence and interest`

## Task 5 — Add actions, contributor ordering, and ranking

Implement first-match-wins action selection, contributor ordering, and the complete equal-score tie-break chain. Add a pure ranking helper that consumes already-produced scores.

Acceptance criteria:

- Only the six documented action labels can be returned.
- Duplicate and already-tracked opportunities cannot prompt a duplicate application.
- Repeated runs return equal serialized results.
- Equal scores are stable regardless of database return order.

Suggested commit: `feat(intelligence): rank scored opportunities deterministically`

## Task 6 — Integrate one read-only consumer

Only after the score contract is reviewed, select one existing backend read path and assemble its scoring context explicitly. Keep this separate from discovery and from the mutating `enrich()` path. Do not expose a new API in the same commit; API and frontend work require their own approved contracts.

The command-center queue was selected as the eventual consumer, but its public snapshot path intentionally refreshes persisted signals and records a dashboard visit. Before ranking integration, the command center therefore exposes separate internal boundaries: `refresh_signals()` owns enrichment, alert/nudge creation, and its commit; `record_visit()` owns visit persistence and its commit; and `read_snapshot()` reads only persisted state. `read_opportunity_candidates()` supplies at most 100 visible, non-demo acting-breakdown candidates in deterministic database order with the relationships needed for later context assembly. The public route continues to refresh, read the existing eight-item display queue, and record the visit; its schema and “since your last visit” behavior are unchanged. No intelligence score or rank is integrated by this precursor.

Acceptance criteria:

- Query count is characterized and bounded.
- Existing responses and persisted records are unchanged.
- No discovery request, provider call, write, flush, or commit occurs.
- Full backend and contract-smoke suites remain green.

Suggested commit: `feat(intelligence): integrate read-only opportunity ranking`

## Deferred phases

- Define an API response only after a real consumer is selected.
- Add frontend score explanations and action labels in a separate vertical slice.
- Measure query and calculation cost before adding request-scoped caching.
- Consider durable history only with a concrete audit or trend requirement and a separate migration design.
- Consider learned signals only after deterministic outcomes are measured; never silently blend them into version 1.
