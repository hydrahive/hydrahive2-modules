"""Skill labor-review: liegt im Modul, wird als System-Skill bereitgestellt (Muster legal/backend/skill_sync.py)."""
from __future__ import annotations

from backend import skill_sync


def test_skill_datei_gueltig():
    from hydrahive.skills.models import parse
    text = (skill_sync.SKILLS_SRC / "labor-review.md").read_text(encoding="utf-8")
    s = parse(text, scope="system", owner="system", fallback_name="labor-review")
    assert s.name == "labor-review" and s.description and s.when_to_use
    for must in ("200 Zeilen", "pytest", "ruff", "Tests zuerst"):
        assert must in s.body


def test_install_legt_system_skill_an(setup_test_env):
    from hydrahive.skills import _paths
    target = _paths.system_dir() / "labor-review.md"
    existed = target.exists()
    skill_sync.install()
    assert target.exists()
    if not existed:
        target.unlink()


def test_install_fehler_bricht_nichts(setup_test_env, monkeypatch):
    from hydrahive.skills import _defaults_sync

    def boom(*a, **k):
        raise OSError("voll")
    monkeypatch.setattr(_defaults_sync, "sync_defaults", boom)
    skill_sync.install()


def test_history_datei_da_damit_spaetere_fassungen_ankommen():
    import json
    hist = json.loads((skill_sync.SKILLS_SRC / "_history.json").read_text(encoding="utf-8"))
    assert set(hist) == {p.name for p in skill_sync.SKILLS_SRC.glob("*.md")}
    assert all(isinstance(v, list) for v in hist.values())


def test_install_ohne_warnung(setup_test_env, caplog):
    import logging
    with caplog.at_level(logging.WARNING):
        skill_sync.install()
    assert "_history.json" not in caplog.text
