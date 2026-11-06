"""Review 6, Teil 3: Archivgrenzen (Mitglieder, Größe, Tiefe, Name) und Zeitbegrenzung des Entpackers."""

from __future__ import annotations

import asyncio
import io
import tarfile

import pytest
from _hh_isolation import remove_test_tree
from hydrahive.projects._paths import ensure_workspace

from backend import (
    container,
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


# --- MITTEL: Grenzen für Mitglieder, logische Größe, Tiefe, Namen ---------------------------------------------------------


def test_zu_viele_mitglieder_werden_abgelehnt(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(workspace_tar, "MAX_MEMBERS", 5)
    members = [(_info(f"d{i}", tarfile.DIRTYPE, mode=0o755), None) for i in range(6)]

    with pytest.raises(container.VibeError) as exc:
        workspace_tar.extract(_tar(tmp_path, *members), tmp_path / "out")

    assert exc.value.code == "vibe_workspace_too_large"


def test_zu_grosse_gesamtgroesse_wird_abgelehnt(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(workspace_tar, "MAX_TOTAL_BYTES", 10)
    members = [(_info("a", size=6), b"abcdef"), (_info("b", size=6), b"abcdef")]

    with pytest.raises(container.VibeError) as exc:
        workspace_tar.extract(_tar(tmp_path, *members), tmp_path / "out")

    assert exc.value.code == "vibe_workspace_too_large"
    assert not (tmp_path / "out" / "work" / "b").exists()


def test_deklarierte_groesse_wird_vor_dem_schreiben_geprueft(tmp_path, monkeypatch) -> None:
    """Eine einzelne riesige Mitgliedergröße (z. B. Sparse) wird abgelehnt, bevor Daten geschrieben werden."""
    monkeypatch.setattr(workspace_tar, "MAX_TOTAL_BYTES", 100)
    archive = tmp_path / "x.tar"
    with open(archive, "wb") as handle:
        handle.write(_info("riesig", size=10**12).tobuf(tarfile.PAX_FORMAT))   # Header ohne Daten, Archiv ist kurz

    with pytest.raises(container.VibeError) as exc:
        workspace_tar.extract(archive, tmp_path / "out")

    assert exc.value.code == "vibe_workspace_too_large"
    assert not (tmp_path / "out" / "work" / "riesig").exists()


def test_zu_tiefe_pfade_und_zu_lange_namen_werden_abgelehnt(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(workspace_tar, "MAX_DEPTH", 4)
    deep = "/".join(["d"] * 6)
    with pytest.raises(container.VibeError) as exc:
        workspace_tar.extract(_tar(tmp_path, (_info(deep, size=1), b"x")), tmp_path / "out")
    assert exc.value.code == "vibe_workspace_too_large"

    monkeypatch.setattr(workspace_tar, "MAX_NAME", 20)
    with pytest.raises(container.VibeError):
        workspace_tar.extract(_tar(tmp_path, (_info("x" * 40, size=1), b"x")), tmp_path / "out2")


def test_normale_projekte_liegen_deutlich_unter_den_grenzen() -> None:
    assert workspace_tar.MAX_MEMBERS >= 200_000
    assert workspace_tar.MAX_TOTAL_BYTES >= 5 << 30         # mindestens die 5-GB-Projektgrenze
    assert workspace_tar.MAX_DEPTH >= 64


# --- MITTEL/NIEDRIG: Fehlercode „Projekt weg“ bleibt erhalten --------------------------------------------------------------


def test_job_behaelt_den_fehlercode_projekt_nicht_gefunden(setup_test_env, db_ready, fake_incus, monkeypatch) -> None:
    from backend import jobs, state

    async def gone(*_a, **_k):
        raise container.VibeError("vibe_project_not_found")

    monkeypatch.setattr(jobs.workspace, "ensure", gone)
    monkeypatch.setattr(state, "get_row", lambda pid: {"agent_id": "a", "progress": ""})
    monkeypatch.setattr(state, "set_state", lambda *a, **k: None)

    with pytest.raises(jobs.JobError) as exc:
        run(jobs._setup("p-weg"))

    assert exc.value.code == "vibe_project_not_found"


def test_hardlink_ohne_ziel_wird_vor_jeder_dateisystemoperation_abgelehnt(tmp_path, monkeypatch) -> None:
    """Die Prüfung des Hardlink-Ziels steht VOR dem Dateisystemzugriff – es hängt nicht vom Auffangnetz ab."""
    calls: list[str] = []
    real = workspace_tar._real_dirs_only

    def spy(root, parts):
        calls.append("real_dirs_only")
        return real(root, parts)

    monkeypatch.setattr(workspace_tar, "_real_dirs_only", spy)
    archive = _tar(tmp_path, (_info("h", tarfile.LNKTYPE, link="."), None))

    with pytest.raises(container.VibeError):
        workspace_tar.extract(archive, tmp_path / "out")

    assert calls == ["real_dirs_only"]          # nur für den Namen „h“, nie für das leere Ziel


@pytest.mark.parametrize("size", [0, 5, 1 << 20, (1 << 20) + 7])
def test_zeitstempel_von_dateien_und_ordnern_bleibt_erhalten(tmp_path, size) -> None:
    """Echtlauf-Befund: Gepufferte Daten wurden erst beim Schließen geschrieben und setzten die Zeit auf „jetzt“."""
    stamp = 915_246_245                                       # 1999-01-02
    archive = _tar(
        tmp_path,
        (_info("d", tarfile.DIRTYPE, mtime=stamp), None),
        (_info("d/f", size=size, mtime=stamp), b"x" * size),
    )

    root = workspace_tar.extract(archive, tmp_path / "out")

    assert int((root / "d" / "f").stat().st_mtime) == stamp
    assert int((root / "d").stat().st_mtime) == stamp
