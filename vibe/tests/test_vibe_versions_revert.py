"""Baustein 5: „Nur diese Änderung zurück“ mit Konflikt (PLAN-V1.md).

Dritter Teil zu test_vibe_versions.py. Gegen ECHTES Git. Der Konfliktablauf ist hier zum ersten Mal gebaut und
getestet (SPEC.md nannte ihn „nicht gebaut oder getestet“).
"""
from __future__ import annotations

import asyncio
import subprocess

import pytest
from backend import versions
from gitbridge import Bridge, clean_env


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def work(tmp_path):
    w = tmp_path / "work"
    w.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(w)], check=True, env=clean_env(tmp_path))
    (w / ".gitignore").write_text("node_modules\ndist\n")
    (w / "k.txt").write_text("eins\n")
    return w


@pytest.fixture
def vm(work, monkeypatch):
    bridge = Bridge(work)
    monkeypatch.setattr(versions, "_run", bridge.run)
    run(versions.commit_turn("p1", "Start", kind="start"))
    return bridge


def turn(work, name, text, summary):
    (work / name).parent.mkdir(parents=True, exist_ok=True)
    (work / name).write_text(text)
    return run(versions.commit_turn("p1", summary, kind="turn"))


def git(work, *a):
    return subprocess.run(["git", *a], cwd=work, capture_output=True, text=True, env=clean_env(work.parent)).stdout


# --- Nur diese Änderung zurück ----------------------------------------------------------------------------------

def test_einzelne_aenderung_zurueck_ohne_konflikt(vm, work):
    v1 = turn(work, "a.txt", "A\n", "a neu")
    turn(work, "b.txt", "B\n", "b neu")
    res = run(versions.revert("p1", v1["commit_id"]))
    assert res["ok"] is True and res["version"]["kind"] == "revert"
    assert not (work / "a.txt").exists() and (work / "b.txt").read_text() == "B\n"


def test_einzelne_aenderung_zurueck_bleibt_in_der_zeitleiste(vm, work):
    v1 = turn(work, "a.txt", "A\n", "a neu")
    run(versions.revert("p1", v1["commit_id"]))
    h = run(versions.history("p1"))
    assert h[0]["kind"] == "revert" and v1["commit_id"] in {v["commit_id"] for v in h}


def test_konflikt_bricht_sauber_ab_und_laesst_work_unveraendert(vm, work):
    v1 = turn(work, "k.txt", "zwei\n", "zwei")
    turn(work, "k.txt", "drei\n", "drei")
    before = git(work, "rev-parse", "HEAD"), (work / "k.txt").read_text()
    res = run(versions.revert("p1", v1["commit_id"]))
    assert res == {"ok": False, "code": "vibe_revert_conflict", "version": None}
    assert (git(work, "rev-parse", "HEAD"), (work / "k.txt").read_text()) == before
    assert "<<<<<<<" not in (work / "k.txt").read_text()
    assert not (work / ".git" / "REVERT_HEAD").exists()
    assert git(work, "status", "--short") == ""


def test_nach_konflikt_geht_alles_weiter(vm, work):
    v1 = turn(work, "k.txt", "zwei\n", "zwei")
    turn(work, "k.txt", "drei\n", "drei")
    run(versions.revert("p1", v1["commit_id"]))
    turn(work, "k.txt", "vier\n", "vier")
    assert [v["summary"] for v in run(versions.history("p1"))][0] == "vier"


def test_revert_der_startversion_abgelehnt(vm):
    start = run(versions.history("p1"))[0]
    with pytest.raises(versions.VersionError) as e:
        run(versions.revert("p1", start["commit_id"]))
    assert e.value.code == "vibe_revert_start"


def test_revert_einer_zurueck_version_erlaubt_wie_jede_andere(vm, work):
    v1 = turn(work, "a.txt", "A\n", "a")
    turn(work, "b.txt", "B\n", "b")
    back = run(versions.restore("p1", v1["commit_id"]))
    res = run(versions.revert("p1", back["commit_id"]))
    assert res["ok"] is True


def test_revert_ohne_wirkung_meldet_nichts_zu_tun(vm, work):
    v1 = turn(work, "a.txt", "A\n", "a")
    run(versions.revert("p1", v1["commit_id"]))
    res = run(versions.revert("p1", v1["commit_id"]))
    assert res["ok"] is False and res["code"] in ("vibe_revert_nothing", "vibe_revert_conflict")
    assert git(work, "status", "--short") == "" and not (work / ".git" / "REVERT_HEAD").exists()


def test_konflikt_raeumt_auch_ungespeicherte_markierungen_im_index_weg(vm, work):
    """Mutanten-Fund: Nach einem Konflikt reicht `revert --abort` allein nicht, wenn der Index schon halb aufgelöst
    war. Danach darf weder ein Konfliktmarker noch ein vorgemerkter Rest übrig sein."""
    v1 = turn(work, "k.txt", "zwei\n", "zwei")
    turn(work, "k.txt", "drei\n", "drei")
    (work / "extra.txt").write_text("neu und vorgemerkt\n")
    subprocess.run(["git", "add", "extra.txt"], cwd=work, check=True, env=clean_env(work.parent))
    run(versions.revert("p1", v1["commit_id"]))
    assert "UU" not in git(work, "status", "--short") and "<<<<<<<" not in (work / "k.txt").read_text()
    assert git(work, "diff", "--cached", "--name-only").strip() == ""
