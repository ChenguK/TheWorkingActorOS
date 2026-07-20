from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.models.source_exclusion import SourceExclusion
from app.services.source_identity import SourceIdentity


URL_ONLY_EXPIRY = timedelta(days=180)

ALLOWED_CLASSIFICATIONS = {
    "Crew Job",
    "Non-Acting Job",
}

ALLOWED_REASON_CODES = {
    "provider_listing_rule",
    "deterministic_classification",
}


@dataclass(frozen=True)
class SourceExclusionResult:
    excluded: bool
    exclusion_id: object | None = None


class SourceExclusionService:
    def __init__(self, db: Session):
        self.db = db

    def record_compatible_sighting(
        self,
        identity: SourceIdentity,
        *,
        now: datetime | None = None,
    ) -> SourceExclusionResult:
        observed_at = self._now(now)

        statement = (
            update(SourceExclusion)
            .where(
                self._strong_identity_predicate(identity),
                SourceExclusion.content_version_hash
                == identity.content_version_hash,
                or_(
                    SourceExclusion.expires_at.is_(None),
                    SourceExclusion.expires_at > observed_at,
                ),
                self._secondary_identity_compatible(identity),
            )
            .values(
                # Use SQL expressions so concurrent updates cannot lose
                # increments or reverse the seen-at timestamp ordering.
                first_seen_at=func.least(
                    SourceExclusion.first_seen_at,
                    observed_at,
                ),
                last_seen_at=func.greatest(
                    SourceExclusion.last_seen_at,
                    observed_at,
                ),
                times_seen=SourceExclusion.times_seen + 1,
                updated_at=func.greatest(
                    SourceExclusion.updated_at,
                    observed_at,
                ),
            )
            .returning(SourceExclusion.id)
        )

        exclusion_id = self.db.execute(statement).scalar_one_or_none()

        return SourceExclusionResult(
            excluded=exclusion_id is not None,
            exclusion_id=exclusion_id,
        )

    def record_confirmed_exclusion(
        self,
        identity: SourceIdentity,
        *,
        classification: str,
        reason_code: str,
        expires_at: datetime | None = None,
        now: datetime | None = None,
    ) -> SourceExclusionResult:
        if classification not in ALLOWED_CLASSIFICATIONS:
            raise ValueError("classification is not confirmed non-acting")

        if reason_code not in ALLOWED_REASON_CODES:
            raise ValueError(
                "reason_code is not approved for source exclusion"
            )

        observed_at = self._now(now)

        expiry = expires_at
        if identity.requires_expiry:
            expiry = expiry or observed_at + URL_ONLY_EXPIRY

            if expiry <= observed_at:
                raise ValueError(
                    "weak identity expiration must be in the future"
                )

        values = {
            "source_name": identity.source_name,
            "external_source_id": identity.external_source_id,
            "canonical_url_hash": identity.canonical_url_hash,
            "content_version_hash": identity.content_version_hash,
            "exclusion_type": "confirmed_non_acting",
            "classification": classification,
            "reason_code": reason_code,
            "first_seen_at": observed_at,
            "last_seen_at": observed_at,
            "times_seen": 1,
            "expires_at": expiry,
            "created_at": observed_at,
            "updated_at": observed_at,
        }

        # Attempt the insert first. The table's partial unique indexes cover
        # both supported identity strategies:
        #
        # 1. source_name + external_source_id
        # 2. source_name + canonical_url_hash
        #
        # PostgreSQL waits for a conflicting concurrent insert to finish
        # before ON CONFLICT DO NOTHING returns.
        inserted_id = self.db.execute(
            insert(SourceExclusion)
            .values(**values)
            .on_conflict_do_nothing()
            .returning(SourceExclusion.id)
        ).scalar_one_or_none()

        if inserted_id is not None:
            return SourceExclusionResult(
                excluded=True,
                exclusion_id=inserted_id,
            )

        # A matching row already exists. Lock it while validating the
        # combined identity and deciding whether this is the same content
        # version or a new version.
        matches = self.db.scalars(
            select(SourceExclusion)
            .where(self._any_identity_predicate(identity))
            .with_for_update()
        ).all()

        unique_matches = {row.id: row for row in matches}

        if len(unique_matches) != 1:
            raise ValueError(
                "source identity resolves to conflicting exclusions"
            )

        row = next(iter(unique_matches.values()))

        if (
            identity.external_source_id
            and row.external_source_id
            and row.external_source_id != identity.external_source_id
        ):
            raise ValueError(
                "source identity conflicts with the persisted exclusion"
            )

        if (
            identity.canonical_url_hash
            and row.canonical_url_hash
            and row.canonical_url_hash != identity.canonical_url_hash
        ):
            raise ValueError(
                "source identity conflicts with the persisted exclusion"
            )

        same_active_version = (
            row.content_version_hash == identity.content_version_hash
            and (
                row.expires_at is None
                or row.expires_at > observed_at
            )
        )

        if same_active_version:
            # Perform the merge entirely in SQL.
            #
            # A worker with an earlier timestamp may reach this update after
            # a worker with a later timestamp inserted the row. LEAST and
            # GREATEST preserve the valid interval regardless of execution
            # order.
            update_statement = (
                update(SourceExclusion)
                .where(SourceExclusion.id == row.id)
                .values(
                    external_source_id=func.coalesce(
                        SourceExclusion.external_source_id,
                        identity.external_source_id,
                    ),
                    canonical_url_hash=func.coalesce(
                        SourceExclusion.canonical_url_hash,
                        identity.canonical_url_hash,
                    ),
                    first_seen_at=func.least(
                        SourceExclusion.first_seen_at,
                        observed_at,
                    ),
                    last_seen_at=func.greatest(
                        SourceExclusion.last_seen_at,
                        observed_at,
                    ),
                    times_seen=SourceExclusion.times_seen + 1,
                    updated_at=func.greatest(
                        SourceExclusion.updated_at,
                        observed_at,
                    ),
                )
                .returning(SourceExclusion.id)
            )

            exclusion_id = self.db.execute(
                update_statement
            ).scalar_one()

            return SourceExclusionResult(
                excluded=True,
                exclusion_id=exclusion_id,
            )

        # The identity matches, but this is a new content version or the
        # previous weak-identity exclusion expired. Begin a new observation
        # window and reset the count.
        replacement_statement = (
            update(SourceExclusion)
            .where(SourceExclusion.id == row.id)
            .values(
                external_source_id=func.coalesce(
                    SourceExclusion.external_source_id,
                    identity.external_source_id,
                ),
                canonical_url_hash=func.coalesce(
                    SourceExclusion.canonical_url_hash,
                    identity.canonical_url_hash,
                ),
                content_version_hash=identity.content_version_hash,
                classification=classification,
                reason_code=reason_code,
                first_seen_at=observed_at,
                last_seen_at=observed_at,
                times_seen=1,
                expires_at=expiry,
                updated_at=observed_at,
            )
            .returning(SourceExclusion.id)
        )

        exclusion_id = self.db.execute(
            replacement_statement
        ).scalar_one()

        return SourceExclusionResult(
            excluded=True,
            exclusion_id=exclusion_id,
        )

    @staticmethod
    def _now(now: datetime | None) -> datetime:
        value = now or datetime.now(timezone.utc)

        if value.tzinfo is None:
            raise ValueError("now must be timezone-aware")

        return value

    @staticmethod
    def _strong_identity_predicate(identity: SourceIdentity):
        if identity.external_source_id:
            return and_(
                SourceExclusion.source_name == identity.source_name,
                SourceExclusion.external_source_id
                == identity.external_source_id,
            )

        return and_(
            SourceExclusion.source_name == identity.source_name,
            SourceExclusion.canonical_url_hash
            == identity.canonical_url_hash,
        )

    @staticmethod
    def _secondary_identity_compatible(identity: SourceIdentity):
        conditions = []

        if identity.external_source_id:
            conditions.append(
                or_(
                    SourceExclusion.external_source_id.is_(None),
                    SourceExclusion.external_source_id
                    == identity.external_source_id,
                )
            )

        if identity.canonical_url_hash:
            conditions.append(
                or_(
                    SourceExclusion.canonical_url_hash.is_(None),
                    SourceExclusion.canonical_url_hash
                    == identity.canonical_url_hash,
                )
            )

        return and_(*conditions)

    @staticmethod
    def _any_identity_predicate(identity: SourceIdentity):
        identities = []

        if identity.external_source_id:
            identities.append(
                SourceExclusion.external_source_id
                == identity.external_source_id
            )

        if identity.canonical_url_hash:
            identities.append(
                SourceExclusion.canonical_url_hash
                == identity.canonical_url_hash
            )

        return and_(
            SourceExclusion.source_name == identity.source_name,
            or_(*identities),
        )