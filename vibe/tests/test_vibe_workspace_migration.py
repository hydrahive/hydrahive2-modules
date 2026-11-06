from __future__ import annotations

import asyncio
import json

import pytest
from _hh_isolation import remove_test_tree
from hydrahive.projects._paths import ensure_workspace

from backend import container, network, workspace, workspace_acl


def run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def clean_workspace():
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


def _device(fake) -> dict | None:
    return fake.containers[container.name_for("p1")]["devices"].get(workspace.DEVICE)


def _container_has_data(fake) -> None:
    fake.exec_answers["find /work"] = (0, "/work/src/App.tsx\n")


def test_bestehendes_work_wird_aus_gestopptem_container_geholt(net) -> None:
    run(container.launch("p1", container.Limits()))
    _container_has_data(net)

    assert run(workspace.ensure("p1")) == "migrated"

    commands = [" ".join(call) for call in net.calls]
    assert any("stop hh-vibe-p1 --force" in call for call in commands)
    assert any("security.idmap.isolated true" in call for call in commands)
    assert any("exec hh-vibe-p1 -- tar -C /work" in call for call in commands)   # tar-Strom statt `file pull`
    assert not any("file pull" in call for call in commands)                       # nie wieder: hängt bei FIFOs
    assert net.tar_count == 2                                                      # zweimal gelesen und verglichen
    assert _device(net)["source"] == str(ensure_workspace("p1"))
    assert (ensure_workspace("p1") / "src" / "App.tsx").read_text() == "app\n"
    assert not workspace._marker("p1").exists()
    assert net.containers[container.name_for("p1")]["running"] is True


def test_migration_verweigert_zwei_unabhaengige_datenbestaende(net) -> None:
    run(container.launch("p1", container.Limits()))
    _container_has_data(net)
    (ensure_workspace("p1") / "host.txt").write_text(
        "nicht überschreiben", encoding="utf-8"
    )

    with pytest.raises(container.VibeError) as exc:
        run(workspace.ensure("p1"))

    assert exc.value.code == "vibe_workspace_conflict"
    assert _device(net) is None
    assert not workspace._marker("p1").exists()
    assert net.containers[container.name_for("p1")]["running"] is True


def test_lesefehler_hinterlaesst_nichts_halbes_und_ist_wiederholbar(net) -> None:
    run(container.launch("p1", container.Limits()))
    _container_has_data(net)
    net.fail["tar -C /work"] = "abgebrochen"

    with pytest.raises(container.VibeError):
        run(workspace.ensure("p1"))

    assert not workspace._marker("p1").exists()                  # nichts gestoppt, nichts veröffentlicht
    assert not any(ensure_workspace("p1").iterdir())
    assert net.containers[container.name_for("p1")]["running"] is True
    assert not [c for c in net.calls if c[:1] == ["stop"] and c[1:2] == ["hh-vibe-p1"]]
    net.fail.clear()

    assert run(workspace.ensure("p1")) == "migrated"
    assert not workspace._marker("p1").exists()


def test_crash_nach_publish_wird_ohne_zweite_kopie_fortgesetzt(net) -> None:
    run(container.launch("p1", container.Limits()))
    name = container.name_for("p1")
    net.containers[name]["running"] = False
    host = ensure_workspace("p1")
    (host / "bereits-kopiert.txt").write_text("ok", encoding="utf-8")
    info = host.stat()  # Absturz NACH os.replace: der Marker trägt die Inode des gezogenen Baums
    workspace._marker("p1").write_text(
        json.dumps(
            {
                "stage": "pulled",
                "was_running": True,
                "source_dev": info.st_dev,
                "source_ino": info.st_ino,
            }
        ),
        encoding="utf-8",
    )

    assert run(workspace.ensure("p1")) == "migrated"

    assert _device(net)["source"] == str(host)
    assert net.containers[name]["running"] is True
    assert not workspace._marker("p1").exists()


def test_urspruenglich_gestoppter_container_bleibt_gestoppt(net) -> None:
    run(container.launch("p1", container.Limits()))
    _container_has_data(net)
    run(container.stop("p1"))

    assert run(workspace.ensure("p1")) == "migrated"

    assert net.containers[container.name_for("p1")]["running"] is False


def test_laufender_agent_blockiert_migration(net, monkeypatch) -> None:
    run(container.launch("p1", container.Limits()))
    from hydrahive.runner import concurrency

    from backend import workspace_lock

    monkeypatch.setattr(workspace_lock, "_session_rows", lambda: [("s1", "agent-1", "p1")])

    async def scenario():
        async with concurrency.session_run_guard("s1"):  # ein Lauf ist aktiv
            await workspace.ensure("p1", agent_id="agent-1")

    with pytest.raises(container.VibeError) as exc:
        run(scenario())

    assert exc.value.code == "vibe_busy"
    assert _device(net) is None


def test_korrupter_migrationsmarker_blockiert_jeden_neuen_mount(net) -> None:
    run(container.launch("p1", container.Limits()))
    workspace._marker("p1").write_text("unterbrochen\n", encoding="utf-8")

    with pytest.raises(container.VibeError) as exc:
        run(workspace.ensure("p1"))

    assert exc.value.code == "vibe_workspace_migration_failed"
    assert _device(net) is None


def test_acl_nutzt_die_idmap_des_naechsten_starts_nach_isolierung(net, monkeypatch) -> None:
    """Realer Befund: Nach `security.idmap.isolated=true` zeigt `current` noch die alte Zuordnung bis zum Start.
    Die ACL muss für die Zuordnung gelten, mit der der Container wieder startet (`next`), sonst darf UID 1000 nie schreiben."""
    calls: list[list[str]] = []
    monkeypatch.setattr(workspace_acl, "_run", lambda args: calls.append(args))
    run(container.launch("p1", container.Limits()))
    _container_has_data(net)

    run(workspace.ensure("p1"))

    joined = " ".join(" ".join(call) for call in calls)
    assert "u:1066536:rwx" in joined and "g:1066536:rwx" in joined      # 1_065_536 + 1000
    assert "u:1001000:rwx" not in joined
