"""Home-Assistant-REST-Client — States lesen, Services aufrufen, Templates rendern.

Spricht die HA-REST-API (https://developers.home-assistant.io/docs/api/rest/)
mit Long-Lived-Access-Token. URL + Token kommen aus den System-Settings
(overrides.resolve) — nie hartkodiert, nie im Modul-Repo.

Alle Netz-Calls laufen durch _request() — in Tests gemockt, kein echter Traffic.
Die Helfer liefern aufbereitete, flache Dicts (nur was Frontend/Tools brauchen),
nicht die rohen HA-Payloads.
"""
from __future__ import annotations

from typing import Any

import httpx
from hydrahive.settings.overrides import resolve

_TIMEOUT = 15.0


class HAConfigError(RuntimeError):
    """URL oder Token fehlt — Modul ist nicht konfiguriert."""


class HAError(RuntimeError):
    """Upstream-HA-Fehler (Netzwerk, Auth, HTTP-Status)."""


def _base_url() -> str:
    raw = (resolve("homeassistant_url") or "").strip().rstrip("/")
    if not raw:
        raise HAConfigError("Home-Assistant-URL ist nicht gesetzt (System → Einstellungen).")
    return raw


def _token() -> str:
    tok = (resolve("homeassistant_token") or "").strip()
    if not tok:
        raise HAConfigError("Home-Assistant-Token ist nicht gesetzt (System → Einstellungen).")
    return tok


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"}


async def _request(method: str, path: str, *, json: Any = None) -> Any:
    url = f"{_base_url()}/api{path}"
    headers = _headers()
    async with httpx.AsyncClient(timeout=_TIMEOUT) as http:
        try:
            r = await http.request(method, url, headers=headers, json=json)
        except httpx.HTTPError as exc:
            raise HAError(f"Verbindung zu Home Assistant fehlgeschlagen: {exc}") from exc
        if r.status_code == 401:
            raise HAError("Home Assistant lehnt den Token ab (401 — Token ungültig/abgelaufen).")
        if r.status_code == 404:
            raise HAError("Home-Assistant-Endpunkt nicht gefunden (404).")
        if r.status_code >= 400:
            raise HAError(f"Home Assistant antwortete mit HTTP {r.status_code}: {r.text[:200]}")
        if not r.content:
            return None
        ctype = r.headers.get("content-type", "")
        return r.json() if "application/json" in ctype else r.text


def _slim_state(s: dict) -> dict:
    """Rohe HA-State auf das Wesentliche eindampfen."""
    attrs = s.get("attributes") or {}
    return {
        "entity_id": s.get("entity_id"),
        "state": s.get("state"),
        "name": attrs.get("friendly_name") or s.get("entity_id"),
        "domain": (s.get("entity_id") or "").split(".", 1)[0],
        "unit": attrs.get("unit_of_measurement"),
        "device_class": attrs.get("device_class"),
        "icon": attrs.get("icon"),
        "last_changed": s.get("last_changed"),
        "attributes": attrs,
    }


async def ping() -> dict:
    """GET /api/ — Verbindungs-/Auth-Check. Liefert die HA-Begrüßung."""
    data = await _request("GET", "/")
    msg = data.get("message") if isinstance(data, dict) else str(data)
    return {"ok": True, "message": msg or "API running."}


async def config() -> dict:
    """GET /api/config — Instanz-Infos (Version, Standort, Einheiten)."""
    data = await _request("GET", "/config")
    if not isinstance(data, dict):
        return {}
    return {
        "location_name": data.get("location_name"),
        "version": data.get("version"),
        "unit_system": data.get("unit_system"),
        "time_zone": data.get("time_zone"),
        "state": data.get("state"),
    }


async def states() -> list[dict]:
    """GET /api/states — alle Entities (eingedampft)."""
    data = await _request("GET", "/states")
    rows = data if isinstance(data, list) else []
    return [_slim_state(s) for s in rows if isinstance(s, dict)]


async def state(entity_id: str) -> dict:
    """GET /api/states/<entity_id> — eine Entity (eingedampft)."""
    data = await _request("GET", f"/states/{entity_id}")
    if not isinstance(data, dict):
        raise HAError(f"Unerwartete Antwort für {entity_id}.")
    return _slim_state(data)


async def call_service(domain: str, service: str, data: dict | None = None) -> list[dict]:
    """POST /api/services/<domain>/<service> — Service ausführen.

    Liefert die Liste der durch den Call geänderten States (eingedampft).
    """
    changed = await _request("POST", f"/services/{domain}/{service}", json=data or {})
    rows = changed if isinstance(changed, list) else []
    return [_slim_state(s) for s in rows if isinstance(s, dict)]


async def services() -> list[dict]:
    """GET /api/services — verfügbare Domains + ihre Services."""
    data = await _request("GET", "/services")
    return data if isinstance(data, list) else []


async def render_template(template: str) -> str:
    """POST /api/template — Jinja-Template serverseitig rendern (read-only-Nutzung)."""
    result = await _request("POST", "/template", json={"template": template})
    return result if isinstance(result, str) else str(result)
