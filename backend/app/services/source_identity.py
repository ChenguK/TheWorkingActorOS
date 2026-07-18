from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass, field
from typing import Mapping
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


MARKETING_QUERY_KEYS = {"fbclid", "gclid", "msclkid"}


@dataclass(frozen=True)
class SourceUrlPolicy:
    host_aliases: Mapping[str, str] = field(default_factory=dict)
    removable_query_keys: frozenset[str] = frozenset()


@dataclass(frozen=True)
class SourceIdentity:
    source_name: str
    external_source_id: str | None
    canonical_url_hash: str | None
    content_version_hash: str

    @property
    def requires_expiry(self) -> bool:
        return self.external_source_id is None


class SourceIdentityService:
    @classmethod
    def build_identity(
        cls,
        *,
        source_name: str,
        external_source_id: str | None,
        raw_url: str | None,
        version_fields: Mapping[str, str | None],
        url_policy: SourceUrlPolicy | None = None,
    ) -> SourceIdentity:
        source = cls._scalar(source_name).lower()
        if not source:
            raise ValueError("source_name is required")
        external_id = cls._scalar(external_source_id) or None
        canonical_url = cls.canonicalize_url(raw_url, url_policy) if raw_url else None
        if not external_id and not canonical_url:
            raise ValueError("an external source ID or absolute URL is required")
        normalized_version = {
            cls._scalar(str(key)): cls._scalar(value)
            for key, value in version_fields.items()
            if cls._scalar(str(key)) and cls._scalar(value)
        }
        if not normalized_version:
            raise ValueError("at least one version field is required")
        return SourceIdentity(
            source_name=source,
            external_source_id=external_id,
            canonical_url_hash=(
                cls._digest("source-identity:v1", source, canonical_url)
                if canonical_url
                else None
            ),
            content_version_hash=cls._digest(
                "source-version:v1", source, normalized_version
            ),
        )

    @classmethod
    def canonicalize_url(
        cls, raw_url: str, policy: SourceUrlPolicy | None = None
    ) -> str:
        policy = policy or SourceUrlPolicy()
        parsed = urlsplit(raw_url)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            raise ValueError("source URL must be absolute HTTP(S)")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("source URL credentials are forbidden")
        scheme = parsed.scheme.lower()
        try:
            host = parsed.hostname.encode("idna").decode("ascii").lower()
        except UnicodeError as exc:
            raise ValueError("source URL hostname is invalid") from exc
        aliases = {key.lower(): value.lower() for key, value in policy.host_aliases.items()}
        host = aliases.get(host, host)
        port = parsed.port
        netloc = host if port is None or (scheme, port) in {("http", 80), ("https", 443)} else f"{host}:{port}"
        removable = {key.lower() for key in policy.removable_query_keys}
        query = []
        for key, value in parse_qsl(parsed.query, keep_blank_values=True):
            lowered = key.lower()
            if lowered.startswith("utm_") or lowered in MARKETING_QUERY_KEYS or lowered in removable:
                continue
            query.append((key, value))
        query.sort()
        return urlunsplit((scheme, netloc, parsed.path or "/", urlencode(query, doseq=True), ""))

    @staticmethod
    def _scalar(value: str | None) -> str:
        if value is None:
            return ""
        return " ".join(unicodedata.normalize("NFKC", value).split())

    @staticmethod
    def _digest(prefix: str, source: str, value: object) -> str:
        payload = json.dumps(
            {"schema": prefix, "source": source, "value": value},
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

