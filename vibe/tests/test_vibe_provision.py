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


# --- Einrichtung ab einem Schritt (Baustein 6: „Nochmal versuchen“) ---------------------------------------------

def _record_setup(monkeypatch):
    ran: list[str] = []

    async def fake_run(*args, timeout=0, input_bytes=None):
        ran.append(args[-1])
        return 0, "", ""
    monkeypatch.setattr(provision.incus, "run", fake_run)
    return ran


def test_setup_ab_schritt_ueberspringt_die_vorherigen(monkeypatch):
    ran = _record_setup(monkeypatch)
    reported: list[str] = []
    asyncio.run(provision.setup("p1", reported.append, start_at="deps"))
    assert reported == ["deps", "devserver"] and len(ran) == 2


def test_setup_ohne_start_at_laeuft_alles(monkeypatch):
    _record_setup(monkeypatch)
    reported: list[str] = []
    asyncio.run(provision.setup("p1", reported.append))
    assert reported == [s.key for s in provision.STEPS]


def test_setup_unbekannter_schritt_wird_abgelehnt(monkeypatch):
    _record_setup(monkeypatch)
    with pytest.raises(provision.SetupError) as e:
        asyncio.run(provision.setup("p1", lambda k: None, start_at="'; rm -rf /"))
    assert e.value.code == "vibe_setup_failed"


# --- `npm ci` kann „erfolgreich“ enden und trotzdem das native Paket von Vite auslassen -------------------------------
# Gemessen hydratest 5.11.2026: ohne Cache fehlte in 6 von 25 Läufen (rc=0 oder Netzfehler) @rolldown/binding-linux-x64-gnu;
# der Dev-Server stirbt dann mit „Cannot find native binding“ (npm/cli#4828). Mit Prüfung + Wiederholung 25 von 25 ok.

def test_deps_prueft_ob_vite_wirklich_laedt():
    s = step("deps").script
    assert "node_modules/vite/dist/node/index.js" in s and "import(" in s


def test_deps_wiederholt_selbst_bis_vite_laedt():
    s = step("deps").script
    assert "rm -rf node_modules" in s and re.search(r"\b(for|while)\b", s)


def test_deps_hoechstens_drei_innere_versuche():
    s = step("deps").script
    assert re.search(r"\b3\b", s)


def test_deps_scheitert_wenn_vite_nie_laedt():
    """Das Skript muss nach dem letzten Fehlversuch mit Fehlercode enden (`exit 1`), nicht mit dem Code der Prüfung davor."""
    s = step("deps").script
    assert "exit 1" in s


def test_deps_loescht_kein_projektcode():
    """Aufgeräumt wird nur node_modules – nie /work selbst, nie src."""
    s = step("deps").script
    assert "rm -rf node_modules" in s and "rm -rf /work" not in s and "rm -rf src" not in s and "rm -rf *" not in s


def test_deps_bleibt_ein_netzschritt_als_nutzer_ohne_sudo():
    st = step("deps")
    assert st.net and st.as_user and "sudo" not in st.script


def test_deps_skript_hat_keine_platzhalter():
    """Feste Texte: nichts von außen eingesetzt (kein `{name}`, kein Format-Platzhalter)."""
    assert not re.search(r"\{[a-z_]+\}", step("deps").script)


# --- Das Skript wirklich ausführen (Ersatz-`npm` und -`node` in einem Wegwerf-Ordner) ---------------------------------
# Der Text allein sagt nicht, ob es sich richtig verhält. Hier läuft das echte Bash-Skript des Schritts `deps`; die
# Ersatzprogramme steuern, wann `npm ci` etwas anlegt und wann die Ladeprüfung gelingt.

import os
import subprocess
import textwrap


def _run_deps(tmp_path, *, load_ok_from_try: int | None, keep=("src", "package.json")):
    """Führt das Skript aus. `load_ok_from_try`: ab dem wievielten npm-Aufruf lädt Vite (None = nie)."""
    work = tmp_path / "work"
    work.mkdir()
    for k in keep:
        (work / k).write_text("x") if "." in k else (work / k).mkdir()
    (work / "src" / "wichtig.txt").write_text("Projektcode")
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    counter = tmp_path / "n"
    counter.write_text("0")
    (bin_ / "npm").write_text(textwrap.dedent(f"""\
        #!/bin/bash
        n=$(( $(cat {counter}) + 1 )); echo $n > {counter}
        mkdir -p /work_ersatz 2>/dev/null; mkdir -p "$PWD/node_modules/vite/dist/node"
        if [ "$n" -ge {load_ok_from_try or 99} ]; then echo ok > "$PWD/node_modules/vite/dist/node/index.js"; fi
        exit 0
        """))
    (bin_ / "node").write_text(textwrap.dedent("""\
        #!/bin/bash
        [ -f /work/node_modules/vite/dist/node/index.js ] && exit 0 || exit 1
        """))
    for f in bin_.iterdir():
        f.chmod(0o755)
    script = provision.step_script("deps") if hasattr(provision, "step_script") else step("deps").script
    script = script.replace("cd /work;", f"cd {work};").replace("/work/node_modules", f"{work}/node_modules")
    (bin_ / "node").write_text((bin_ / "node").read_text().replace("/work/node_modules", f"{work}/node_modules"))
    env = {"PATH": f"{bin_}:/usr/bin:/bin", "HOME": str(tmp_path)}
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, env=env, timeout=30)
    return r, int(counter.read_text()), work


def test_skript_erster_versuch_laedt_ein_npm_aufruf(tmp_path):
    r, n, work = _run_deps(tmp_path, load_ok_from_try=1)
    assert r.returncode == 0 and n == 1 and (work / "src" / "wichtig.txt").exists()


def test_skript_zweiter_versuch_laedt_zwei_npm_aufrufe(tmp_path):
    r, n, _ = _run_deps(tmp_path, load_ok_from_try=2)
    assert r.returncode == 0 and n == 2


def test_skript_dritter_versuch_laedt_drei_npm_aufrufe(tmp_path):
    r, n, _ = _run_deps(tmp_path, load_ok_from_try=3)
    assert r.returncode == 0 and n == 3


def test_skript_nie_geladen_nach_genau_drei_versuchen_mit_fehlercode(tmp_path):
    r, n, _ = _run_deps(tmp_path, load_ok_from_try=None)
    assert r.returncode == 1 and n == 3 and "Vite lässt sich nach 3 Versuchen nicht laden" in r.stderr


def test_skript_loescht_nur_node_modules_nie_projektcode(tmp_path):
    r, _, work = _run_deps(tmp_path, load_ok_from_try=None)
    assert (work / "src" / "wichtig.txt").read_text() == "Projektcode" and (work / "package.json").exists()
    assert not (work / "node_modules").exists()                 # nach dem Fehlschlag aufgeräumt


def test_skript_raeumt_zwischen_den_versuchen_node_modules_weg(tmp_path):
    """Beim 2. Versuch darf nichts vom 1. übrig sein – sonst würde eine halbe Installation für fertig gehalten."""
    r, n, work = _run_deps(tmp_path, load_ok_from_try=3)
    assert r.returncode == 0 and n == 3 and (work / "node_modules" / "vite" / "dist" / "node" / "index.js").exists()


def test_skript_npm_fehlercode_allein_entscheidet_nicht(tmp_path):
    """Selbst wenn `npm ci` rc=0 meldet, zählt nur, ob Vite wirklich lädt (npm/cli#4828)."""
    r, n, _ = _run_deps(tmp_path, load_ok_from_try=None)
    assert r.returncode == 1
