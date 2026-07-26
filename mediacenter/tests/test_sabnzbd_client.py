from __future__ import annotations

import logging
import traceback

import httpx
import pytest

from backend import sabnzbd
from backend.errors import SabAuthError, SabResponseError, SabUnavailable
from backend.sab_credentials import SabConnection

_CONNECTION = SabConnection(origin="http://sab.example:8080", api_key="top-secret-sab-key")


async def test_version_and_categories_use_pinned_secret_transport(caplog):
    captured: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        mode = request.url.params["mode"]
        payload = (
            {"version": "4.5.3"}
            if mode == "version"
            else {"categories": ["movies", "tv", "audio", "audiobook", "ebook"]}
        )
        return httpx.Response(200, headers={"content-type": "application/json"}, json=payload)

    caplog.set_level(logging.INFO, logger="httpx")
    transport = httpx.MockTransport(handler)
    version = await sabnzbd.fetch_version(
        _CONNECTION, inner_transport=transport, pinned_ip="93.184.216.34"
    )
    categories = await sabnzbd.fetch_categories(
        _CONNECTION, inner_transport=transport, pinned_ip="93.184.216.34"
    )

    assert version == "4.5.3"
    assert categories == {"movies", "tv", "audio", "audiobook", "ebook"}
    assert len(captured) == 2
    assert all(request.url.params["apikey"] == "top-secret-sab-key" for request in captured)
    assert all(request.headers["host"] == "sab.example:8080" for request in captured)
    assert all(request.url.host == "93.184.216.34" for request in captured)
    assert all(request.extensions["sni_hostname"] == "sab.example" for request in captured)
    assert "top-secret-sab-key" not in caplog.text


@pytest.mark.parametrize("status", [301, 302, 307, 308])
async def test_sab_redirects_are_rejected(status):
    transport = httpx.MockTransport(
        lambda _: httpx.Response(status, headers={"location": "http://127.0.0.1/private"})
    )

    with pytest.raises(SabResponseError) as exc_info:
        await sabnzbd.fetch_version(
            _CONNECTION, inner_transport=transport, pinned_ip="93.184.216.34"
        )

    assert exc_info.value.code == "sab_redirect_rejected"
    assert "127.0.0.1" not in str(exc_info.value)


async def test_sab_network_exception_has_no_secret_in_exception_graph():
    secret = _CONNECTION.api_key

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"failed {secret}", request=request)

    with pytest.raises(SabUnavailable) as exc_info:
        await sabnzbd.fetch_version(
            _CONNECTION,
            inner_transport=httpx.MockTransport(handler),
            pinned_ip="93.184.216.34",
        )

    rendered = "".join(traceback.format_exception(exc_info.value))
    assert secret not in rendered
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__context__ is None


@pytest.mark.parametrize(
    "payload",
    [
        {"version": ""},
        {"version": 453},
        {"other": "4.5.3"},
        ["4.5.3"],
    ],
)
async def test_sab_version_rejects_unexpected_json(payload):
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, headers={"content-type": "application/json"}, json=payload)
    )

    with pytest.raises(SabResponseError) as exc_info:
        await sabnzbd.fetch_version(
            _CONNECTION, inner_transport=transport, pinned_ip="93.184.216.34"
        )

    assert exc_info.value.code == "sab_response_invalid"


async def test_sab_json_auth_error_is_stable_and_sanitized():
    transport = httpx.MockTransport(
        lambda _: httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={"status": False, "error": "API Key Incorrect"},
        )
    )

    with pytest.raises(SabAuthError) as exc_info:
        await sabnzbd.fetch_categories(
            _CONNECTION, inner_transport=transport, pinned_ip="93.184.216.34"
        )

    assert exc_info.value.code == "sab_auth_failed"
    assert "Incorrect" not in str(exc_info.value)


async def test_invalid_json_has_no_upstream_body_in_exception_graph():
    secret_body = b'{"private":"never-leak-body"'
    transport = httpx.MockTransport(
        lambda _: httpx.Response(
            200, headers={"content-type": "application/json"}, content=secret_body
        )
    )

    with pytest.raises(SabResponseError) as exc_info:
        await sabnzbd.fetch_version(
            _CONNECTION, inner_transport=transport, pinned_ip="93.184.216.34"
        )

    rendered = "".join(traceback.format_exception(exc_info.value))
    assert "never-leak-body" not in rendered
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__context__ is None


async def test_sab_version_rejects_api_key_reflection():
    transport = httpx.MockTransport(
        lambda _: httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={"version": _CONNECTION.api_key},
        )
    )

    with pytest.raises(SabResponseError):
        await sabnzbd.fetch_version(
            _CONNECTION, inner_transport=transport, pinned_ip="93.184.216.34"
        )


async def test_sab_response_size_and_content_type_are_limited():
    too_large = httpx.MockTransport(
        lambda _: httpx.Response(
            200, headers={"content-type": "application/json"}, content=b"x" * 101
        )
    )
    with pytest.raises(SabResponseError) as size_error:
        await sabnzbd.fetch_version(
            _CONNECTION,
            inner_transport=too_large,
            pinned_ip="93.184.216.34",
            max_bytes=100,
        )
    assert size_error.value.code == "sab_response_too_large"

    html = httpx.MockTransport(
        lambda _: httpx.Response(
            200, headers={"content-type": "application/jsonp"}, content=b"{}"
        )
    )
    with pytest.raises(SabResponseError) as type_error:
        await sabnzbd.fetch_version(
            _CONNECTION, inner_transport=html, pinned_ip="93.184.216.34"
        )
    assert type_error.value.code == "sab_content_type_invalid"
