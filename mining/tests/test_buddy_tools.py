"""Buddy-Werkzeuge: Lesen für alle mit Mining-Zugriff, Steuern nur mit mining.control.

Der Kern filtert Werkzeuge nach den Freigaben des Besitzers (tool_filter, Manifest
capabilities[].tools). Zusätzlich prüft jedes Steuer-Werkzeug selbst (Verteidigung
in der Tiefe: falls ein Agent das Werkzeug per Konfiguration fest eingetragen hat).
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from backend import buddy_tools, catalog, history, rigs, runtime_store, store
from backend.decide import Assignment
from backend.profit import CoinQuote

MANIFEST = json.loads((Path(__file__).resolve().parents[1] / "manifest.json").read_text())


def _ctx(user="admin"):
    from hydrahive.tools.base import ToolContext
    return ToolContext(session_id="s", agent_id="a", user_id=user, workspace=Path("/tmp"))


def run(tool, args, user="admin"):
    return asyncio.run(tool.execute(args, _ctx(user)))


@pytest.fixture
def quotes():
    store.replace_quotes([CoinQuote(coin=c, name=c.upper(), algo="A", fee=0.01, fee_type="PPS+",
                                    profit_per_hs_day=1e-6, price_usd=1.0) for c in catalog.coins()])
    store.set_usd_per_eur(1.25)


@pytest.fixture
def rig(client, admin_headers):
    from tests.test_planner import _rig
    e = _rig(client, admin_headers, name="rig-01")
    return e["rig_id"]


def test_all_tools_registered_and_named():
    names = [t.name for t in buddy_tools.TOOLS]
    assert names == ["mining_status", "mining_earnings", "mining_rig_history", "mining_benchmarks",
                     "mining_clore_dryrun", "mining_rig_control", "mining_settings"]
    assert all(t.description and t.schema["type"] == "object" for t in buddy_tools.TOOLS)


def test_manifest_maps_control_tools_to_control_capability():
    caps = {c["id"]: c for c in MANIFEST["capabilities"]}
    assert set(caps["mining.control"]["tools"]) == {"mining_rig_control", "mining_settings"}
    assert MANIFEST["default_agent_tools"] is True


def test_status_lists_rigs_with_state(rig, quotes):
    runtime_store.set_assignment(rig, Assignment("mine", "cfx", "rigel", "octopus", "best"), None, power_changed=False)
    r = run(buddy_tools.STATUS, {})
    assert r.success, r.error
    out = r.output
    assert out["rigs"][0]["name"] == "rig-01" and out["rigs"][0]["activity"] == "schürft CFX (rigel)"
    assert out["summary"]["total"] == 1


def test_earnings_from_history_in_eur(rig, quotes):
    from datetime import datetime, timezone
    runtime_store.set_assignment(rig, Assignment("mine", "cfx", "rigel", "octopus", "best"), None, power_changed=False)
    history.record({"id": rig, "name": "rig-01"}, {"hashrate": 5e6, "gpus": []}, now=datetime.now(timezone.utc))
    r = run(buddy_tools.EARNINGS, {"hours": 24})
    assert r.success, r.error
    assert r.output["now_eur_day"] == pytest.approx(5e6 * 1e-6 / 1.25)
    assert r.output["by_rig"][0]["name"] == "rig-01"


def test_history_unknown_rig_fails_cleanly(quotes):
    r = run(buddy_tools.HISTORY, {"rig": "gibt-es-nicht"})
    assert not r.success and "gibt-es-nicht" in r.error


@pytest.mark.parametrize("hours", [0, 500, "x"])
def test_bad_hours_rejected(hours, quotes):
    assert not run(buddy_tools.EARNINGS, {"hours": hours}).success


def test_control_switch_off_and_on(rig, quotes):
    r = run(buddy_tools.CONTROL, {"rig": "rig-01", "action": "off"})
    assert r.success, r.error
    assert next(x for x in rigs.list_rigs() if x["id"] == rig)["enabled"] == 0
    assert run(buddy_tools.CONTROL, {"rig": "rig-01", "action": "on"}).success
    assert next(x for x in rigs.list_rigs() if x["id"] == rig)["enabled"] == 1


def test_control_rebench_clears_measurements(rig, quotes):
    runtime_store.save_bench(rig, "cfx", "rigel", "octopus", 5e7, 150.0, None)
    assert run(buddy_tools.CONTROL, {"rig": "rig-01", "action": "rebench"}).success
    assert runtime_store.bench_for(rig) == ({}, set())


@pytest.mark.parametrize("action", ["revoke", "delete", "approve", "", None])
def test_control_has_no_destructive_actions(rig, action, quotes):
    r = run(buddy_tools.CONTROL, {"rig": "rig-01", "action": action})
    assert not r.success
    assert next(x for x in rigs.list_rigs() if x["id"] == rig)["status"] == "active"


def test_control_needs_capability(rig, quotes):
    """testuser hat kein mining.control (admin_only) → nichts passiert, auch wenn das Werkzeug erreichbar ist."""
    r = run(buddy_tools.CONTROL, {"rig": "rig-01", "action": "off"}, user="testuser")
    assert not r.success and "mining.control" in r.error
    assert next(x for x in rigs.list_rigs() if x["id"] == rig)["enabled"] == 1


def test_settings_change_validated(quotes):
    r = run(buddy_tools.SETTINGS, {"changes": {"switch_threshold": 0.1, "min_runtime_min": 30}})
    assert r.success, r.error
    assert store.get_config()["switch_threshold"] == 0.1 and store.get_config()["min_runtime_min"] == 30
    bad = run(buddy_tools.SETTINGS, {"changes": {"switch_threshold": 7}})
    assert not bad.success and store.get_config()["switch_threshold"] == 0.1


def test_settings_cannot_touch_kryptex_user(quotes):
    """Auszahlungs-Ziel ändern ist zu folgenreich für einen Chat-Befehl — nur über die Oberfläche."""
    store.update_config({"kryptex_user": "krxECHT"})
    r = run(buddy_tools.SETTINGS, {"changes": {"kryptex_user": "krxFREMD"}})
    assert not r.success and store.get_config()["kryptex_user"] == "krxECHT"


def test_settings_needs_capability(quotes):
    r = run(buddy_tools.SETTINGS, {"changes": {"min_runtime_min": 60}}, user="testuser")
    assert not r.success and store.get_config()["min_runtime_min"] != 60


def test_settings_without_changes_shows_config(quotes):
    store.update_config({"kryptex_user": "krxECHT"})
    r = run(buddy_tools.SETTINGS, {})
    assert r.success and r.output["config"]["kryptex_user"] == "krxECHT"


def test_benchmarks_ranked_by_earnings(rig, quotes):
    runtime_store.save_bench(rig, "cfx", "rigel", "octopus", 5e7, 150.0, None)
    runtime_store.save_bench(rig, "erg", "rigel", "autolykos2", 1e8, 160.0, None)
    runtime_store.save_bench(rig, "rvn", "rigel", "kawpow", None, None, "watchdog:exited")
    r = run(buddy_tools.BENCHMARKS, {"rig": "rig-01"})
    assert r.success, r.error
    assert [b["coin"] for b in r.output["measured"]][:2] == ["erg", "cfx"]
    assert r.output["failed"][0]["error"] == "watchdog:exited"


def test_skill_parses_and_names_every_tool():
    """Vorlage für den System-Skill muss mit dem Kern-Parser lesbar sein und alle Werkzeuge nennen."""
    from hydrahive.skills.models import parse
    text = (Path(__file__).resolve().parents[1] / "skills" / "mining-workflow.md").read_text()
    skill = parse(text, scope="system", owner="system", fallback_name="x")
    assert skill.name == "mining-workflow" and skill.description and skill.when_to_use
    assert set(skill.tools_required) == {t.name for t in buddy_tools.TOOLS}
    for t in buddy_tools.TOOLS:
        assert f"`{t.name}`" in skill.body


def test_skill_sync_installs_and_respects_admin_edit(tmp_path, monkeypatch):
    from backend import skill_sync
    monkeypatch.setattr("hydrahive.skills._paths.system_dir", lambda: tmp_path)
    skill_sync.install()
    live = tmp_path / "mining-workflow.md"
    assert live.read_text() == (skill_sync.SKILLS_SRC / "mining-workflow.md").read_text()
    live.write_text("Admin hat das angepasst")
    skill_sync.install()
    assert live.read_text() == "Admin hat das angepasst"       # Admin-Änderung bleibt


SKILL_050_SHA = "259a9bab20fea282f0caf9830407b792b689c0686bb730fb338fd3023bc4302f"  # Auslieferung 0.5.0


def test_skill_history_knows_all_shipped_versions():
    """Ohne Eintrag gilt eine alte Auslieferung als Admin-Änderung und wird nie ersetzt
    (05.10.2026: Prod und hydratest blieben auf der 0.5.0-Fassung ohne Clore-Werkzeug)."""
    import hashlib
    import json

    from backend import skill_sync
    history = json.loads((skill_sync.SKILLS_SRC / "_history.json").read_text())
    for f in skill_sync.SKILLS_SRC.glob("*.md"):
        assert hashlib.sha256(f.read_bytes()).hexdigest() in history.get(f.name, []), f.name
    assert SKILL_050_SHA in history["mining-workflow.md"]


def test_skill_sync_replaces_earlier_shipped_version(tmp_path, monkeypatch):
    import hashlib
    import json

    from backend import skill_sync
    src = tmp_path / "src"
    src.mkdir()
    (src / "mining-workflow.md").write_text("neu")
    old = b"alt ausgeliefert"
    (src / "_history.json").write_text(json.dumps({"mining-workflow.md": [hashlib.sha256(old).hexdigest()]}))
    live_dir = tmp_path / "live"
    live_dir.mkdir()
    (live_dir / "mining-workflow.md").write_bytes(old)
    monkeypatch.setattr(skill_sync, "SKILLS_SRC", src)
    monkeypatch.setattr("hydrahive.skills._paths.system_dir", lambda: live_dir)
    skill_sync.install()
    assert (live_dir / "mining-workflow.md").read_text() == "neu"


def test_skill_sync_never_raises(monkeypatch):
    from backend import skill_sync

    def boom(*a):
        raise OSError("schreibgeschützt")
    monkeypatch.setattr("hydrahive.skills._defaults_sync.sync_defaults", boom)
    skill_sync.install()                                       # darf das Modul nicht am Laden hindern


def test_revoked_rig_is_invisible_to_tools(rig, quotes):
    """Gesperrte Rechner gibt es für Buddy nicht — weder anzeigen noch schalten."""
    rigs.revoke(rig)
    assert not run(buddy_tools.CONTROL, {"rig": "rig-01", "action": "on"}).success
    assert not run(buddy_tools.HISTORY, {"rig": "rig-01"}).success
    assert run(buddy_tools.STATUS, {}).output["summary"]["total"] == 0


def test_core_filter_viewer_keeps_read_tools_loses_control(monkeypatch):
    """Wer Mining ansehen, aber nicht steuern darf: Lese-Werkzeuge bleiben, Steuer-Werkzeuge fallen weg.

    Nachgebaut wie im Server (api/lifespan.py): Werkzeuge mit module_id registriert.
    """
    import dataclasses

    from hydrahive.access import check, tool_filter
    from hydrahive.tools import REGISTRY, register_module_tools
    register_module_tools([dataclasses.replace(t, module_id="mining") for t in buddy_tools.TOOLS])
    try:
        monkeypatch.setattr(check, "can_use_as", lambda user, cap: cap == "module.mining")
        names = [t.name for t in buddy_tools.TOOLS]
        read = ["mining_status", "mining_earnings", "mining_rig_history", "mining_benchmarks", "mining_clore_dryrun"]
        assert tool_filter.filter_tools("viewer", names) == read
    finally:
        for t in buddy_tools.TOOLS:
            REGISTRY.pop(t.name, None)


def test_clore_dryrun_tool_reads_summary_in_eur(quotes):
    from backend import clore_store
    clore_store.save_run({"ok": True, "free": 3, "rated": 2, "hits": 1, "best_roi": 0.4},
                         [{"server_id": 5, "gpu": "nvidia-rtx-3070", "count": 2, "coin": "prl", "source": "reference",
                           "revenue": 2.5, "cost_od": 1.25, "cost_spot": None, "roi_od": 1.0, "roi_spot": None,
                           "reliability": 0.99, "mrl": 72}])
    r = run(buddy_tools.CLORE_DRYRUN, {})
    assert r.success, r.error
    d = r.output
    assert d["note"].startswith("Nur gerechnet") and d["last_run"]["hits"] == 1
    (hit,) = d["hits_24h"]
    assert hit["revenue_eur_day"] == pytest.approx(2.0) and hit["cost_od_eur_day"] == pytest.approx(1.0)
    assert hit["roi_od_pct"] == pytest.approx(100.0) and hit["roi_spot_pct"] is None


def test_clore_dryrun_tool_without_runs(quotes):
    r = run(buddy_tools.CLORE_DRYRUN, {})
    assert r.success and r.output["last_run"] is None and r.output["hits_24h"] == []
