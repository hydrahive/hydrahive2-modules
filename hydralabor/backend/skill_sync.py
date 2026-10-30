"""Modul-Skill labor-review als System-Skill bereitstellen (Muster legal/backend/skill_sync.py).

Nutzt die Sync-Logik des Kerns (skills/_defaults_sync.py): fehlt → kopieren, frühere Auslieferung → ersetzen,
Admin-Änderung → stehen lassen. Ein Fehler darf das Modul nie am Start hindern.
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)
SKILLS_SRC = Path(__file__).resolve().parents[1] / "skills"


def install() -> None:
    try:
        from hydrahive.skills import _defaults_sync, _paths
        _defaults_sync.sync_defaults(SKILLS_SRC, _paths.system_dir())
    except Exception:
        logger.exception("Hydra-Labor: Skill labor-review nicht installiert")
