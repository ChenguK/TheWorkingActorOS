from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from enum import Enum

from app.services.source_identity import SourceUrlPolicy


MAX_SOURCE_KEY_LENGTH = 160
MAX_SOURCE_URL_LENGTH = 1000
MAX_EXTERNAL_SOURCE_ID_LENGTH = 255
MAX_VERSION_FIELDS = 16
MAX_VERSION_FIELD_NAME_LENGTH = 80
MAX_VERSION_FIELD_VALUE_LENGTH = 500
MAX_RULE_KEY_LENGTH = 120


class IdentityAuthority(str, Enum):
    PROVIDER = "provider"
    USER_SUPPLIED_URL = "user_supplied_url"
    NONE = "none"


class SourceClassification(str, Enum):
    ACTING_ROLE = "Acting Role"
    CREW_JOB = "Crew Job"
    NON_ACTING_JOB = "Non-Acting Job"
    UNKNOWN = "Unknown"


class ClassificationConfidence(str, Enum):
    DETERMINISTIC = "deterministic"
    PROBABILISTIC = "probabilistic"
    UNKNOWN = "unknown"


def _bounded_scalar(value: str, *, field_name: str, maximum: int) -> str:
    normalized = " ".join(unicodedata.normalize("NFKC", value).split())
    if not normalized:
        raise ValueError(f"{field_name} is required")
    if len(normalized) > maximum:
        raise ValueError(f"{field_name} must be at most {maximum} characters")
    return normalized


def _optional_scalar(value: str | None, *, field_name: str, maximum: int) -> str | None:
    if value is None:
        return None
    return _bounded_scalar(value, field_name=field_name, maximum=maximum)


@dataclass(frozen=True)
class SourceVersionField:
    name: str
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "name",
            _bounded_scalar(
                self.name,
                field_name="version field name",
                maximum=MAX_VERSION_FIELD_NAME_LENGTH,
            ),
        )
        object.__setattr__(
            self,
            "value",
            _bounded_scalar(
                self.value,
                field_name="version field value",
                maximum=MAX_VERSION_FIELD_VALUE_LENGTH,
            ),
        )


@dataclass(frozen=True)
class SourceEvidence:
    source_key: str
    source_url: str | None
    external_source_id: str | None
    identity_authority: IdentityAuthority
    version_fields: tuple[SourceVersionField, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_key",
            _bounded_scalar(
                self.source_key,
                field_name="source_key",
                maximum=MAX_SOURCE_KEY_LENGTH,
            ),
        )
        object.__setattr__(
            self,
            "source_url",
            _optional_scalar(
                self.source_url,
                field_name="source_url",
                maximum=MAX_SOURCE_URL_LENGTH,
            ),
        )
        object.__setattr__(
            self,
            "external_source_id",
            _optional_scalar(
                self.external_source_id,
                field_name="external_source_id",
                maximum=MAX_EXTERNAL_SOURCE_ID_LENGTH,
            ),
        )
        fields = tuple(sorted(self.version_fields, key=lambda item: item.name))
        if len(fields) > MAX_VERSION_FIELDS:
            raise ValueError(f"version_fields must contain at most {MAX_VERSION_FIELDS} items")
        names = [item.name for item in fields]
        if len(names) != len(set(names)):
            raise ValueError("version_fields contains a duplicate field name")
        object.__setattr__(self, "version_fields", fields)

    def version_mapping(self) -> dict[str, str]:
        return {field.name: field.value for field in self.version_fields}


@dataclass(frozen=True)
class SourceClassificationEvidence:
    rule_key: str
    suggested_classification: SourceClassification
    confidence_kind: ClassificationConfidence
    acting_signal_present: bool
    non_acting_signal_present: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "rule_key",
            _bounded_scalar(
                self.rule_key,
                field_name="rule_key",
                maximum=MAX_RULE_KEY_LENGTH,
            ),
        )


@dataclass(frozen=True)
class SourceCapabilities:
    trusted_source: bool
    automatic_non_acting_exclusion: bool
    url_policy: SourceUrlPolicy

