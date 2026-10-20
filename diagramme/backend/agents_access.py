"""Für alle Agenten freischalten (Spec §12.4): Werkzeuge ergänzen, merken wer neu dazukam, nur dort zurücknehmen."""
from __future__ import annotations

import json
import logging
import os

from hydrahive.agents import config as agent_config
from hydrahive.agents._config_utils import list_all

from . import store

logger = logging.getLogger(__name__)
TOOLS = ("diagramm_erstellen", "diagramm_hilfe", "diagramm_liste")
FILE = "_freischaltung.json"


def _known_tools() -> set[str]:
    from hydrahive.tools import REGISTRY
    return {t for t in TOOLS if t in REGISTRY}


def _scope() -> set[str] | None:
    """Welche Agenten betroffen sind – None = alle (Tests grenzen das ein)."""
    return None


def _agents(only: set[str] | None) -> list[dict]:
    limit = only if only is not None else _scope()
    return [a for a in list_all() if limit is None or a.get("id") in limit]


def _load() -> list[str]:
    path = store.root() / FILE
    try:
        return list(json.loads(path.read_text()).get("agents", []))
    except (OSError, ValueError):
        return []


def _save(ids: list[str]) -> None:
    root = store.root()
    root.mkdir(parents=True, exist_ok=True)
    tmp = root / f".{FILE}.tmp"
    tmp.write_text(json.dumps({"agents": sorted(set(ids))}, indent=1))
    os.replace(tmp, root / FILE)


def status(*, only: set[str] | None = None) -> dict:
    agents = _agents(only)
    return {"total": len(agents), "with_tool": sum("diagramm_erstellen" in (a.get("tools") or []) for a in agents),
            "unlocked_by_us": len(_load())}


def unlock(*, only: set[str] | None = None) -> dict:
    wanted = [t for t in TOOLS if t in _known_tools()]
    remembered = _load()
    changed = errors = 0
    for a in _agents(only):
        tools = list(a.get("tools") or [])
        if a.get("status") == "disabled" or "diagramm_erstellen" in tools:
            continue
        try:
            agent_config.update(a["id"], tools=tools + [t for t in wanted if t not in tools])
        except Exception as e:  # noqa: BLE001 – ein Agent darf die anderen nicht aufhalten
            logger.warning("Diagramme: Freischalten für Agent %s fehlgeschlagen: %s", a.get("id"), e)
            errors += 1
            continue
        remembered.append(a["id"])
        changed += 1
    _save(remembered)
    return {"changed": changed, "errors": errors}


def relock() -> dict:
    changed = errors = 0
    for aid in _load():
        cfg = agent_config.get(aid)
        if not cfg:
            continue
        try:
            agent_config.update(aid, tools=[t for t in cfg.get("tools") or [] if t not in TOOLS])
        except Exception as e:  # noqa: BLE001
            logger.warning("Diagramme: Zurücknehmen für Agent %s fehlgeschlagen: %s", aid, e)
            errors += 1
            continue
        changed += 1
    _save([])
    return {"changed": changed, "errors": errors}
