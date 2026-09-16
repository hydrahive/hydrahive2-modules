"""Secret-safe process boundary for the isolated SIP spike runtime."""

from __future__ import annotations

import json
import os
import signal
import subprocess
from threading import Lock

from .probe_models import ProbeOutcome, RegistrationProbeRequest

_REGISTRATION_COMMAND = [
    "incus",
    "exec",
    "hh-telephony-spike",
    "--",
    "/opt/hh-telephony-spike/spike/run-stdin-probe.sh",
]
_INCOMING_COMMAND = [
    "incus",
    "exec",
    "hh-telephony-spike",
    "--",
    "/opt/hh-telephony-spike/spike/run-stdin-incoming-probe.sh",
]
_STOP_COMMAND = ["incus", "stop", "--force", "hh-telephony-spike"]
_START_COMMAND = ["incus", "start", "hh-telephony-spike"]
_PROBE_LOCK = Lock()
_REGISTRATION_PROCESS_TIMEOUT_SECONDS = 12
_INCOMING_PROCESS_TIMEOUT_SECONDS = 76
_ALLOWED_OUTPUTS = {outcome.value: outcome for outcome in ProbeOutcome}


def run_registration_probe(request: RegistrationProbeRequest) -> ProbeOutcome:
    """Execute one bounded registration probe with an stdin-only secret payload."""
    return _run_with_lock(
        request,
        command=_REGISTRATION_COMMAND,
        timeout_seconds=_REGISTRATION_PROCESS_TIMEOUT_SECONDS,
        cleanup_after=False,
    )


def run_incoming_call_probe(request: RegistrationProbeRequest) -> ProbeOutcome:
    """Execute one Gate-2 call and remove its runtime process state afterwards."""
    return _run_with_lock(
        request,
        command=_INCOMING_COMMAND,
        timeout_seconds=_INCOMING_PROCESS_TIMEOUT_SECONDS,
        cleanup_after=True,
    )


def _run_with_lock(
    request: RegistrationProbeRequest,
    *,
    command: list[str],
    timeout_seconds: int,
    cleanup_after: bool,
) -> ProbeOutcome:
    if not _PROBE_LOCK.acquire(blocking=False):
        return ProbeOutcome.BUSY
    try:
        return _run_locked(
            request,
            command=command,
            timeout_seconds=timeout_seconds,
            cleanup_after=cleanup_after,
        )
    finally:
        _PROBE_LOCK.release()


def _run_locked(
    request: RegistrationProbeRequest,
    *,
    command: list[str],
    timeout_seconds: int,
    cleanup_after: bool,
) -> ProbeOutcome:
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
            command,
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
        stdout, stderr = process.communicate(input=payload, timeout=timeout_seconds)
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
    if outcome is not ProbeOutcome.BUSY and (
        cleanup_after or outcome is ProbeOutcome.TIMEOUT
    ):
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
