"""Process lifecycle for the isolated Gate-2 incoming-call probe."""

from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path

from .config import ProbeTarget, SecureIncomingBaresipConfig, SipCredentials
from .ctrl_tcp import BaresipControlClient, ControlProtocolError
from .incoming_probe import (
    IncomingOutcome,
    IncomingReport,
    drive_incoming_call,
)


def run_incoming_probe(
    *,
    target: ProbeTarget,
    credentials: SipCredentials,
    binary: Path,
    module_dir: Path,
    incoming_timeout_seconds: int = 45,
    tone_seconds: int = 4,
    temp_parent: Path | None = None,
) -> IncomingReport:
    """Run one Gate-2 attempt with no inherited logs or audio persistence."""
    if not 15 <= incoming_timeout_seconds <= 45:
        raise ValueError("incoming timeout must be between 15 and 45 seconds")
    if not 1 <= tone_seconds <= 5:
        raise ValueError("tone duration must be between 1 and 5 seconds")

    started = time.monotonic()
    outcome = IncomingOutcome.RUNTIME_UNAVAILABLE
    with SecureIncomingBaresipConfig(
        target=target,
        credentials=credentials,
        module_dir=module_dir,
        temp_parent=temp_parent,
    ) as config_dir:
        process = subprocess.Popen(
            [str(binary), "-4", "-c", "-f", str(config_dir), "-t", "70"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=None,
            start_new_session=True,
        )
        channel: BaresipControlClient | None = None
        try:
            channel = BaresipControlClient.connect(timeout_seconds=5)
            outcome = drive_incoming_call(
                channel,
                incoming_timeout_seconds=incoming_timeout_seconds,
                tone_seconds=tone_seconds,
            )
        except TimeoutError:
            outcome = IncomingOutcome.TIMEOUT
        except (OSError, ControlProtocolError):
            outcome = IncomingOutcome.RUNTIME_UNAVAILABLE
        finally:
            _best_effort_shutdown(channel, process)

    return IncomingReport(outcome=outcome, duration_ms=_elapsed_ms(started))


def _best_effort_shutdown(
    channel: BaresipControlClient | None,
    process: subprocess.Popen[bytes],
) -> None:
    if channel is not None:
        for command, params, token in (
            ("hangupall", "all", "cleanup-calls"),
            ("uareg", "0 0", "cleanup-register"),
            ("quit", "", "cleanup-quit"),
        ):
            try:
                channel.send_command(command, params, token)
            except OSError:
                break
        channel.close()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        _kill_process_group(process)


def _kill_process_group(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except PermissionError:
        try:
            process.kill()
        except PermissionError:
            return
    except ProcessLookupError:
        return


def _elapsed_ms(started: float) -> int:
    return round((time.monotonic() - started) * 1000)
