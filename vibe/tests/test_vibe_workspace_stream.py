"""tar-Strom: Ablauf der Migration (Dev-Server, Container an/aus, Abbruch) – zweiter Teil zu test_vibe_workspace_tar.py."""

from __future__ import annotations

import asyncio
import io
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



def test_sonderdatei_im_container_stoppt_die_migration_ohne_veraenderung(net) -> None:
    run(container.launch("p1", container.Limits()))
    net.tar_files = {"src/App.tsx": b"app\n"}
    net.tar_extra = [("pipe", "fifo")]

    with pytest.raises(container.VibeError) as exc:
        run(workspace.ensure("p1"))

    assert exc.value.code == "vibe_workspace_special_files"
    assert not any(ensure_workspace("p1").iterdir())
    assert workspace_tar_marker_gone("p1")
    assert not [c for c in net.calls if c[:2] == ["file", "pull"]]
    assert net.containers[container.name_for("p1")]["running"] is True


def workspace_tar_marker_gone(pid: str) -> bool:
    return not workspace._marker(pid).exists()


def test_dev_server_wird_vor_dem_lesen_angehalten_und_danach_wieder_gestartet(net) -> None:
    run(container.launch("p1", container.Limits()))
    net.tar_files = {"src/App.tsx": b"app\n"}
    net.tar_break_second = True                              # erzwingt einen Abbruch → Dev-Server muss wieder an

    with pytest.raises(container.VibeError):
        run(workspace.ensure("p1"))

    systemd = [" ".join(c) for c in net.calls if "systemctl" in c]
    assert any("stop vibe-dev.service" in c for c in systemd)
    assert any("start vibe-dev.service" in c for c in systemd)
    assert systemd.index(next(c for c in systemd if "stop " in c)) < systemd.index(
        next(c for c in systemd if "start " in c)
    )


def test_gestoppter_container_wird_fuer_das_lesen_gestartet_und_danach_wieder_gestoppt(net) -> None:
    run(container.launch("p1", container.Limits()))
    run(container.stop("p1"))
    net.tar_files = {"src/App.tsx": b"app\n"}

    assert run(workspace.ensure("p1")) == "migrated"

    assert net.containers[container.name_for("p1")]["running"] is False       # war aus → bleibt aus
    assert (ensure_workspace("p1") / "src" / "App.tsx").read_text() == "app\n"


def test_gestoppter_container_wird_bei_abbruch_wieder_gestoppt(net) -> None:
    run(container.launch("p1", container.Limits()))
    run(container.stop("p1"))
    net.tar_files = {"x": b"1"}
    net.tar_break_second = True

    with pytest.raises(container.VibeError):
        run(workspace.ensure("p1"))

    assert net.containers[container.name_for("p1")]["running"] is False


def test_absturz_im_gestoppten_zustand_liest_nicht_erneut(net) -> None:
    """Nach `pulled`/`stopped` darf ein Neustart nicht noch einmal aus dem Container lesen."""
    run(container.launch("p1", container.Limits()))
    net.tar_files = {"src/App.tsx": b"app\n"}
    original = workspace_acl.configure_tree

    async def boom(*_a, **_k):
        raise RuntimeError("Absturz nach dem Veröffentlichen")

    workspace_acl.configure_tree = boom
    try:
        with pytest.raises(RuntimeError):
            run(workspace.ensure("p1"))
    finally:
        workspace_acl.configure_tree = original
    reads = net.tar_count

    assert run(workspace.ensure("p1")) == "migrated"

    assert net.tar_count == reads                            # kein weiteres Auslesen
