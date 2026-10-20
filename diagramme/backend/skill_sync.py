"""Modul-Skill als System-Skill bereitstellen (Kern kann keine Modul-Skills registrieren).

Nutzt die Sync-Logik des Kerns (skills/_defaults_sync.py): fehlt → kopieren,
frühere Auslieferung → ersetzen, Admin-Änderung → stehen lassen. Läuft beim
Laden des Moduls; ein Fehler darf das Modul nie am Start hindern.

Herkunft: Kopie von mining/backend/skill_sync.py (Module importieren nicht voneinander).
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)
SKILLS_SRC = Path(__file__).resolve().parents[1] / "skills"


def install() -> None:
    try:
        from hydrahive.skills._defaults_sync import sync_defaults
        from hydrahive.skills._paths import system_dir
    except ImportError:  # älterer Kern ohne Sync — Skill dann von Hand übernehmen
        logger.info("Diagramme: Kern ohne Skill-Sync, Skill diagramme nicht installiert")
        return
    try:
        sync_defaults(SKILLS_SRC, system_dir())
    except OSError:
        logger.exception("Diagramme: Skill diagramme nicht installiert")
