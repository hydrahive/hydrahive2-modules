"""Chat am Gehäuse (S6): eine Nachricht geht über den Kern-Weg der Kanäle (`communication.router.handle_incoming`) an
Tills Buddy – erst der Butler, dann der Buddy, eigene dauerhafte Session (Kanal „vitrine“, Absender „gehaeuse“). Der Kern
schwärzt die Antwort. Diese Datei ergänzt nur: Textgrenzen, ein Gespräch zur Zeit, `chat_busy` im Datenordner (damit
der Dienst während der Antwort nicht zum Video zurückgeht) und den Verlauf (nur Text, geschwärzt).
"""
from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Callable

log = logging.getLogger(__name__)
CHANNEL, EXTERNAL_ID, SENDER = "vitrine", "gehaeuse", "Gehäuse"
TEXT_MAX, REPLY_MAX, HISTORY_N = 2000, 8000, 20
BUSY_FILE = "chat_busy.json"
NO_REPLY = "(Hydra hat nichts geantwortet.)"
_lock = threading.Lock()


class ChatInvalid(ValueError):
    pass


class ChatBusy(RuntimeError):
    pass


class ChatUnavailable(RuntimeError):
    pass


def _cut(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def _hh_handle():
    from hydrahive.communication.router import handle_incoming
    return handle_incoming


def _hh_event(**kw: Any):
    from hydrahive.communication.base import IncomingEvent
    return IncomingEvent(**kw)


def send(user: str, text, *, data_dir: Path, handle: Callable | None = None, make_event: Callable = _hh_event) -> str:
    if not isinstance(text, str) or not (t := text.strip()) or len(t) > TEXT_MAX:
        raise ChatInvalid(f"text: 1–{TEXT_MAX} Zeichen")
    if not _lock.acquire(blocking=False):
        raise ChatBusy()
    busy = data_dir / BUSY_FILE
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        busy.write_text(json.dumps({"since": time.time()}))
        try:
            event = make_event(channel=CHANNEL, external_user_id=EXTERNAL_ID, target_username=user, text=t, sender_name=SENDER)
            reply = asyncio.run((handle or _hh_handle())(event))
        except RuntimeError as e:
            if "läuft bereits" in str(e):
                raise ChatBusy() from e
            log.warning("Chat am Gehäuse: Kern-Fehler (%s)", type(e).__name__)
            raise ChatUnavailable() from e
        except Exception as e:  # noqa: BLE001 – kein Fehler des Agenten darf die Route umwerfen
            log.warning("Chat am Gehäuse: fehlgeschlagen (%s)", type(e).__name__)
            raise ChatUnavailable() from e
        return _cut(reply, REPLY_MAX) if isinstance(reply, str) and reply.strip() else NO_REPLY
    finally:
        busy.unlink(missing_ok=True)
        _lock.release()


def _text_of(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
                           and isinstance(b.get("text"), str)).strip()
    return ""


def _hh_find(user: str) -> str | None:
    from hydrahive.agents.primary import primary_agent_for
    from hydrahive.db.connection import db
    agent = primary_agent_for(user)
    if not agent:
        return None
    with db() as c:
        row = c.execute("SELECT id FROM sessions WHERE agent_id = ? AND channel = ? AND external_user_id = ? "
                        "ORDER BY updated_at DESC LIMIT 1", (agent["id"], CHANNEL, EXTERNAL_ID)).fetchone()
    return row["id"] if row else None


def _hh_tail(sid: str, n: int) -> list:
    from hydrahive.db.messages import list_tail_for_session
    return list_tail_for_session(sid, limit=n)


def _hh_secrets(user: str) -> set[str]:
    from hydrahive.credentials.redaction import egress_secrets
    return egress_secrets(user, None)


def history(user: str, *, find=_hh_find, tail=_hh_tail, secrets=_hh_secrets, n: int = HISTORY_N) -> list[dict]:
    """Letzte n Beiträge (user/assistant, nur Text) der Gehäuse-Session. Fehlt sie → [] (wird nicht angelegt)."""
    sid = find(user)
    if not sid:
        return []
    out = []
    for m in tail(sid, n * 5):                       # dazwischen liegen Werkzeug-Nachrichten
        if m.role not in ("user", "assistant"):
            continue
        t = _text_of(m.content)
        if t:
            out.append({"role": m.role, "text": t})
    sec = sorted((s for s in secrets(user) if s and len(s) >= 6), key=len, reverse=True)
    for m in out:
        for s in sec:
            m["text"] = m["text"].replace(s, "[REDACTED]")
        m["text"] = _cut(m["text"], REPLY_MAX)
    return out[-n:]
