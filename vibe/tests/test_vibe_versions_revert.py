"""Baustein 5: „Nur diese Änderung zurück“ mit Konflikt, Dateiregeln beim Speichern einer Version (PLAN-V1.md).

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


# --- Dateiregeln beim Speichern ---------------------------------------------------------------------------------

def test_node_modules_und_dist_kommen_nie_hinein_auch_ohne_gitignore(vm, work):
    (work / ".gitignore").write_text("")                                   # der Agent leert die Datei
    (work / "node_modules" / "p").mkdir(parents=True)
    (work / "node_modules" / "p" / "i.js").write_text("x\n")
    (work / "dist").mkdir()
    (work / "dist" / "b.js").write_text("x\n")
    (work / "sub" / "node_modules").mkdir(parents=True)
    (work / "sub" / "node_modules" / "q.js").write_text("x\n")
    (work / "ok.ts").write_text("ok\n")
    run(versions.commit_turn("p1", "ignore leer", kind="turn"))
    tracked = git(work, "ls-files").split()
    assert "ok.ts" in tracked and not any("node_modules" in t or t.startswith("dist/") for t in tracked)


def test_grosse_dateien_werden_nicht_versioniert(vm, work):
    (work / "gross.bin").write_bytes(b"\0" * (versions.MAX_FILE_BYTES + 1))
    (work / "klein.txt").write_text("k\n")
    run(versions.commit_turn("p1", "mit gross", kind="turn"))
    tracked = git(work, "ls-files").split()
    assert "klein.txt" in tracked and "gross.bin" not in tracked


def test_grosse_datei_allein_erzeugt_keine_version(vm, work):
    (work / "gross.bin").write_bytes(b"\0" * (versions.MAX_FILE_BYTES + 1))
    assert run(versions.commit_turn("p1", "nur gross", kind="turn")) is None


def test_verschachteltes_repo_wird_nicht_eingebettet(vm, work):
    (work / "fremd").mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(work / "fremd")], check=True, env=clean_env(work.parent))
    (work / "fremd" / "y.txt").write_text("y\n")
    (work / "ok.txt").write_text("ok\n")
    run(versions.commit_turn("p1", "mit fremd", kind="turn"))
    stage = git(work, "ls-files", "--stage")
    assert "160000" not in stage and "ok.txt" in stage


def test_dateinamen_mit_sonderzeichen(vm, work):
    for n in ("Mein Bild äö.txt", "mit'apostroph.txt", "$(touch pwn).txt", "-opt.txt"):
        (work / n).write_text("x\n")
    v = run(versions.commit_turn("p1", "namen", kind="turn"))
    names = {f["path"] for f in run(versions.changes("p1", v["commit_id"]))["files"]}
    assert {"Mein Bild äö.txt", "mit'apostroph.txt", "$(touch pwn).txt", "-opt.txt"} <= names
    assert not (work / "pwn").exists() and not (work.parent / "pwn").exists()


def test_git_hooks_des_agenten_laufen_nie(vm, work):
    hook = work / ".git" / "hooks" / "pre-commit"
    hook.parent.mkdir(exist_ok=True)
    hook.write_text("#!/bin/sh\ntouch /tmp/vibe-hook-lief\nexit 1\n")
    hook.chmod(0o755)
    (work / "a.txt").write_text("x\n")
    assert run(versions.commit_turn("p1", "mit hook", kind="turn")) is not None
    import os
    assert not os.path.exists("/tmp/vibe-hook-lief")


def test_agent_aendert_git_config_hooks_pfad_wirkungslos(vm, work):
    subprocess.run(["git", "config", "core.hooksPath", "/tmp/boese-hooks"], cwd=work, check=True, env=clean_env(work.parent))
    (work / "a.txt").write_text("y\n")
    assert run(versions.commit_turn("p1", "t", kind="turn")) is not None
