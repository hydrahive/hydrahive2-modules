"""Skill „rechtsbrief“ (Plan L3 Schritt 6): als System-Skill bereitgestellt (Kern lädt keine Modul-Skills, Muster wie
mining/diagramme), Anweisung verweist darauf, Inhalt nennt die Pflichtregeln."""
from __future__ import annotations

from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[1] / "skills" / "rechtsbrief.md"


def test_skill_file_frontmatter_and_rules():
    text = SKILL.read_text(encoding="utf-8")
    assert text.startswith("---\nname: rechtsbrief\n")
    for must in ("legal_letter_draft", "legal_check_letter", "legal_propose_letter", "legal_norm", "legal_deadline",
                 "Einwurf-Einschreiben", "Datum", "keine Rechtsberatung", "Anwalt"):
        assert must.lower() in text.lower(), must
    for t in ("mangelanzeige", "mahnung", "widerspruch", "kuendigung", "akteneinsicht", "anwalt"):
        assert t in text, t


def test_history_contains_current_version():
    import hashlib
    import json
    hist = json.loads((SKILL.parent / "_history.json").read_text())
    assert hashlib.sha256(SKILL.read_bytes()).hexdigest() in hist["rechtsbrief.md"]


def test_install_copies_to_system_dir(tmp_path, monkeypatch):
    from backend import skill_sync
    from hydrahive.skills import _paths
    monkeypatch.setattr(_paths, "system_dir", lambda: tmp_path / "system")
    skill_sync.install()
    assert (tmp_path / "system" / "rechtsbrief.md").read_bytes() == SKILL.read_bytes()


def test_install_never_raises(monkeypatch):
    from backend import skill_sync
    from hydrahive.skills import _defaults_sync

    def boom(*a, **k):
        raise OSError("Platte voll")
    monkeypatch.setattr(_defaults_sync, "sync_defaults", boom)
    skill_sync.install()          # darf das Modul nicht am Start hindern


@pytest.mark.parametrize("word", ["rechtsbrief", "load_skill"])
def test_agent_prompt_points_to_skill(word):
    from backend import agent_profile
    assert word in agent_profile.system_prompt("T", "", "Niedersachsen")


def test_register_installs_skill():
    import inspect

    import backend
    assert "skill_sync.install()" in inspect.getsource(backend.register)
