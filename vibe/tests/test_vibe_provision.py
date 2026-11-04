"""Baustein 3: Einrichtung im Container (PLAN-V1.md; Muster hydralabor/tests/test_labor_setup.py).

Die Skripte sind feste Texte im Modul. Der Kern-Launcher setzt `HOME=/home/labor` und arbeitet als UID 1000 in /work –
der Nutzer im Container MUSS deshalb `labor` heißen (gelesen in tools/_launcher_container.py, 5.11.).
"""
from __future__ import annotations

import asyncio
import io
import re
import tarfile

import pytest
from backend import container, network, provision


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def box(fake_incus, monkeypatch):
    monkeypatch.setattr(network, "_host_networks", lambda: set())
    monkeypatch.setattr(network, "_host_addresses", lambda: set())
    monkeypatch.setattr(container, "_ubuntu_version", lambda: "24.04")
    run(network.ensure_network())
    run(container.launch("p1", container.Limits()))
    return fake_incus


def execs(fake):
    return [c for c in fake.calls if c[0] == "exec" and "hh-vibe-p1" in c]


def step(key):
    return next(s for s in provision.STEPS if s.key == key)


def test_schritte_in_fester_reihenfolge():
    assert [s.key for s in provision.STEPS] == ["user", "packages", "node", "template", "git", "deps", "devserver"]


def test_genau_diese_schritte_als_nutzer():
    assert [s.key for s in provision.STEPS if s.as_user] == ["template", "git", "deps"]


def test_alle_schritte_laufen_und_melden(box):
    seen = []
    run(provision.setup("p1", seen.append))
    assert seen == [s.key for s in provision.STEPS]
    assert len(execs(box)) == len(provision.STEPS)


def test_nutzerschritte_als_uid_1000_in_work_mit_home(box):
    run(provision.setup("p1", lambda _k: None))
    for s, call in zip(provision.STEPS, execs(box), strict=True):
        as_user = call[call.index("--user") + 1] if "--user" in call else None
        assert as_user == ("1000" if s.as_user else None), s.key
        if s.as_user:
            assert call[call.index("--cwd") + 1] == "/work"
            assert "HOME=/home/labor" in call
            assert call[call.index("--group") + 1] == "1000"


def test_nutzer_heisst_labor_wie_im_kern_launcher():
    """Der Kern setzt HOME=/home/labor fest; ein anderer Name liesse npm/git ins Leere schreiben."""
    script = step("user").script
    assert "labor" in script and "/home/labor" in script and "useradd -m -u 1000" in script


def test_nutzer_ohne_sudo():
    script = step("user").script
    assert "gpasswd -d labor sudo" in script and "/etc/sudoers.d/" in script


def test_pakete_nur_das_noetige():
    script = step("packages").script
    for pkg in ("git", "curl", "ca-certificates", "xz-utils", "ripgrep"):
        assert f" {pkg}" in script
    for unnoetig in ("build-essential", "python3-pip", "qemu-utils", "docker"):
        assert unnoetig not in script


# --- Node ------------------------------------------------------------------------------------------------------

def test_node_fest_gepinnt_mit_pruefsumme():
    s = step("node").script
    assert provision.NODE_VERSION in s and provision.NODE_SHA256 in s
    assert re.fullmatch(r"v\d+\.\d+\.\d+", provision.NODE_VERSION)
    assert re.fullmatch(r"[0-9a-f]{64}", provision.NODE_SHA256)
    assert "sha256sum -c" in s


def test_node_ohne_pipe_in_die_shell():
    """Das Labor nutzt `curl … | bash` (NodeSource). Vibe lädt einen Tarball und prüft ihn, führt nichts Fremdes aus."""
    s = step("node").script
    assert "| bash" not in s and "| sh" not in s and "nodesource" not in s.lower()
    assert "https://nodejs.org/dist/" in s


def test_node_pruefung_vor_dem_entpacken():
    s = step("node").script
    assert s.index("sha256sum -c") < s.index("tar -xJ")


def test_node_version_wird_nach_dem_einrichten_geprueft():
    assert f"node -v | grep -qx {provision.NODE_VERSION}" in step("node").script


def test_node_ist_nicht_die_zu_alte_ubuntu_version():
    """Befund hydratest 4.11.: Node 18 aus apt kann `create-vite` nicht ausführen."""
    assert "apt-get install" in step("packages").script and "nodejs" not in step("packages").script


# --- Vorlage ---------------------------------------------------------------------------------------------------

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


def test_vorlage_ist_klein():
    assert len(provision.template_tar()) < 1_000_000


def test_vorlage_wird_per_stdin_in_den_container_geschoben(box):
    run(provision.setup("p1", lambda _k: None))
    pushes = [(a, b) for a, b in box.inputs if "tar" in a]
    assert len(pushes) == 1
    a, data = pushes[0]
    assert "--no-same-owner" in a and a[a.index("-C") + 1] == "/work"
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


# --- Git und Abhängigkeiten ------------------------------------------------------------------------------------

def test_git_erst_commit_start_ohne_hooks():
    s = step("git").script
    assert "git init" in s and "Start" in s and "core.hooksPath /dev/null" in s
    assert "user.name" in s and "user.email" in s


def test_git_ohne_zugangsdaten_und_ohne_remote():
    s = step("git").script
    assert "remote" not in s and "token" not in s.lower() and "http" not in s


def test_abhaengigkeiten_mit_npm_ci_als_nutzer():
    s = step("deps").script
    assert "npm ci" in s and "--no-audit" in s and "sudo" not in s


# --- Dev-Server ------------------------------------------------------------------------------------------------

def test_devserver_als_dienst_der_nach_dem_wecken_wieder_startet():
    s = step("devserver").script
    assert "vibe-dev.service" in s and "Restart=always" in s and "User=labor" in s
    assert "systemctl enable" in s and "WantedBy=multi-user.target" in s
    assert "/work/node_modules/vite/bin/vite.js" in s


def test_devserver_wartet_auf_antwort():
    s = step("devserver").script
    assert "127.0.0.1:5173" in s and "curl" in s


# --- Fehler und Sicherheit der Skripte -------------------------------------------------------------------------

def test_schritt_scheitert_meldet_schritt(box):
    box.exec_answers["sha256sum -c"] = (1, "")
    seen = []
    with pytest.raises(provision.SetupError) as e:
        run(provision.setup("p1", seen.append))
    assert e.value.code == "vibe_setup_failed" and e.value.step == "node"
    assert seen == ["user", "packages", "node"]


def test_nach_fehler_keine_weiteren_schritte(box):
    box.exec_answers["git init"] = (1, "")
    with pytest.raises(provision.SetupError):
        run(provision.setup("p1", lambda _k: None))
    assert not any("npm ci" in " ".join(c) for c in box.calls)


def test_skripte_sind_feste_texte_ohne_platzhalter():
    """Keine Eingabe des Nutzers landet je in einem Skript: nichts wird per Formatierung eingesetzt, und der
    Projekt-Name/die ID kommt in KEINEM Skript vor (der Container-Name steckt nur in der incus-Argumentliste)."""
    for s in provision.STEPS:
        assert not re.search(r"%\(|%s|\{\w+\}", s.script), s.key
        assert "hh-vibe" not in s.script and "project" not in s.script.lower(), s.key
        assert isinstance(s.script, str) and s.script == s.script.strip(), s.key


def test_unbekannter_container_wird_abgelehnt(box):
    with pytest.raises(container.VibeError):
        run(provision.setup("../hh-labor", lambda _k: None))
    assert execs(box) == []


def test_kein_token_in_den_befehlen(box):
    run(provision.setup("p1", lambda _k: None))
    line = " ".join(" ".join(c) for c in box.calls)
    for wort in ("GH_TOKEN", "GITEA_TOKEN", "HH_SECRET", "secret_key"):
        assert wort not in line
