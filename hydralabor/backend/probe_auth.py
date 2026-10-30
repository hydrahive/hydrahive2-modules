"""L3: Anmeldung an der Durchreiche :8443 (PLAN-L3.md „Anmeldung“, Muster Kern _agentlink_dashboard.py).

Das HydraHive-Login liegt im Browser im sessionStorage und wird beim Öffnen von :8443 nicht mitgeschickt. Deshalb:
- `POST /api/modules/hydralabor/probe/open` (nur Admins) gibt ein Einmal-Ticket (60 s) als Link auf :8443.
- `GET  /api/module-device/hydralabor/probe/login?t=…` löst es ein und setzt ein eigenes Cookie (HttpOnly, Secure,
  SameSite=Strict, 8 h), signiert mit einem zweckgebundenen Schlüssel. Kein Login-Token, öffnet keine HydraHive-API.
- `GET  /api/module-device/hydralabor/probe/auth` prüft das Cookie für nginx (auth_request): Signatur, Ablauf und ob
  der Nutzer NOCH Admin ist. 204 oder 401.
Die beiden letzten laufen über den Geräte-Weg des Kerns (ohne HydraHive-Login, mit Bremse je Client-Adresse).
Der Kern läuft mit einem Prozess (uvicorn ohne --workers) – Tickets im Speicher genügen.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import time

COOKIE = "hh_labor_probe"
MAX_AGE = 8 * 3600
TICKET_TTL = 60
MAX_TICKETS = 50
PORT = 8443
_CONTEXT = b"hydrahive-labor-probe-v1"
_MAX_LEN = 512
_HOST = re.compile(r"^(\[[0-9a-fA-F:.]+\]|[A-Za-z0-9.-]{1,253})(:\d{1,5})?$")
_tickets: dict[str, tuple[str, float]] = {}


def _key() -> bytes:
    from hydrahive.settings import settings
    return hmac.new(settings.secret_key.encode(), _CONTEXT, hashlib.sha256).digest()


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def probe_url(host_header: str, ticket: str) -> str | None:
    """Link auf die Durchreiche am selben Namen, unter dem der Admin HydraHive gerade nutzt. None = komischer Host."""
    m = _HOST.match(host_header or "")
    if not m:
        return None
    return f"https://{m.group(1)}:{PORT}/__labor_login?t={ticket}"


def new_ticket(user_id: str) -> str:
    now = time.time()
    for t, (_, exp) in list(_tickets.items()):
        if exp < now:
            del _tickets[t]
    while len(_tickets) >= MAX_TICKETS:
        del _tickets[next(iter(_tickets))]          # ältestes zuerst (dict behält die Reihenfolge)
    t = secrets.token_urlsafe(32)
    _tickets[t] = (user_id, now + TICKET_TTL)
    return t


def redeem(ticket: str) -> str | None:
    """Einmal: liefert user_id, wenn das Ticket gilt und der Nutzer noch Admin ist."""
    entry = _tickets.pop(ticket, None)
    if not entry or entry[1] < time.time():
        return None
    return entry[0] if _is_admin(entry[0]) else None


def issue_cookie(user_id: str) -> str:
    body = _b64(json.dumps({"uid": user_id, "exp": int(time.time()) + MAX_AGE}).encode())
    sig = _b64(hmac.new(_key(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}"


def _is_admin(uid: str) -> bool:
    from hydrahive.api.middleware import users
    current = users.get_by_id(uid)
    return bool(current and current.get("role") == "admin")


def admin_from(cookie: str | None) -> bool:
    if not cookie or len(cookie) > _MAX_LEN or cookie.count(".") != 1:
        return False
    body, sig = cookie.split(".")
    expected = _b64(hmac.new(_key(), body.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(sig, expected):
        return False
    try:
        data = json.loads(_unb64(body))
        uid, exp = data["uid"], int(data["exp"])
    except (ValueError, KeyError, TypeError):
        return False
    if exp < time.time() or not isinstance(uid, str):
        return False
    return _is_admin(uid)
