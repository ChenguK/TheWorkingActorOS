# Deterministic Opportunity Intelligence Design

Status: Phase 1 design; no production behavior or API contract is changed by this document.

## 1. Philosophy

Discovery answers **what exists**. Opportunity Intelligence answers **what deserves the actor's limited attention today**. The first scoring framework is therefore a deterministic, explainable decision aid, not a prediction model.

The score is actor-specific and time-relative. It consumes already-derived Opportunity and actor data; it does not fetch, parse, classify, route, or persist discovery results. A score is advisory: existing hard eligibility and visibility decisions remain authoritative.

Every contribution has a stable identifier, category, integer point value, deterministic explanation template, and ordering priority. Missing facts are neutral unless their absence creates a documented decision risk. The engine must never infer a protected identity, union status, language, location, or preference.

## 2. Existing boundaries and reusable evidence

`OpportunityIntelligenceService` already owns post-discovery enrichment in `backend/app/services/opportunity_intelligence_service.py::OpportunityIntelligenceService.enrich`: deadline validation, visibility, hard eligibility, watch-list matching, urgency, quality, confidence, risk, and goal priority. Phase 1 should add a side-effect-free `score(...)` operation to this service. It should not create a generalized rules engine.

Useful source facts already exist:

- Opportunity fit, logistics, source, deadline, confidence, visibility, duplicate, and classification fields in `backend/app/db/models/opportunity.py::Opportunity`.
- Per-role fit and character archetypes in `backend/app/db/models/opportunity.py::BreakdownRole` and `CharacterProfile`.
- Actor identities, languages, union, role preferences, location, and skills in `backend/app/db/models/actor_profile.py::ActorProfile`.
- Local and travel constraints in `backend/app/db/models/travel_preference.py::TravelPreference`.
- Active goals and target archetypes, project types, markets, and casting offices in `backend/app/db/models/agent.py::CastingGoal` and `backend/app/db/models/intelligence.py::DreamRoleTarget`.
- Explicit watch-list interest in `backend/app/db/models/agent.py::WatchList`.
- Submission history in `backend/app/db/models/submission.py::Submission`.
- User feedback in `backend/app/db/models/agent.py::RecommendationFeedback`.
- Deterministic trust evidence in `backend/app/services/trust_verification_service.py::TrustVerificationService`.

Two existing scores must remain distinct. `Opportunity.urgency_score` and `quality_score` are mutable enrichment projections used by the command center. `AgentRecommendation.score` is a persisted, asset-aware strategy-agent result produced by `backend/app/agents/strategy_agent.py::StrategyAgent.analyze`. Phase 1 must neither overwrite nor reinterpret either score.

## 3. Scoring dimensions and point table

The raw score begins at a documented baseline of **50**. Category contributions are summed, category-capped, then the result is clamped to 0–100. Only the best applicable factor in each mutually exclusive group applies.

| Priority | Factor ID | Category | Condition | Points |
| ---: | --- | --- | --- | ---: |
| 10 | `match.role.strong` | Match quality | Best parsed role is Strong Fit | +18 |
| 11 | `match.role.possible` | Match quality | Best parsed role is Possible Fit | +10 |
| 12 | `match.role.stretch` | Match quality | Best parsed role is Stretch Fit | +6 |
| 13 | `match.role.not_fit` | Match quality | Parsed roles exist and none fits | -25 |
| 20 | `match.demographic.confirmed` | Match quality | Existing matcher says Match | +8 |
| 21 | `match.demographic.review` | Match quality | Existing matcher requires review | 0 |
| 30 | `match.role_type.preferred` | Match quality | Role type is explicitly included | +4 |
| 40 | `match.language.confirmed` | Match quality | Explicit role language overlaps saved actor languages | +4 |
| 41 | `match.language.mismatch` | Match quality | Explicit required language has no overlap | -8 |
| 50 | `match.union.compatible` | Match quality | Stored union facts explicitly establish compatibility | +3 |
| 100 | `career.goal.match` | Career value | Best active goal matches project, market, archetype, or casting office | +8 |
| 110 | `career.dream_target.match` | Career value | Best active dream target matches | +7 |
| 120 | `career.watchlist.high` | Career value | Enabled High-priority watch-list term matches | +5 |
| 130 | `career.stretch.strategic` | Career value | Stretch role matches an explicit stretch archetype or active goal | +5 |
| 200 | `practicality.self_tape` | Practicality | Self-Tape or Virtual audition | +8 |
| 210 | `practicality.local` | Practicality | In-person travel is within the saved threshold | +4 |
| 211 | `practicality.travel_exception` | Practicality | Existing visibility decision is travel exception | -15 |
| 220 | `practicality.travel_covered` | Practicality | Travel covered | +4 |
| 221 | `practicality.housing_covered` | Practicality | Housing covered | +4 |
| 230 | `practicality.compensation_known` | Practicality | Nonblank rate is present | +3 |
| 240 | `practicality.deadline.24h` | Practicality | Deadline is after `as_of` and within 24 hours | +8 |
| 241 | `practicality.deadline.72h` | Practicality | Deadline is within 72 hours | +5 |
| 242 | `practicality.deadline.7d` | Practicality | Deadline is within seven days | +2 |
| 243 | `practicality.deadline.missing` | Practicality | No actionable deadline is known | -5 |
| 300 | `confidence.parse.high` | Confidence | Parse confidence is at least 85 | +6 |
| 301 | `confidence.parse.medium` | Confidence | Parse confidence is 70–84 | +3 |
| 302 | `confidence.parse.low` | Confidence | Parse confidence is present below 70 | -6 |
| 303 | `confidence.parse.missing` | Confidence | Parse confidence is absent or invalid | -4 |
| 310 | `confidence.trust.verified` | Confidence | Existing trust result is verified/passing | +5 |
| 311 | `confidence.trust.review` | Confidence | Existing trust result requires review | -5 |
| 320 | `confidence.source.high` | Confidence | Source reliability is at least 0.85 | +4 |
| 321 | `confidence.source.medium` | Confidence | Source reliability is 0.70–0.849 | +2 |
| 322 | `confidence.source.low` | Confidence | Source reliability is below 0.50 | -4 |
| 330 | `confidence.details.complete` | Confidence | All defined critical fields are present | +4 |
| 331 | `confidence.details.incomplete` | Confidence | At least two defined critical fields are absent | -5 |
| 400 | `interest.watchlist.high` | Actor interest | Enabled High-priority watch-list match | +8 |
| 401 | `interest.watchlist.medium` | Actor interest | Enabled Medium-priority watch-list match | +5 |
| 402 | `interest.watchlist.low` | Actor interest | Enabled Low-priority watch-list match | +3 |
| 410 | `interest.feedback.positive` | Actor interest | Latest applicable feedback is This Fits Me or Save For Later | +6 / +2 |
| 411 | `interest.feedback.stretch` | Actor interest | Latest applicable feedback is Interesting Stretch | +4 |
| 412 | `interest.feedback.negative` | Actor interest | Latest applicable feedback is Not My Type | -8 |

Category caps prevent a dense record from dominating through repeated evidence: Match quality -35..+30; Career value -10..+20; Practicality -25..+20; Confidence -20..+15; Actor interest -20..+15. Repeated goals, roles, languages, archetypes, or watch-list terms select the single highest contribution for their factor group; they do not accumulate.

The initial critical-field set is fixed and versioned with the scorer: project, role, description, project type/category, audition type, location, and a submission/audition deadline. A field is assessed only by presence, never by invented content.

## 4. Overrides and normalization

Hard outcomes are evaluated before point calculation and return score 0 with `Ignore`:

- deadline expired under the existing deadline contract;
- existing visibility is `discarded`;
- existing classification is rejected/non-acting;
- `hidden_by_rule == "user_rejected"`;
- an existing hard role-type, demographic, availability, or audition-travel dealbreaker applies.

Trust metadata alone is informational in the current domain and does not trigger a Phase 1 hard override. It may contribute to the later Confidence category, but only an existing eligibility, rejection, classification, or deadline decision can force the foundation score to zero.

`is_duplicate` is not treated as evidence that the source is unsafe. It contributes `duplicate.existing = -25`; when the canonical opportunity is already retained, the duplicate's suggested action is `Ignore`. This preserves duplicate identity behavior without mutating it.

For non-overridden records:

```text
category subtotal = clamp(sum(applicable factor points), category minimum, category maximum)
raw score         = 50 + sum(category subtotals) + duplicate contribution
overall score     = clamp(round(raw score), 0, 100)
```

All values are integers, so rounding is specified but normally has no effect. Conflicting positive and negative factors remain visible; one does not erase the other's explanation.

## 5. Deterministic guarantees

- `score(opportunity, actor, context, *, as_of)` requires a timezone-aware `as_of`. It never calls the wall clock internally. Naive persisted deadlines are interpreted as UTC consistently with current deadline handling.
- Inputs are read-only. Scoring performs no flush, commit, network call, AI call, or lazy discovery operation.
- Factor evaluation order is fixed by numeric priority, then factor ID.
- Positive contributors sort by points descending, priority ascending, ID ascending. Negative contributors sort by absolute points descending, priority ascending, ID ascending. Zero-point diagnostic factors remain in the full breakdown but are not top contributors.
- Ranking sorts by overall score descending, then earliest future actionable deadline (missing last), normalized project, normalized role, canonical source URL, and finally Opportunity UUID text. Equal inputs therefore remain stable across runs and database plans.
- The scoring contract has an explicit integer `version = 1`. Any future weight change creates a new version and characterization update.
- String matching uses Unicode case-folding, whitespace collapse, and exact normalized terms or existing structured matches. It does not use fuzzy or semantic inference.

## 6. Explanation contract

Use immutable typed result objects (dataclasses are sufficient):

```text
OpportunityScore
  version: 1
  opportunity_id
  overall_score: 0..100
  categories: ordered CategoryScore[]
  factors: ordered ScoreFactor[]
  top_positive_contributors: first 3 positive factors
  top_negative_contributors: first 3 negative factors
  confidence_summary: deterministic string
  suggested_action: fixed enum/string
```

`ScoreFactor` contains exactly `id`, `category`, `points`, `explanation`, and `priority`. Category results contain the uncapped sum, applied cap, and final subtotal so normalization is auditable.

Explanations use fixed templates, for example: `Strong Fit is the best parsed role fit (+18).` The confidence summary is assembled from facts, for example: `High confidence: parse confidence is 91; trust verification passed; 7 of 7 critical fields are present.` It is never generated by an LLM.

## 7. Suggested actions

Apply the following first-match-wins rules after hard overrides:

1. **Ignore** — hard override, or retained canonical duplicate exists.
2. **Save for Later** — already submitted/booked/tracked; scoring may explain value but must not invite another application.
3. **Good Stretch Role** — score at least 65, best role fit is Stretch Fit, and no hard blocker exists.
4. **Apply Now** — score at least 85, confidence is not Low, actionable deadline is within seven days, and the opportunity is visible.
5. **Review Today** — score at least 70, or an actionable deadline is within 72 hours, and no earlier rule applies.
6. **Save for Later** — score at least 55 and deadline is more than seven days away or absent.
7. **Low Priority** — all other eligible opportunities.

The order intentionally lets an urgent but incomplete record say Review Today rather than Apply Now. Actions do not submit, hide, delete, or change priority.

## 8. Architecture

Add the typed score contract and pure factor helpers to `backend/app/services/opportunity_intelligence_service.py`, exposed through `OpportunityIntelligenceService.score(opportunity, actor, context, *, as_of)`. `context` is a small, explicitly assembled input containing applicable goals, dream targets, watch-list matches, submission state, feedback, and travel preference. Database loading remains outside the pure calculation so tests can construct complete inputs and query behavior stays visible.

Keep `enrich()` unchanged during initial implementation. It remains the mutating post-discovery enrichment path. The new method is a read-only ranking projection and must not be called by discovery. If the service file becomes materially harder to navigate during implementation, typed contracts may move to one adjacent `opportunity_score.py` module; that is a file organization choice, not a second service or rules framework.

The Strategy Agent remains asset-package and submission-strategy analysis. The Intelligence score ranks attention across opportunities. Neither consumes or overwrites the other in Phase 1.

## 9. Persistence recommendation

Calculate Phase 1 scores **on demand**. Do not add columns, tables, migrations, or reuse `quality_score`, `urgency_score`, or `AgentRecommendation.score`.

Reasons:

- scoring is inexpensive and based on data already loaded for an opportunity queue;
- deadline urgency changes with `as_of`, so a persisted total becomes stale;
- actor goals, feedback, travel preferences, and submissions change independently;
- a versioned returned projection is safer than a denormalized value before a UI/API consumer exists.

If profiling later proves a need, use request-scoped memoization keyed by scorer version, opportunity ID/update timestamp, actor ID/update timestamp, context revision, and an explicit time bucket. Durable persistence should be reconsidered only when a concrete API, audit-history, or batch-ranking requirement exists; it would require a separate design and migration.

## 10. Testing strategy

Characterization tests use fixed UUIDs and a timezone-aware fixed `as_of`. They assert the exact total, ordered categories, full ordered factor list, contributors, confidence summary, and action—not merely a range.

Required cases:

1. perfect match reaches the bounded upper end with all reasons retained;
2. excellent strategic stretch selects Good Stretch Role;
3. deadline tomorrow adds the 24-hour factor deterministically;
4. expired opportunity hard-overrides to 0/Ignore;
5. low parse/trust/source confidence applies explicit penalties;
6. missing information neither fabricates matches nor disappears from explanation;
7. travel burden distinguishes reviewable travel exception from hard dealbreaker;
8. dream target uses only the single best target contribution;
9. duplicate receives one penalty and deterministic Ignore behavior;
10. conflicting positive/negative factors both remain visible;
11. repeated evaluation with identical inputs and `as_of` is byte-for-byte equivalent;
12. equal-score ranking follows the complete documented tie-break chain;
13. category and final bounds hold under maximal repeated input;
14. scoring causes no ORM mutation, flush, commit, network, discovery, or agent call;
15. existing `enrich()` and Strategy Agent characterization tests remain unchanged.

## 11. Future ML boundaries

Machine learning, embeddings, vector search, LLM scoring, AI-written explanations, opaque personalization, and inferred protected attributes are explicitly out of scope. A future learned signal may only be considered after deterministic outcomes are measured, must be separately labeled, cannot replace hard eligibility or trust controls, and cannot make the explanation contract false. Version 1 remains reproducible even if later versions add optional learned evidence.

Other deferred work includes API exposure, frontend ranking UI, durable score history, background recomputation, cross-actor/multi-tenant optimization, and automatic actions.
