"""Machine-only stdin adapter for the isolated incoming-call Gate-2 probe."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TextIO

from .incoming_runtime import run_incoming_probe
from .stdin_payload import InvalidProbePayload, read_probe_payload

_BINARY = Path("/opt/baresip/bin/baresip")
_MODULE_DIR = Path("/opt/baresip/lib/baresip/modules")


def main(input_stream: TextIO = sys.stdin, output_stream: TextIO = sys.stdout) -> int:
    try:
        target, credentials = read_probe_payload(input_stream)
    except InvalidProbePayload:
        return _write(output_stream, "invalid_input", 64)

    try:
        report = run_incoming_probe(
            target=target,
            credentials=credentials,
            binary=_BINARY,
            module_dir=_MODULE_DIR,
            incoming_timeout_seconds=45,
            tone_seconds=4,
        )
    except Exception:
        return _write(output_stream, "runtime_unavailable", 69)

    return _write(output_stream, report.outcome.value, 0)


def _write(output_stream: TextIO, outcome: str, exit_code: int) -> int:
    output_stream.write(f"{outcome}\n")
    output_stream.flush()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
