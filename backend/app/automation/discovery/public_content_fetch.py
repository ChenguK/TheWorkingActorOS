from __future__ import annotations

import ipaddress
import re
import socket
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urljoin, urlparse

import httpx


PUBLIC_CONTENT_MAX_REDIRECTS = 4
PUBLIC_CONTENT_TIMEOUT_SECONDS = 12.0
PUBLIC_CONTENT_CONNECT_TIMEOUT_SECONDS = 5.0
PUBLIC_CONTENT_READ_TIMEOUT_SECONDS = 8.0
PUBLIC_CONTENT_MAX_RESPONSE_BYTES = 500_000
PUBLIC_CONTENT_MAX_VISIBLE_TEXT_LENGTH = 12_000
PUBLIC_CONTENT_MAX_FAILURE_MESSAGE_LENGTH = 160
PUBLIC_CONTENT_MAX_URL_LENGTH = 1_000

PUBLIC_CONTENT_USER_AGENT = "WorkingActorOS/0.1 public casting-source fetch"
PUBLIC_CONTENT_ACCEPT = "text/html,text/plain;q=0.9"
PUBLIC_CONTENT_ALLOWED_TYPES = {"text/html", "text/plain"}
PUBLIC_CONTENT_REDIRECT_STATUSES = {301, 302, 303, 307, 308}


class PublicContentFetchOutcome(StrEnum):
    SUCCESS = "success"
    INVALID_URL = "invalid_url"
    UNSUPPORTED_SCHEME = "unsupported_scheme"
    NON_PUBLIC_DESTINATION = "non_public_destination"
    DNS_FAILURE = "dns_failure"
    MIXED_PUBLIC_PRIVATE_DNS = "mixed_public_private_dns"
    REDIRECT_REJECTED = "redirect_rejected"
    REDIRECT_LIMIT_EXCEEDED = "redirect_limit_exceeded"
    TIMEOUT = "timeout"
    UNSUPPORTED_CONTENT_TYPE = "unsupported_content_type"
    RESPONSE_TOO_LARGE = "response_too_large"
    PROTECTED_LOGIN_REQUIRED = "protected_login_required"
    CAPTCHA_ACCESS_DENIED = "captcha_access_denied"
    HTTP_FAILURE = "http_failure"
    EMPTY_USABLE_CONTENT = "empty_usable_content"


_SAFE_MESSAGES = {
    PublicContentFetchOutcome.SUCCESS: "Public page fetched.",
    PublicContentFetchOutcome.INVALID_URL: "Candidate URL is invalid.",
    PublicContentFetchOutcome.UNSUPPORTED_SCHEME: "Candidate URL uses an unsupported scheme.",
    PublicContentFetchOutcome.NON_PUBLIC_DESTINATION: "Candidate URL does not resolve to a public destination.",
    PublicContentFetchOutcome.DNS_FAILURE: "Candidate hostname could not be resolved.",
    PublicContentFetchOutcome.MIXED_PUBLIC_PRIVATE_DNS: "Candidate hostname has an unsafe mixed DNS result.",
    PublicContentFetchOutcome.REDIRECT_REJECTED: "Candidate redirect was rejected by the public fetch policy.",
    PublicContentFetchOutcome.REDIRECT_LIMIT_EXCEEDED: "Candidate exceeded the public redirect limit.",
    PublicContentFetchOutcome.TIMEOUT: "Candidate page fetch timed out.",
    PublicContentFetchOutcome.UNSUPPORTED_CONTENT_TYPE: "Candidate returned an unsupported content type.",
    PublicContentFetchOutcome.RESPONSE_TOO_LARGE: "Candidate response exceeded the public fetch size limit.",
    PublicContentFetchOutcome.PROTECTED_LOGIN_REQUIRED: "Candidate requires login or authentication.",
    PublicContentFetchOutcome.CAPTCHA_ACCESS_DENIED: "Candidate is blocked by access controls or a bot challenge.",
    PublicContentFetchOutcome.HTTP_FAILURE: "Candidate returned an unsuccessful HTTP response.",
    PublicContentFetchOutcome.EMPTY_USABLE_CONTENT: "Candidate contained no usable public text.",
}


@dataclass(frozen=True)
class PublicContentFetchResult:
    outcome: PublicContentFetchOutcome
    text: str | None = None
    message: str = ""

    @property
    def succeeded(self) -> bool:
        return self.outcome is PublicContentFetchOutcome.SUCCESS and self.text is not None


Resolver = Callable[[str, int], list[str]]


class PublicContentFetcher:
    def __init__(
        self,
        *,
        resolver: Resolver | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._resolver = resolver or self._resolve_addresses
        self._transport = transport

    def fetch(self, url: str) -> PublicContentFetchResult:
        current_url = url
        visited: set[str] = set()
        timeout = httpx.Timeout(
            PUBLIC_CONTENT_TIMEOUT_SECONDS,
            connect=PUBLIC_CONTENT_CONNECT_TIMEOUT_SECONDS,
            read=PUBLIC_CONTENT_READ_TIMEOUT_SECONDS,
        )
        try:
            with httpx.Client(
                follow_redirects=False,
                timeout=timeout,
                transport=self._transport,
                trust_env=False,
            ) as client:
                for redirect_count in range(PUBLIC_CONTENT_MAX_REDIRECTS + 1):
                    validation = self._validate_destination(current_url)
                    if validation:
                        return validation
                    canonical = self._without_fragment(current_url)
                    if canonical in visited:
                        return self._failure(PublicContentFetchOutcome.REDIRECT_REJECTED)
                    visited.add(canonical)

                    result, redirect = self._request(client, canonical)
                    if result:
                        return result
                    if redirect is None:
                        return self._failure(PublicContentFetchOutcome.HTTP_FAILURE)
                    if redirect_count == PUBLIC_CONTENT_MAX_REDIRECTS:
                        return self._failure(PublicContentFetchOutcome.REDIRECT_LIMIT_EXCEEDED)
                    next_url = urljoin(canonical, redirect)
                    redirect_validation = self._validate_destination(next_url)
                    if redirect_validation:
                        return self._failure(PublicContentFetchOutcome.REDIRECT_REJECTED)
                    if (
                        urlparse(canonical).scheme == "https"
                        and urlparse(next_url).scheme == "http"
                    ):
                        return self._failure(PublicContentFetchOutcome.REDIRECT_REJECTED)
                    current_url = next_url
        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.TimeoutException):
            return self._failure(PublicContentFetchOutcome.TIMEOUT)
        except httpx.HTTPError:
            return self._failure(PublicContentFetchOutcome.HTTP_FAILURE)
        return self._failure(PublicContentFetchOutcome.REDIRECT_LIMIT_EXCEEDED)

    def _request(
        self, client: httpx.Client, url: str
    ) -> tuple[PublicContentFetchResult | None, str | None]:
        headers = {"User-Agent": PUBLIC_CONTENT_USER_AGENT, "Accept": PUBLIC_CONTENT_ACCEPT}
        with client.stream("GET", url, headers=headers) as response:
            if response.status_code in PUBLIC_CONTENT_REDIRECT_STATUSES:
                location = response.headers.get("location")
                if not location:
                    return self._failure(PublicContentFetchOutcome.HTTP_FAILURE), None
                return None, location
            if response.status_code < 200 or response.status_code >= 300:
                if response.status_code in {401, 407}:
                    return self._failure(PublicContentFetchOutcome.PROTECTED_LOGIN_REQUIRED), None
                if response.status_code in {403, 429}:
                    return self._failure(PublicContentFetchOutcome.CAPTCHA_ACCESS_DENIED), None
                return self._failure(PublicContentFetchOutcome.HTTP_FAILURE), None

            content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
            if content_type not in PUBLIC_CONTENT_ALLOWED_TYPES:
                return self._failure(PublicContentFetchOutcome.UNSUPPORTED_CONTENT_TYPE), None

            body = bytearray()
            for chunk in response.iter_bytes():
                if len(body) + len(chunk) > PUBLIC_CONTENT_MAX_RESPONSE_BYTES:
                    return self._failure(PublicContentFetchOutcome.RESPONSE_TOO_LARGE), None
                body.extend(chunk)
            decoded = bytes(body).decode(response.encoding or "utf-8", errors="ignore")
            protected = self._protected_outcome(decoded)
            if protected:
                return self._failure(protected), None
            return PublicContentFetchResult(
                PublicContentFetchOutcome.SUCCESS,
                text=decoded,
                message=_SAFE_MESSAGES[PublicContentFetchOutcome.SUCCESS],
            ), None

    def _validate_destination(self, url: str) -> PublicContentFetchResult | None:
        if not isinstance(url, str) or not url or len(url) > PUBLIC_CONTENT_MAX_URL_LENGTH:
            return self._failure(PublicContentFetchOutcome.INVALID_URL)
        try:
            parsed = urlparse(url)
            port = parsed.port
        except ValueError:
            return self._failure(PublicContentFetchOutcome.INVALID_URL)
        if not parsed.scheme:
            return self._failure(PublicContentFetchOutcome.INVALID_URL)
        if parsed.scheme not in {"http", "https"}:
            return self._failure(PublicContentFetchOutcome.UNSUPPORTED_SCHEME)
        if not parsed.hostname or parsed.username is not None or parsed.password is not None:
            return self._failure(PublicContentFetchOutcome.INVALID_URL)
        hostname = parsed.hostname.rstrip(".").casefold()
        if hostname == "localhost" or hostname.endswith(".localhost"):
            return self._failure(PublicContentFetchOutcome.NON_PUBLIC_DESTINATION)
        try:
            literal = ipaddress.ip_address(hostname)
        except ValueError:
            literal = None
        if literal is not None:
            return (
                None
                if self._is_public(literal)
                else self._failure(PublicContentFetchOutcome.NON_PUBLIC_DESTINATION)
            )
        try:
            addresses = self._resolver(hostname, port or (443 if parsed.scheme == "https" else 80))
        except (OSError, socket.gaierror):
            return self._failure(PublicContentFetchOutcome.DNS_FAILURE)
        if not addresses:
            return self._failure(PublicContentFetchOutcome.DNS_FAILURE)
        states: list[bool] = []
        try:
            states = [self._is_public(ipaddress.ip_address(address)) for address in addresses]
        except ValueError:
            return self._failure(PublicContentFetchOutcome.DNS_FAILURE)
        if any(states) and not all(states):
            return self._failure(PublicContentFetchOutcome.MIXED_PUBLIC_PRIVATE_DNS)
        if not all(states):
            return self._failure(PublicContentFetchOutcome.NON_PUBLIC_DESTINATION)
        return None

    def _resolve_addresses(self, hostname: str, port: int) -> list[str]:
        infos = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
        return list(dict.fromkeys(info[4][0] for info in infos))

    def _is_public(self, address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
            address = address.ipv4_mapped
        return address.is_global and not any(
            (
                address.is_loopback,
                address.is_private,
                address.is_link_local,
                address.is_multicast,
                address.is_reserved,
                address.is_unspecified,
            )
        )

    def _protected_outcome(self, body: str) -> PublicContentFetchOutcome | None:
        sample = body[:100_000]
        lowered = re.sub(r"\s+", " ", sample).casefold()
        if re.search(r"<input\b[^>]*type=[\"']?password", sample, re.I) or any(
            phrase in lowered
            for phrase in (
                "login required",
                "log in to continue",
                "sign in to continue",
                "authentication required",
                "you must be logged in",
            )
        ):
            return PublicContentFetchOutcome.PROTECTED_LOGIN_REQUIRED
        if any(
            phrase in lowered
            for phrase in (
                "access denied",
                "verify you are human",
                "captcha",
                "unusual traffic",
                "checking your browser before accessing",
                "cloudflare ray id",
                "enable javascript and cookies to continue",
            )
        ):
            return PublicContentFetchOutcome.CAPTCHA_ACCESS_DENIED
        return None

    def _without_fragment(self, url: str) -> str:
        parsed = urlparse(url)
        return parsed._replace(fragment="").geturl()

    def _failure(self, outcome: PublicContentFetchOutcome) -> PublicContentFetchResult:
        message = _SAFE_MESSAGES[outcome][:PUBLIC_CONTENT_MAX_FAILURE_MESSAGE_LENGTH]
        return PublicContentFetchResult(outcome=outcome, message=message)
