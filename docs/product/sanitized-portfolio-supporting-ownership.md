# Sanitized Portfolio Supporting-Record Ownership

## Scope and conclusions

This document characterizes supporting-record ownership for a future sanitized portfolio dataset. It does not define or create fictional records. The ownership root remains an isolated portfolio database plus one fictional `ActorProfile`; portfolio `Opportunity` rows remain operationally normal (`is_demo_data=False`) and are identified only by `source_metadata.portfolio_seed.namespace == "sanitized-portfolio-v1"` through `PortfolioSeedOwnershipService` (`backend/app/services/portfolio_seed_ownership_service.py`).

Supporting rows generally do not need their own marker when an existing required foreign key provides a deterministic path to the fictional actor, a portfolio-owned Opportunity, or a Submission owned by both. Nullable `SET NULL` relationships are the important exception for cleanup planning: the row must be selected and deleted while its ownership links still exist.

## Ownership matrix

| Model | Owner | Seed? | Marker Needed? | Cleanup Strategy | Risk |
| --- | --- | --- | --- | --- | --- |
| `RecommendationFeedback` | ActorProfile + Opportunity; optional recommendation | Yes, bounded | No | Delete by fictional actor or marked Opportunity before recommendations/Opportunity | Low; recommendation deletion only nulls its optional link |
| `WatchList` | ActorProfile when populated; otherwise unclear/global-like | Yes, preferably derived | No when `actor_profile_id` is set | Delete by fictional actor; never claim null-owner rows | Medium; global queries and title-only upsert can cross actors |
| `CastingGoal` | ActorProfile when populated | Yes | No when `actor_profile_id` is set | Delete by fictional actor; delete derived WatchLists first or together | Medium; production save creates/updates WatchLists and refreshes Opportunities |
| `DreamRoleTarget` | ActorProfile | Defer from minimal v1 | No | Delete by fictional actor; delete its derived WatchList separately | Low–medium; service has cross-feature side effects |
| `CareerMemory` | ActorProfile when populated; otherwise unclear | Yes, one actor-owned row | No when `actor_profile_id` is set | Delete by fictional actor; never claim null-owner rows | Medium; get-or-create can create null-owner memory when no actor exists |
| `TravelPreference` | ActorProfile | Yes, one | No | Actor cascade or explicit delete before actor | Low |
| `AuditionJournalEntry` | Submission and/or Opportunity; otherwise unclear | Yes, derived | No while at least one owned link exists | Identify and delete before Submission/Opportunity | High if cleanup order is wrong: both links become null |
| `ActorJournalEntry` | Deterministic linked record, not directly ActorProfile | Yes, derived | No while an owned link exists | Identify and delete before linked Submission/Opportunity/Asset/task | High if cleanup order is wrong: links become null |
| `CallbackEvent` | Submission and/or Opportunity | Optional in v1 | No while an owned link exists | Delete before parents for clarity; database cascade also removes it when either linked parent is deleted | Medium; deleting either parent deletes the entire event |
| `AuditionCalendarEvent` | Submission and/or Opportunity; otherwise unclear | Yes, derived | No while an owned link exists | Must delete before Submission and Opportunity | High: both parent deletions set links to null and leave the event |
| `SubmissionStatusHistory` | Submission | Yes, derived | No | Delete through Submission ORM/database cascade | Low |
| `SubmissionAsset` | Submission-to-Asset association | Defer with Assets | No | Delete through Submission cascade before any Asset deletion | Medium; Asset FK is `RESTRICT` |
| `Asset` | ActorProfile | Defer from v1 | No | Use `AssetService.delete` before actor deletion so the file is removed | High: direct/database cascade leaves filesystem residue |
| `Archetype` | Global reference data | No new rows for v1 | Not applicable | Preserve; only remove seed-owned association rows | High shared-reference risk; name and slug are globally unique |

## Detailed ownership and deletion behavior

### RecommendationFeedback

- **Primary owner:** both `ActorProfile` and `Opportunity`. `RecommendationFeedback.actor_profile_id` and `.opportunity_id` are required; `.recommendation_id` is optional (`backend/app/db/models/agent.py`, `RecommendationFeedback`).
- **Foreign keys:** actor and Opportunity use `ON DELETE CASCADE`; recommendation uses `ON DELETE SET NULL`.
- **ORM cascade:** only child-to-parent relationships are declared. Neither `ActorProfile` nor `Opportunity` declares a feedback collection, so cleanup relies on explicit selection or database cascades, not an ORM delete-orphan cascade.
- **Identification:** safely reachable by fictional actor ID and independently by portfolio Opportunity ID. A recommendation link is additional evidence, not the ownership root.
- **Marker:** unnecessary.
- **Cleanup:** delete explicitly before its Opportunity/actor for auditable counts, or allow either required-owner database cascade. Delete feedback before `AgentRecommendation` if preserving the recommendation association matters to the reset report.
- **Residue risk:** none after actor or Opportunity deletion. Deleting only the recommendation preserves feedback with `recommendation_id=NULL`, intentionally.
- **Creation path:** the recommendation-feedback route constructs the row from an existing `AgentRecommendation`, then calls `LearningAgent.analyze` (`backend/app/api/v1/routes/agents.py`, `create_recommendation_feedback`). That path safely guarantees actor/Opportunity consistency and exercises learning, but `LearningAgent.analyze` commits and creates a `LearningInsight` (`backend/app/agents/learning_agent.py`). A future atomic seed must account for that transaction owner rather than blindly calling the route logic.
- **Dataset v1:** recommended. It is the direct persisted input used for actor-interest signals; `LearningAgent.analyze` filters by actor and ignores demo Opportunities.

### WatchList

- **Primary owner:** `ActorProfile` only when `actor_profile_id` is populated; the nullable FK permits ownerless rows (`backend/app/db/models/agent.py`, `WatchList`).
- **Foreign key:** `actor_profile_id -> actor_profiles.id ON DELETE CASCADE`, nullable.
- **ORM cascade:** child-to-parent relationship only; `ActorProfile` has no WatchList collection.
- **Identification:** fictional actor ID is sufficient. Null-owner WatchLists must never be claimed by title, category, or terms.
- **Marker:** unnecessary for actor-owned rows; the model has no metadata field.
- **Cleanup:** delete actor-owned WatchLists before the actor or rely on database cascade.
- **Residue/shared risk:** actor-owned rows do not survive actor deletion. Ownerless rows do, and global list/refresh queries include them.
- **Creation path:** prefer `WatchListService` semantics (`backend/app/services/watch_list_service.py`) because creation refreshes watch-list matches. However, it defaults ownership to the first ActorProfile, queries enabled WatchLists globally, mutates every non-demo Opportunity, and commits internally. The future seed must pass the fictional actor explicitly and avoid using this service against a mixed database.
- **Dataset v1:** recommended, preferably created as the deterministic side effect of one CastingGoal rather than duplicated manually.

### CastingGoal

- **Primary owner:** `ActorProfile` when its nullable `actor_profile_id` is populated (`backend/app/db/models/agent.py`, `CastingGoal`).
- **Foreign key:** actor uses `ON DELETE CASCADE`.
- **ORM cascade:** child-to-parent only; no collection on `ActorProfile`.
- **Identification/marker:** fictional actor ID is sufficient; no marker is needed. Null-owner goals are out of scope.
- **Cleanup:** remove any WatchList derived from the goal, then delete the goal or fictional actor. The database deletes actor-owned goals with the actor.
- **Residue/shared risk:** the goal itself cannot orphan when actor-owned. Its generated WatchList is not FK-linked to the goal and must be found through actor ownership, not title alone.
- **Creation path:** preserve `create_casting_goal` orchestration (`backend/app/api/v1/routes/agents.py`): it calls `WorkflowConnectorService.after_casting_goal_saved`, refreshes WatchLists against Opportunities, and commits. Direct ORM construction would omit those effects. The internal WatchList upsert currently matches title globally (`WorkflowConnectorService._upsert_watch_list`), so isolation is essential.
- **Dataset v1:** recommended because active goals feed Opportunity Intelligence and can establish a meaningful WatchList.

### DreamRoleTarget

- **Primary owner:** required `ActorProfile` (`backend/app/db/models/intelligence.py`, `DreamRoleTarget`).
- **Foreign key:** actor uses `ON DELETE CASCADE`.
- **ORM cascade:** child-to-parent only.
- **Identification/marker:** fictional actor ID is deterministic; no marker needed.
- **Cleanup:** delete its actor-owned derived WatchList, then target or actor.
- **Residue/shared risk:** the target cascades with actor deletion, but its generated WatchList has no target FK.
- **Creation path:** use `IntelligenceService.create_dream_target` semantics. It creates an actor-owned WatchList through `WorkflowConnectorService`, refreshes all matches, and commits (`backend/app/services/intelligence_service.py`).
- **Dataset v1:** defer. CastingGoal plus WatchList already exercises targeting and ranking with less overlapping setup. Add a DreamRoleTarget in a later presentation-completeness pass.

### CareerMemory

- **Primary owner:** `ActorProfile` when set; nullable ownership otherwise (`backend/app/db/models/agent.py`, `CareerMemory`).
- **Foreign key:** actor uses `ON DELETE CASCADE`.
- **ORM cascade:** child-to-parent only.
- **Identification/marker:** fictional actor ID is sufficient. Do not claim a null-owner record.
- **Cleanup:** explicit actor-ID delete or actor cascade.
- **Residue risk:** actor-owned memory is removed; null-owner memory survives.
- **Creation path:** use `ExecutiveIntelligenceService.get_or_create_memory/update_memory` semantics (`backend/app/services/executive_intelligence_service.py`) only after the fictional actor exists. Both methods commit internally, and `get_or_create_memory(None)` intentionally creates an ownerless row.
- **Dataset v1:** recommended as one actor-owned record to populate executive-intelligence context.

### TravelPreference

- **Primary owner:** required `ActorProfile` (`backend/app/db/models/travel_preference.py`, `TravelPreference`).
- **Foreign key:** actor uses `ON DELETE CASCADE`.
- **ORM cascade:** `ActorProfile.travel_preferences` uses `cascade="all, delete-orphan"`; the child has `back_populates`.
- **Identification/marker:** fictional actor ID is definitive; no marker needed.
- **Cleanup:** actor ORM cascade, database cascade, or explicit child-first deletion are all safe.
- **Residue risk:** none.
- **Creation path:** use the travel-preference repository/upsert contract (`backend/app/repositories/travel_preference.py`, `backend/app/api/v1/routes/travel_preferences.py`) to preserve the one-preference-per-actor application convention, even though the database model has no uniqueness constraint.
- **Dataset v1:** required because Opportunity Intelligence and Command Center context read actor travel constraints.

### AuditionJournalEntry

- **Primary owner:** Submission and/or Opportunity; both are nullable (`backend/app/db/models/intelligence.py`, `AuditionJournalEntry`).
- **Foreign keys:** both use `ON DELETE SET NULL`.
- **ORM cascade:** child-to-parent only; no parent collection.
- **Identification:** select rows whose `submission_id` belongs to a portfolio Submission or whose `opportunity_id` belongs to a marked Opportunity. A row with neither link is unclear and must not be claimed.
- **Marker:** not needed if cleanup occurs before parents. There is no metadata field.
- **Cleanup:** delete before Calendar-independent parent cleanup, before Submission, and before Opportunity.
- **Orphan risk:** high. Deleting parents first leaves a valid row with both links null.
- **Creation path:** prefer `WorkflowConnectorService.after_submission_created`, which calls `_ensure_journal_entry` once per Submission. `IntelligenceService.create_journal_entry` is appropriate only for intentionally standalone/manual entries and commits independently.
- **Dataset v1:** recommended as a Submission-derived row, not a separately invented record.

### ActorJournalEntry

- **Primary owner:** no direct actor FK. Ownership is inferred from nullable links to Opportunity (`linked_breakdown_id`), Submission (`linked_audition_id`), Asset, or CareerDevelopmentTask (`backend/app/db/models/journal.py`, `ActorJournalEntry`).
- **Foreign keys:** every link uses `ON DELETE SET NULL`.
- **ORM cascade:** child-to-parent relationships only.
- **Identification:** use a portfolio Opportunity or Submission link. Asset/task-only entries require separately proven fictional ownership. Rows with no owned link are not portfolio-owned.
- **Marker:** not needed while a deterministic link exists; no metadata field exists.
- **Cleanup:** delete before every linked parent.
- **Orphan/filesystem risk:** deleting parents first leaves a fully detached journal record. The journal itself owns no file.
- **Creation path:** use `ActorWorkEventService`/`JournalService.record_once` (`backend/app/services/actor_work_event_service.py`, `backend/app/services/journal_service.py`) because event-type mapping and duplicate prevention are production behavior. Direct `JournalService.create` commits and does not provide `record_once` idempotency.
- **Dataset v1:** recommended only as a natural Submission or callback side effect.

### CallbackEvent

- **Primary owner:** Submission and/or Opportunity; both links are nullable (`backend/app/db/models/intelligence.py`, `CallbackEvent`).
- **Foreign keys:** both use `ON DELETE CASCADE`.
- **ORM cascade:** child-to-parent only.
- **Identification:** either portfolio Submission or marked Opportunity is sufficient while linked. A fully unlinked event is unclear.
- **Marker:** unnecessary.
- **Cleanup:** delete explicitly before parents for predictable reporting. Otherwise deletion of either linked parent deletes the event.
- **Orphan risk:** linked rows cannot survive deletion of a linked parent, but the schema permits creating an initially unlinked row.
- **Creation path:** prefer `IntelligenceService.create_callback_event`; it validates links, updates eligible Submission status, records an actor-work journal event, projects Calendar work through `ActorWorkEventService`, and commits.
- **Dataset v1:** optional. A callback-status Submission can already demonstrate outcomes; add one CallbackEvent only if the first presentation explicitly needs callback UI.

### AuditionCalendarEvent

- **Primary owner:** Submission and/or Opportunity; both links are nullable (`backend/app/db/models/operations.py`, `AuditionCalendarEvent`).
- **Foreign keys:** both use `ON DELETE SET NULL`.
- **ORM cascade:** child-to-parent only; neither parent declares a Calendar collection.
- **Identification:** select by portfolio Submission IDs and marked Opportunity IDs before parent deletion. Rows with neither owned link must not be claimed.
- **Marker:** not needed if cleanup order is enforced; no metadata field exists.
- **Required cleanup proof:** deleting the Opportunity sets `opportunity_id=NULL`; deleting the Submission sets `submission_id=NULL`. If both parents go first, the event remains and no longer carries any portfolio ownership evidence. Portfolio reset therefore **must delete AuditionCalendarEvent rows before Submission and Opportunity rows**.
- **Residue risk:** high if parent-first cleanup is used; no filesystem risk.
- **Creation path:** prefer automatic projection via `SubmissionService.create`, `WorkflowConnectorService._ensure_calendar_events`, and `ActorWorkEventService`; those paths use duplicate guards and consistent event types. Use `OperationsService.create_event` only for an intentionally manual event.
- **Dataset v1:** required, but derived from seeded Opportunity/Submission dates rather than constructed independently.

### SubmissionStatusHistory

- **Primary owner:** required `Submission` (`backend/app/db/models/submission.py`, `SubmissionStatusHistory`).
- **Foreign key:** Submission uses `ON DELETE CASCADE`.
- **ORM cascade:** `Submission.status_history` uses `cascade="all, delete-orphan"`.
- **Identification/marker:** portfolio Submission ownership is sufficient; no marker needed.
- **Cleanup:** delete with Submission; no separate pass is required.
- **Residue risk:** none.
- **Creation path:** use `SubmissionService.create` and `.add_status`; they validate statuses, maintain `current_status`, add history, and invoke workflow projections.
- **Dataset v1:** required as a Submission-derived record.

### SubmissionAsset

- **Primary owner:** association between Submission and Asset (`backend/app/db/models/submission.py`, `SubmissionAsset`).
- **Foreign keys:** Submission uses `ON DELETE CASCADE`; Asset uses `ON DELETE RESTRICT`.
- **ORM cascade:** `Submission.assets` is a secondary relationship without delete cascade to Asset. This correctly treats Asset as independently owned/shared within the actor profile.
- **Identification/marker:** portfolio Submission identifies association rows. It never proves that the referenced Asset itself is portfolio-exclusive.
- **Cleanup:** delete Submission/association before attempting Asset deletion.
- **Shared-reference risk:** deleting an Asset while an association remains is blocked; deleting a Submission removes only its association and preserves the Asset.
- **Creation path:** use `SubmissionService.create`, which validates every Asset ID and updates `Asset.last_used_date`.
- **Dataset v1:** defer because v1 should omit Asset rows.

## Related parent and reference behavior

- `ActorProfile` declares delete-orphan ORM ownership only for `travel_preferences`, `assets`, and `submissions` among the reviewed models (`backend/app/db/models/actor_profile.py`, `ActorProfile`). Other actor-owned rows rely on database `ON DELETE CASCADE`.
- `Opportunity.recommendations` uses ORM `cascade="all, delete-orphan"`; `Opportunity.submissions` uses `passive_deletes=True`, relying on the database cascade (`backend/app/db/models/opportunity.py`, `Opportunity`). Feedback, Calendar, callbacks, and journal rows are not parent collections.
- `Submission.status_history` is delete-orphan owned; `Submission.assets` is a non-owning many-to-many relationship (`backend/app/db/models/submission.py`, `Submission`).
- `Asset` is delete-orphan owned by ActorProfile at the ORM layer, but database deletion cannot remove its physical `local_file_path` (`backend/app/db/models/asset.py`, `Asset`). `AssetService.delete` commits the row deletion and then calls `FileStorageService.delete_file`; actor cascade does not run that service (`backend/app/services/asset_service.py`).
- `Archetype` is global reference data: `name` and `slug` are globally unique, and Assets relate through `asset_archetypes`. The association foreign keys cascade, but the Archetype itself is not actor-owned (`backend/app/db/models/asset.py`, `Archetype`, `asset_archetypes`). The portfolio dataset must reuse an existing Archetype only when appropriate and must not create or delete shared Archetype rows.

## Asset decision for dataset v1

Dataset v1 should omit Assets and `SubmissionAsset` associations.

`Asset.local_file_path` is required. The supported creation path, `AssetService.create`, requires persistent storage and a real `UploadFile`, writes a controlled file beneath `upload_dir`, creates workflow records, and removes the file if the database operation fails. Metadata-only Asset construction would bypass those guarantees, while a fabricated path would create a broken downloadable record. Direct actor/database cascade would also leave physical files behind.

If Assets are added later, use controlled packaged fixture files copied through `AssetService.create` in an environment with durable file storage, record the resulting actor-owned IDs, delete submission associations first, and remove each Asset through `AssetService.delete` before deleting the actor. Do not seed metadata-only rows or fake paths.

## Minimum supporting records for dataset v1

After the future fictional actor and marked Opportunities exist, the smallest meaningful supporting set is:

1. One actor-owned `TravelPreference` with explicit travel and audition modality values.
2. One active actor-owned `CastingGoal`, allowing the production connector to derive one actor-owned `WatchList` and refresh Opportunity matches.
3. One actor-owned `CareerMemory` to populate executive-intelligence context.
4. A bounded set of `Submission` records spanning meaningful statuses. Create them through `SubmissionService`, producing initial `SubmissionStatusHistory` rows.
5. Submission-derived `AuditionCalendarEvent`, `AuditionJournalEntry`, and `ActorJournalEntry` records produced by existing workflow services from real Opportunity dates.
6. At least one `AgentRecommendation` followed by one `RecommendationFeedback` tied to the same fictional actor and portfolio Opportunity, so actor-interest scoring has a valid persisted signal.

The seed should not manufacture duplicate derived rows after service orchestration. Exact IDs and natural keys must be planned before applying writes so reruns remain deterministic.

## Records deferred from dataset v1

- `Asset` and `SubmissionAsset`, until controlled fixture-file lifecycle and durable storage are explicitly included.
- `DreamRoleTarget`, because CastingGoal plus its derived WatchList already covers target-driven matching in the minimum slice.
- Standalone/manual `AuditionJournalEntry`, `ActorJournalEntry`, and `AuditionCalendarEvent`; v1 should use workflow-derived records.
- `CallbackEvent`, unless callback-specific presentation is a first-release requirement.
- New `Archetype` rows. Existing global reference data must not be duplicated or deleted.

## Exact cleanup dependency order

All ownership IDs must be collected before any deletion begins, in the same reset transaction. The safe order is:

1. Resolve the fictional ActorProfile ID, portfolio Opportunity IDs from the exact metadata namespace, and Submission IDs that point to both that actor and those Opportunities.
2. Delete owned `AuditionCalendarEvent` rows by Submission or Opportunity ID.
3. Delete owned `AuditionJournalEntry` and `ActorJournalEntry` rows while their links are intact.
4. Delete owned `CallbackEvent` rows explicitly for deterministic reset reporting.
5. Delete `RecommendationFeedback`, followed by portfolio `AgentRecommendation` rows.
6. Delete `SubmissionAsset` associations if Assets are ever included; then delete Submissions. `SubmissionStatusHistory` is removed through ORM/database cascade.
7. Delete derived actor-owned WatchLists, then CastingGoals and DreamRoleTargets.
8. Delete actor-owned CareerMemory and TravelPreference rows (or allow the final actor cascade once counts have been recorded).
9. If a later dataset includes Assets, delete each through filesystem-aware `AssetService.delete` only after associations are gone. Never delete shared Archetypes.
10. Delete portfolio-owned Opportunities.
11. Delete the fictional ActorProfile last, after verifying no owned `SET NULL` link rows remain.

The isolated portfolio database remains the primary protection. Relationship traversal is defense in depth and enables deterministic dry-run/reset reports; it is not a substitute for database isolation.

## Service-reuse recommendations

| Record/workflow | Production path to preserve | Reason |
| --- | --- | --- |
| TravelPreference | Travel preference repository/upsert route | Preserves the application convention of one current preference per actor |
| CastingGoal | Casting-goal route orchestration + `WorkflowConnectorService` | Produces the expected WatchList and refreshes matches |
| WatchList | Prefer goal-derived connector; otherwise `WatchListService` | Applies matching fields and counters to Opportunities |
| CareerMemory | `ExecutiveIntelligenceService` with an explicit actor | Avoids null-owner memory and preserves get-or-create behavior |
| Submission/history | `SubmissionService` | Validates statuses/costs/assets and triggers Calendar/journal/workflow projections |
| Calendar | Submission/actor-work projection; `OperationsService` only for manual events | Preserves event types and duplicate guards |
| Audition journal | `WorkflowConnectorService.after_submission_created` | Creates at most one linked entry per Submission |
| Actor journal | `ActorWorkEventService` + `JournalService.record_once` | Preserves event vocabulary and idempotency |
| CallbackEvent | `IntelligenceService.create_callback_event` | Validates links, updates Submission state, and records related work |
| RecommendationFeedback | Existing recommendation-feedback orchestration | Derives actor/Opportunity from recommendation and refreshes learning |
| Assets, later only | `AssetService.create/delete` | Keeps database and physical-file lifecycle aligned |

Several production services commit internally and some create additional records. A future seed must not call them naively inside the ownership script's single transaction. Task 3 should first define an explicit, bounded dataset plan and decide how to preserve these service invariants without nested or partial commits. This is a transaction-composition constraint, not justification for bypassing all production behavior with direct ORM construction.

## Principal risks to carry forward

1. Parent-first deletion permanently loses ownership evidence for Calendar and journal rows using `SET NULL`.
2. Nullable actor ownership on WatchList, CastingGoal, and CareerMemory means null-owner records cannot safely be claimed.
3. WatchList queries and connector title matching are global; database isolation is mandatory.
4. Service-owned commits conflict with a future all-or-nothing seed transaction unless composition is designed explicitly.
5. Submission creation has intentional cross-feature side effects; direct ORM construction would underrepresent the application.
6. Asset database cascades do not remove files, and fake file paths would create broken portfolio behavior.
7. Archetypes are globally unique shared reference data and must never be treated as seed-owned merely because a seeded Asset references them.
8. `CallbackEvent` uses `CASCADE`, whereas Calendar and journals use `SET NULL`; cleanup cannot apply one generic parent-deletion policy to all supporting rows.
