"""Baustein 1: Manifest, Zugriff und Migration des Moduls Vibe (PLAN-V1.md)."""
from __future__ import annotations

import json
from pathlib import Path

from hydrahive.db.connection import db

MODULE_DIR = Path(__file__).resolve().parents[1]
REPO = MODULE_DIR.parent


def _manifest() -> dict:
    return json.loads((MODULE_DIR / "manifest.json").read_text(encoding="utf-8"))


def test_manifest_felder():
    m = _manifest()
    assert m["id"] == "vibe" and m["name"] == "Vibe"
    assert m["nav_group"] == "working"
    assert m["has_service"] is False
    assert m["default_agent_tools"] is False       # Agenten bekommen die Vibe-Werkzeuge nicht von selbst
    assert m["min_core_version"]


def test_manifest_laesst_der_kern_laden():
    from hydrahive.modules.manifest import ModuleManifest
    mm = ModuleManifest.load(MODULE_DIR / "manifest.json")
    assert mm.id == "vibe"


def test_nur_admins_per_voreinstellung():
    """Container verbrauchen Platz und Speicher: Standard `admin_only` (SPEC.md „Zugriff“)."""
    caps = _manifest()["capabilities"]
    assert [c["id"] for c in caps] == ["module.vibe"]
    assert caps[0]["default"] == "admin_only"


def test_kein_vault_tor():
    """Vibe ist kein Gesundheits-/Finanzbereich; das Vault-Tor wäre hier falsch."""
    assert _manifest().get("vault", False) is not True


def test_hub_kennt_vibe():
    hub = json.loads((REPO / "hub.json").read_text(encoding="utf-8"))
    assert {"id": "vibe", "name": "Vibe", "path": "vibe"} in hub["modules"]


def test_migration_legt_beide_tabellen_an(db_ready):
    with db() as conn:
        names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"module_vibe_projects", "module_vibe_versions"} <= names


def test_projekte_tabelle_spalten(db_ready):
    with db() as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(module_vibe_projects)")}
    assert {"project_id", "agent_id", "container", "name", "owner", "state", "heal_enabled",
            "last_used_at", "created_at"} <= cols


def test_versionen_tabelle_spalten(db_ready):
    with db() as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(module_vibe_versions)")}
    assert {"id", "project_id", "commit_id", "summary", "kind", "created_at"} <= cols


def test_versionen_gehoeren_zum_projekt(db_ready):
    """Ein Commit kann in zwei Projekten gleich heißen (Vorlage), nicht aber doppelt im selben."""
    with db() as conn:
        conn.execute("INSERT INTO module_vibe_projects (project_id, agent_id, container, name, owner) "
                     "VALUES ('p1','a1','hh-vibe-p1','Test','boss')")
        conn.execute("INSERT INTO module_vibe_versions (project_id, commit_id, summary, kind) "
                     "VALUES ('p1','abc','Start','start')")
        try:
            conn.execute("INSERT INTO module_vibe_versions (project_id, commit_id, summary, kind) "
                         "VALUES ('p1','abc','nochmal','turn')")
            doppelt = True
        except Exception:
            doppelt = False
        conn.rollback()
    assert doppelt is False
