"""NAV_AREA.de.md: Jedes Modul mit Menüeintrag trägt seinen Bereich (nav.area) selbst ein.

Läuft ohne HydraHive-Core: liest nur frontend/index.tsx der Module (stdlib + pytest).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

# Erlaubte Kennungen – müssen zu frontend/src/features/startdesk/areas.ts im Kern passen.
AREAS = {"medien", "schreiben", "wissen", "agenten", "kommunikation", "zuhause", "freizeit", "verwaltung"}

# Von Till am 24.10.2026 freigegebene Zuordnung (wie die Kern-Tabelle aus hydrahive2.0#618).
EXPECTED = {
    "studio": "medien", "atelier": "medien", "videoeditor": "medien", "tonstudio": "medien", "musicplayer": "medien",
    "radiostream": "medien",
    "storyteller": "schreiben", "notizbuch": "schreiben", "scratchpad": "schreiben", "diagramme": "schreiben",
    "blueprint": "schreiben",
    "deepresearch": "wissen", "archiver": "wissen", "legal": "wissen", "opentor": "wissen",
    "tickets": "agenten", "hydralabor": "agenten",
    "mailbox": "kommunikation", "telephony": "kommunikation", "voice": "kommunikation",
    "haushaltsbuch": "zuhause", "patientenakte": "zuhause", "homeassistant": "zuhause", "cryptoboard": "zuhause",
    "mining": "zuhause", "vitrine": "zuhause", "network": "zuhause",
    "mediacenter": "freizeit", "boardgames": "freizeit", "minigames": "freizeit", "vr": "freizeit",
    "ai-security": "verwaltung",
}
WITHOUT_AREA = {"example", "tasks"}

_NAV = re.compile(r"export const nav\s*=\s*\[(.*?)\]\s*(?:as const)?\s*\n", re.S)
_ENTRY = re.compile(r"\{[^{}]*?path:\s*\"[^\"]+\"[^{}]*\}", re.S)
_AREA = re.compile(r"\barea:\s*\"([^\"]*)\"")


def _modules() -> list[str]:
    return sorted(p.parent.parent.name for p in ROOT.glob("*/frontend/index.ts*"))


def _nav_entries(module: str) -> list[str]:
    src = next((ROOT / module / "frontend").glob("index.ts*")).read_text(encoding="utf-8")
    m = _NAV.search(src)
    return _ENTRY.findall(m.group(1)) if m else []


def test_every_module_is_listed():
    """Ein neues Modul muss hier (und in NAV_AREA.de.md) bewusst einsortiert werden."""
    assert set(_modules()) == set(EXPECTED) | WITHOUT_AREA


@pytest.mark.parametrize("module", sorted(EXPECTED))
def test_module_has_its_area(module):
    entries = _nav_entries(module)
    assert entries, f"{module}: kein nav-Eintrag gefunden"
    for entry in entries:
        found = _AREA.findall(entry)
        assert found == [EXPECTED[module]], f"{module}: area {found!r}, erwartet {EXPECTED[module]!r}"


@pytest.mark.parametrize("module", sorted(WITHOUT_AREA))
def test_module_without_area(module):
    for entry in _nav_entries(module):
        assert not _AREA.search(entry), f"{module}: soll keine area haben"


def test_only_known_area_ids():
    used = {a for mod in _modules() for e in _nav_entries(mod) for a in _AREA.findall(e)}
    assert used <= AREAS, used - AREAS
    assert set(EXPECTED.values()) <= AREAS
