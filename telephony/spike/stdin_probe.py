"""Machine-only stdin adapter for the isolated registration probe."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TextIO

from .config import ProbeTarget, SipCredentials
from .probe import ProbeOutcome, run_probe

_MAX_INPUT_BYTES = 1024
_REQUIRED_KEYS = {"registrar", "port", "username", "password"}
_BINARY = Path("/opt/baresip/bin/baresip")
_MODULE_DIR = Path("/opt/baresip/lib/baresip/modules")


def main(input_stream: TextIO = sys.stdin, output_stream: TextIO = sys.stdout) -> int:
    raw = input_stream.read(_MAX_INPUT_BYTES + 1)
    if len(raw) > _MAX_INPUT_BYTES:
        return _write(output_stream, "invalid_input", 64)
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict) or set(payload) != _REQUIRED_KEYS:
            raise ValueError
        if type(payload["port"]) is not int:
            raise ValueError
        if not all(
            isinstance(payload[key], str)
            for key in ("registrar", "username", "password")
        ):
            raise ValueError
        target = ProbeTarget(payload["registrar"], payload["port"])
        credentials = SipCredentials(payload["username"], payload["password"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return _write(output_stream, "invalid_input", 64)

    try:
        report = run_probe(
            target=target,
            credentials=credentials,
            binary=_BINARY,
            module_dir=_MODULE_DIR,
            timeout_seconds=8,
        )
    except Exception:
        return _write(output_stream, "runtime_unavailable", 69)
    finally:
        raw = ""
        payload = {}

    outcome = report.outcome
    if outcome is ProbeOutcome.NO_RESULT:
        outcome = ProbeOutcome.REGISTRATION_FAILED
    return _write(output_stream, outcome.value, 0)


def _write(output_stream: TextIO, outcome: str, exit_code: int) -> int:
    output_stream.write(f"{outcome}\n")
    output_stream.flush()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
