"""Laufende Microsoft-Anmeldungen (Geräte-Code) im Speicher des Dienstes (PLAN-M1b).

- je Vorgang: Besitzer, device_code (verlässt den Server nie), Ablauf, Takt (interval, slow_down +5 s)
- status() fragt Microsoft höchstens im vorgegebenen Takt; Endzustände bleiben stehen, ohne erneut zu fragen
- take() gibt die Tokens genau einmal heraus und löscht den Vorgang
- gehört nur dem Nutzer, der ihn gestartet hat (sonst None/FlowError → Route antwortet 404)
- höchstens MAX_OPEN offene je Nutzer; abgelaufene werden beim nächsten Zugriff aufgeräumt
Ein Dienst-Prozess (uvicorn ohne --workers) – deshalb reicht der Speicher; nach Neustart einfach neu anmelden.
"""
from __future__ import annotations

import secrets
import threading
import time

from . import ms_app, oauth_ms

MAX_OPEN = 5
KEEP_DONE = 600          # fertige/fehlgeschlagene Vorgänge noch so lange abrufbar
_FLOWS: dict[str, dict] = {}
_LOCK = threading.Lock()


class NotConfigured(RuntimeError):
    pass


class TooMany(RuntimeError):
    pass


class FlowError(LookupError):
    pass


def _now() -> float:
    return time.monotonic()


def _gc(now: float) -> None:
    for fid, f in list(_FLOWS.items()):
        if now > f["expires"] + KEEP_DONE:
            del _FLOWS[fid]


def start(user: str) -> dict:
    app = ms_app.get()
    if not app["client_id"]:
        raise NotConfigured("Microsoft-Anmeldung ist noch nicht eingerichtet")
    now = _now()
    with _LOCK:
        _gc(now)
        if sum(1 for f in _FLOWS.values() if f["user"] == user and f["state"] == "pending" and now < f["expires"]) \
                >= MAX_OPEN:
            raise TooMany("zu viele offene Anmeldungen")
    d = oauth_ms.device_code(app["client_id"], app["tenant"])
    fid = secrets.token_urlsafe(18)
    with _LOCK:
        _FLOWS[fid] = {"user": user, "app": (app["client_id"], app["tenant"]), "device": d["device_code"],
                       "expires": now + d["expires_in"], "interval": d["interval"], "next": now + d["interval"],
                       "state": "pending", "tokens": None, "error": ""}
    return {"flow_id": fid, "user_code": d["user_code"], "verification_uri": d["verification_uri"],
            "expires_in": d["expires_in"], "interval": d["interval"]}


def _end(f: dict, state: str, error: str = "") -> None:
    f.update(state=state, error=error[:300], device="")


def _public(f: dict) -> dict:
    return {"state": f["state"], **({"error": f["error"]} if f["error"] else {})}


def status(user: str, fid: str) -> dict | None:
    now = _now()
    with _LOCK:
        _gc(now)
        f = _FLOWS.get(fid)
        if not f or f["user"] != user:
            return None
        if f["state"] != "pending":
            return _public(f)
        if now >= f["expires"]:
            _end(f, "expired")
            return _public(f)
        app = ms_app.get()
        if (app["client_id"], app["tenant"]) != f["app"]:
            _end(f, "error", "Die Microsoft-App wurde inzwischen geändert – bitte neu anmelden")
            return _public(f)
        if now < f["next"]:
            return {"state": "pending"}
        f["next"] = now + f["interval"]          # Platz reservieren, bevor (ohne Sperre) gefragt wird
        device = f["device"]
    try:
        r = oauth_ms.poll(app["client_id"], app["tenant"], device)
    except oauth_ms.OAuthError as e:
        with _LOCK:
            if e.code == "network":
                return {"state": "pending"}
            state = {"access_denied": "denied", "authorization_declined": "denied",
                     "expired_token": "expired"}.get(e.code, "error")
            _end(f, state, "" if state != "error" else str(e))
            return _public(f)
    with _LOCK:
        if r["state"] == "slow_down":
            f["interval"] += 5
            f["next"] = now + f["interval"]
            return {"state": "pending"}
        if r["state"] == "done":
            _end(f, "done")
            f["tokens"] = r["tokens"]
            return {"state": "done"}
        return {"state": "pending"}


def take(user: str, fid: str) -> dict:
    """Tokens eines fertigen Vorgangs – genau einmal. Fremd/unbekannt/verbraucht → FlowError(not_found)."""
    with _LOCK:
        f = _FLOWS.get(fid)
        if not f or f["user"] != user:
            raise FlowError("not_found")
        if f["state"] != "done" or not f["tokens"]:
            raise FlowError("not_done")
        del _FLOWS[fid]
        return f["tokens"]
