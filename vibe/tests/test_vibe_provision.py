"""Baustein 3: Einrichtung im Container (PLAN-V1.md; Muster hydralabor/tests/test_labor_setup.py).

Die Skripte sind feste Texte im Modul. Der Kern-Launcher setzt `HOME=/home/labor` und arbeitet als UID 1000 in /work –
der Nutzer im Container MUSS deshalb `labor` heißen (gelesen in tools/_launcher_container.py, 5.11.).
"""
from __future__ import annotations

import asyncio
import re

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
    assert "useradd -m -u 1000 -s /bin/bash labor;" in script
    assert "usermod -l labor -d /home/labor -m ubuntu" in script and "install -d -o labor -g labor /work" in script
    assert "vibe" not in script.split("useradd")[1].split(";")[0]


def test_nutzer_ohne_sudo():
    script = step("user").script
    assert "gpasswd -d labor sudo" in script and "/etc/sudoers.d/" in script


def test_pakete_nur_das_noetige():
    script = step("packages").script
    for pkg in ("git", "curl", "ca-certificates", "xz-utils", "ripgrep"):
        assert f" {pkg}" in script
    # Befund hydratest 5.11. (echte Probe): Der offizielle Node-Tarball bricht im schlanken Ubuntu-Container mit
    # „libatomic.so.1: cannot open shared object file“ ab. Ohne diese Bibliothek scheitert jeder Projektstart.
    assert " libatomic1" in script
    for unnoetig in ("build-essential", "python3-pip", "qemu-utils", "docker"):
        assert unnoetig not in script


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
