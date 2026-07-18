from dataclasses import FrozenInstanceError, fields

import pytest


def test_source_evidence_is_immutable_bounded_and_canonically_ordered():
    from app.automation.discovery.source_evidence import (
        IdentityAuthority,
        SourceEvidence,
        SourceVersionField,
    )

    evidence = SourceEvidence(
        source_key="  Public   Source  ",
        source_url="https://example.test/items/1",
        external_source_id=" item-1 ",
        identity_authority=IdentityAuthority.PROVIDER,
        version_fields=(
            SourceVersionField(" updated ", " 2026-07-18 "),
            SourceVersionField("title", "  Acting   Notice  "),
        ),
    )

    assert evidence.source_key == "Public Source"
    assert evidence.external_source_id == "item-1"
    assert [(item.name, item.value) for item in evidence.version_fields] == [
        ("title", "Acting Notice"),
        ("updated", "2026-07-18"),
    ]
    with pytest.raises(FrozenInstanceError):
        evidence.source_key = "changed"


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("", "value"),
        ("x" * 81, "value"),
        ("name", ""),
        ("name", "x" * 501),
    ],
)
def test_source_version_field_rejects_empty_or_oversized_scalars(name, value):
    from app.automation.discovery.source_evidence import SourceVersionField

    with pytest.raises(ValueError):
        SourceVersionField(name, value)


def test_source_evidence_rejects_programmer_errors_but_represents_incomplete_input():
    from app.automation.discovery.source_evidence import (
        IdentityAuthority,
        SourceEvidence,
        SourceVersionField,
    )

    incomplete = SourceEvidence(
        source_key="manual",
        source_url=None,
        external_source_id=None,
        identity_authority=IdentityAuthority.NONE,
        version_fields=(),
    )
    assert incomplete.version_fields == ()

    with pytest.raises(ValueError, match="source_key"):
        SourceEvidence(
            source_key="",
            source_url=None,
            external_source_id=None,
            identity_authority=IdentityAuthority.NONE,
            version_fields=(),
        )
    with pytest.raises(ValueError, match="duplicate"):
        SourceEvidence(
            source_key="source",
            source_url=None,
            external_source_id="1",
            identity_authority=IdentityAuthority.PROVIDER,
            version_fields=(SourceVersionField("title", "a"), SourceVersionField("title", "b")),
        )


def test_classification_and_capabilities_are_bounded_and_immutable():
    from app.automation.discovery.source_evidence import (
        ClassificationConfidence,
        SourceCapabilities,
        SourceClassification,
        SourceClassificationEvidence,
    )
    from app.services.source_identity import SourceUrlPolicy

    classification = SourceClassificationEvidence(
        rule_key=" deterministic_rule ",
        suggested_classification=SourceClassification.CREW_JOB,
        confidence_kind=ClassificationConfidence.DETERMINISTIC,
        acting_signal_present=False,
        non_acting_signal_present=True,
    )
    capabilities = SourceCapabilities(
        trusted_source=True,
        automatic_non_acting_exclusion=True,
        url_policy=SourceUrlPolicy(),
    )
    assert classification.rule_key == "deterministic_rule"
    with pytest.raises(FrozenInstanceError):
        classification.rule_key = "changed"
    with pytest.raises(FrozenInstanceError):
        capabilities.trusted_source = False
    with pytest.raises(ValueError):
        SourceClassificationEvidence(
            rule_key="x" * 121,
            suggested_classification=SourceClassification.UNKNOWN,
            confidence_kind=ClassificationConfidence.UNKNOWN,
            acting_signal_present=False,
            non_acting_signal_present=False,
        )


def test_contract_surface_has_no_payload_session_or_orm_fields():
    from app.automation.discovery.source_evidence import (
        SourceCapabilities,
        SourceClassificationEvidence,
        SourceEvidence,
        SourceVersionField,
    )

    names = {
        item.name
        for contract in (
            SourceVersionField,
            SourceEvidence,
            SourceClassificationEvidence,
            SourceCapabilities,
        )
        for item in fields(contract)
    }
    assert names == {
        "name",
        "value",
        "source_key",
        "source_url",
        "external_source_id",
        "identity_authority",
        "version_fields",
        "rule_key",
        "suggested_classification",
        "confidence_kind",
        "acting_signal_present",
        "non_acting_signal_present",
        "trusted_source",
        "automatic_non_acting_exclusion",
        "url_policy",
    }
    assert not names.intersection({"payload", "metadata", "session", "db", "opportunity", "html"})

