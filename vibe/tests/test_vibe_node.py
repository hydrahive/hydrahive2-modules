"""Baustein 3: Node im Container – gepinnt, geprüft, ohne fremde Skripte (PLAN-V1.md).

Zweiter Teil zu test_vibe_provision.py (Datei geteilt: höchstens 200 Zeilen je Datei).
"""
from __future__ import annotations

import re

from backend import provision


def step(key):
    return next(s for s in provision.STEPS if s.key == key)


def test_node_fest_gepinnt_mit_pruefsumme():
    s = step("node").script
    assert provision.NODE_VERSION in s and provision.NODE_SHA256 in s
    assert re.fullmatch(r"v\d+\.\d+\.\d+", provision.NODE_VERSION)
    assert re.fullmatch(r"[0-9a-f]{64}", provision.NODE_SHA256)
    assert "sha256sum -c" in s


def test_node_download_mit_wiederholung_und_zeitlimit():
    """Echte Probe hydratest 5.11.: Ein Lauf scheiterte am Node-Schritt nach 127 s, nicht wiederholbar (Ursache nicht
    bewiesen). Ein hängender Download darf weder ewig laufen noch beim ersten Aussetzer das Projekt kippen lassen."""
    s = step("node").script
    for opt in ("--retry 3", "--retry-delay 2", "--connect-timeout 15", "--max-time 180"):
        assert opt in s, opt
    assert s.index("--max-time") < s.index("sha256sum -c")


def test_node_ohne_pipe_in_die_shell():
    """Das Labor nutzt `curl … | bash` (NodeSource). Vibe lädt einen Tarball und prüft ihn, führt nichts Fremdes aus."""
    s = step("node").script
    assert not re.search(r"\|\s*(ba|z)?sh\b", s) and "nodesource" not in s.lower()
    assert "https://nodejs.org/dist/" in s


def test_node_pruefung_vor_dem_entpacken():
    s = step("node").script
    assert s.index("sha256sum -c") < s.index("tar -xJ")


def test_node_version_wird_nach_dem_einrichten_geprueft():
    assert f"node -v | grep -qx {provision.NODE_VERSION}" in step("node").script


def test_node_pruefsumme_ist_die_von_nodejs_org():
    """Wert aus SHASUMS256.txt von nodejs.org (abgerufen 4.11.2026, Version v26.13.0). Ändert sich NODE_VERSION, muss
    dieser Wert mit; ein falscher Wert würde die Einrichtung jedes Projekts scheitern lassen (sha256sum -c)."""
    assert provision.NODE_VERSION == "v26.13.0"
    assert provision.NODE_SHA256 == "d28a96af6c38596f6d9d97c0ee531c13d238d757742387d1928de822d959e997"
    assert f"{provision.NODE_SHA256}  node-v26.13.0-linux-x64.tar.xz" in step("node").script


def test_node_ist_nicht_die_zu_alte_ubuntu_version():
    """Befund hydratest 4.11.: Node 18 aus apt kann `create-vite` nicht ausführen."""
    assert "apt-get install" in step("packages").script and "nodejs" not in step("packages").script
