"""Run a bounded Baresip registration probe without returning raw logs."""

from __future__ import annotations

import os
import signal
import subprocess
import time
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from .config import ProbeTarget, SecureBaresipConfig, SipCredentials


class ProbeOutcome(StrEnum):
    REGISTERED = "registered"
    AUTH_FAILED = "auth_failed"
    REGISTRATION_FAILED = "registration_failed"
    TIMEOUT = "timeout"
    NO_RESULT = "no_result"


@dataclass(frozen=True, slots=True)
class ProbeReport:
    outcome: ProbeOutcome
    exit_code: int | None
    duration_ms: int


def classify_registration_output(output: str) -> ProbeOutcome:
    """Map provider output to a stable result without preserving it."""
    normalized = output.lower()
    if "registered successfully" in normalized or "} 200 ok" in normalized:
        return ProbeOutcome.REGISTERED
    if any(
        marker in normalized
        for marker in (
            "401 unauthorized",
            "403 forbidden",
            "authentication failed",
            "auth failed",
        )
    ):
        return ProbeOutcome.AUTH_FAILED
    if any(
        marker in normalized
        for marker in (
            "register failed",
            "registration failed",
            "network is unreachable",
        )
    ):
        return ProbeOutcome.REGISTRATION_FAILED
    return ProbeOutcome.NO_RESULT


def run_probe(
    *,
    target: ProbeTarget,
    credentials: SipCredentials,
    binary: Path,
    module_dir: Path,
    timeout_seconds: int = 20,
    temp_parent: Path | None = None,
) -> ProbeReport:
    """Run one registration attempt; credentials stay in temporary 0600 files."""
    if not 5 <= timeout_seconds <= 27:
        raise ValueError("timeout must be between 5 and 27 seconds")

    started = time.monotonic()
    with SecureBaresipConfig(
        target=target,
        credentials=credentials,
        module_dir=module_dir,
        temp_parent=temp_parent,
    ) as config_dir:
        command = [
            str(binary),
            "-4",
            "-c",
            "-f",
            str(config_dir),
            "-t",
            str(timeout_seconds),
        ]
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=None,
            start_new_session=True,
        )
        timed_out = False
        try:
            stdout, stderr = process.communicate(timeout=timeout_seconds + 2)
        except subprocess.TimeoutExpired:
            timed_out = True
            _kill_process_group(process)
            try:
                stdout, stderr = process.communicate(timeout=1)
            except subprocess.TimeoutExpired:
                stdout, stderr = "", ""

        output = f"{stdout}\n{stderr}"
        outcome = classify_registration_output(output)
        del output, stdout, stderr
        if timed_out and outcome is ProbeOutcome.NO_RESULT:
            outcome = ProbeOutcome.TIMEOUT
        elif outcome is ProbeOutcome.NO_RESULT and process.returncode != 0:
            outcome = ProbeOutcome.REGISTRATION_FAILED

    return ProbeReport(
        outcome=outcome,
        exit_code=process.returncode,
        duration_ms=_elapsed_ms(started),
    )


def _kill_process_group(process: subprocess.Popen[str]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        return


def _elapsed_ms(started: float) -> int:
    return round((time.monotonic() - started) * 1000)
