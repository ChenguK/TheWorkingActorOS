from __future__ import annotations

import gzip
from collections.abc import Callable

import httpx
import pytest

from app.automation.discovery.public_content_fetch import (
    PUBLIC_CONTENT_ACCEPT,
    PUBLIC_CONTENT_MAX_FAILURE_MESSAGE_LENGTH,
    PUBLIC_CONTENT_MAX_REDIRECTS,
    PUBLIC_CONTENT_MAX_RESPONSE_BYTES,
    PUBLIC_CONTENT_USER_AGENT,
    PublicContentFetchOutcome,
    PublicContentFetcher,
)
from app.automation.discovery.public_web_search import PublicWebBreakdownSearch


PUBLIC_HTML = (
    "<html><body>Public casting notice seeking actors for a film role. "
    + ("Audition details and submission information. " * 8)
    + "</body></html>"
)


def resolver_for(addresses: list[str]) -> Callable[[str, int], list[str]]:
    return lambda _hostname, _port: addresses


def fetcher(
    handler: Callable[[httpx.Request], httpx.Response],
    addresses: list[str] | None = None,
) -> PublicContentFetcher:
    return PublicContentFetcher(
        resolver=resolver_for(addresses or ["93.184.216.34"]),
        transport=httpx.MockTransport(handler),
    )


def html_response(request: httpx.Request, body: str = PUBLIC_HTML, status: int = 200):
    return httpx.Response(
        status,
        headers={"content-type": "text/html; charset=utf-8"},
        text=body,
        request=request,
    )


@pytest.mark.parametrize(
    ("url", "addresses"),
    [
        ("https://93.184.216.34/casting", None),
        ("https://[2606:2800:220:1:248:1893:25c8:1946]/casting", None),
        ("https://casting.example/casting", ["93.184.216.34", "2606:4700::1111"]),
    ],
)
def test_public_destinations_are_allowed(url, addresses):
    result = fetcher(html_response, addresses).fetch(url)

    assert result.outcome == PublicContentFetchOutcome.SUCCESS
    assert result.text == PUBLIC_HTML


@pytest.mark.parametrize(
    "url",
    [
        "https://localhost/casting",
        "https://127.0.0.1/casting",
        "https://[::1]/casting",
        "https://10.0.0.1/casting",
        "https://172.16.0.1/casting",
        "https://192.168.1.1/casting",
        "https://169.254.1.1/casting",
        "https://224.0.0.1/casting",
        "https://192.0.2.1/casting",
        "https://0.0.0.0/casting",
        "https://[::ffff:10.0.0.1]/casting",
    ],
)
def test_non_public_literal_destinations_are_rejected_without_http(url):
    called = False

    def handler(request):
        nonlocal called
        called = True
        return html_response(request)

    result = fetcher(handler).fetch(url)

    assert result.outcome == PublicContentFetchOutcome.NON_PUBLIC_DESTINATION
    assert not called


@pytest.mark.parametrize("address", ["10.0.0.4", "169.254.2.2", "100.64.0.1"])
def test_hostname_resolving_only_to_non_public_addresses_is_rejected(address):
    result = fetcher(html_response, [address]).fetch("https://casting.example/role")

    assert result.outcome == PublicContentFetchOutcome.NON_PUBLIC_DESTINATION


def test_mixed_public_private_dns_is_rejected():
    result = fetcher(html_response, ["93.184.216.34", "10.0.0.4"]).fetch(
        "https://casting.example/role"
    )

    assert result.outcome == PublicContentFetchOutcome.MIXED_PUBLIC_PRIVATE_DNS


def test_dns_failure_is_safe_and_typed():
    def resolver(_hostname, _port):
        raise OSError("private resolver detail")

    result = PublicContentFetcher(
        resolver=resolver, transport=httpx.MockTransport(html_response)
    ).fetch("https://casting.example/role")

    assert result.outcome == PublicContentFetchOutcome.DNS_FAILURE
    assert "private resolver detail" not in result.message


def test_public_to_public_redirect_is_followed_with_minimal_headers():
    requests: list[httpx.Request] = []

    def handler(request):
        requests.append(request)
        if request.url.host == "casting.example":
            return httpx.Response(302, headers={"location": "https://roles.example/open"})
        return html_response(request)

    result = fetcher(handler).fetch("https://casting.example/start")

    assert result.outcome == PublicContentFetchOutcome.SUCCESS
    assert [request.url.host for request in requests] == ["casting.example", "roles.example"]
    for request in requests:
        assert request.headers["user-agent"] == PUBLIC_CONTENT_USER_AGENT
        assert request.headers["accept"] == PUBLIC_CONTENT_ACCEPT
        assert "authorization" not in request.headers
        assert "cookie" not in request.headers
        assert "referer" not in request.headers


@pytest.mark.parametrize(
    "location",
    [
        "https://127.0.0.1/private",
        "https://localhost/private",
        "file:///private/data",
        "https://user:secret@roles.example/private",
        "http://roles.example/downgrade",
    ],
)
def test_unsafe_redirect_is_rejected(location):
    def handler(request):
        return httpx.Response(302, headers={"location": location}, request=request)

    result = fetcher(handler).fetch("https://casting.example/start")

    assert result.outcome == PublicContentFetchOutcome.REDIRECT_REJECTED


def test_redirect_loop_is_rejected():
    def handler(request):
        location = "/b" if request.url.path == "/a" else "/a"
        return httpx.Response(302, headers={"location": location}, request=request)

    result = fetcher(handler).fetch("https://casting.example/a")

    assert result.outcome == PublicContentFetchOutcome.REDIRECT_REJECTED


def test_redirect_limit_is_enforced():
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(302, headers={"location": f"/next-{calls}"}, request=request)

    result = fetcher(handler).fetch("https://casting.example/start")

    assert result.outcome == PublicContentFetchOutcome.REDIRECT_LIMIT_EXCEEDED
    assert calls == PUBLIC_CONTENT_MAX_REDIRECTS + 1


@pytest.mark.parametrize(
    ("exception", "outcome"),
    [
        (httpx.ConnectTimeout("connect"), PublicContentFetchOutcome.TIMEOUT),
        (httpx.ReadTimeout("read"), PublicContentFetchOutcome.TIMEOUT),
    ],
)
def test_timeouts_are_typed(exception, outcome):
    def handler(request):
        exception.request = request
        raise exception

    assert fetcher(handler).fetch("https://casting.example/role").outcome == outcome


@pytest.mark.parametrize(
    ("status", "outcome"),
    [
        (401, PublicContentFetchOutcome.PROTECTED_LOGIN_REQUIRED),
        (403, PublicContentFetchOutcome.CAPTCHA_ACCESS_DENIED),
        (404, PublicContentFetchOutcome.HTTP_FAILURE),
        (500, PublicContentFetchOutcome.HTTP_FAILURE),
    ],
)
def test_http_failures_have_stable_outcomes(status, outcome):
    result = fetcher(lambda request: html_response(request, status=status)).fetch(
        "https://casting.example/role"
    )
    assert result.outcome == outcome


@pytest.mark.parametrize("content_type", ["application/pdf", "application/json", "image/png", ""])
def test_unsupported_or_missing_content_type_is_rejected(content_type):
    def handler(request):
        headers = {"content-type": content_type} if content_type else {}
        return httpx.Response(200, headers=headers, content=b"payload", request=request)

    result = fetcher(handler).fetch("https://casting.example/role")

    assert result.outcome == PublicContentFetchOutcome.UNSUPPORTED_CONTENT_TYPE


def test_oversized_streamed_response_is_rejected():
    content = b"x" * (PUBLIC_CONTENT_MAX_RESPONSE_BYTES + 1)
    result = fetcher(
        lambda request: httpx.Response(
            200, headers={"content-type": "text/plain"}, content=content, request=request
        )
    ).fetch("https://casting.example/role")

    assert result.outcome == PublicContentFetchOutcome.RESPONSE_TOO_LARGE


def test_oversized_decompressed_response_is_rejected():
    compressed = gzip.compress(b"x" * (PUBLIC_CONTENT_MAX_RESPONSE_BYTES + 1))
    result = fetcher(
        lambda request: httpx.Response(
            200,
            headers={"content-type": "text/plain", "content-encoding": "gzip"},
            content=compressed,
            request=request,
        )
    ).fetch("https://casting.example/role")

    assert result.outcome == PublicContentFetchOutcome.RESPONSE_TOO_LARGE


@pytest.mark.parametrize(
    ("body", "outcome"),
    [
        (
            '<form><input type="password"></form>',
            PublicContentFetchOutcome.PROTECTED_LOGIN_REQUIRED,
        ),
        (
            "Authentication required to view this casting notice",
            PublicContentFetchOutcome.PROTECTED_LOGIN_REQUIRED,
        ),
        ("Access denied", PublicContentFetchOutcome.CAPTCHA_ACCESS_DENIED),
        ("Please complete the CAPTCHA", PublicContentFetchOutcome.CAPTCHA_ACCESS_DENIED),
        ("Checking your browser before accessing", PublicContentFetchOutcome.CAPTCHA_ACCESS_DENIED),
    ],
)
def test_protected_pages_are_rejected(body, outcome):
    result = fetcher(lambda request: html_response(request, body=body)).fetch(
        "https://casting.example/role"
    )
    assert result.outcome == outcome


def test_harmless_login_word_does_not_trigger_protected_page_detection():
    body = "The character recalls a login problem in an office scene. " * 20
    result = fetcher(lambda request: html_response(request, body=body)).fetch(
        "https://casting.example/role"
    )
    assert result.outcome == PublicContentFetchOutcome.SUCCESS


@pytest.mark.parametrize(
    ("url", "outcome"),
    [
        ("not a url", PublicContentFetchOutcome.INVALID_URL),
        ("ftp://casting.example/role", PublicContentFetchOutcome.UNSUPPORTED_SCHEME),
        ("https:///missing-host", PublicContentFetchOutcome.INVALID_URL),
        ("https://user:secret@casting.example/role", PublicContentFetchOutcome.INVALID_URL),
    ],
)
def test_malformed_urls_are_rejected(url, outcome):
    assert fetcher(html_response).fetch(url).outcome == outcome


def test_empty_usable_content_and_candidate_report_are_typed_and_safe():
    client = type(
        "Client",
        (),
        {"search": lambda self, **kwargs: {"results": [{"url": "https://casting.example/empty"}]}},
    )()
    service = PublicWebBreakdownSearch(
        parallel_client=client,
        content_fetcher=fetcher(lambda request: html_response(request, body="tiny")),
    )
    service.configured = lambda: True

    result = service.search("FilmTV")
    report = result.candidate_reports[0]

    assert report["fetch_outcome"] == PublicContentFetchOutcome.EMPTY_USABLE_CONTENT
    assert report["rejection_reason"] == "Candidate contained no usable public text."
    assert len(report["rejection_reason"]) <= PUBLIC_CONTENT_MAX_FAILURE_MESSAGE_LENGTH
    assert "tiny" not in str(report)
