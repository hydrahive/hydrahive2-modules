"""Baustein 1: Manifest, Zugriff und Tabellen der TV-Werkstatt (PLAN-E1.md)."""
from __future__ import annotations

import json
from pathlib import Path

from hydrahive.db.connection import db

MODULE_DIR = Path(__file__).resolve().parents[1]
REPO = MODULE_DIR.parent


def _manifest() -> dict:
    return json.loads((MODULE_DIR / "manifest.json").read_text(encoding="utf-8"))


def _cols(table: str) -> set[str]:
    with db() as conn:
        return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}


def test_manifest_felder():
    m = _manifest()
    assert m["id"] == "tvwerkstatt" and m["name"] == "TV-Werkstatt"
    assert m["version"] == "0.4.0"
    assert m["has_service"] is False
    assert m["default_agent_tools"] is False        # SPEC: keine Werkzeuge für Agenten in E1
    assert m["min_core_version"]


def test_manifest_laesst_der_kern_laden():
    from hydrahive.modules.manifest import ModuleManifest
    assert ModuleManifest.load(MODULE_DIR / "manifest.json").id == "tvwerkstatt"


def test_nur_admins_per_voreinstellung():
    """Container und Zugriff auf Fernseher im Heimnetz: nur Admins (SPEC.md, Entscheidung 9)."""
    caps = _manifest()["capabilities"]
    assert [c["id"] for c in caps] == ["module.tvwerkstatt"]
    assert caps[0]["default"] == "admin_only"
    assert "tools" not in caps[0]


def test_kein_vault_tor():
    assert _manifest().get("vault", False) is not True


def test_hub_kennt_tvwerkstatt():
    hub = json.loads((REPO / "hub.json").read_text(encoding="utf-8"))
    assert {"id": "tvwerkstatt", "name": "TV-Werkstatt", "path": "tvwerkstatt"} in hub["modules"]


def test_migration_legt_alle_tabellen_an(db_ready):
    with db() as conn:
        names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"module_tvwerkstatt_devices", "module_tvwerkstatt_sources", "module_tvwerkstatt_builds",
            "module_tvwerkstatt_installed", "module_tvwerkstatt_jobs"} <= names


def test_geraete_spalten(db_ready):
    assert {"device_id", "name", "address", "kind", "android", "sdk", "build", "stock_home", "live_tv",
            "adb_state", "created_by", "created_at"} <= _cols("module_tvwerkstatt_devices")


def test_quellen_spalten(db_ready):
    assert {"source_id", "repo", "commit_id", "license", "checked_at"} <= _cols("module_tvwerkstatt_sources")


def test_bauten_spalten(db_ready):
    assert {"build_id", "source_id", "part", "commit_id", "sha256", "package", "state", "log_tail",
            "created_at"} <= _cols("module_tvwerkstatt_builds")


def test_installiert_spalten(db_ready):
    assert {"device_id", "package", "build_id", "sha256", "installed_at"} <= _cols("module_tvwerkstatt_installed")


def test_auftraege_spalten(db_ready):
    assert {"job_id", "kind", "target", "state", "step", "error_code", "error_detail", "started_by",
            "created_at", "updated_at"} <= _cols("module_tvwerkstatt_jobs")


def test_adresse_eines_geraets_ist_eindeutig(db_ready):
    """Zwei Einträge für dieselbe Adresse würden zwei Ausnahmen in der Sperrliste für ein Gerät bedeuten."""
    with db() as conn:
        conn.execute("INSERT INTO module_tvwerkstatt_devices (device_id, name, address, created_by) "
                     "VALUES ('d1', 'Test', '192.0.2.10', 'boss')")
        try:
            conn.execute("INSERT INTO module_tvwerkstatt_devices (device_id, name, address, created_by) "
                         "VALUES ('d2', 'Doppelt', '192.0.2.10', 'boss')")
            doppelt = True
        except Exception:
            doppelt = False
        conn.rollback()
    assert doppelt is False
