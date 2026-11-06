"""Anmeldung an der Vorschau-Durchreiche :8444 (PLAN-V1.md Entscheidung 7/8; Muster hydralabor probe_auth.py).

HydraHive meldet per Bearer im sessionStorage an – beim Aufruf von :8444 geht davon nichts mit. Darum:
- `POST /api/modules/vibe/preview/open` (Admin) gibt ein Einmal-Ticket (60 s) als Link auf :8444.
- `GET /api/module-device/vibe/preview/login?t=…` löst es ein und setzt das Cookie `hh_vibe_preview` (HttpOnly, Secure,
  SameSite=None, 8 h), signiert mit einem zweckgebundenen Schlüssel. Im Cookie steht, WELCHES Projekt gemeint ist.
- `GET /api/module-device/vibe/preview/auth` prüft das Cookie für nginx (auth_request) und nennt nginx das Ziel.

SameSite=None, weil das iframe `sandbox` ohne `allow-same-origin` trägt: Für den Browser ist es dann „fremd“, ein
Strict-Cookie ginge nicht mit (Messung 5.11.: dann scheitert der WebSocket der Vorschau). Das Cookie öffnet keine
HydraHive-API; es gilt nur für die Durchreiche. Der Kern läuft mit einem Prozess – Tickets im Speicher genügen.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import time

COOKIE = "hh_vibe_preview"
MAX_AGE = 8 * 3600
TICKET_TTL = 60
MAX_TICKETS = 50
PORT = 8444
_CONTEXT = b"hydrahive-vibe-preview-v1"
_MAX_LEN = 600
_HOST = re.compile(r"^(\[[0-9a-fA-F:.]+\]|[A-Za-z0-9.-]{1,253})(:\d{1,5})?$")
_tickets: dict[str, tuple[str, str, float]] = {}


def _key() -> bytes:
    from hydrahive.settings import settings
    return hmac.new(settings.secret_key.encode(), _CONTEXT, hashlib.sha256).digest()


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def preview_url(host_header: str, ticket: str) -> str | None:
    """Link auf die Durchreiche am selben Namen, unter dem der Admin HydraHive gerade nutzt. None = komischer Host."""
    m = _HOST.match(host_header or "")
    return f"https://{m.group(1)}:{PORT}/__vibe_login?t={ticket}" if m else None


def new_ticket(user_id: str, project_id: str) -> str:
    now = time.time()
    for t, (_, _, exp) in list(_tickets.items()):
        if exp < now:
            del _tickets[t]
    while len(_tickets) >= MAX_TICKETS:
        del _tickets[next(iter(_tickets))]          # ältestes zuerst (dict behält die Reihenfolge)
    t = secrets.token_urlsafe(32)
    _tickets[t] = (user_id, project_id, now + TICKET_TTL)
    return t


def _owner_ok(uid: str, project_id: str) -> bool:
    """Nutzer ist NOCH Admin und das Projekt gehört ihm."""
    from hydrahive.api.middleware import users
    from . import state
    current = users.get_by_id(uid)
    row = state.get_row(project_id)
    return bool(current and current.get("role") == "admin" and row and row["owner"] == current.get("username"))


def redeem(ticket: str) -> tuple[str, str] | None:
    """Einmal: liefert (user_id, project_id), wenn das Ticket gilt und die Rechte noch stimmen."""
    entry = _tickets.pop(ticket, None)
    if not entry or entry[2] < time.time():
        return None
    return (entry[0], entry[1]) if _owner_ok(entry[0], entry[1]) else None


def issue_cookie(user_id: str, project_id: str) -> str:
    body = _b64(json.dumps({"uid": user_id, "pid": project_id, "exp": int(time.time()) + MAX_AGE}).encode())
    return f"{body}.{_b64(hmac.new(_key(), body.encode(), hashlib.sha256).digest())}"


def project_from(cookie: str | None) -> str | None:
    """Projekt-ID aus einem gültigen Cookie (Signatur, Ablauf, Admin-Recht, Besitz) – sonst None."""
    if not cookie or len(cookie) > _MAX_LEN or cookie.count(".") != 1:
        return None
    body, sig = cookie.split(".")
    if not hmac.compare_digest(sig, _b64(hmac.new(_key(), body.encode(), hashlib.sha256).digest())):
        return None
    try:
        data = json.loads(_unb64(body))
        uid, pid, exp = data["uid"], data["pid"], int(data["exp"])
    except (ValueError, KeyError, TypeError):
        return None
    if exp < time.time() or not isinstance(uid, str) or not isinstance(pid, str):
        return None
    return pid if _owner_ok(uid, pid) else None
