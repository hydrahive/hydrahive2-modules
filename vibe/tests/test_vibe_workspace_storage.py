from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest
from _hh_isolation import remove_test_tree
from hydrahive.projects._paths import ensure_workspace

from backend import container, network, workspace, workspace_acl


def run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def clean_named_workspaces():
    for pid in ("p1", "p2"):
        path = ensure_workspace(pid)
        if path.exists():
            remove_test_tree(path)
        workspace.forget(pid)
    yield
    for pid in ("p1", "p2"):
        path = ensure_workspace(pid)
        if path.exists():
            remove_test_tree(path)
        workspace.forget(pid)


@pytest.fixture
def net(fake_incus, monkeypatch):
    monkeypatch.setattr(network, "_host_networks", lambda: set())
    monkeypatch.setattr(network, "_host_addresses", lambda: {"192.168.178.2/32"})
    run(network.ensure_network())
    return fake_incus


@pytest.fixture
def acl_calls(monkeypatch):
    calls: list[list[str]] = []
    monkeypatch.setattr(workspace_acl, "_run", lambda args: calls.append(args))
    monkeypatch.setattr(workspace_acl.os, "getuid", lambda: 997)
    monkeypatch.setattr(workspace_acl.os, "getgid", lambda: 987)
    return calls


def _device(fake, pid: str) -> dict | None:
    return fake.containers[container.name_for(pid)]["devices"].get(workspace.DEVICE)


def test_neues_projekt_mountet_seinen_hydrahive_workspace_als_work(
    net, acl_calls
) -> None:
    run(container.launch("p1", container.Limits()))

    run(workspace.attach_new("p1"))

    host = ensure_workspace("p1")
    assert _device(net, "p1") == {"type": "disk", "source": str(host), "path": "/work"}
    joined = " ".join(" ".join(call) for call in acl_calls)
    assert "u:1001000:rwx" in joined and "g:1001000:rwx" in joined
    assert "u:997:rwx" in joined and "g:987:rwx" in joined


def test_mount_ist_idempotent_und_verlangt_dieselbe_quelle(net, acl_calls) -> None:
    run(container.launch("p1", container.Limits()))
    run(workspace.attach_new("p1"))

    assert run(workspace.ensure("p1")) == "ready"
    adds = [call for call in net.calls if call[:3] == ["config", "device", "add"]]
    assert len(adds) == 1

    net.containers[container.name_for("p1")]["devices"][workspace.DEVICE]["source"] = (
        "/fremd"
    )
    with pytest.raises(container.VibeError) as exc:
        run(workspace.ensure("p1"))
    assert exc.value.code == "vibe_workspace_conflict"


def test_zwei_projekte_erhalten_getrennte_container_ids(net, acl_calls) -> None:
    run(container.launch("p1", container.Limits()))
    run(workspace.attach_new("p1"))
    run(container.launch("p2", container.Limits()))
    run(workspace.attach_new("p2"))

    joined = " ".join(" ".join(call) for call in acl_calls)
    assert "u:1001000:rwx" in joined
    assert "u:2001000:rwx" in joined


def test_acl_fehlende_idmap_wird_nicht_geraten(net, acl_calls) -> None:
    run(container.launch("p1", container.Limits()))
    net.fail["volatile.idmap.current"] = "nicht verfügbar"
    net.fail["volatile.idmap.next"] = "nicht verfügbar"

    with pytest.raises(container.VibeError) as exc:
        run(workspace.attach_new("p1"))

    assert exc.value.code == "vibe_workspace_unavailable"
    assert _device(net, "p1") is None


def test_bestehende_hostdateien_erhalten_rekursive_und_default_acls(
    net, acl_calls
) -> None:
    run(container.launch("p1", container.Limits()))
    host = ensure_workspace("p1")
    (host / "src").mkdir()
    (host / "src" / "App.tsx").write_text("app", encoding="utf-8")

    run(workspace_acl.configure_tree(container.name_for("p1"), host))

    assert any(call[:2] == ["-R", "-m"] for call in acl_calls)
    defaults = [call for call in acl_calls if call[:2] == ["-d", "-m"]]
    assert any(str(host / "src") in call for call in defaults)


def test_incus_ausfall_gilt_nicht_als_fehlendes_device(net, acl_calls) -> None:
    run(container.launch("p1", container.Limits()))
    net.fail["config device get"] = "daemon nicht erreichbar"

    with pytest.raises(container.VibeError) as exc:
        run(workspace.ensure("p1"))

    assert exc.value.code == "vibe_workspace_unavailable"
    assert not any(call[:3] == ["config", "device", "add"] for call in net.calls)


def test_workspace_symlink_aus_dem_projektroot_wird_abgelehnt(net, acl_calls) -> None:
    run(container.launch("p1", container.Limits()))
    path = ensure_workspace("p1")
    remove_test_tree(path)
    target = Path(os.environ["HH_DATA_DIR"]) / "escape"
    target.mkdir(parents=True, exist_ok=True)
    path.symlink_to(target, target_is_directory=True)
    try:
        with pytest.raises(container.VibeError) as exc:
            run(workspace.attach_new("p1"))
        assert exc.value.code == "vibe_workspace_unavailable"
        assert _device(net, "p1") is None
    finally:
        path.unlink(missing_ok=True)
        remove_test_tree(target)


def test_forget_entfernt_nur_den_marker_des_projekts() -> None:
    own = workspace._marker("p1")
    other = workspace._marker("p2")
    own.write_text("x", encoding="utf-8")
    other.write_text("y", encoding="utf-8")

    workspace.forget("p1")

    assert not own.exists()
    assert other.exists()


def test_workspace_bleibt_im_projekt_datenroot(net, acl_calls) -> None:
    run(container.launch("p1", container.Limits()))
    run(workspace.attach_new("p1"))

    source = Path(_device(net, "p1")["source"])
    assert source == ensure_workspace("p1")
    assert source.is_relative_to(
        Path(os.environ["HH_DATA_DIR"]) / "workspaces" / "projects"
    )
