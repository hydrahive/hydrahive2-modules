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
        "url_pattern": "http://192.168.178.3:30055/",
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

    assert connection.origin == "http://192.168.178.3:30055"
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
        _credential(url_pattern="http://192.168.178.4:30055/"),
    ],
)
def test_sab_connection_rejects_unsafe_or_missing_config(monkeypatch, credential):
    monkeypatch.setattr(sab_credentials, "get_credential", lambda *_: credential)

    with pytest.raises(MediacenterConfigError) as exc_info:
        sab_credentials.resolve_sab_connection("alice")

    assert exc_info.value.code == "sab_not_configured"
    assert "secret-sab-key" not in str(exc_info.value)
