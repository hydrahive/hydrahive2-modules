"""Hilfe-Guard im Modul-Repo (docs/specs/hilfe-guard.md §2/§5, Abnahme HG3). Nur stdlib + pytest."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import check_help_updated as guard  # noqa: E402


def _eval(files, *, body="", ui_manifests=()):
    return guard.evaluate(list(files), body=body, ui_manifests=set(ui_manifests))


def _help(module):
    return f"{module}/frontend/help/de/{module}.md"


# --- nutzersichtbar: je Muster ---------------------------------------------------------------------------------

@pytest.mark.parametrize(("path", "module"), [
    ("atelier/frontend/AtelierPage.tsx", "atelier"),
    ("studio/frontend/components/Panel.tsx", "studio"),
    ("storyteller/frontend/views/deep/Tab.tsx", "storyteller"),
    ("vibe/frontend/i18n/de.ts", "vibe"),
    ("vibe/frontend/i18n/de/labels.json", "vibe"),
    ("vibe/frontend/i18n/de-extra.ts", "vibe"),
])
def test_nutzersichtbar_wird_erkannt(path, module):
    result = _eval([path])
    assert result.modules == {module: [path]}
    assert result.violation


@pytest.mark.parametrize("path", [
    "atelier/frontend/AtelierEmpty.test.tsx",          # Test
    "atelier/frontend/__tests__/Panel.tsx",            # __tests__/
    "atelier/frontend/tests/helper.tsx",               # tests/ im Frontend
    "atelier/tests/test_api.py",                       # Backend-Test
    "atelier/frontend/Panel.spec.tsx",
    "atelier/frontend/api.ts",                         # nur .tsx zählt
    "atelier/frontend/styles.css",
    "atelier/frontend/i18n/en.ts",                     # nur Deutsch
    "atelier/frontend/i18n.ts",                        # Spec nennt frontend/i18n/de*, nicht i18n.ts
    "atelier/backend/routes.py",
    "atelier/SPEC.md",                                 # Doku allein löst nichts aus
    "atelier/manifest.json",                           # Manifest ohne routes/nav/settings-Änderung
    "atelier/frontend/help/de/atelier.md",             # Hilfe selbst ist nicht „sichtbar“
    "README.md",
    "scripts/check_help_updated.py",
    ".github/workflows/hilfe-guard.yml",
    "ziele/hilfe-aktuell.md",
    "frontend/Top.tsx",                                # kein Modulordner
])
def test_unsichtbar_loest_nichts_aus(path):
    result = _eval([path])
    assert result.modules == {}
    assert result.ok


def test_tests_und_doku_zusammen_loesen_nichts_aus():
    assert _eval(["atelier/frontend/A.test.tsx", "atelier/SPEC.md", "atelier/tests/test_a.py"]).ok


# --- Manifest nur bei routes / nav / settings -----------------------------------------------------------------------

def test_manifest_zaehlt_nur_wenn_freigegeben():
    assert _eval(["atelier/manifest.json"]).ok
    result = _eval(["atelier/manifest.json"], ui_manifests=["atelier"])
    assert result.modules == {"atelier": ["atelier/manifest.json"]}
    assert result.violation


def test_manifest_freigabe_gilt_nur_fuer_das_eigene_modul():
    assert _eval(["studio/manifest.json"], ui_manifests=["atelier"]).ok


@pytest.mark.parametrize("key", ["routes", "nav", "settings"])
@pytest.mark.parametrize(("base", "head"), [
    ({}, {"x": 1}),                      # Wert neu
    ({"x": 1}, {"x": 2}),                # Wert geändert
    ({"x": 1}, {}),                      # Wert entfernt
    ({"x": [1]}, {"x": [1, 2]}),
])
def test_manifest_ui_aenderung_wird_erkannt(key, base, head):
    b = json.dumps({"version": "1", **({key: base["x"]} if "x" in base else {})})
    h = json.dumps({"version": "1", **({key: head["x"]} if "x" in head else {})})
    assert guard.manifest_ui_changed(b, h)


@pytest.mark.parametrize(("base", "head"), [
    ({"version": "1.0.0", "routes": [1]}, {"version": "1.0.1", "routes": [1]}),           # nur Version
    ({"nav_group": "working"}, {"nav_group": "media"}),                                   # kein nav/settings
    ({"description": "a", "nav": {"a": 1}}, {"description": "b", "nav": {"a": 1}}),
    ({"routes": [1], "nav": 2, "settings": 3}, {"settings": 3, "nav": 2, "routes": [1]}),  # nur Reihenfolge der Schlüssel
])
def test_manifest_ohne_ui_aenderung(base, head):
    assert not guard.manifest_ui_changed(json.dumps(base), json.dumps(head))


def test_manifest_neues_modul_mit_oder_ohne_ui_felder():
    assert guard.manifest_ui_changed(None, json.dumps({"routes": []}))
    assert not guard.manifest_ui_changed(None, json.dumps({"version": "0.1.0"}))


def test_manifest_geloescht_oder_kaputt_loest_nichts_aus():
    assert not guard.manifest_ui_changed(json.dumps({"routes": [1]}), None)
    assert not guard.manifest_ui_changed("{kaputt", "{auch kaputt")
    assert not guard.manifest_ui_changed(json.dumps({"routes": [1]}), json.dumps([1, 2]))


# --- Hilfe desselben Moduls -----------------------------------------------------------------------------------------

def test_hilfe_desselben_moduls_ist_ok():
    result = _eval(["atelier/frontend/AtelierPage.tsx", _help("atelier")])
    assert result.helps == {"atelier": [_help("atelier")]}
    assert result.ok


def test_neue_hilfe_datei_mit_anderem_namen_zaehlt():
    assert _eval(["atelier/frontend/A.tsx", "atelier/frontend/help/de/zusatz.md"]).ok


def test_hilfe_eines_anderen_moduls_zaehlt_nicht():
    result = _eval(["atelier/frontend/AtelierPage.tsx", _help("studio")])
    assert result.violation
    assert result.missing == ["atelier"]


@pytest.mark.parametrize("other", [
    "atelier/frontend/help/en/atelier.md",             # englische Hilfe zählt nicht (Nicht-Ziel)
    "atelier/frontend/help/de/atelier.txt",
    "atelier/frontend/help/de/sub/atelier.md",
    "atelier/help/de/atelier.md",                      # falscher Ort
    "frontend/src/i18n/help/de/agents.md",             # Kern-Hilfe zählt im Modul-Repo nicht
    "atelier/SPEC.md",
])
def test_andere_dateien_sind_keine_hilfe(other):
    assert _eval(["atelier/frontend/A.tsx", other]).violation


def test_mehrere_module_jedes_braucht_seine_hilfe():
    files = ["atelier/frontend/A.tsx", "studio/frontend/B.tsx", _help("atelier")]
    result = _eval(files)
    assert result.violation
    assert result.missing == ["studio"]
    assert _eval([*files, _help("studio")]).ok


def test_manifest_modul_braucht_seine_hilfe():
    files = ["atelier/manifest.json", _help("studio")]
    assert _eval(files, ui_manifests=["atelier"]).missing == ["atelier"]
    assert _eval([*files, _help("atelier")], ui_manifests=["atelier"]).ok


# --- Ausnahme (wie im Kern) -----------------------------------------------------------------------------------------

def test_ausnahme_mit_begruendung_ist_ok_und_gilt_fuer_alle_module():
    files = ["atelier/frontend/A.tsx", "studio/frontend/B.tsx"]
    result = _eval(files, body="Text\nKeine Hilfe nötig: reiner Bugfix ohne neue Bedienung\n")
    assert result.exemption == "reiner Bugfix ohne neue Bedienung"
    assert result.ok


def test_ausnahme_grenze_10_zeichen():
    assert _eval(["atelier/frontend/A.tsx"], body="Keine Hilfe nötig: 0123456789").ok
    assert _eval(["atelier/frontend/A.tsx"], body="Keine Hilfe nötig: 012345678").violation


@pytest.mark.parametrize("body", [
    "Keine Hilfe nötig: Bugfix",                                  # zu kurz
    "Keine Hilfe nötig:",                                         # leer
    "Keine Hilfe nötig: <Begründung>",                            # Platzhalter aus der Meldung
    "Die Zeile Keine Hilfe nötig: interner Umbau steht in der Spec.",   # nicht eigene Zeile
    None,
])
def test_ausnahme_gilt_nicht(body):
    assert _eval(["atelier/frontend/A.tsx"], body=body).violation


def test_ausnahme_gross_klein_egal_und_eingerueckt():
    assert _eval(["atelier/frontend/A.tsx"], body="  keine hilfe nötig: interner Umbau ohne Wirkung").ok


def test_ausnahme_mit_windows_zeilenende():
    body = "Beschreibung\r\nKeine Hilfe nötig: reiner Bugfix\r\nWeiter\r\n"
    result = _eval(["atelier/frontend/A.tsx"], body=body)
    assert result.exemption == "reiner Bugfix"          # ohne \r-Fix: „reiner Bugfix\r“ (13 statt 12 Zeichen)
    assert _eval(["atelier/frontend/A.tsx"], body="Keine Hilfe nötig: 123456789\r\n").violation


# --- Meldung (Spec §4, Modul-Variante) ------------------------------------------------------------------------------

def test_meldung_ein_modul_wie_im_kern():
    text = guard.message(_eval(["atelier/frontend/A.tsx", "atelier/frontend/i18n/de.ts"]))
    assert text.startswith("Hilfe fehlt: 2 nutzersichtbare Datei(en) geändert (")
    assert "atelier/frontend/A.tsx" in text and "keine Hilfe-Datei." in text
    assert "WARUM: Wiki und PDF-Handbuch entstehen aus den Hilfe-Artikeln" in text
    assert "(Regel docs/specs/hilfe-guard.md)" in text
    assert "BEHEBEN: atelier/frontend/help/de/atelier.md ergänzen" in text
    assert "„Keine Hilfe nötig: <Begründung>“" in text


def test_meldung_mehrere_module_je_modul_eine_zeile():
    text = guard.message(_eval(["atelier/frontend/A.tsx", "studio/frontend/B.tsx", "studio/frontend/C.tsx"]))
    first = text.splitlines()[0]
    assert first == "Hilfe fehlt: 2 Module ohne Hilfe-Datei (atelier, studio)."
    assert "atelier: 1 nutzersichtbare Datei(en) geändert (atelier/frontend/A.tsx)" in text
    assert "studio: 2 nutzersichtbare Datei(en) geändert (studio/frontend/B.tsx, studio/frontend/C.tsx)" in text
    assert "atelier/frontend/help/de/atelier.md" in text and "studio/frontend/help/de/studio.md" in text


def test_meldung_nennt_nur_fehlende_module():
    text = guard.message(_eval(["atelier/frontend/A.tsx", "studio/frontend/B.tsx", _help("atelier")]))
    assert text.startswith("Hilfe fehlt: 1 nutzersichtbare Datei(en) geändert (studio/frontend/B.tsx)")
    assert "atelier/frontend/help/de" not in text


def test_meldung_kuerzt_dateiliste():
    files = [f"atelier/frontend/F{i}.tsx" for i in range(8)]
    text = guard.message(_eval(files))
    assert "F4.tsx" in text and "F5.tsx" not in text and "…" in text


def test_meldung_ok_faelle():
    assert "Regel greift nicht" in guard.message(_eval(["atelier/backend/x.py"]))
    assert "Hilfe geändert" in guard.message(_eval(["atelier/frontend/A.tsx", _help("atelier")]))
    assert "begründet" in guard.message(_eval(["atelier/frontend/A.tsx"], body="Keine Hilfe nötig: interner Umbau"))


# --- Modus / Exit-Code ----------------------------------------------------------------------------------------------

def test_warn_ist_exit_0_und_block_exit_1():
    bad = _eval(["atelier/frontend/A.tsx"])
    assert guard.exit_code(bad, "warn") == 0
    assert guard.exit_code(bad, "") == 0
    assert guard.exit_code(bad, "block") == 1
    assert guard.exit_code(bad, " BLOCK ") == 1


def test_block_ohne_verstoss_exit_0():
    assert guard.exit_code(_eval(["atelier/backend/x.py"]), "block") == 0
    assert guard.exit_code(_eval(["atelier/frontend/A.tsx", _help("atelier")]), "block") == 0


# --- Ende-zu-Ende gegen ein echtes Git-Repo -------------------------------------------------------------------------

_SCRIPT = SCRIPTS / "check_help_updated.py"


def _git(cwd, *args):
    return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=cwd, check=True,
                          capture_output=True, text=True).stdout.strip()


def _write(repo, rel, text):
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _run(repo, base, head, *, body="", mode="warn", summary=None):
    env = {**os.environ, "HILFE_GUARD_MODE": mode, "PR_BODY": body}
    env.pop("GITHUB_STEP_SUMMARY", None)
    if summary:
        env["GITHUB_STEP_SUMMARY"] = str(summary)
    return subprocess.run([sys.executable, str(_SCRIPT), base, head], cwd=repo, env=env, capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path):
    _git(tmp_path, "init", "-q", "-b", "main")
    _write(tmp_path, "atelier/manifest.json", json.dumps({"id": "atelier", "version": "1.0.0", "nav_group": "working"}))
    _write(tmp_path, "studio/manifest.json", json.dumps({"id": "studio", "version": "1.0.0"}))
    _write(tmp_path, "atelier/frontend/Page.tsx", "export {}\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "init")
    return tmp_path, _git(tmp_path, "rev-parse", "HEAD")


def _commit(repo_dir, msg="x"):
    _git(repo_dir, "add", "-A")
    _git(repo_dir, "commit", "-q", "-m", msg)
    return _git(repo_dir, "rev-parse", "HEAD")


def test_e2e_warnung_exit_0_und_block_exit_1(repo):
    repo_dir, base = repo
    _write(repo_dir, "atelier/frontend/areas/X.tsx", "export {}\n")
    head = _commit(repo_dir)
    warn = _run(repo_dir, base, head)
    assert warn.returncode == 0
    assert "::warning title=Hilfe-Guard::Hilfe fehlt: 1 nutzersichtbare Datei(en)" in warn.stdout
    assert "BEHEBEN: atelier/frontend/help/de/atelier.md ergänzen" in warn.stdout
    block = _run(repo_dir, base, head, mode="block")
    assert block.returncode == 1
    assert "::error title=Hilfe-Guard::" in block.stdout


def test_e2e_hilfe_desselben_moduls_ok_anderes_modul_nicht(repo):
    repo_dir, base = repo
    _write(repo_dir, "atelier/frontend/areas/X.tsx", "export {}\n")
    _write(repo_dir, "studio/frontend/help/de/studio.md", "# Studio\n")
    other = _commit(repo_dir)
    assert _run(repo_dir, base, other, mode="block").returncode == 1
    _write(repo_dir, "atelier/frontend/help/de/atelier.md", "# Atelier\n")
    own = _commit(repo_dir)
    result = _run(repo_dir, base, own, mode="block")
    assert result.returncode == 0 and "Hilfe geändert" in result.stdout


def test_e2e_manifest_nur_bei_routes_nav_settings(repo):
    repo_dir, base = repo
    _write(repo_dir, "atelier/manifest.json", json.dumps({"id": "atelier", "version": "1.0.1", "nav_group": "media"}))
    bump = _commit(repo_dir, "bump")
    ok = _run(repo_dir, base, bump, mode="block")
    assert ok.returncode == 0 and "Regel greift nicht" in ok.stdout
    _write(repo_dir, "atelier/manifest.json", json.dumps({"id": "atelier", "version": "1.0.2", "nav": {"label": "A"}}))
    nav = _commit(repo_dir, "nav")
    bad = _run(repo_dir, base, nav, mode="block")
    assert bad.returncode == 1
    assert "atelier/manifest.json" in bad.stdout


def test_e2e_manifest_vergleich_gegen_merge_base_nicht_gegen_base_spitze(repo):
    # main ändert nach dem Abzweigen die routes; der PR hebt nur die Version. Gegen die Spitze von main
    # verglichen sähe das nach einer routes-Änderung durch den PR aus (Fehlalarm).
    repo_dir, fork = repo
    _git(repo_dir, "checkout", "-q", "-b", "pr")
    _write(repo_dir, "atelier/manifest.json", json.dumps({"id": "atelier", "version": "1.0.1", "nav_group": "working"}))
    head = _commit(repo_dir, "bump")
    _git(repo_dir, "checkout", "-q", "main")
    _write(repo_dir, "atelier/manifest.json",
           json.dumps({"id": "atelier", "version": "1.0.0", "nav_group": "working", "routes": ["/a"]}))
    main_tip = _commit(repo_dir, "main ändert routes")
    result = _run(repo_dir, main_tip, head, mode="block")
    assert result.returncode == 0 and "Regel greift nicht" in result.stdout


def test_e2e_neues_modul_mit_routes_im_manifest(repo):
    repo_dir, base = repo
    _write(repo_dir, "neu/manifest.json", json.dumps({"id": "neu", "version": "0.1.0", "routes": ["/neu"]}))
    head = _commit(repo_dir)
    result = _run(repo_dir, base, head, mode="block")
    assert result.returncode == 1 and "neu/manifest.json" in result.stdout


def test_e2e_ausnahme_aus_env_body_auch_mit_crlf(repo):
    repo_dir, base = repo
    _write(repo_dir, "atelier/frontend/areas/X.tsx", "export {}\n")
    head = _commit(repo_dir)
    result = _run(repo_dir, base, head, body="Text\r\nKeine Hilfe nötig: interner Umbau ohne Wirkung\r\n", mode="block")
    assert result.returncode == 0 and "begründet: interner Umbau ohne Wirkung" in result.stdout


def test_e2e_umlaut_dateiname_wird_erkannt(repo):
    # Ohne core.quotepath=off käme der Name als "atelier/frontend/\303\234bersicht.tsx" in Anführungszeichen zurück.
    repo_dir, base = repo
    _write(repo_dir, "atelier/frontend/Übersicht.tsx", "export {}\n")
    head = _commit(repo_dir)
    result = _run(repo_dir, base, head)
    assert "atelier/frontend/Übersicht.tsx" in result.stdout


def test_e2e_zusammenfassung_wird_geschrieben(repo, tmp_path_factory):
    repo_dir, base = repo
    _write(repo_dir, "atelier/frontend/areas/X.tsx", "export {}\n")
    head = _commit(repo_dir)
    summary = tmp_path_factory.mktemp("summary") / "summary.md"
    _run(repo_dir, base, head, summary=summary)
    assert "### Hilfe-Guard (warn)" in summary.read_text(encoding="utf-8")


def test_aufruf_ohne_argumente_exit_2():
    result = subprocess.run([sys.executable, str(_SCRIPT)], capture_output=True, text=True)
    assert result.returncode == 2
    assert "Aufruf:" in result.stdout
