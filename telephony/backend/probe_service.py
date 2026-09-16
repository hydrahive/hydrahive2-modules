"""Secret-safe process boundary for the isolated SIP spike runtime."""

from __future__ import annotations

import json
import os
import signal
import subprocess
from threading import Lock

from .probe_models import ProbeOutcome, RegistrationProbeRequest

_COMMAND = [
    "incus",
    "exec",
    "hh-telephony-spike",
    "--",
    "/opt/hh-telephony-spike/spike/run-stdin-probe.sh",
]
_STOP_COMMAND = ["incus", "stop", "--force", "hh-telephony-spike"]
_START_COMMAND = ["incus", "start", "hh-telephony-spike"]
_PROBE_LOCK = Lock()
_PROCESS_TIMEOUT_SECONDS = 12
_ALLOWED_OUTPUTS = {
    outcome.value: outcome
    for outcome in (
        ProbeOutcome.REGISTERED,
        ProbeOutcome.AUTH_FAILED,
        ProbeOutcome.REGISTRATION_FAILED,
        ProbeOutcome.TIMEOUT,
        ProbeOutcome.BUSY,
    )
}


def run_registration_probe(request: RegistrationProbeRequest) -> ProbeOutcome:
    """Execute one bounded probe; secret values travel only in the stdin payload."""
    if not _PROBE_LOCK.acquire(blocking=False):
        return ProbeOutcome.BUSY
    try:
        return _run_locked(request)
    finally:
        _PROBE_LOCK.release()


def _run_locked(request: RegistrationProbeRequest) -> ProbeOutcome:
    payload = json.dumps(
        {
            "registrar": request.registrar,
            "port": request.port,
            "username": request.username,
            "password": request.password.get_secret_value(),
        },
        separators=(",", ":"),
    )
    try:
        process = subprocess.Popen(
            _COMMAND,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=_safe_environment(),
            shell=False,
            start_new_session=True,
        )
    except OSError:
        return ProbeOutcome.RUNTIME_UNAVAILABLE

    try:
        stdout, stderr = process.communicate(
            input=payload,
            timeout=_PROCESS_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        _kill_process_group(process)
        try:
            process.communicate(input="", timeout=1)
        except (subprocess.TimeoutExpired, ValueError):
            pass
        _cleanup_runtime()
        return ProbeOutcome.TIMEOUT
    finally:
        payload = ""

    del stderr
    outcome = _ALLOWED_OUTPUTS.get(stdout.strip(), ProbeOutcome.RUNTIME_UNAVAILABLE)
    if outcome is ProbeOutcome.TIMEOUT:
        _cleanup_runtime()
    return outcome


def _cleanup_runtime() -> None:
    for command in (_STOP_COMMAND, _START_COMMAND):
        try:
            subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=8,
                check=False,
                env=_safe_environment(),
            )
        except (OSError, subprocess.TimeoutExpired):
            continue


def _safe_environment() -> dict[str, str]:
    environment = {"PATH": os.environ.get("PATH", os.defpath)}
    for name in ("HOME", "INCUS_DIR", "INCUS_CONF", "INCUS_SOCKET", "INCUS_REMOTE"):
        value = os.environ.get(name)
        if value:
            environment[name] = value
    return environment


def _kill_process_group(process: subprocess.Popen[str]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except PermissionError:
        try:
            process.kill()
        except PermissionError:
            return
    except ProcessLookupError:
        pass
