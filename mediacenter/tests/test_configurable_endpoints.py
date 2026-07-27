"""Keine festen Adressen im Code — alles ueber Konfiguration.

Bisher standen Indexer-Host, Bildhost und die SABnzbd-Adresse als Literale im
Code (teils mit tills IP). Das ist fuer jeden anderen Betreiber unbrauchbar und
macht einen Umzug zur Code-Aenderung.

Vertrag:
- Jede externe Adresse kommt aus einer Umgebungsvariable mit sinnvollem Default.
- Die Werte werden EINMAL zentral in config.py aufgeloest.
- Kein Modul enthaelt noch eine IP oder einen festen Hostnamen.
"""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1] / "backend"


@pytest.fixture
def reload_config(monkeypatch):
    """Config mit veraenderter Umgebung neu laden."""
    def _reload(**env: str):
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        from backend import config
        return importlib.reload(config)
    yield _reload
    # Ursprungszustand wiederherstellen, damit Folgetests nicht erben.
    from backend import config
    importlib.reload(config)


# --- 1. Keine Literale mehr im Code ----------------------------------------

def test_kein_modul_enthaelt_eine_ip_adresse():
    """Eine IP im Quellcode ist bei einem Umzug eine Zeitbombe."""
    import re
    pattern = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
    offenders = []
    for path in BACKEND.glob("*.py"):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue  # Kommentare/Beispiele sind erlaubt
            if pattern.search(line):
                offenders.append(f"{path.name}:{number}")
    assert offenders == [], f"IP-Adressen im Code: {offenders}"


def test_nur_config_kennt_externe_hostnamen():
    """Hostnamen gehoeren ausschliesslich in config.py — sonst muss man bei
    einem Wechsel mehrere Dateien anfassen und vergisst eine."""
    offenders = []
    for path in BACKEND.glob("*.py"):
        if path.name == "config.py":
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            if "treasure-maps" in line or "picbit" in line:
                offenders.append(f"{path.name}:{number}")
    assert offenders == [], f"Feste Hostnamen ausserhalb config.py: {offenders}"


# --- 2. Umgebungsvariablen wirken -------------------------------------------

def test_indexer_adresse_ist_konfigurierbar(reload_config):
    config = reload_config(HH_MEDIACENTER_INDEXER_ORIGIN="https://mein-indexer.example")
    assert config.INDEXER_ORIGIN == "https://mein-indexer.example"
    assert config.INDEXER_API_URL == "https://mein-indexer.example/api"
    assert config.INDEXER_HOST == "mein-indexer.example"


def test_indexer_dateihost_folgt_dem_indexer(reload_config):
    """Der NZB-Download laeuft ueber einen eigenen Host (file.<indexer>) —
    der muss beim Wechsel automatisch mitziehen."""
    config = reload_config(HH_MEDIACENTER_INDEXER_ORIGIN="https://mein-indexer.example")
    assert config.INDEXER_FILE_HOST == "file.mein-indexer.example"


def test_dateihost_kann_separat_gesetzt_werden(reload_config):
    config = reload_config(
        HH_MEDIACENTER_INDEXER_ORIGIN="https://a.example",
        HH_MEDIACENTER_INDEXER_FILE_HOST="downloads.b.example",
    )
    assert config.INDEXER_FILE_HOST == "downloads.b.example"


def test_bildhosts_sind_konfigurierbar(reload_config):
    config = reload_config(HH_MEDIACENTER_COVER_HOSTS="bilder.example, cdn.example")
    assert "bilder.example" in config.COVER_HOSTS
    assert "cdn.example" in config.COVER_HOSTS


def test_sab_adresse_ist_konfigurierbar(reload_config):
    config = reload_config(HH_MEDIACENTER_SAB_ORIGIN="http://nas.example:8080")
    assert config.SAB_ALLOWED_ORIGIN == "http://nas.example:8080"


def test_radarr_und_sonarr_sind_konfigurierbar(reload_config):
    config = reload_config(
        HH_MEDIACENTER_RADARR_ORIGIN="http://nas.example:7878",
        HH_MEDIACENTER_SONARR_ORIGIN="http://nas.example:8989",
    )
    assert config.RADARR_ORIGIN == "http://nas.example:7878"
    assert config.SONARR_ORIGIN == "http://nas.example:8989"


def test_arr_dienste_sind_ohne_konfiguration_leer(reload_config, monkeypatch):
    """Kein Default auf fremde Adressen: wer Radarr nicht konfiguriert, soll
    auch nichts ansprechen. Leer = Funktion deaktiviert."""
    monkeypatch.delenv("HH_MEDIACENTER_RADARR_ORIGIN", raising=False)
    monkeypatch.delenv("HH_MEDIACENTER_SONARR_ORIGIN", raising=False)
    import importlib

    from backend import config
    config = importlib.reload(config)
    assert config.RADARR_ORIGIN == ""
    assert config.SONARR_ORIGIN == ""


# --- 3. Abwaertskompatibilitaet: Defaults bleiben die bisherigen Werte -----

def test_defaults_entsprechen_dem_bisherigen_verhalten(reload_config, monkeypatch):
    for key in ("HH_MEDIACENTER_INDEXER_ORIGIN", "HH_MEDIACENTER_COVER_HOSTS",
                "HH_MEDIACENTER_INDEXER_FILE_HOST"):
        monkeypatch.delenv(key, raising=False)
    import importlib

    from backend import config
    config = importlib.reload(config)
    assert config.INDEXER_ORIGIN == "https://treasure-maps.com"
    assert config.INDEXER_API_URL == "https://treasure-maps.com/api"
    assert config.INDEXER_FILE_HOST == "file.treasure-maps.com"
    assert "picbit.io" in config.COVER_HOSTS


def test_trailing_slash_wird_entfernt(reload_config):
    config = reload_config(HH_MEDIACENTER_INDEXER_ORIGIN="https://x.example/")
    assert config.INDEXER_ORIGIN == "https://x.example"


def test_cover_hosts_akzeptiert_leere_eintraege(reload_config):
    config = reload_config(HH_MEDIACENTER_COVER_HOSTS="a.example,,  ,b.example")
    assert config.COVER_HOSTS == frozenset({"a.example", "b.example"})
