"""Review 6, Teil 2: run_to_file räumt den Prozess auf; der Entpacker übersetzt jede Ausnahme und hat Grenzen."""

from __future__ import annotations

import asyncio
import io
import os
import tarfile
import textwrap

import pytest
from _hh_isolation import remove_test_tree
from hydrahive.projects._paths import ensure_workspace

from backend import (
    container,
    incus,
    network,
    workspace,
    workspace_acl,
    workspace_tar,
)


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


# --- MITTEL: run_to_file räumt Prozess und Handle auf ------------------------------------------------------------------


@pytest.fixture
def fake_binary(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    script = bin_dir / "incus"
    marker = tmp_path / "lebt.pid"
    script.write_text(textwrap.dedent(f"""\
        #!/usr/bin/env python3
        import os, sys, time
        open({str(marker)!r}, "w").write(str(os.getpid()))
        time.sleep(60)
        """))
    script.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ['PATH']}")
    return marker


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    try:
        with open(f"/proc/{pid}/stat") as stat_file:
            return stat_file.read().split()[2] != "Z"
    except OSError:
        return False


def test_abbruch_beendet_den_incus_prozess(tmp_path, fake_binary) -> None:
    async def scenario():
        task = asyncio.create_task(incus.run_to_file("x", out_path=tmp_path / "o.bin", timeout=60))
        for _ in range(100):
            if fake_binary.exists() and fake_binary.read_text():
                break
            await asyncio.sleep(0.05)
        pid = int(fake_binary.read_text())
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await asyncio.sleep(0.3)
        return pid

    pid = run(scenario())

    assert not _alive(pid)                                   # Kindprozess ist weg, kein Zombie, läuft nicht weiter


# --- MITTEL: Entpacker übersetzt alle Ausnahmen -----------------------------------------------------------------------


def _tar(tmp_path, *members) -> object:
    path = tmp_path / "x.tar"
    with tarfile.open(path, "w", format=tarfile.PAX_FORMAT) as tar:
        for info, data in members:
            tar.addfile(info, io.BytesIO(data) if data is not None else None)
    return path


def _info(name, typ=tarfile.REGTYPE, size=0, link="", mtime=0, mode=0o644):
    info = tarfile.TarInfo(name)
    info.type, info.size, info.linkname, info.mtime, info.mode = typ, size, link, mtime, mode
    return info


@pytest.mark.parametrize("link", [".", "", "./", "a/.."])
def test_hardlink_ohne_ziel_ist_ein_sauberer_fehler(tmp_path, link) -> None:
    archive = _tar(tmp_path, (_info("h", tarfile.LNKTYPE, link=link), None))

    with pytest.raises(container.VibeError) as exc:
        workspace_tar.extract(archive, tmp_path / "out")

    assert exc.value.code == "vibe_workspace_migration_failed"


@pytest.mark.parametrize("mtime", [1e30, -1e30, 2**70, -(2**70), 4102444801, -1])
def test_verzeichnis_mit_unmoeglicher_zeit_ist_ein_sauberer_fehler_oder_wird_angenommen(tmp_path, mtime) -> None:
    info = _info("sub", tarfile.DIRTYPE, mtime=mtime, mode=0o755)
    archive = tmp_path / "x.tar"
    with tarfile.open(archive, "w", format=tarfile.PAX_FORMAT) as tar:
        tar.addfile(info)

    try:
        root = workspace_tar.extract(archive, tmp_path / "out")
    except container.VibeError as exc:
        assert exc.code == "vibe_workspace_migration_failed"
    else:
        assert (root / "sub").is_dir()                       # alternativ: sauber angenommen, aber nie eine rohe Ausnahme


@pytest.mark.parametrize("mtime", [1e30, -1e30, 2**70, -(2**70), 4102444801, -1])
def test_datei_mit_unmoeglicher_zeit_ist_ein_sauberer_fehler_oder_wird_angenommen(tmp_path, mtime) -> None:
    info = _info("f", size=1, mtime=mtime)
    archive = tmp_path / "x.tar"
    with tarfile.open(archive, "w", format=tarfile.PAX_FORMAT) as tar:
        tar.addfile(info, io.BytesIO(b"x"))

    try:
        root = workspace_tar.extract(archive, tmp_path / "out")
    except container.VibeError as exc:
        assert exc.code == "vibe_workspace_migration_failed"
    else:
        assert (root / "f").read_text() == "x"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (float("nan"), 0.0),
        (float("inf"), workspace_tar.MAX_TIME),
        (-float("inf"), 0.0),
        (1e30, workspace_tar.MAX_TIME),
        (-5.0, 0.0),
        (1_700_000_000.0, 1_700_000_000.0),
        ("kaputt", 0.0),
        (None, 0.0),
    ],
)
def test_zeitbegrenzung_nimmt_jeden_wert_an(value, expected) -> None:
    """NaN/inf können nicht in ein tar geschrieben, wohl aber von einem manipulierten Archiv geliefert werden."""
    assert workspace_tar._time(value) == expected


def test_unmoegliche_zeit_wird_beim_schreiben_nie_roh_durchgereicht(tmp_path, monkeypatch) -> None:
    """Auch wenn `os.utime` selbst scheitert, kommt nur ein VibeError heraus."""
    def boom(*_a, **_k):
        raise OverflowError("zeit")

    monkeypatch.setattr(workspace_tar.os, "utime", boom)
    archive = _tar(tmp_path, (_info("f", size=1), b"x"))

    with pytest.raises(container.VibeError) as exc:
        workspace_tar.extract(archive, tmp_path / "out")

    assert exc.value.code == "vibe_workspace_migration_failed"
