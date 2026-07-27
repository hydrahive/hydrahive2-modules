"""Radarr/Sonarr: eine Konfigurationsquelle, im Mediacenter sichtbar.

Kernproblem aus tills Rueckmeldung: er hat radarr_token und sonarr_token im
Credential-Store eingetragen, aber das Mediacenter zeigt die Dienste nicht an.
Und die Adressen mussten zusaetzlich als Umgebungsvariable gesetzt werden —
zwei Stellen fuer dieselbe Information.

Vertrag:
1. Die Adresse kommt aus dem `url_pattern` des Credentials. Eine
   Umgebungsvariable ist OPTIONAL und nur eine Einschraenkung (Allowlist),
   keine Voraussetzung.
2. Der Modul-Status meldet jeden Dienst einzeln, damit die Oberflaeche zeigen
   kann, was konfiguriert ist und was nicht.
3. Ein nicht konfigurierter Zusatzdienst blockiert das Modul NIE — Suche und
   Downloads muessen ohne Radarr/Sonarr weiterlaufen.
"""
from __future__ import annotations

import pytest
from hydrahive.credentials.models import Credential

from backend import arr_credentials
from backend.errors import MediacenterConfigError


def _credential(name: str = "radarr_token", **overrides) -> Credential:
    values = {
        "name": name,
        "type": "bearer",
        "value": "geheimer-arr-key",
        "url_pattern": "http://arr.example:7878/",
    }
    values.update(overrides)
    return Credential(**values)


# --- 1. Adresse kommt aus dem Credential -----------------------------------

def test_adresse_stammt_aus_dem_credential(monkeypatch):
    """Kein zweiter Ort: wer den Key eintraegt, hat die Adresse schon gepflegt."""
    monkeypatch.setattr(arr_credentials, "get_credential", lambda *_: _credential())
    monkeypatch.setattr(arr_credentials, "RADARR_ORIGIN", "")

    connection = arr_credentials.resolve_arr_connection("till", "radarr")

    assert connection.origin == "http://arr.example:7878"
    assert connection.api_key == "geheimer-arr-key"


def test_umgebungsvariable_schraenkt_nur_ein(monkeypatch):
    """Ist die Variable gesetzt, muss das Credential dazu passen — so kann ein
    Betreiber die erlaubte Instanz festnageln."""
    monkeypatch.setattr(arr_credentials, "get_credential", lambda *_: _credential())
    monkeypatch.setattr(arr_credentials, "RADARR_ORIGIN", "http://anderer:7878")

    with pytest.raises(MediacenterConfigError) as exc:
        arr_credentials.resolve_arr_connection("till", "radarr")
    assert exc.value.code == "radarr_not_configured"


def test_passende_umgebungsvariable_laesst_durch(monkeypatch):
    monkeypatch.setattr(arr_credentials, "get_credential", lambda *_: _credential())
    monkeypatch.setattr(arr_credentials, "RADARR_ORIGIN", "http://arr.example:7878")

    assert arr_credentials.resolve_arr_connection("till", "radarr").origin == "http://arr.example:7878"


def test_fehlendes_credential_ergibt_klaren_fehlercode(monkeypatch):
    monkeypatch.setattr(arr_credentials, "get_credential", lambda *_: None)

    with pytest.raises(MediacenterConfigError) as exc:
        arr_credentials.resolve_arr_connection("till", "sonarr")
    assert exc.value.code == "sonarr_not_configured"


def test_schluessel_erscheint_nie_in_der_fehlermeldung(monkeypatch):
    monkeypatch.setattr(arr_credentials, "get_credential",
                        lambda *_: _credential(url_pattern="*"))

    with pytest.raises(MediacenterConfigError) as exc:
        arr_credentials.resolve_arr_connection("till", "radarr")
    assert "geheimer-arr-key" not in str(exc.value)


@pytest.mark.parametrize("pattern", [
    "*", "ftp://arr.example/", "http://user:pass@arr.example/",
    "http://arr.example/api", "http://arr.example/?token=x", "http://arr.example/#f",
])
def test_unsichere_adressen_werden_abgelehnt(monkeypatch, pattern):
    monkeypatch.setattr(arr_credentials, "get_credential",
                        lambda *_: _credential(url_pattern=pattern))
    with pytest.raises(MediacenterConfigError):
        arr_credentials.resolve_arr_connection("till", "radarr")


def test_unbekannter_dienst_wird_abgewiesen():
    """Kein frei waehlbarer Dienstname — sonst waere das ein Einfallstor."""
    with pytest.raises(ValueError):
        arr_credentials.resolve_arr_connection("till", "beliebig")


# --- 2. Status meldet jeden Dienst einzeln ---------------------------------

def test_status_meldet_arr_dienste(monkeypatch):
    from backend import service

    monkeypatch.setattr(service, "resolve_indexer_api_key", lambda _: "k")
    monkeypatch.setattr(service, "resolve_sab_connection", lambda _: object())
    monkeypatch.setattr(service, "_arr_configured", lambda *_: True)

    status = service.connection_status("till")

    assert status.radarr_configured is True
    assert status.sonarr_configured is True


def test_fehlender_arr_dienst_blockiert_das_modul_nicht(monkeypatch):
    """Suche und Downloads muessen ohne Radarr/Sonarr weiterlaufen — sie sind
    Zusatz, nicht Voraussetzung."""
    from backend import service

    monkeypatch.setattr(service, "resolve_indexer_api_key", lambda _: "k")
    monkeypatch.setattr(service, "resolve_sab_connection", lambda _: object())
    monkeypatch.setattr(service, "_arr_configured", lambda *_: False)

    status = service.connection_status("till")

    assert status.state == "ready", "Modul muss ohne Radarr/Sonarr nutzbar bleiben"
    assert status.radarr_configured is False
    assert status.sonarr_configured is False
