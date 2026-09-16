from __future__ import annotations

import pytest

from backend.probe_models import ProbeOutcome

_VALID_REQUEST = {
    "registrar": "192.168.3.1",
    "port": 5060,
    "username": "phone-user-01",
    "password": "TopSecretPhonePassword",
}


def test_registration_probe_requires_current_principal(client) -> None:
    response = client.post(
        "/api/modules/telephony/spike/registration-test", json=_VALID_REQUEST
    )

    assert response.status_code == 401


def test_registration_probe_returns_only_stable_outcome(
    client, auth_headers, monkeypatch: pytest.MonkeyPatch
) -> None:
    from backend import probe_routes

    observed: dict[str, object] = {}

    def fake_probe(request):
        observed["request"] = request
        return ProbeOutcome.REGISTERED

    monkeypatch.setattr(probe_routes, "run_registration_probe", fake_probe)
    response = client.post(
        "/api/modules/telephony/spike/registration-test",
        headers=auth_headers,
        json=_VALID_REQUEST,
    )

    assert response.status_code == 200
    assert response.json() == {"outcome": "registered"}
    assert "phone-user-01" not in repr(observed["request"])
    assert "TopSecretPhonePassword" not in repr(observed["request"])


@pytest.mark.parametrize(
    "patch",
    [
        {"registrar": "37.202.238.230"},
        {"registrar": "fritz.box"},
        {"registrar": "192.168.178.1"},
        {"port": 5061},
        {"registrar": "192.168.3.1\nmodule evil.so"},
        {"username": "phone-user;regint=0"},
        {"password": "password;regint=0"},
        {"password": "password\nmodule evil.so"},
        {"unexpected": "TopSecretUnexpectedValue"},
    ],
)
def test_registration_probe_sanitizes_invalid_requests_without_echoing_values(
    client, auth_headers, patch: dict[str, object]
) -> None:
    body = {**_VALID_REQUEST, **patch}

    response = client.post(
        "/api/modules/telephony/spike/registration-test",
        headers=auth_headers,
        json=body,
    )

    assert response.status_code == 422
    assert response.json() == {"detail": {"code": "telephony_probe_request_invalid"}}
    payload = response.text
    for value in patch.values():
        assert str(value) not in payload


def test_registration_probe_rejects_oversized_body_without_echoing_it(
    client, auth_headers
) -> None:
    secret_marker = "TopSecretOversizedValue"

    response = client.post(
        "/api/modules/telephony/spike/registration-test",
        content=(secret_marker * 200).encode(),
        headers={**auth_headers, "Content-Type": "application/json"},
    )

    assert response.status_code == 413
    assert response.json() == {"detail": {"code": "telephony_probe_request_too_large"}}
    assert secret_marker not in response.text


def test_registration_probe_is_rate_limited_per_principal(
    client, auth_headers, monkeypatch: pytest.MonkeyPatch
) -> None:
    from backend import probe_routes

    monkeypatch.setattr(
        probe_routes, "check_rate", lambda *_args, **_kwargs: (False, 42)
    )

    response = client.post(
        "/api/modules/telephony/spike/registration-test",
        headers=auth_headers,
        json=_VALID_REQUEST,
    )

    assert response.status_code == 429
    assert response.json() == {
        "detail": {
            "code": "telephony_probe_rate_limited",
            "params": {"retry_after": 42},
        }
    }
    assert "TopSecretPhonePassword" not in response.text


def test_incoming_probe_requires_current_principal(client) -> None:
    response = client.post(
        "/api/modules/telephony/spike/incoming-test", json=_VALID_REQUEST
    )

    assert response.status_code == 401


def test_incoming_probe_returns_only_stable_outcome(
    client, auth_headers, monkeypatch: pytest.MonkeyPatch
) -> None:
    from backend import probe_routes

    observed: dict[str, object] = {}

    def fake_probe(request):
        observed["request"] = request
        return ProbeOutcome.INCOMING_ANSWERED

    monkeypatch.setattr(probe_routes, "run_incoming_call_probe", fake_probe)
    response = client.post(
        "/api/modules/telephony/spike/incoming-test",
        headers=auth_headers,
        json=_VALID_REQUEST,
    )

    assert response.status_code == 200
    assert response.json() == {"outcome": "incoming_answered"}
    assert "phone-user-01" not in repr(observed["request"])
    assert "TopSecretPhonePassword" not in repr(observed["request"])


def test_incoming_probe_is_rate_limited_per_principal(
    client, auth_headers, monkeypatch: pytest.MonkeyPatch
) -> None:
    from backend import probe_routes

    monkeypatch.setattr(
        probe_routes, "check_rate", lambda *_args, **_kwargs: (False, 37)
    )

    response = client.post(
        "/api/modules/telephony/spike/incoming-test",
        headers=auth_headers,
        json=_VALID_REQUEST,
    )

    assert response.status_code == 429
    assert response.json() == {
        "detail": {
            "code": "telephony_probe_rate_limited",
            "params": {"retry_after": 37},
        }
    }
    assert "TopSecretPhonePassword" not in response.text
