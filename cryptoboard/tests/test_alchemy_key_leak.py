"""Sicherheits-Regression: Der Alchemy-Key darf nie in URL, Log oder Exception landen.

Echter httpx-Weg über MockTransport (kein Netz). Geprüft je Fehlerart (401, 403,
500, Timeout, Verbindungsfehler) und für den Erfolgsfall: Key nicht in der URL,
nur im Authorization-Header; nicht im Log (inkl. httpx/httpcore auf DEBUG); nicht
in str/repr/__cause__/__context__/traceback.format_exception; auch nicht, wenn ein
Aufrufer logger.exception() macht.
"""
from __future__ import annotations

import logging
import traceback

import httpx
import pytest

from backend import alchemy_client as ac

KEY = "GEHEIMKEY-leakprobe-1234567890abcdef"


def _patch_transport(monkeypatch, handler):
    orig = httpx.AsyncClient

    class _Client(orig):
        def __init__(self, *a, **kw):
            kw["transport"] = httpx.MockTransport(handler)
            super().__init__(*a, **kw)

    monkeypatch.setattr(ac.httpx, "AsyncClient", _Client)


def _assert_clean(exc: BaseException) -> None:
    seen = 0
    cur: BaseException | None = exc
    while cur is not None and seen < 10:
        assert KEY not in str(cur)
        assert KEY not in repr(cur)
        assert KEY not in repr(getattr(cur, "__dict__", {}))
        cur = cur.__cause__ or cur.__context__
        seen += 1
    assert exc.__cause__ is None and exc.__context__ is None
    assert KEY not in "".join(traceback.format_exception(exc))


def _status(code):
    return lambda req: httpx.Response(code, text="Must be authenticated!", request=req)


def _raise(exc_cls):
    def handler(req):
        raise exc_cls(f"kaputt bei {req.url} {req.headers}", request=req)
    return handler


CASES = [
    ("401", _status(401), ac.AlchemyHttpError),
    ("403", _status(403), ac.AlchemyHttpError),
    ("500", _status(500), ac.AlchemyHttpError),
    ("timeout", _raise(httpx.ReadTimeout), ac.AlchemyNetworkError),
    ("connect", _raise(httpx.ConnectError), ac.AlchemyNetworkError),
]


@pytest.mark.parametrize("name,handler,expected", CASES, ids=[c[0] for c in CASES])
@pytest.mark.asyncio
async def test_key_nie_in_log_oder_exception(name, handler, expected, monkeypatch, caplog):
    _patch_transport(monkeypatch, handler)
    caplog.set_level(logging.DEBUG)  # root inkl. httpx/httpcore auf DEBUG
    for lg in ("httpx", "httpcore"):
        logging.getLogger(lg).setLevel(logging.DEBUG)
    try:
        await ac.call("base", KEY, "eth_blockNumber", [])
    except expected as exc:
        _assert_clean(exc)
        logging.getLogger("aufrufer").exception("Aufrufer loggt den Fehler")
    else:
        pytest.fail("Fehler erwartet")
    assert caplog.records, "Log-Prüfung ohne Einträge wäre wertlos"
    assert KEY not in caplog.text
    for rec in caplog.records:
        assert KEY not in rec.getMessage()
        if rec.exc_info:
            assert KEY not in "".join(traceback.format_exception(*rec.exc_info))


@pytest.mark.asyncio
async def test_key_nur_im_header_nie_in_der_url(monkeypatch, caplog):
    seen = {}

    def handler(req):
        seen["url"] = str(req.url)
        seen["auth"] = req.headers.get("authorization")
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": "0x10"})

    _patch_transport(monkeypatch, handler)
    caplog.set_level(logging.DEBUG)
    logging.getLogger("httpx").setLevel(logging.DEBUG)
    assert await ac.call("base", KEY, "eth_blockNumber", []) == "0x10"
    assert seen["url"] == "https://base-mainnet.g.alchemy.com/v2"
    assert seen["auth"] == f"Bearer {KEY}"
    assert "HTTP Request" in caplog.text  # httpx hat geloggt …
    assert KEY not in caplog.text          # … aber ohne Key


@pytest.mark.asyncio
async def test_rpc_fehlerobjekt_ohne_key(monkeypatch):
    def handler(req):
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1,
                                         "error": {"code": -32600, "message": "not enabled on this app"}})

    _patch_transport(monkeypatch, handler)
    with pytest.raises(ac.AlchemyApiError) as info:
        await ac.call("base", KEY, "eth_blockNumber", [])
    _assert_clean(info.value)
    assert info.value.rpc_message == "not enabled on this app"
