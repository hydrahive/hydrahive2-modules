from __future__ import annotations

import pytest

from hydrahive.credentials.models import Credential

from backend import credentials
from backend.errors import MediacenterConfigError


def _credential(**overrides) -> Credential:
    values = {
        "name": "tresuere_token",
        "type": "bearer",
        "value": "secret-indexer-key",
        "url_pattern": "https://treasure-maps.com/*",
    }
    values.update(overrides)
    return Credential(**values)


def test_resolve_indexer_key_accepts_exact_configured_origin(monkeypatch):
    monkeypatch.setattr(
        credentials,
        "get_credential",
        lambda *_: _credential(url_pattern="https://treasure-maps.com"),
    )

    assert credentials.resolve_indexer_api_key("alice") == "secret-indexer-key"


def test_resolve_indexer_key_is_scoped_to_current_user(monkeypatch):
    seen: list[tuple[str, str]] = []

    def fake_get(username: str, name: str):
        seen.append((username, name))
        return _credential()

    monkeypatch.setattr(credentials, "get_credential", fake_get)

    assert credentials.resolve_indexer_api_key("alice") == "secret-indexer-key"
    assert seen == [("alice", "tresuere_token")]


@pytest.mark.parametrize(
    "credential",
    [
        None,
        _credential(value=""),
        _credential(value=" "),
        _credential(value="x" * 4097),
        _credential(url_pattern="https://example.invalid/*"),
    ],
)
def test_resolve_indexer_key_rejects_missing_or_invalid_config(monkeypatch, credential):
    monkeypatch.setattr(credentials, "get_credential", lambda *_: credential)

    with pytest.raises(MediacenterConfigError) as exc_info:
        credentials.resolve_indexer_api_key("alice")

    assert exc_info.value.code == "indexer_not_configured"
    assert "secret-indexer-key" not in str(exc_info.value)


def test_config_errors_never_include_credential_value(monkeypatch):
    secret = "never-print-this-secret"
    monkeypatch.setattr(
        credentials,
        "get_credential",
        lambda *_: _credential(value=secret, url_pattern="https://example.invalid/*"),
    )

    with pytest.raises(MediacenterConfigError) as exc_info:
        credentials.resolve_indexer_api_key("alice")

    assert secret not in str(exc_info.value)
    assert secret not in repr(exc_info.value)
