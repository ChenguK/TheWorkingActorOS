from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import cast
from uuid import UUID

from sqlalchemy.orm import Session

from app.automation.discovery.source_evidence import (
    ClassificationConfidence,
    IdentityAuthority,
    SourceCapabilities,
    SourceClassification,
    SourceClassificationEvidence,
    SourceEvidence,
)
from app.services.source_exclusion_service import SourceExclusionService
from app.services.source_identity import SourceIdentity, SourceIdentityService


class SourceExclusionGateOutcome(str, Enum):
    EXCLUDED_EXISTING = "excluded_existing"
    EXCLUDED_NEW = "excluded_new"
    CONTINUE_PROCESSING = "continue_processing"
    INELIGIBLE_FOR_EXCLUSION = "ineligible_for_exclusion"


@dataclass(frozen=True)
class SourceExclusionGateResult:
    outcome: SourceExclusionGateOutcome
    exclusion_id: UUID | None = None


class SourceExclusionGate:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.exclusions = SourceExclusionService(db)

    def evaluate(
        self,
        evidence: SourceEvidence,
        capabilities: SourceCapabilities,
        classification: SourceClassificationEvidence | None = None,
        *,
        now: datetime | None = None,
    ) -> SourceExclusionGateResult:
        identity = self._eligible_identity(evidence, capabilities)
        if identity is None:
            return SourceExclusionGateResult(
                SourceExclusionGateOutcome.INELIGIBLE_FOR_EXCLUSION
            )

        compatible = self.exclusions.record_compatible_sighting(identity, now=now)
        if compatible.excluded:
            return SourceExclusionGateResult(
                SourceExclusionGateOutcome.EXCLUDED_EXISTING,
                cast(UUID | None, compatible.exclusion_id),
            )

        if classification is None:
            return SourceExclusionGateResult(
                SourceExclusionGateOutcome.CONTINUE_PROCESSING
            )
        if not self._classification_is_eligible(classification):
            return SourceExclusionGateResult(
                SourceExclusionGateOutcome.INELIGIBLE_FOR_EXCLUSION
            )

        created = self.exclusions.record_confirmed_exclusion(
            identity,
            classification=classification.suggested_classification.value,
            reason_code="provider_listing_rule",
            now=now,
        )
        return SourceExclusionGateResult(
            SourceExclusionGateOutcome.EXCLUDED_NEW,
            cast(UUID | None, created.exclusion_id),
        )

    def identity_for(
        self, evidence: SourceEvidence, capabilities: SourceCapabilities
    ) -> SourceIdentity:
        return SourceIdentityService.build_identity(
            source_name=evidence.source_key,
            external_source_id=evidence.external_source_id,
            raw_url=evidence.source_url,
            version_fields=evidence.version_mapping(),
            url_policy=capabilities.url_policy,
        )

    def _eligible_identity(
        self, evidence: SourceEvidence, capabilities: SourceCapabilities
    ) -> SourceIdentity | None:
        if (
            not capabilities.trusted_source
            or not capabilities.automatic_non_acting_exclusion
            or evidence.identity_authority is not IdentityAuthority.PROVIDER
            or not evidence.version_fields
            or (not evidence.source_url and not evidence.external_source_id)
        ):
            return None
        try:
            return self.identity_for(evidence, capabilities)
        except ValueError:
            return None

    @staticmethod
    def _classification_is_eligible(
        classification: SourceClassificationEvidence,
    ) -> bool:
        return bool(
            classification.confidence_kind is ClassificationConfidence.DETERMINISTIC
            and classification.suggested_classification
            in {SourceClassification.CREW_JOB, SourceClassification.NON_ACTING_JOB}
            and classification.non_acting_signal_present
            and not classification.acting_signal_present
        )
