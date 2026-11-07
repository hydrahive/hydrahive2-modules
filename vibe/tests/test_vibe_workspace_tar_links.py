"""Entpacker: Symlink-/Verzeichnis-Tricks (Review 4, R4-H1) – zweiter Teil zu test_vibe_workspace_tar.py."""

from __future__ import annotations

import asyncio
import io
import os
import stat
import tarfile
from pathlib import Path

import pytest
from _hh_isolation import remove_test_tree
from hydrahive.projects._paths import ensure_workspace

from backend import container, network, workspace, workspace_acl, workspace_tar


def run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def clean_workspace():
    for _ in range(2):
        path = ensure_workspace("p1")
        if path.exists():
            remove_test_tree(path)
        workspace.forget("p1")
    yield
    path = ensure_workspace("p1")
    if path.exists():
        remove_test_tree(path)
    workspace.forget("p1")


@pytest.fixture
def net(fake_incus, monkeypatch):
    monkeypatch.setattr(network, "_host_networks", lambda: set())
    monkeypatch.setattr(network, "_host_addresses", lambda: {"192.168.178.2/32"})
    monkeypatch.setattr(workspace_acl, "_run", lambda _args: None)
    run(network.ensure_network())
    return fake_incus


def _archive(tmp_path: Path, *members: tuple[str, str, bytes | str]) -> Path:
    path = tmp_path / "x.tar"
    with tarfile.open(path, "w") as tar:
        for name, kind, payload in members:
            info = tarfile.TarInfo(name)
            if kind == "file":
                data = payload if isinstance(payload, bytes) else payload.encode()
                info.size, info.mode = len(data), 0o4755
                tar.addfile(info, io.BytesIO(data))
                # TarInfo.mode behält Spezialbits nur mit einem rohen Header: Setuid wirklich im Archiv ablegen.
            elif kind == "dir":
                info.type, info.mode = tarfile.DIRTYPE, 0o755
                tar.addfile(info)
            elif kind == "sym":
                info.type, info.linkname = tarfile.SYMTYPE, str(payload)
                tar.addfile(info)
            elif kind == "hard":
                info.type, info.linkname = tarfile.LNKTYPE, str(payload)
                tar.addfile(info)
            elif kind == "fifo":
                info.type = tarfile.FIFOTYPE
                tar.addfile(info)
            elif kind == "chr":
                info.type = tarfile.CHRTYPE
                tar.addfile(info)
    return path


def _extract(tmp_path: Path, *members) -> Path:
    return workspace_tar.extract(_archive(tmp_path, *members), tmp_path / "out")


def test_symlink_und_danach_verzeichnis_gleichen_namens_wird_abgelehnt(tmp_path) -> None:
    """Review 4 (R4-H1): `mkdir(exist_ok=True)` akzeptierte den Symlink als Verzeichnis; das abschließende
    `chmod`/`utime` folgte ihm danach aus dem Staging hinaus."""
    outside = tmp_path / "aussen"
    outside.mkdir()
    os.chmod(outside, 0o750)

    with pytest.raises(container.VibeError):
        _extract(tmp_path, ("./d", "sym", str(outside)), ("./d/", "dir", b""))

    assert stat.S_IMODE(outside.stat().st_mode) == 0o750          # Ziel außerhalb unberührt


def test_symlink_auf_verzeichnis_im_baum_wird_nie_als_verzeichnis_angenommen(tmp_path) -> None:
    with pytest.raises(container.VibeError):
        _extract(tmp_path, ("./echt", "dir", b""), ("./d", "sym", "echt"), ("./d", "dir", b""))


def test_datei_und_danach_verzeichnis_gleichen_namens_wird_abgelehnt(tmp_path) -> None:
    with pytest.raises(container.VibeError):
        _extract(tmp_path, ("./x", "file", "a"), ("./x", "dir", b""))


def test_verzeichnisrechte_werden_nur_ueber_ein_handle_ohne_linkfolgen_gesetzt(tmp_path, monkeypatch) -> None:
    """Zusätzliche Absicherung: die Rechtevergabe läuft über ein O_NOFOLLOW-Handle, nie über den Pfadnamen."""
    path_calls: list[str] = []
    real_chmod, real_utime = os.chmod, os.utime

    def spy_chmod(path, mode, *a, **k):
        if not isinstance(path, int):
            path_calls.append("chmod")
        return real_chmod(path, mode, *a, **k)

    def spy_utime(path, times=None, *a, **k):
        if not isinstance(path, int):
            path_calls.append("utime")
        return real_utime(path, times, *a, **k)

    monkeypatch.setattr(workspace_tar.os, "chmod", spy_chmod)
    monkeypatch.setattr(workspace_tar.os, "utime", spy_utime)
    root = _extract(tmp_path, ("./sub", "dir", b""), ("./f", "file", "x"))

    # Dateien: utime per Pfad nur mit follow_symlinks=False (vorhanden); Verzeichnisse: ausschließlich per Handle.
    assert "chmod" not in path_calls
    assert (root / "sub").is_dir()


def test_vorhandenes_echtes_verzeichnis_darf_doppelt_vorkommen(tmp_path) -> None:
    root = _extract(tmp_path, ("./sub", "dir", b""), ("./sub", "dir", b""), ("./sub/a", "file", "x"))

    assert (root / "sub" / "a").read_text() == "x"
