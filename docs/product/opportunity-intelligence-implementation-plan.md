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

The command-center queue is the first read-only consumer. Its public snapshot path intentionally refreshes persisted signals and records a dashboard visit, so the command center exposes separate internal boundaries: `refresh_signals()` owns enrichment, alert/nudge creation, and its commit; `record_visit()` owns visit persistence and its commit; and `read_snapshot()` reads only persisted state. `read_opportunity_candidates()` supplies at most 100 visible, non-demo acting-breakdown candidates with parsed roles and submissions eagerly loaded. The reader scores the full bounded set with one shared aware `as_of`, ranks it once using the version-1 projection, and only then selects the existing eight cards. Context uses loaded actor role, language, union, and demographic facts; parsed-role fit; persisted watch-list matches; deterministic latest submission status; one batched latest actor/Opportunity feedback record; and the saved audition-travel threshold. Career-goal, dream-target, and strategic-stretch matches remain neutral because no stable Opportunity association exists and this consumer does not invent semantic matching. Empty snapshots remain at 24 SELECTs; non-empty snapshots use 28 SELECTs for 1–100 candidates, including two fixed context queries, without candidate-count growth. The public schema, non-Opportunity sections, “since your last visit” behavior, score persistence, and score/action exposure are unchanged. When no actor profile exists, the bounded candidates retain the legacy urgency/quality ordering rather than fabricating actor context.

Acceptance criteria:

- Query count is characterized and bounded.
- Existing responses and persisted records are unchanged.
- No discovery request, provider call, write, flush, or commit occurs.
- Full backend and contract-smoke suites remain green.

Suggested commit: `feat(intelligence): integrate read-only opportunity ranking`

## Task 7B — Characterize the command-center API boundary

### Current boundary and absence guarantee

`GET /api/v1/command-center` is owned by `backend/app/api/v1/routes/command_center.py::get_command_center`, which calls `CommandCenterService.snapshot()` and validates the result with `ActorCommandCenterRead`. The response is a Pydantic model, but `today_opportunities` is intentionally a `list[dict]`; each entry is the manual `_opportunity_card()` projection rather than ORM serialization. A current card contains exactly `id`, `role`, `project`, `original_post_url`, `priority`, `urgency_score`, `quality_score`, `confidence_level`, and `risk_level`. `original_post_url` is the only nullable card field in ordinary output. The response contains no intelligence version, deterministic overall score, suggested action or reason, category/factor details, contributors, intelligence confidence, hard-override details, ranking projection or position, `as_of`, or scoring context. Intelligence affects only which existing card identities appear and their order.

The frontend receives this through `getCommandCenter()` and `useCommandCenter()` under the existing live TanStack Query key. `ActorCommandCenter.today_opportunities` is `CommandCenterCard[]`, where `CommandCenterCard` is a loose scalar-valued record. The Dashboard reads only `role` and `project`, presents loading with `role="status"`, presents failure with `role="alert"`, and uses an empty-state message when no priority breakdown exists. The generic request client performs no runtime response parsing. Current TypeScript fixtures and the strict Playwright mock contain no intelligence data; Playwright permits exactly the existing `GET /command-center` request and no score/history request. No existing response-size test existed before this characterization. Current OpenAPI exposes `today_opportunities.items` as an object with arbitrary properties, and current contract tests depend on route behavior and selected fields rather than a generated client with a typed card schema.

### Recommended additive owner and versioned summary

Future exposure should be one optional nested `intelligence` projection on each existing Opportunity card. The score belongs to that actor-specific, time-relative ranked card; nesting avoids collisions with legacy `quality_score`, `urgency_score`, and Strategy Agent score fields, adds no request or parallel ID map, and remains ergonomic for card rendering. A new endpoint would split ordering from its explanation, while a parallel response map would duplicate identity bookkeeping. The eventual schema must replace the loose proposal with an explicit typed nested model, but retain backward-compatible omission.

The proposed contract is:

```json
{
  "intelligence": {
    "version": 1,
    "overall_score": 87,
    "action": "apply_now",
    "action_label": "Apply Now",
    "action_reason_code": "high_priority_actionable",
    "confidence": {
      "level": "High",
      "summary": "High confidence: 4 bounded confidence factors contribute +15 points."
    },
    "hard_override": false,
    "hard_override_reason": null,
    "top_positive_contributors": [
      {
        "id": "match.role_fit.strong",
        "points": 18,
        "explanation": "Strong Fit is the best parsed role fit (+18)."
      }
    ],
    "top_negative_contributors": []
  }
}
```

`version` is a distinct command-center intelligence contract version, not the discovery-evidence version. It begins at integer `1`. `overall_score` is 0–100. `action` uses the existing six serialized `SuggestedAction` values and `action_label` carries the matching bounded display label. `action_reason_code` and hard-override reasons use bounded public codes. Confidence preserves the current `High`, `Medium`, `Low`, or `Not Scored` domain values. Contributor arrays are capped at three positive and three negative entries. Contributor `explanation` is optional and appears only for an approved public-safe template. Unknown versions must be treated as absent by the frontend. Adding or omitting the nested projection requires no data migration and no persisted score.

### Absent, neutral, override, duplicate, and tracked states

An omitted field is valid for old responses. A new server may use `intelligence: null` when evaluation is unavailable because no actor exists, the consumer intentionally skipped scoring, or a bounded internal evaluation failed while the legacy card remains usable. Evaluated neutral intelligence is a populated version-1 projection, normally with score 50, empty contributors, and its deterministic confidence/action fields. It must never be represented as `null` or `{}`.

Hard user rejection, expiration, discarded state, proven demographic incompatibility, excluded role type, and hard travel failure may expose score `0`, action `ignore`, `action_reason_code: hard_override`, and the stable bounded `hard_override_reason`. Raw rejection text and internal rule payloads remain excluded. Retained duplicates expose only deterministic `ignore / duplicate_opportunity`. Submitted, requested, callback, pinned, booked, passed, and no-response states expose only `save_for_later / already_tracked`; workflow notes and the private status history are not part of this projection.

### Payload-size evidence

Measurements use compact, key-sorted UTF-8 JSON, the complete current command-center envelope, deterministic fictional cards, the actual version-1 score serializer, and no production data.

| Fixture | Bytes | Increase over corresponding current envelope |
| --- | ---: | ---: |
| One current card | 571 | baseline |
| Eight current cards | 2,363 | baseline |
| One card with summary | 1,193 | 108.9% |
| Eight cards with summaries | 7,339 | 210.6% |
| One card with full maximum-factor score | 4,927 | 762.9% |
| Eight cards with full maximum-factor scores | 37,211 | 1,474.7% |
| One hard-override full score | 1,589 | 178.3% |
| One neutral full score | 1,632 | 185.8% |

The maximum-factor full score is 4,927 bytes. The largest growth is the repeated five-category structure, factor objects, contributor duplication, and explanation prose. The summary removes category totals, complete factor arrays, score explanation, action explanation, baseline, and Opportunity ID duplication. Full `OpportunityScore.as_dict()` remains an internal/debug comparison and should not be exposed by the command center.

### Privacy and factor-explanation safety

The future API must never include ActorProfile demographics, private notes, raw career goals, dream-target or watch-list notes, recommendation-feedback notes, raw trust/source metadata, provider evidence, fetched content, scoring context, ranking/canonical keys, database IDs beyond the existing card ID, `as_of`, stack traces, or validation errors.

Current operational templates are safe for actor-facing exposure because they contain no source values: parsed-role fit; remote/local/travel/housing/compensation/deadline facts; parser/trust/source/completeness bands; and generic watch-list priority. Demographic, preferred-role, union, and language factor IDs/templates are safe only under an explicitly actor-facing privacy policy because they reveal the existence or result of sensitive matching even though they do not reveal the underlying profile value. The current `career.goal.active_match`, `career.dream_target.match`, and `career.stretch.strategic` explanations interpolate user-controlled labels and must be redacted, replaced by approved generic prose, or omitted. Feedback factor explanations encode a private actor choice and should likewise omit prose or use a generic actor-authorized explanation. Public contributor serialization therefore requires an explicit factor allowlist; deterministic prose alone is not sufficient evidence of safety.

### Frontend, accessibility, and compatibility requirements

The eventual card should communicate numeric score and a text action label without relying on color. Contributor disclosure must be keyboard operable, must not be tooltip-only, and must expose descriptive screen-reader text such as “Opportunity intelligence score 87 of 100; Apply Now.” Hard overrides need a text reason and may not appear as a generic failure. Absent intelligence renders the existing card unchanged; neutral intelligence states that evaluation completed but no strong contributors were found. Unsupported versions degrade to the absent presentation. Mobile cards must preserve role/project and action before optional contributor details. Loading remains owned by the existing command-center request; no second spinner or request is introduced. Partial intelligence absence must not suppress or reorder an otherwise usable card.

Backward compatibility requires old responses to keep rendering, new optional projections to be ignored by old frontend code, missing/`null` projections to preserve ranked order, unsupported versions to degrade safely, strict mocks to remain valid until deliberately updated, and an OpenAPI diff containing only additive nested definitions/fields. No route or existing field may be removed.

### Required implementation test matrix

Backend contract tests must cover evaluated summary, absent and explicit-null intelligence, neutral baseline, each hard override, retained duplicate, every tracked status, maximum contributors, version serialization, unknown-version documentation, privacy sentinels, payload bounds, unchanged card fields, and an additive-only OpenAPI diff. Backend unit tests must verify public factor allowlisting/redaction and prove serialization does not mutate scores or ORM records.

Frontend unit tests must cover all six actions, score bounds, contributor disclosure, hard override, absent and neutral fallback, unsupported version, color-independent and screen-reader labels, keyboard disclosure, mobile-safe content order, and old fixtures against updated optional types. Playwright must use the same single `GET /command-center` request to cover a populated projection, absent-field compatibility, retained backend order, and strict unknown-request rejection. Compatibility tests must run the old frontend fixture against the new optional backend schema, the old response fixture against updated TypeScript types, and assert that OpenAPI changes are additive only.

## Task 8 — Expose bounded command-center intelligence summaries

The existing `GET /api/v1/command-center` route now adds only `today_opportunities[].intelligence`. The field is nullable and uses an explicit version-1 Pydantic schema. Existing card fields, route orchestration, ranking order, the 100-candidate ceiling, the eight-card display ceiling, and the 24/28 SELECT boundaries remain unchanged.

The request-local ranking path retains both `Opportunity UUID → Opportunity` and `Opportunity UUID → completed OpportunityScore`. It ranks the completed entries, selects eight, and passes the exact retained score to `_opportunity_card()`. Serialization never calls the scorer, queries the database, mutates an ORM record, or persists the score.

The version-1 summary contains `version`, `overall_score`, `action`, `action_label`, `action_reason_code`, generic confidence level/summary, bounded hard-override state, and at most three positive and three negative contributors. A maximum-factor fixture serializes to 558 compact UTF-8 JSON bytes and eight copies serialize to 4,473 bytes; neutral and hard-override fixtures serialize to 364 and 353 bytes. Each summary is capped at 2,048 bytes, materially below the characterized 4,927-byte full-score payload. Full categories, factor collections, priorities, caps, ranking keys, evaluation time, context, and internal explanations remain private.

Contributor serialization is allowlist-first. Operational role-fit, modality, deadline, compensation, travel-support, parser, trust, source, and completeness factors receive fixed generic prose. Sensitive demographic, language, union, role-preference, goal, dream-target, watch-list, feedback, and travel-threshold values never pass through; their bounded factor ID and points may remain without an explanation when already present in the completed top-three contributors. The serializer does not refill contributor positions after filtering. Demographic and excluded-role hard overrides map to `profile_incompatibility`; internal text and profile values remain private.

No actor produces `intelligence: null`; an evaluated neutral score produces a populated score-50 projection. The frontend renders absent and explicit-null values as the unchanged legacy card, and treats unsupported versions the same way without another request. Version 1 preserves role and project first, then shows visible action, numeric score, confidence, an assistive action/score label, and a semantic `details/summary` contributor disclosure. Hard overrides show only a bounded generic reason. The strict browser contract remains one `GET /command-center` request.

## Deferred phases

- Define an API response only after a real consumer is selected.
- Add frontend score explanations and action labels in a separate vertical slice.
- Measure query and calculation cost before adding request-scoped caching.
- Consider durable history only with a concrete audit or trend requirement and a separate migration design.
- Consider learned signals only after deterministic outcomes are measured; never silently blend them into version 1.
