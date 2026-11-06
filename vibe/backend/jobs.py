"""Auftrag „Projekt anlegen und einrichten“ mit sichtbarem Fortschritt (PLAN-V1.md Baustein 6).

Zustände: new → setting_up → ready; bei Fehler failed (mit Code und Schritt). Ein gescheitertes Projekt bleibt
stehen (Container, Agent): der Nutzer sieht, wo es hing, kann „Nochmal versuchen“ (ab dem Fehlerschritt) oder löschen.
Je Projekt läuft höchstens ein Auftrag. Nach einem Neustart gilt ein halber Auftrag als unterbrochen.
"""
from __future__ import annotations

import logging

from . import container, projects, provision, state

logger = logging.getLogger(__name__)

_busy: set[str] = set()


class JobError(RuntimeError):
    def __init__(self, code: str, step: str = "", detail: str = ""):
        super().__init__(code)
        self.code = code
        self.step = step
        self.detail = detail


def reset() -> None:
    _busy.clear()


async def _setup(pid: str, *, start_at: str = "") -> None:
    """Einrichtung mit Zustandsführung. Wirft JobError, das Projekt steht dann auf failed."""
    _busy.add(pid)
    state.set_state(pid, "setting_up")
    try:
        await provision.setup(pid, lambda step: state.set_progress(pid, step), start_at=start_at)
    except provision.SetupError as exc:
        state.set_state(pid, "failed", error_code=exc.code, error_step=exc.step, error_detail=exc.detail)
        raise JobError(exc.code, exc.step, exc.detail) from None
    except Exception:                                    # noqa: BLE001 – Grenze des Auftrags: lesbar festhalten
        logger.exception("Vibe: Einrichtung von %s gescheitert", pid)
        step = (state.get_row(pid) or {}).get("progress", "")
        state.set_state(pid, "failed", error_code="vibe_setup_failed", error_step=step)
        raise JobError("vibe_setup_failed", step) from None
    else:
        state.set_state(pid, "ready")
    finally:
        _busy.discard(pid)


async def create_and_setup(*, admin: str, name: str, model: str,
                           limits: container.Limits | None = None) -> dict:
    out = await projects.create(admin=admin, name=name, model=model, limits=limits)
    await _setup(out["project_id"])
    return out


async def retry_setup(project_id: str, *, owner: str) -> None:
    row = state.get_row(project_id)
    if row is None or row["owner"] != owner:
        raise JobError("vibe_project_not_found")
    if project_id in _busy:
        raise JobError("vibe_busy")
    if row["state"] != "failed":
        raise JobError("vibe_not_failed")
    await _setup(project_id, start_at=row["error_step"] if row["error_step"] in {s.key for s in provision.STEPS} else "")


async def find_orphans() -> dict:
    """Waisen melden, NIE löschen: Container mit Vibe-Namen ohne Datenzeile und Datenzeilen ohne Container. Fremde
    Container (anderer Name, Labor, …) kommen nie vor."""
    rows = {r["project_id"]: r for r in state.all_rows()}
    have = await container.all_names()
    known = {r["container"] for r in rows.values()}
    return {"containers": sorted(have - known),
            "rows": sorted(pid for pid, r in rows.items() if r["container"] not in have)}


def recover_after_restart() -> None:
    """Nach einem Neustart läuft kein Auftrag mehr: Halbes → failed (unterbrochen), Fertiges bleibt."""
    for row in state.all_rows():
        if row["state"] == "setting_up":
            state.set_state(row["project_id"], "failed", error_code="vibe_interrupted", error_step=row["progress"])
