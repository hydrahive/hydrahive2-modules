"""tar-Strom statt `incus file pull` (echter Vorfall 6.11.: ein FIFO ließ den root-Daemonhelfer endlos hängen).

Alles nur mit Fake-Incus und Archiven aus dem Speicher – keine echten FIFOs, Container oder Sonderdateien.
"""

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


def test_normale_dateien_ordner_und_links_werden_uebernommen(tmp_path) -> None:
    root = _extract(
        tmp_path,
        ("./", "dir", b""),
        ("./src", "dir", b""),
        ("./src/a.txt", "file", "hallo"),
        ("./link", "sym", "src/a.txt"),
        ("./.git", "dir", b""),
        ("./.git/HEAD", "file", "ref"),
    )

    assert (root / "src" / "a.txt").read_text() == "hallo"
    assert os.readlink(root / "link") == "src/a.txt"
    assert (root / ".git" / "HEAD").exists()


def test_setuid_und_setgid_werden_verworfen(tmp_path) -> None:
    """Das Archiv trägt echte Spezialbits (04755). Auf dem Host dürfen sie nie ankommen."""
    path = tmp_path / "suid.tar"
    with tarfile.open(path, "w", format=tarfile.GNU_FORMAT) as tar:
        for name, mode in (("run.sh", 0o4755), ("grp.sh", 0o2755), ("alles.sh", 0o6777)):
            info = tarfile.TarInfo(name)
            info.size, info.mode = 3, mode
            tar.addfile(info, io.BytesIO(b"abc"))
    with tarfile.open(path) as check:                       # Vorbedingung: die Bits stehen wirklich im Archiv
        assert [oct(m.mode) for m in check.getmembers()] == ["0o4755", "0o2755", "0o6777"]

    root = workspace_tar.extract(path, tmp_path / "out")

    for name in ("run.sh", "grp.sh", "alles.sh"):
        mode = stat.S_IMODE((root / name).stat().st_mode)
        assert mode & 0o6000 == 0, name                     # kein Setuid/Setgid
        assert mode & 0o111, name                           # ausführbar bleibt


@pytest.mark.parametrize("name", ["/etc/passwd", "../x", "a/../../x", "./a/../../../x"])
def test_pfade_ausserhalb_werden_abgelehnt(tmp_path, name) -> None:
    with pytest.raises(container.VibeError) as exc:
        _extract(tmp_path, (name, "file", "böse"))

    assert exc.value.code == "vibe_workspace_migration_failed"
    assert not (tmp_path / "x").exists() and not (tmp_path / "out" / "x").exists()


def test_schreiben_durch_einen_symlink_ist_unmoeglich(tmp_path) -> None:
    """Klassischer Angriff: erst Symlink auf /etc, dann Datei „durch“ den Link."""
    outside = tmp_path / "aussen"
    outside.mkdir()

    with pytest.raises(container.VibeError):
        _extract(tmp_path, ("./d", "sym", str(outside)), ("./d/boese.txt", "file", "x"))

    assert not (outside / "boese.txt").exists()


def test_hardlink_nach_aussen_wird_abgelehnt(tmp_path) -> None:
    with pytest.raises(container.VibeError):
        _extract(tmp_path, ("./h", "hard", "../../etc/passwd"))


def test_hardlink_innerhalb_wird_uebernommen(tmp_path) -> None:
    root = _extract(tmp_path, ("./a", "file", "x"), ("./b", "hard", "a"))

    assert (root / "b").read_text() == "x"


@pytest.mark.parametrize("kind", ["fifo", "chr"])
def test_sonderdateien_im_archiv_brechen_ab(tmp_path, kind) -> None:
    with pytest.raises(container.VibeError) as exc:
        _extract(tmp_path, ("./pipe", kind, b""))

    assert exc.value.code == "vibe_workspace_special_files"


def test_defektes_archiv_bricht_ab_statt_halb_zu_entpacken(tmp_path) -> None:
    broken = tmp_path / "kaputt.tar"
    broken.write_bytes(b"das ist kein tar" * 100)

    with pytest.raises(container.VibeError) as exc:
        workspace_tar.extract(broken, tmp_path / "out")

    assert exc.value.code == "vibe_workspace_migration_failed"
