from __future__ import annotations

import pytest

from hydrahive.credentials.models import Credential

from backend import sab_credentials
from backend.errors import MediacenterConfigError


def _credential(**overrides) -> Credential:
    values = {
        "name": "sabnzb_token",
        "type": "bearer",
        "value": "secret-sab-key",
        "url_pattern": "http://sab.example:30055/",
    }
    values.update(overrides)
    return Credential(**values)


def test_sab_connection_is_scoped_to_user_and_canonicalized(monkeypatch):
    seen = []

    def fake_get(username: str, name: str):
        seen.append((username, name))
        return _credential()

    monkeypatch.setattr(sab_credentials, "get_credential", fake_get)

    connection = sab_credentials.resolve_sab_connection("alice")

    assert connection.origin == "http://sab.example:30055"
    assert connection.api_key == "secret-sab-key"
    assert seen == [("alice", "sabnzb_token")]


@pytest.mark.parametrize(
    "credential",
    [
        None,
        _credential(value=""),
        _credential(value="x" * 4097),
        _credential(url_pattern="*"),
        _credential(url_pattern="ftp://sab.example/"),
        _credential(url_pattern="http://user:pass@sab.example/"),
        _credential(url_pattern="http://sab.example/api"),
        _credential(url_pattern="http://sab.example/?token=secret"),
        _credential(url_pattern="http://sab.example/#fragment"),
    ],
)
def test_sab_connection_rejects_unsafe_or_missing_config(monkeypatch, credential):
    monkeypatch.setattr(sab_credentials, "get_credential", lambda *_: credential)

    with pytest.raises(MediacenterConfigError) as exc_info:
        sab_credentials.resolve_sab_connection("alice")

    assert exc_info.value.code == "sab_not_configured"
    assert "secret-sab-key" not in str(exc_info.value)


def test_adresse_aus_dem_credential_wird_ohne_allowlist_akzeptiert(monkeypatch):
    """Ohne HH_MEDIACENTER_SAB_ORIGIN entscheidet allein das Credential —
    sonst muesste im Code eine feste Adresse stehen."""
    monkeypatch.setattr(sab_credentials, "SAB_ALLOWED_ORIGIN", "")
    monkeypatch.setattr(sab_credentials, "get_credential",
                        lambda *_: _credential(url_pattern="http://anderer-host:8080/"))

    connection = sab_credentials.resolve_sab_connection("alice")

    assert connection.origin == "http://anderer-host:8080"


def test_allowlist_nagelt_die_erlaubte_adresse_fest(monkeypatch):
    """Ist die Variable gesetzt, wird jede abweichende Adresse abgelehnt —
    so kann ein Betreiber die Instanz serverseitig festlegen."""
    monkeypatch.setattr(sab_credentials, "SAB_ALLOWED_ORIGIN", "http://sab.example:30055")
    monkeypatch.setattr(sab_credentials, "get_credential",
                        lambda *_: _credential(url_pattern="http://fremder-host:30055/"))

    with pytest.raises(MediacenterConfigError) as exc_info:
        sab_credentials.resolve_sab_connection("alice")

    assert exc_info.value.code == "sab_not_configured"


def test_allowlist_laesst_die_passende_adresse_durch(monkeypatch):
    monkeypatch.setattr(sab_credentials, "SAB_ALLOWED_ORIGIN", "http://sab.example:30055")
    monkeypatch.setattr(sab_credentials, "get_credential", lambda *_: _credential())

    assert sab_credentials.resolve_sab_connection("alice").origin == "http://sab.example:30055"
