"""Einblendungen als Dateien: <daten>/inbox/<zeit>-<id>.json. HydraHive legt ab, der Dienst zeigt und räumt auf.

Keine Netzwerk-Schnittstelle – nur Dateien im Modul-Datenordner (wie config.json).
S3: Eine Meldung ist bis `expires` als Karte auf dem Video (solange ungelesen) und bleibt 24 h nach `created` für die
Statuszentrale erhalten: ungelesen unter „Neu“, gelesen (`read` gesetzt) im Verlauf. Danach wird die Datei gelöscht.
"""
from __future__ import annotations

import json
import re
import secrets
import time
from pathlib import Path

KINDS = ("info", "success", "warning", "error")
MAX_TEXT, MAX_TITLE, MAX_VISIBLE, MAX_FILES = 280, 60, 3, 100
DEFAULT_SECONDS, ERROR_SECONDS, MERGE_SECONDS = 15, 600, 60
KEEP_SECONDS = 24 * 3600
_CTRL = re.compile(r"[\x00-\x1f\x7f]")


class InboxError(ValueError):
    pass


def _clean(s: str, limit: int) -> str:
    s = re.sub(r"\s+", " ", _CTRL.sub(lambda m: " " if m.group() in "\n\t\r" else "", str(s or ""))).strip()
    return s if len(s) <= limit else s[: limit - 1] + "…"


def _dir(data: Path) -> Path:
    return data / "inbox"


def _load(p: Path) -> dict | None:
    try:
        m = json.loads(p.read_text())
        return m if isinstance(m, dict) and "id" in m else None
    except (OSError, ValueError):
        return None


def _all(data: Path, now: float | None = None) -> list[tuple[Path, dict]]:
    """Alle Meldungen der letzten 24 h; ältere und kaputte Dateien werden dabei gelöscht."""
    now = time.time() if now is None else now
    out = []
    try:
        files = sorted(_dir(data).glob("*.json"))
    except OSError:
        return []
    for p in files:
        m = _load(p)
        if m is None or now - float(m.get("created", 0)) > KEEP_SECONDS:
            p.unlink(missing_ok=True)
            continue
        out.append((p, m))                                  # Dateien vor S3 haben kein "read" → gelten als ungelesen
    return out


def _write(path: Path, m: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(m, ensure_ascii=False))
    tmp.replace(path)


def _default_seconds(data: Path) -> int:
    from . import config                                    # spät: config braucht inbox nicht
    return int(config.load(data).get("message_seconds") or DEFAULT_SECONDS)


def post(data: Path, text: str, *, kind: str = "info", title: str = "", seconds: int | None = None,
         source: str = "", now: float | None = None) -> dict:
    now = time.time() if now is None else now
    text, title = _clean(text, MAX_TEXT), _clean(title, MAX_TITLE)
    if not text:
        raise InboxError("text: leer")
    if kind not in KINDS:
        raise InboxError(f"kind: eine von {', '.join(KINDS)}")
    if seconds is None:
        seconds = ERROR_SECONDS if kind == "error" else _default_seconds(data)
    if not 3 <= int(seconds) <= 600:
        raise InboxError("seconds: 3 bis 600")
    d = _dir(data)
    d.mkdir(parents=True, exist_ok=True)
    for p, m in _all(data, now):                            # gleiche Nachricht kurz hintereinander → zählen
        if m["text"] == text and m["kind"] == kind and now - m["created"] <= MERGE_SECONDS:
            m.update(count=m.get("count", 1) + 1, created=now, expires=now + int(seconds), read=None)  # wieder neu
            _write(p, m)
            return m
    m = {"id": secrets.token_hex(6), "text": text, "title": title, "kind": kind, "count": 1,
         "created": now, "expires": now + int(seconds), "source": _clean(source, 40), "read": None}
    _write(d / f"{now:017.6f}-{m['id']}.json", m)
    files = sorted(d.glob("*.json"))
    for p in files[: max(0, len(files) - MAX_FILES)]:      # Ordner begrenzen: älteste fallen raus
        p.unlink(missing_ok=True)
    return m


def active(data: Path, *, now: float | None = None) -> list[dict]:
    """Karten fürs Video: noch nicht abgelaufen und ungelesen, neueste zuerst."""
    now = time.time() if now is None else now
    out = [m for _, m in _all(data, now) if m.get("expires", 0) > now and not m.get("read")]
    return sorted(out, key=lambda m: m["created"], reverse=True)


def visible(data: Path, *, now: float | None = None) -> list[dict]:
    return active(data, now=now)[:MAX_VISIBLE]


def recent(data: Path, *, now: float | None = None) -> tuple[list[dict], list[dict]]:
    """Für die Statuszentrale: (ungelesen, gelesen) der letzten 24 h, je neueste zuerst."""
    msgs = sorted((m for _, m in _all(data, now)), key=lambda m: m["created"], reverse=True)
    return [m for m in msgs if not m.get("read")], [m for m in msgs if m.get("read")]


def mark_read(data: Path, msg_id: str, *, now: float | None = None) -> bool:
    """Meldung als gelesen markieren. Die ID wird nur verglichen, nie zu einem Pfad zusammengesetzt."""
    now = time.time() if now is None else now
    for p, m in _all(data, now):
        if m["id"] == msg_id:
            m["read"] = now
            _write(p, m)
            return True
    return False


def dismiss(data: Path, msg_id: str, *, now: float | None = None) -> bool:
    """Entfernt die Nachricht mit dieser ID (Cockpit). Die ID wird nur verglichen, nie zu einem Pfad zusammengesetzt."""
    for p, m in _all(data, now):
        if m["id"] == msg_id:
            p.unlink(missing_ok=True)
            return True
    return False
