"""Zugriff auf die Dream Machine (nur lesen in Etappe 1). Schlüssel nur im Kopf X-API-KEY, nur mit
bestätigtem Zertifikat. Fehler werden zu Codes; der Schlüssel taucht nie in Meldungen auf."""
from __future__ import annotations

from typing import Any

import httpx

from . import pinned
from .errors import NetError

_TIMEOUT = 20.0


async def _send(method: str, url: str, *, headers: dict, json: Any, pin: str):
    async with httpx.AsyncClient(verify=pinned.no_ca_context(), timeout=_TIMEOUT) as http:
        return await http.request(method, url, headers=headers, json=json,
                                  extensions={"trace": pinned.make_trace(pin)})


class Udm:
    def __init__(self, base_url: str, key: str, pin: str | None):
        self.base = base_url.rstrip("/")
        self.key = key
        self.pin = pin

    async def _call(self, method: str, path: str, body: Any = None) -> Any:
        if not self.pin:
            raise NetError("network_cert_unconfirmed")
        headers = {"Accept": "application/json", "X-API-KEY": self.key}
        try:
            r = await _send(method, self.base + path, headers=headers, json=body, pin=self.pin)
        except pinned.PinMismatch:
            raise NetError("network_cert_changed") from None
        except (OSError, httpx.HTTPError):
            raise NetError("network_unreachable") from None
        if r.status_code in (401, 403):
            raise NetError("network_auth_failed")
        if r.status_code >= 400:
            raise NetError("network_bad_response")
        try:
            return r.json()
        except ValueError:
            raise NetError("network_bad_response") from None

    async def get(self, path: str) -> Any:
        return await self._call("GET", path)

    async def post(self, path: str, body: Any) -> Any:
        return await self._call("POST", path, body)
