import pytest

from app.services.source_identity import SourceIdentityService, SourceUrlPolicy


def test_source_identity_normalizes_url_without_stripping_significant_parameters():
    identity = SourceIdentityService.build_identity(
        source_name="  Playbill  ",
        external_source_id=None,
        raw_url=(
            "HTTPS://WWW.PLAYBILL.COM:443/job/Caf%C3%A9/?role=Lead&utm_source=email"
            "&token=ABC#details"
        ),
        version_fields={"title": "  Café   Casting  "},
        url_policy=SourceUrlPolicy(host_aliases={"www.playbill.com": "playbill.com"}),
    )

    equivalent = SourceIdentityService.build_identity(
        source_name="playbill",
        external_source_id=None,
        raw_url="https://playbill.com/job/Caf%C3%A9/?token=ABC&role=Lead",
        version_fields={"title": "Café Casting"},
    )

    assert identity.source_name == "playbill"
    assert identity.canonical_url_hash == equivalent.canonical_url_hash
    assert identity.content_version_hash == equivalent.content_version_hash
    assert len(identity.canonical_url_hash or "") == 64


def test_source_identity_is_deterministic_source_scoped_and_version_sensitive():
    first = SourceIdentityService.build_identity(
        source_name="playbill",
        external_source_id=" JOB-42 ",
        raw_url=None,
        version_fields={"category": None, "title": "Open Call"},
    )
    reordered = SourceIdentityService.build_identity(
        source_name="playbill",
        external_source_id="JOB-42",
        raw_url=None,
        version_fields={"title": "Open Call", "category": ""},
    )
    changed = SourceIdentityService.build_identity(
        source_name="playbill",
        external_source_id="JOB-42",
        raw_url=None,
        version_fields={"title": "Open Call — Revised"},
    )
    other_source = SourceIdentityService.build_identity(
        source_name="parallel",
        external_source_id="JOB-42",
        raw_url=None,
        version_fields={"title": "Open Call"},
    )

    assert first == reordered
    assert first.content_version_hash != changed.content_version_hash
    assert first.content_version_hash != other_source.content_version_hash


@pytest.mark.parametrize(
    ("source_name", "external_source_id", "raw_url", "version_fields"),
    [
        ("playbill", None, None, {"title": "Title only"}),
        ("playbill", "JOB-1", None, {}),
        ("playbill", "JOB-1", "relative/path", {"title": "Role"}),
        ("playbill", "JOB-1", "https://user:secret@example.com/job", {"title": "Role"}),
    ],
)
def test_source_identity_rejects_unsafe_inputs(
    source_name, external_source_id, raw_url, version_fields
):
    with pytest.raises(ValueError):
        SourceIdentityService.build_identity(
            source_name=source_name,
            external_source_id=external_source_id,
            raw_url=raw_url,
            version_fields=version_fields,
        )

