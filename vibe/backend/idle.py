"""Ruhe: nach 30 min ohne Nutzung den Container stoppen, vor jeder Anfrage wecken (SPEC.md, PLAN-V1.md Baustein 7).

Der Kern startet einen gestoppten Container NICHT von selbst (tools/_launcher_container.py: „Container aus → Fehler“),
darum weckt das Modul ihn vor jedem Agentenlauf. Der Dev-Server ist ein systemd-Dienst (`enable --now`) und startet mit
dem Container; `wake` prüft das nach.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from . import chat, container, incus, state

logger = logging.getLogger(__name__)
IDLE_MINUTES = 30
SWEEP_SECONDS = 60
WAKE_TIMEOUT = 60
_DEV_UP = ["exec", "{name}", "--", "bash", "-c", "curl -s -o /dev/null -m 1 http://127.0.0.1:5173/"]


def _busy(project_id: str) -> bool:
    """Läuft gerade ein Agentenzug in der Vibe-Sitzung des Projekts? Dann bleibt der Container wach."""
    row = state.get_row(project_id)
    sid = chat.session_id(row["agent_id"]) if row else None
    return bool(sid and chat.is_running(sid))


def _idle_since(row: dict) -> timedelta | None:
    try:
        last = datetime.strptime(row["last_used_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except (ValueError, TypeError):
        return None
    return datetime.now(UTC) - last


async def _sweep_one(row: dict) -> None:
    pid = row["project_id"]
    age = _idle_since(row)
    if age is None or age < timedelta(minutes=IDLE_MINUTES):
        return
    if _busy(pid) or not await container.running(pid):
        return
    await container.stop(pid)
    state.set_state(pid, "sleeping")
    logger.info("Vibe: Container von %s nach %d min Leerlauf gestoppt", pid, IDLE_MINUTES)


async def sweep() -> None:
    """Ein Durchlauf. Nur fertig eingerichtete Projekte; ein Fehler bei einem hält die anderen nicht auf."""
    try:
        rows = [r for r in state.all_rows() if r["state"] == "ready"]
    except Exception:                                      # noqa: BLE001
        logger.exception("Vibe-Leerlauf: Projektliste nicht lesbar")
        return
    for row in rows:
        try:
            await _sweep_one(row)
        except Exception:                                  # noqa: BLE001
            logger.exception("Vibe-Leerlauf: Projekt %s", row["project_id"])


async def wake(project_id: str) -> None:
    """Container starten und warten, bis er antwortet (WAKE_TIMEOUT s). Sonst `vibe_container_down`. Ein laufender
    Container wird nicht angefasst. Aktualisiert die letzte Nutzung."""
    name = container.name_for(project_id)
    row = state.get_row(project_id)
    if row is None:
        raise container.VibeError("vibe_project_not_found")
    state.touch(project_id)
    if await container.running(project_id):
        return
    try:
        async def _up() -> None:
            await container.start(project_id)
            await container.wait_for_address(project_id)
            await incus.run(*[name if a == "{name}" else a for a in _DEV_UP], timeout=10)
        await asyncio.wait_for(_up(), WAKE_TIMEOUT)
    except (TimeoutError, container.VibeError):
        raise container.VibeError("vibe_container_down") from None
    if row["state"] == "sleeping":
        state.set_state(project_id, "ready")
