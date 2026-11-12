"""Manifest, Menüeintrag und Hub-Eintrag müssen zusammenpassen."""
from __future__ import annotations

import json
import re
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parents[1]


def _manifest() -> dict:
    return json.loads((MODULE_DIR / "manifest.json").read_text(encoding="utf-8"))


def test_modul_heisst_ideen_und_behaelt_die_id():
    manifest = _manifest()
    assert manifest["id"] == "scratchpad"
    assert manifest["name"] == "Ideen"
    assert manifest["default_agent_tools"] is True
    assert "Zettel" not in manifest["description"] and "Notizzettel" not in manifest["description"]


def test_version_ist_mindestens_2():
    assert int(_manifest()["version"].split(".")[0]) >= 2


def test_symbol_ist_im_manifest_und_im_menue_dasselbe():
    index = (MODULE_DIR / "frontend" / "index.tsx").read_text(encoding="utf-8")
    icons = re.findall(r'icon:\s*"([^"]+)"', index)
    assert icons == [_manifest()["icon"]] == ["Lightbulb"]


def test_hub_nennt_das_modul_wie_das_manifest():
    hub = json.loads((MODULE_DIR.parent / "hub.json").read_text(encoding="utf-8"))
    entry = next(m for m in hub["modules"] if m["id"] == "scratchpad")
    assert entry["name"] == _manifest()["name"]
    assert entry["path"] == "scratchpad"
