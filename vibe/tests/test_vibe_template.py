"""Baustein 3: Die Vorlage (Vite + React) – Inhalt, Sicherheit der Verpackung, Pinning (PLAN-V1.md).

Zweiter Teil zu test_vibe_provision.py (Datei geteilt: höchstens 200 Zeilen je Datei).
"""
from __future__ import annotations

import asyncio
import io
import tarfile

import pytest
from backend import container, network, provision


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def box(fake_incus, monkeypatch):
    monkeypatch.setattr(network, "_host_networks", lambda: set())
    monkeypatch.setattr(network, "_host_addresses", lambda: set())
    run(network.ensure_network())
    run(container.launch("p1", container.Limits()))
    return fake_incus


def _tar_names(data: bytes) -> list[str]:
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as t:
        return t.getnames()


def test_vorlage_enthaelt_das_noetige():
    names = set(_tar_names(provision.template_tar()))
    for f in ("package.json", "package-lock.json", "vite.config.ts", "index.html", "VIBE.md",
              "public/vibe-report.js", "src/App.tsx", "src/main.tsx", ".gitignore"):
        assert f in names, f


def test_vorlage_ohne_node_modules_und_ohne_dist():
    names = _tar_names(provision.template_tar())
    assert not any(n.startswith(("node_modules", "dist")) or "/node_modules/" in n for n in names)


def test_vorlage_pfade_sicher_nur_dateien():
    with tarfile.open(fileobj=io.BytesIO(provision.template_tar()), mode="r:*") as t:
        for m in t.getmembers():
            assert not m.name.startswith(("/", "..")) and ".." not in m.name.split("/"), m.name
            assert m.isfile() or m.isdir(), (m.name, "keine Links/Geräte")
            assert m.uid == 0 and m.gid == 0 and m.uname == "" and m.gname == "", m.name   # neutral verpackt
            assert not m.mode & 0o6000, m.name               # kein setuid/setgid


def test_vorlage_filter_haelt_node_modules_und_dist_fern(monkeypatch, tmp_path):
    """Auch wenn jemand `npm install` im Vorlagenordner ausführt, gelangt das nicht in jede Vorlage."""
    for d in ("node_modules/x", "dist/assets", "src"):
        (tmp_path / d).mkdir(parents=True)
    (tmp_path / "node_modules/x/a.js").write_text("x")
    (tmp_path / "dist/assets/b.js").write_text("x")
    (tmp_path / "src/ok.ts").write_text("x")
    (tmp_path / "package.json").write_text("{}")
    monkeypatch.setattr(provision, "TEMPLATE_DIR", tmp_path)
    names = _tar_names(provision.template_tar())
    assert "src/ok.ts" in names and "package.json" in names
    assert not any(n.startswith(("node_modules", "dist")) for n in names)


def test_vorlage_nimmt_keine_links_mit(monkeypatch, tmp_path):
    """Ein Link im Vorlagenordner (z. B. auf /etc/passwd) darf nie in den Container gelangen."""
    (tmp_path / "ok.txt").write_text("x")
    (tmp_path / "boese").symlink_to("/etc/passwd")
    (tmp_path / "ordner").mkdir()
    (tmp_path / "ordner" / "weg").symlink_to("/etc")
    monkeypatch.setattr(provision, "TEMPLATE_DIR", tmp_path)
    names = _tar_names(provision.template_tar())
    assert "ok.txt" in names and "boese" not in names and "ordner/weg" not in names


def test_vorlage_ist_klein():
    assert len(provision.template_tar()) < 1_000_000


def test_vorlage_wird_per_stdin_in_den_container_geschoben(box):
    run(provision.setup("p1", lambda _k: None))
    pushes = [(a, b) for a, b in box.inputs if "tar -x" in " ".join(a)]
    assert len(pushes) == 1
    a, data = pushes[0]
    line = " ".join(a)
    assert "--no-same-owner" in line and "tar -x -C /work" in line and a[a.index("--user") + 1] == "1000"
    assert data == provision.template_tar()


def test_vite_erlaubt_fremde_hostnamen():
    """Befund hydratest 4.11.: Vite antwortet auf einen fremden Host-Kopf mit 403."""
    cfg = provision.template_file("vite.config.ts")
    assert "allowedHosts: true" in cfg and "5173" in cfg and "strictPort: true" in cfg


def test_meldeskript_ist_eingebunden():
    assert '<script src="/vibe-report.js"></script>' in provision.template_file("index.html")
    assert "postMessage" in provision.template_file("public/vibe-report.js")


def test_versionen_in_der_vorlage_sind_gepinnt():
    import json
    lock = json.loads(provision.template_file("package-lock.json"))
    assert lock["lockfileVersion"] >= 3 and len(lock["packages"]) > 10
