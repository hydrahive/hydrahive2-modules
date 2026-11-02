"""Container-Aktionen: Zustand, Netz, Start und Dateiuebergabe.

Der Adapter kennt genau eine Containerart. Er fuehrt keine Analysebefehle aus,
sondern richtet nur die Umgebung her und reicht Dateien hinein und heraus.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from .exec import CommandResult

CONTAINER_NAME = "hh-zerlegewerkstatt"
NETWORK_BRIDGE = "br0"
WORKDIR = "/work"


class ContainerError(RuntimeError):
    """Fehler der Containerumgebung mit stabilem Code."""

    def __init__(self, code: str, **params):
        super().__init__(code)
        self.code = code
        self.params = params


@dataclass
class ContainerStatus:
    """Zustand der Containerumgebung."""

    available: bool = False
    running: bool = False
    network_disabled: bool = False
    code: str = ""
    detail: dict = field(default_factory=dict)


class IncusContainer:
    """Zustand und Aktionen des Incus-Analysecontainers."""

    def __init__(self, container: str = CONTAINER_NAME, runner=None):
        self.container = container
        self._run = runner
        #: Bei gesetztem Runner wird das echte incus-Binary nicht geprueft.
        #: Sonst wuerde die Suite auf einem Rechner ohne Incus abbrechen.
        self._extern = runner is None

    def _exec(self, command: list[str], *, timeout: float) -> CommandResult:
        if self._run is None:
            from .runtime import _run as default_runner

            self._run = default_runner
        return self._run(command, timeout=timeout)

    # --- Zustand ---------------------------------------------------------

    def status(self) -> ContainerStatus:
        """Ist der Container vorhanden, laeuft er und ist sein Netz weg?"""
        if self._extern and shutil.which("incus") is None:
            return ContainerStatus(code="runtime_missing")
        exists = self._exec(["incus", "info", self.container], timeout=20)
        if exists.returncode != 0:
            return ContainerStatus(code="runtime_container_missing")
        running = self._exec(["incus", "list", self.container, "--format", "csv", "-c", "s"],
                             timeout=20)
        state = running.stdout.strip().splitlines()
        is_running = bool(state) and state[0].strip().upper() == "RUNNING"
        network = self._exec(["incus", "config", "device", "list", self.container],
                             timeout=20)
        return ContainerStatus(
            available=True,
            running=is_running,
            network_disabled="eth0" not in network.stdout,
            code="",
        )

    # --- Netz ------------------------------------------------------------

    def disable_network(self) -> None:
        """Netzwerk des Containers abklemmen. Analyse laeuft offline."""
        self._exec(["incus", "config", "device", "remove", self.container, "eth0"], timeout=30)

    def enable_network(self) -> None:
        """Netzwerk des Containers wieder anklemmen."""
        self._exec(["incus", "config", "device", "add", self.container, "eth0", "nic",
                    "nictype=bridged", f"parent={NETWORK_BRIDGE}", "name=eth0"],
                   timeout=30)

    # --- Start -----------------------------------------------------------

    def ensure_running(self) -> None:
        """Container starten, wenn er steht."""
        status = self.status()
        if not status.available:
            raise ContainerError(status.code or "runtime_missing")
        if status.running:
            return
        result = self._exec(["incus", "start", self.container], timeout=180)
        if result.returncode != 0:
            raise ContainerError("runtime_start_failed")

    # --- Dateien ---------------------------------------------------------

    def prepare_workdir(self, token: str) -> str:
        """Frischen Arbeitsordner im Container anlegen und zurueckgeben."""
        path = f"{WORKDIR}/{token}"
        result = self._exec(["incus", "exec", self.container, "--", "mkdir", "-p", path],
                            timeout=60)
        if result.returncode != 0:
            raise ContainerError("runtime_workdir_failed")
        ownership = self._exec(
            ["incus", "exec", self.container, "--", "chown", "rea:rea", path],
            timeout=60,
        )
        mode = self._exec(
            ["incus", "exec", self.container, "--", "chmod", "0700", path],
            timeout=60,
        )
        if ownership.returncode != 0 or mode.returncode != 0:
            raise ContainerError("runtime_workdir_failed")
        return path

    def push(self, local: Path, remote_dir: str, name: str) -> None:
        """Datei in den Arbeitsordner kopieren."""
        result = self._exec(
            ["incus", "file", "push", str(local), f"{self.container}{remote_dir}/{name}"],
            timeout=300,
        )
        if result.returncode != 0:
            raise ContainerError("runtime_push_failed")
        remote_path = f"{remote_dir}/{name}"
        ownership = self._exec(
            ["incus", "exec", self.container, "--", "chown", "rea:rea", remote_path],
            timeout=60,
        )
        if ownership.returncode != 0:
            raise ContainerError("runtime_push_failed")

    def cleanup_workdir(self, remote_dir: str) -> None:
        """Arbeitsordner im Container loeschen."""
        self._exec(["incus", "exec", self.container, "--", "rm", "-rf", remote_dir], timeout=120)

    def read_file(self, remote_path: str, *, timeout: float = 120) -> str:
        """Datei aus dem Container lesen. Fehlt sie, ist das Ergebnis leer."""
        result = self._exec(["incus", "exec", self.container, "--", "cat", remote_path],
                            timeout=timeout)
        return result.stdout if result.returncode == 0 else ""
