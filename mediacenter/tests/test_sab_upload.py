from __future__ import annotations

import httpx
import pytest

from backend.errors import SabResponseError
from backend.sab_credentials import SabConnection
from backend.sab_upload import upload_nzb

_CONNECTION = SabConnection(origin="https://sabnzb.home.server.ha", api_key="secret-key")

_NZB = b'<?xml version="1.0"?><nzb><file poster="x" /></nzb>'


@pytest.mark.parametrize("priority,expected", [("default", "0"), ("high", "1"), ("low", "-1")])
async def test_upload_nzb_uses_fixed_origin_and_safe_multipart(priority, expected):
    seen = {}

    async def handler(request: httpx.Request):
        seen["request"] = request
        seen["body"] = await request.aread()
        return httpx.Response(
            200, headers={"content-type": "application/json"},
            json={"status": True, "nzo_ids": ["SABnzbd_nzo_abc123"]},
        )

    job_id = await upload_nzb(
        _CONNECTION, _NZB, handoff_id="hh-safe", title="../../bad\nTitle",
        category="film", priority=priority,
        inner_transport=httpx.MockTransport(handler), pinned_ip="93.184.216.34",
    )
    request = seen["request"]
    body = seen["body"]
    assert job_id == "SABnzbd_nzo_abc123"
    assert request.url.host == "93.184.216.34"
    assert request.headers["host"] == "sabnzb.home.server.ha"
    assert request.url.params["apikey"] == "secret-key"
    assert b'name="mode"\r\n\r\naddfile' in body
    assert f'name="priority"\r\n\r\n{expected}'.encode() in body
    assert b'name="cat"\r\n\r\nfilm' in body
    assert b'filename="hh-safe.nzb"' in body
    assert b"../../bad" not in body
    assert _NZB in body


@pytest.mark.parametrize(
    "payload",
    [
        {"status": False, "error": "bad"},
        {"status": True, "nzo_ids": []},
        {"status": True, "nzo_ids": ["evil"]},
        {"status": True, "nzo_ids": ["SABnzbd_nzo_a", "SABnzbd_nzo_b"]},
    ],
)
async def test_upload_nzb_rejects_ambiguous_or_invalid_response(payload):
    transport = httpx.MockTransport(
        lambda _: httpx.Response(
            200, headers={"content-type": "application/json"}, json=payload
        )
    )
    with pytest.raises(SabResponseError):
        await upload_nzb(
            _CONNECTION, _NZB, handoff_id="hh-safe", title="Title", category="film",
            priority="default", inner_transport=transport, pinned_ip="93.184.216.34",
        )
