"""Zug-Ende erkennen und genau eine Version speichern (PLAN-V1.md Entscheidung 3, Baustein 6).

Poller statt Event-Bus: `bus.open()` startet je Lauf einen frischen Kanal, ein vorher angehängter Hörer bekäme nichts.
Je Projekt merkt sich der Poller, ob die Sitzung beim letzten Blick lief und wie die letzte Antwort lautete.
Zug zu Ende = „lief“ → „läuft nicht“, oder (kurzer Zug zwischen zwei Blicken) die letzte Antwort hat sich geändert.
Misslingt das Speichern, bleibt der Zug „offen“ und wird beim nächsten Blick wiederholt.

Bekannte Grenze: Antwortet der Agent in einem sehr kurzen Zug mit exakt demselben Text wie im Zug davor, bemerkt der
Poller ihn nur, wenn er ihn laufen sah. Das kostet höchstens eine Version, nie eine falsche.
"""
from __future__ import annotations

import logging

from . import chat, heal, jobs, state, versions

logger = logging.getLogger(__name__)
INTERVAL_SECONDS = 2.0

_state: dict[str, dict] = {}
_recovered = False


def reset() -> None:
    global _recovered
    _state.clear()
    _recovered = False


def _sessions() -> dict[str, str | None]:
    """Projekt → Sitzung für alle Projekte, die fertig eingerichtet sind."""
    out: dict[str, str | None] = {}
    for row in state.all_rows():
        if row["state"] == "ready":
            out[row["project_id"]] = chat.session_id(row["agent_id"])
    return out


def _is_running(sid: str) -> bool:
    return chat.is_running(sid)


def _last_reply(sid: str) -> str:
    return chat.last_reply(sid)


async def _one(pid: str, sid: str) -> None:
    running = _is_running(sid)
    reply = _last_reply(sid)
    st = _state.get(pid)
    if st is None:                                   # erster Blick: nur Ausgangslage merken (auch nach Neustart)
        _state[pid] = {"running": running, "sig": reply, "pending": False}
        return
    if running:
        st["running"] = True
        return
    if st["running"] or reply != st["sig"]:
        st["pending"] = True
    st["running"] = False
    if not st["pending"]:
        return
    await versions.commit_turn(pid, reply, kind="turn")      # wirft → pending bleibt, nächster Blick versucht es neu
    st["pending"] = False
    st["sig"] = reply
    if not heal.consume_fix_turn(pid):                       # ein Zug des Nutzers (nicht der Reparatur) = frischer Start
        heal.reset_project(pid)


def _recover_once() -> None:
    """Halbe Einrichtungen nach einem Neustart als unterbrochen markieren – hier statt in `register()`, weil der Kern
    `register()` VOR den Migrationen aufruft (an hydratest 5.11. gemessen: „no such table: module_vibe_projects“)."""
    global _recovered
    if _recovered:
        return
    _recovered = True
    try:
        jobs.recover_after_restart()
    except Exception:                                # noqa: BLE001
        logger.exception("Vibe: unterbrochene Aufträge nicht lesbar")


async def poll() -> None:
    """Ein Durchlauf für alle Projekte. Ein Fehler bei einem Projekt hält die anderen nicht auf."""
    _recover_once()
    try:
        sessions = _sessions()
    except Exception:                                # noqa: BLE001
        logger.exception("Vibe-Wächter: Projektliste nicht lesbar")
        return
    for pid in [p for p in _state if p not in sessions]:
        del _state[pid]
    for pid, sid in sessions.items():
        if not sid:
            continue
        try:
            await _one(pid, sid)
        except Exception:                            # noqa: BLE001
            logger.exception("Vibe-Wächter: Projekt %s", pid)
