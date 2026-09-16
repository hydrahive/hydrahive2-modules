from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from spike import stdin_incoming_probe
from spike.incoming_probe import IncomingOutcome, IncomingReport

_VALID = {
    "registrar": "192.168.3.1",
    "port": 5060,
    "username": "phone-user-01",
    "password": "TopSecretPhonePassword",
}


def _run(payload: object) -> tuple[int, str]:
    output = io.StringIO()
    code = stdin_incoming_probe.main(io.StringIO(json.dumps(payload)), output)
    return code, output.getvalue()


def test_stdin_incoming_probe_emits_only_stable_outcome(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_probe(**kwargs: object) -> IncomingReport:
        captured.update(kwargs)
        return IncomingReport(IncomingOutcome.INCOMING_ANSWERED, 20)

    monkeypatch.setattr(stdin_incoming_probe, "run_incoming_probe", fake_probe)

    code, output = _run(_VALID)

    assert code == 0
    assert output == "incoming_answered\n"
    assert "phone-user-01" not in output
    assert "TopSecretPhonePassword" not in output
    assert captured["binary"] == Path("/opt/baresip/bin/baresip")
    assert captured["incoming_timeout_seconds"] == 45
    assert captured["tone_seconds"] == 4


@pytest.mark.parametrize(
    "payload",
    [
        {**_VALID, "unexpected": "value"},
        {**_VALID, "registrar": "8.8.8.8"},
        {**_VALID, "password": "password;regint=0"},
    ],
)
def test_stdin_incoming_probe_rejects_invalid_or_extra_fields(payload: object) -> None:
    code, output = _run(payload)

    assert code == 64
    assert output == "invalid_input\n"
    assert "TopSecretPhonePassword" not in output


def test_stdin_incoming_probe_rejects_oversized_input() -> None:
    output = io.StringIO()

    code = stdin_incoming_probe.main(io.StringIO("x" * 1025), output)

    assert code == 64
    assert output.getvalue() == "invalid_input\n"


def test_stdin_incoming_probe_sanitizes_internal_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(**_kwargs: object) -> IncomingReport:
        raise RuntimeError("TopSecretPhonePassword")

    monkeypatch.setattr(stdin_incoming_probe, "run_incoming_probe", fail)

    code, output = _run(_VALID)

    assert code == 69
    assert output == "runtime_unavailable\n"
    assert "TopSecretPhonePassword" not in output
