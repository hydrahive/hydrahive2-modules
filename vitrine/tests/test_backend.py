"""Modul-Hülle: Manifest lädt mit dem Kern-Format, Status-Route liest state.json."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_manifest():
    m = json.loads((ROOT / "manifest.json").read_text())
    assert m["id"] == "vitrine" and m["has_service"] is True
    assert m["default_agent_tools"] is False
    assert {c["id"]: c["default"] for c in m["capabilities"]} == {"module.vitrine": "admin_only"}
    assert "videos/*" in m["persistent_paths"]


def test_manifest_mit_kernklasse():
    mf = pytest.importorskip("hydrahive.modules.manifest")
    m = mf.ModuleManifest.load(ROOT / "manifest.json")
    assert m.id == "vitrine" and m.has_service


def test_status_ohne_dienst(tmp_path):
    from backend import state
    s = state.read(tmp_path)
    assert s == {"running": False, "connected": False, "frames": 0, "fps": None, "video": None, "error": None, "size": None}


def test_status_frisch(tmp_path):
    from backend import state
    now = time.time()
    (tmp_path / "state.json").write_text(json.dumps(
        {"connected": True, "frames": 300, "reconnects": 0, "size": [1080, 1920], "video": "herbst.mp4", "error": None, "updated": now}))
    s = state.read(tmp_path, now=now + 2)
    assert s["running"] and s["connected"] and s["video"] == "herbst.mp4" and s["size"] == [1080, 1920]


def test_status_veraltet_heisst_dienst_steht(tmp_path):
    from backend import state
    (tmp_path / "state.json").write_text(json.dumps({"connected": True, "frames": 9, "updated": 1000.0}))
    s = state.read(tmp_path, now=1000.0 + state.STALE_SECONDS + 1)
    assert s["running"] is False and s["connected"] is False


def test_status_kaputte_datei(tmp_path):
    from backend import state
    (tmp_path / "state.json").write_text("{kaputt")
    assert state.read(tmp_path)["running"] is False


def test_fps_aus_zwei_messungen(tmp_path):
    from backend import state
    state.reset_rate()
    (tmp_path / "state.json").write_text(json.dumps({"connected": True, "frames": 100, "updated": 10.0}))
    state.read(tmp_path, now=10.0)
    (tmp_path / "state.json").write_text(json.dumps({"connected": True, "frames": 400, "updated": 20.0}))
    assert state.read(tmp_path, now=20.0)["fps"] == 30.0


@pytest.mark.parametrize("name", ["../config.json", "/etc/passwd", "sub/datei.mp4", ".versteckt.mp4", "A.MP4X", "x.mp4/"])
def test_safe_existing_lehnt_pfade_ab(tmp_path, name):
    from backend import videos
    (tmp_path / "v").mkdir()
    (tmp_path / "config.json").write_text("{}")
    with pytest.raises(videos.VideoError) as e:
        videos.safe_existing(tmp_path / "v", name)
    assert e.value.status == 400


def test_safe_existing_findet_eigene_datei(tmp_path):
    from backend import videos
    (tmp_path / "herbst-hydra.mp4").write_bytes(b"x")
    assert videos.safe_existing(tmp_path, "herbst-hydra.mp4").name == "herbst-hydra.mp4"
