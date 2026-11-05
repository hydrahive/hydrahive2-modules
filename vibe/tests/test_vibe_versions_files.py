"""Baustein 5: Dateiregeln beim Speichern einer Version (PLAN-V1.md): was nie hineingehört, und was nie etwas ausführt.

Vierter Teil zu test_vibe_versions.py. Gegen ECHTES Git (siehe dort).
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


def git(work, *a):
    return subprocess.run(["git", *a], cwd=work, capture_output=True, text=True, env=clean_env(work.parent)).stdout


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


def _inner_repo(work, name, with_commit):
    d = work / name
    d.mkdir(parents=True)
    env = clean_env(work.parent)
    subprocess.run(["git", "init", "-q", "-b", "main", str(d)], check=True, env=env)
    (d / "y.txt").write_text("y\n")
    if with_commit:
        subprocess.run(["git", "add", "-A"], cwd=d, check=True, env=env)
        subprocess.run(["git", "-c", "user.name=x", "-c", "user.email=x@x", "commit", "-q", "-m", "i"], cwd=d, check=True, env=env)


@pytest.mark.parametrize("with_commit", [False, True])
def test_verschachteltes_repo_ohne_und_mit_commit_bricht_den_zug_nicht_ab(vm, work, with_commit):
    """Echtes Git: Ein inneres Repo OHNE Commit lässt `git add` mit „hat keinen Commit ausgecheckt“ scheitern."""
    _inner_repo(work, "fremd", with_commit)
    _inner_repo(work, "sub/tief", with_commit)
    (work / "ok.txt").write_text("ok\n")
    assert run(versions.commit_turn("p1", "mit inneren Repos", kind="turn")) is not None
    stage = git(work, "ls-files", "--stage")
    assert "160000" not in stage and "ok.txt" in stage and "fremd" not in stage and "tief" not in stage


def test_verschachteltes_repo_mit_sonderzeichen_im_ordnernamen(vm, work):
    _inner_repo(work, "wei rd's äö", False)
    (work / "ok.txt").write_text("ok\n")
    assert run(versions.commit_turn("p1", "sonderzeichen", kind="turn")) is not None
    assert "wei rd" not in git(work, "ls-files")


def test_altlast_gitlink_im_index_wird_entfernt(vm, work):
    """Früher eingebettetes Repo (Gitlink) verschwindet beim nächsten Zug aus dem Index."""
    _inner_repo(work, "alt", True)
    subprocess.run(["git", "add", "alt"], cwd=work, check=True, env=clean_env(work.parent))
    subprocess.run(["git", "-c", "user.name=x", "-c", "user.email=x@x", "commit", "-q", "-m", "mit gitlink"], cwd=work,
                   check=True, env=clean_env(work.parent))
    (work / "ok.txt").write_text("ok\n")
    run(versions.commit_turn("p1", "räumt auf", kind="turn"))
    assert "160000" not in git(work, "ls-files", "--stage")


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


def test_erster_zug_ohne_jede_aenderung_erzeugt_die_startversion(work, monkeypatch):
    """Mutanten-Fund: Auch ein leerer Ordner bekommt seine erste Version (sonst gäbe es nichts, wohin man zurück kann)."""
    (work / "a.txt").unlink(missing_ok=True)
    for f in list(work.iterdir()):
        if f.name != ".git":
            f.unlink()
    monkeypatch.setattr(versions, "_run", Bridge(work).run)
    v = run(versions.commit_turn("p1", "Start", kind="start"))
    assert v is not None and v["summary"] == "Start"
    assert len(run(versions.history("p1"))) == 1


def test_ausnahme_fuer_inneres_repo_ist_wortwoertlich_nicht_als_muster(vm, work):
    """Mutanten-Fund: Ein Ordner mit Glob-Zeichen im Namen darf als Ausnahme nicht wie ein Muster wirken – sonst
    verschwänden fremde Dateien mit aus der Version. Hier wirkt `[ab]*` ungewollt auf `a-*` und `b-*`."""
    inner = work / "[ab]*"
    inner.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(inner)], check=True, env=clean_env(work.parent))
    (inner / "y.txt").write_text("y\n")
    (work / "a-wichtig.txt").write_text("muss in die Version\n")
    (work / "b-wichtig.txt").write_text("auch\n")
    run(versions.commit_turn("p1", "mit Glob-Namen", kind="turn"))
    tracked = git(work, "ls-files").split()
    assert "a-wichtig.txt" in tracked and "b-wichtig.txt" in tracked
