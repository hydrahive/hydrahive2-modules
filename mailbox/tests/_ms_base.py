"""Attrappe für login.microsoftonline.com (M1b): beantwortet devicecode/token aus Warteschlangen, merkt alle Anfragen.

Kein echtes Netz: oauth_ms._client wird auf einen httpx.MockTransport umgebogen.
"""
from __future__ import annotations

from urllib.parse import parse_qs

import httpx
import pytest

CID = "11111111-2222-3333-4444-555555555555"
DEVICE = {"device_code": "DEV-geheim", "user_code": "ABCD-EFGH", "verification_uri": "https://microsoft.com/devicelogin",
          "expires_in": 900, "interval": 5, "message": "To sign in …"}
TOKENS = {"token_type": "Bearer", "access_token": "AT-1", "refresh_token": "RT-1", "expires_in": 3600}


def err(code: str, desc: str = "", status: int = 400) -> tuple[int, dict]:
    return status, {"error": code, "error_description": desc + "\r\nTrace ID: 123\r\nCorrelation ID: 456"}


class FakeMS:
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []    # (Pfad, Formulardaten)
        self.device: list[tuple[int, dict]] = []
        self.token: list[tuple[int, dict]] = []
        self.fail_network = False

    def handler(self, request: httpx.Request) -> httpx.Response:
        if self.fail_network:
            raise httpx.ConnectError("kein Netz")
        form = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
        self.calls.append((request.url.host + request.url.path, form))
        if request.url.path.endswith("/devicecode"):
            st, body = self.device.pop(0) if self.device else (200, DEVICE)
        elif request.url.path.endswith("/token"):
            st, body = self.token.pop(0) if self.token else (200, TOKENS)
        else:
            st, body = 404, {}
        return httpx.Response(st, json=body)

    def paths(self) -> list[str]:
        return [p for p, _ in self.calls]


@pytest.fixture
def ms(monkeypatch):
    from backend import oauth_ms
    fake = FakeMS()
    monkeypatch.setattr(oauth_ms, "_client", lambda: httpx.Client(transport=httpx.MockTransport(fake.handler)))
    return fake


@pytest.fixture
def clock(monkeypatch):
    """Steuerbare Uhr für Vorgänge und Token-Ablauf."""
    from backend import ms_flows, ms_tokens
    t = {"now": 1000.0}
    monkeypatch.setattr(ms_flows, "_now", lambda: t["now"])
    monkeypatch.setattr(ms_tokens, "_now", lambda: t["now"])
    return t


@pytest.fixture
def app_set():
    from backend import ms_app
    ms_app.save(CID, "common")
    return CID


@pytest.fixture(autouse=True)
def _ms_state():
    """Vorgänge und Token-Speicher je Test leer (beides lebt im Speicher des Dienstes)."""
    from backend import ms_flows, ms_tokens
    ms_flows._FLOWS.clear()
    ms_tokens._CACHE.clear()
    ms_tokens._DEAD.clear()
    yield
    ms_flows._FLOWS.clear()
    ms_tokens._CACHE.clear()
    ms_tokens._DEAD.clear()
