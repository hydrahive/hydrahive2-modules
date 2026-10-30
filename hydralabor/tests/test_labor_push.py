"""Hydra-Labor L2 Baustein 4c: Bündel auf dem Server in den Fork schieben – echtes git gegen ein lokales Ziel.

Prüft: Token nur über die Umgebung (nie in Befehl, URL, Datei), Arbeits-Repo ist bare und danach weg, nur der
Labor-Branch wird geschoben, Ziel nur der Fork.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path

import pytest
from backend import push

TOKEN = "gho_PUSHsecret0123456789abcdef"
ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
       "HOME": "/nonexistent", "GIT_CONFIG_NOSYSTEM": "1"}


def git(*a, cwd):
    return subprocess.run(["git", *a], cwd=cwd, env={**os.environ, **ENV}, check=True, capture_output=True,
                          text=True).stdout


@pytest.fixture
def world(tmp_path):
    """Labor-Repo mit einem Commit über origin/main, Bündel daraus, leeres bare-Ziel als „Fork“."""
    lab = tmp_path / "lab"
    lab.mkdir()
    git("init", "-q", "-b", "main", cwd=lab)
    git("commit", "-q", "--allow-empty", "-m", "basis", cwd=lab)
    git("update-ref", "refs/remotes/origin/main", "HEAD", cwd=lab)
    (lab / "neu.txt").write_text("hallo\n")
    git("add", "-A", cwd=lab)
    git("commit", "-q", "-m", "Änderung", cwd=lab)
    fork = tmp_path / "fork.git"
    git("init", "-q", "--bare", "-b", "main", str(fork), cwd=tmp_path)
    git("push", "-q", str(fork), "origin/main:refs/heads/main", cwd=lab)
    bundle = tmp_path / "labor.bundle"
    git("bundle", "create", "-q", str(bundle), "origin/main..HEAD", cwd=lab)
    work = tmp_path / "work"
    work.mkdir()
    return {"lab": lab, "fork": fork, "bundle": bundle, "work": work, "head": git("rev-parse", "HEAD", cwd=lab).strip()}


@pytest.fixture
def local_target(monkeypatch, world):
    """Ziel-URL auf das lokale bare-Repo umbiegen (statt https://github.com/<fork>.git)."""
    seen = {}

    def url(fork):
        seen["fork"] = fork
        return str(world["fork"])
    monkeypatch.setattr(push, "_remote_url", url)
    monkeypatch.setattr(push, "_base_url", lambda target: str(world["fork"]))
    return seen


def run(c):
    return asyncio.run(c)


def test_branch_im_fork(world, local_target):
    run(push.push_bundle(world["bundle"], fork="nutzer/hydrahive2.0", target="core",
                         branch="labor/test-20261030-1800", token=TOKEN, workdir=world["work"]))
    assert local_target["fork"] == "nutzer/hydrahive2.0"
    heads = git("for-each-ref", "--format=%(refname) %(objectname)", cwd=world["fork"])
    assert f"refs/heads/labor/test-20261030-1800 {world['head']}" in heads
    assert "refs/heads/main" in heads


def test_arbeitsordner_und_buendel_danach_weg(world, local_target):
    run(push.push_bundle(world["bundle"], fork="nutzer/hydrahive2.0", target="core",
                         branch="labor/test-1", token=TOKEN, workdir=world["work"]))
    assert list(world["work"].iterdir()) == []
    assert not world["bundle"].exists()


def test_token_nirgends_auf_platte(world, local_target, monkeypatch):
    calls = []
    real = push._git

    async def spy(args, *, cwd, env, timeout=300):
        calls.append((args, dict(env)))
        snapshot = [p.read_bytes() for p in Path(cwd).rglob("*") if p.is_file()] if Path(cwd).exists() else []
        assert all(TOKEN.encode() not in b for b in snapshot)
        return await real(args, cwd=cwd, env=env, timeout=timeout)
    monkeypatch.setattr(push, "_git", spy)
    run(push.push_bundle(world["bundle"], fork="nutzer/hydrahive2.0", target="core",
                         branch="labor/test-2", token=TOKEN, workdir=world["work"]))
    for args, env in calls:
        assert all(TOKEN not in a for a in args)                     # nie im Befehl / in der URL
    pushes = [env for args, env in calls if "push" in args]
    assert len(pushes) == 1
    env = pushes[0]
    assert env.get("GIT_CONFIG_COUNT") == "1" and env.get("GIT_CONFIG_KEY_0") == "http.extraHeader"
    assert TOKEN in env["GIT_CONFIG_VALUE_0"]
    fetches = [env for args, env in calls if "fetch" in args]
    assert fetches and all(TOKEN not in str(e) for e in fetches)       # beim Holen aus dem Bündel kein Token


def test_nur_labor_branch_name_erlaubt(world, local_target):
    for bad in ["main", "refs/heads/main", "labor/../main", "labor/x y", "-f", "labor/x:main"]:
        with pytest.raises(push.PushError):
            run(push.push_bundle(world["bundle"], fork="nutzer/hydrahive2.0", target="core",
                                 branch=bad, token=TOKEN, workdir=world["work"]))


@pytest.mark.parametrize("fork", ["hydrahive/hydrahive2.0", "nutzer/../hydrahive2.0", "nutzer/andere", "nutzer"])
def test_nur_fork_als_ziel(world, local_target, fork):
    with pytest.raises(push.PushError):
        run(push.push_bundle(world["bundle"], fork=fork, target="core", branch="labor/x-1", token=TOKEN,
                             workdir=world["work"]))


def test_kaputtes_buendel(world, local_target):
    world["bundle"].write_bytes(b"# v2 git bundle\nkaputt\n")
    with pytest.raises(push.PushError) as e:
        run(push.push_bundle(world["bundle"], fork="nutzer/hydrahive2.0", target="core",
                             branch="labor/x-1", token=TOKEN, workdir=world["work"]))
    assert e.value.code == "labor_submit_bundle_invalid"
    assert list(world["work"].iterdir()) == [] and not world["bundle"].exists()


def test_push_abgelehnt(world, local_target, monkeypatch):
    monkeypatch.setattr(push, "_remote_url", lambda fork: str(world["work"] / "gibt-es-nicht.git"))
    with pytest.raises(push.PushError) as e:
        run(push.push_bundle(world["bundle"], fork="nutzer/hydrahive2.0", target="core",
                             branch="labor/x-1", token=TOKEN, workdir=world["work"]))
    assert e.value.code == "labor_submit_push_failed"
    assert TOKEN not in str(e.value) and list(world["work"].iterdir()) == []


def test_echte_urls():
    assert push._remote_url("nutzer/hydrahive2.0") == "https://github.com/nutzer/hydrahive2.0.git"
    assert push._base_url("core") == "https://github.com/hydrahive/hydrahive2.0.git"
    assert push._base_url("modules") == "https://github.com/hydrahive/hydrahive2-modules.git"
