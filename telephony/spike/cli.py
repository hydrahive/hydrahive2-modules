"""Interactive CLI for Gate 1 of the FRITZ!Box SIP spike."""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

from .config import ProbeTarget, SipCredentials
from .probe import ProbeOutcome, run_probe

_DEFAULT_BINARY = Path("/opt/baresip/bin/baresip")
_DEFAULT_MODULE_DIR = Path("/opt/baresip/lib/baresip/modules")
_EXIT_CODES = {
    ProbeOutcome.REGISTERED: 0,
    ProbeOutcome.AUTH_FAILED: 2,
    ProbeOutcome.REGISTRATION_FAILED: 3,
    ProbeOutcome.NO_RESULT: 3,
    ProbeOutcome.TIMEOUT: 4,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a secret-safe FRITZ!Box SIP registration probe."
    )
    parser.add_argument("--registrar", default="192.168.3.1")
    parser.add_argument("--port", type=int, default=5060)
    parser.add_argument("--binary", type=Path, default=_DEFAULT_BINARY)
    parser.add_argument("--module-dir", type=Path, default=_DEFAULT_MODULE_DIR)
    parser.add_argument("--timeout", type=int, default=20)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not sys.stdin.isatty():
        print("refused: credentials require an interactive TTY", file=sys.stderr)
        return 64
    if not args.binary.is_file() or not args.module_dir.is_dir():
        print("runtime_unavailable", file=sys.stderr)
        return 69

    try:
        username = getpass.getpass("FRITZ!Box phone username (hidden): ")
        password = getpass.getpass("FRITZ!Box phone password (hidden): ")
        credentials = SipCredentials(username=username, password=password)
        target = ProbeTarget(registrar=args.registrar, port=args.port)
        report = run_probe(
            target=target,
            credentials=credentials,
            binary=args.binary,
            module_dir=args.module_dir,
            timeout_seconds=args.timeout,
        )
    except (EOFError, KeyboardInterrupt):
        print("cancelled", file=sys.stderr)
        return 130
    except ValueError:
        print("invalid_input", file=sys.stderr)
        return 64
    finally:
        username = ""
        password = ""

    print(report.outcome.value)
    return _EXIT_CODES[report.outcome]


if __name__ == "__main__":
    raise SystemExit(main())
