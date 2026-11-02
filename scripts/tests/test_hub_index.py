"""hub.json muss jedes Modul des Repos listen.

`hub.json` ist der Index, aus dem der Kern die verfuegbare Modulliste baut.
Ein Modul, das nicht in der Liste steht, ist im Cockpit-Hub unsichtbar und
nicht installierbar - auch dann nicht, wenn der Ordner im Repo liegt.

Anlass: Die Zerlege-Werkstatt war vollstaendig implementiert, im Repo und
in der Produktivinstallation vorhanden, aber nicht auffindbar, weil der
Eintrag in hub.json fehlte.

Dieser Guard verhindert, dass das wieder passiert.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HUB = REPO_ROOT / "hub.json"


def _hub_modules() -> dict[str, dict]:
    data = json.loads(HUB.read_text(encoding="utf-8"))
    return {m["id"]: m for m in data.get("modules", [])}


def _repo_modules() -> dict[str, Path]:
    """Alle Module des Repos: Ordner mit manifest.json."""
    return {
        path.name: path
        for path in REPO_ROOT.iterdir()
        if path.is_dir()
        and not path.name.startswith(".")
        and (path / "manifest.json").is_file()
    }


def test_hub_ist_gueltiges_json():
    data = json.loads(HUB.read_text(encoding="utf-8"))
    assert isinstance(data.get("modules"), list)


def test_jedes_modul_steht_im_hub():
    """Ein Modul ohne Hub-Eintrag ist unsichtbar."""
    fehlend = sorted(set(_repo_modules()) - set(_hub_modules()))
    assert fehlend == [], f"nicht im hub.json: {fehlend}"


def test_kein_hub_eintrag_zeigt_auf_fehlenden_ordner():
    """Jeder Hub-Eintrag braucht einen Ordner mit manifest.json."""
    repo = _repo_modules()
    falsch = sorted(
        mid for mid, entry in _hub_modules().items()
        if entry.get("path") not in repo
    )
    assert falsch == [], f"Hub-Eintraege ohne Modulordner: {falsch}"


def test_hub_und_manifest_stimmen_ueberein():
    """Die ID im Hub muss zur ID im Manifest passen.

    Der Anzeigename darf abweichen (musicplayer heisst im Manifest
    "Mediaplayer", im Hub "Musicplayer"). Nur die ID muss uebereinstimmen -
    sie ist der Schluessel fuer Installation und Berechtigung.
    """
    falsch = []
    for mid, entry in _hub_modules().items():
        manifest_path = REPO_ROOT / entry["path"] / "manifest.json"
        if not manifest_path.is_file():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("id") != mid:
            falsch.append(f"{mid}: manifest-id={manifest.get('id')}")
    assert falsch == [], falsch


def test_modul_ids_eindeutig():
    data = json.loads(HUB.read_text(encoding="utf-8"))
    ids = [m["id"] for m in data.get("modules", [])]
    doppelt = sorted({mid for mid in ids if ids.count(mid) > 1})
    assert doppelt == [], f"doppelte Modul-IDs: {doppelt}"


@pytest.mark.parametrize("module_id", sorted(_hub_modules()))
def test_hub_eintrag_hat_pfad_und_name(module_id):
    entry = _hub_modules()[module_id]
    assert entry.get("path"), f"{module_id}: kein path"
    assert entry.get("name"), f"{module_id}: kein name"
