"""Dünne Hülle um die Sitzung des Vibe-Chats im Kern (PLAN-V1.md Baustein 6). Alles Lesen, nichts Gefährliches.

Eine Vibe-Sitzung gehört dem Agenten des Projekts und trägt `metadata.embedded_in = "vibe"`. Kern-Importe sind
nachgeladen, damit die Datei ohne Kern importierbar bleibt (Tests ersetzen die Funktionen im Wächter/Heiler).
"""
from __future__ import annotations

_TAIL = 40


def session_id(agent_id: str) -> str | None:
    """Jüngste Vibe-Sitzung des Agenten (bevorzugt mit Markierung), sonst keine."""
    from hydrahive.db import sessions as sessions_db
    found = sessions_db.list_for_agent(agent_id, limit=20)
    marked = [s for s in found if (s.metadata or {}).get("embedded_in") == "vibe"]
    pick = (marked or found or [None])[0]
    return pick.id if pick else None


def is_running(sid: str) -> bool:
    from hydrahive.runner.concurrency import is_running as running
    return bool(running(sid))


def _text(content) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return " ".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text").strip()
    return ""


def last_reply(sid: str) -> str:
    """Text der letzten Assistenten-Nachricht, die Text enthält (reine Werkzeug-Runden zählen nicht)."""
    from hydrahive.db import messages as messages_db
    for m in reversed(messages_db.list_tail_for_session(sid, _TAIL)):
        if m.role == "assistant":
            t = _text(m.content)
            if t:
                return t
    return ""


def say(sid: str, text: str) -> None:
    """Eine Nachricht des Assistenten in den Chat legen (z. B. „Ich komme nicht weiter“) und offene Tabs anstoßen."""
    from hydrahive.api._session_broadcast import broadcaster
    from hydrahive.db import messages as messages_db
    messages_db.append(sid, "assistant", [{"type": "text", "text": text}], metadata={"vibe": "notice"})
    broadcaster.broadcast(sid, '{"t":"activity"}')
