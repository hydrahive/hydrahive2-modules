"""Isolierter Analyseadapter: feste Positivliste, Zeitlimit, Abbruch.

Der Adapter kennt genau eine Containerart und eine Positivliste von Befehlen.
Nutzer- oder Agenteneingaben erreichen ihn nur ueber die Analysetypen aus
`analysis_types`.

Sicherheitsregeln:
- Kein Shell. Befehle werden als Argumentliste uebergeben.
- Netzwerk des Containers wird vor der Analyse abgeschaltet und danach
  wiederhergestellt, auch wenn etwas schiefgeht.
- Dateien werden in einen frischen Arbeitsordner kopiert; der Arbeitsordner
  wird danach geloescht.
- Jeder Aufruf hat ein Zeitlimit. Bei Ueberschreitung wird die ganze
  Prozessgruppe beendet, damit keine Analyseprozesse zurueckbleiben.
- Die Ausgabe ist begrenzt. Hostpfade und Befehlszeilen verlassen den
  Adapter nicht.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from . import analysis_types, exec
from .container import CONTAINER_NAME, ContainerError, IncusContainer
from .exec import CommandResult

logger = logging.getLogger(__name__)

#: REA braucht den Pfad zur JADX-Bridge fuer Android-Pakete.
JADX_JAR = "/opt/jadx-headless-mcp.jar"
#: REA und Node liegen nicht im Standard-PATH des Containers.
CONTAINER_PATH = "/opt/node/bin:/usr/local/bin:/usr/bin:/bin"
MAX_OUTPUT_BYTES = exec.MAX_OUTPUT_BYTES
#: Incus begrenzt `exec` auf 600 Sekunden. Das ist die harte Obergrenze.
DEFAULT_TIMEOUT = 600
MAX_TIMEOUT = 600


class RuntimeError_(RuntimeError):
    """Fehler der Analyseumgebung mit stabilem Code."""

    def __init__(self, code: str, **params):
        super().__init__(code)
        self.code = code
        self.params = params


def _run(command: list[str], *, timeout: float, cwd: str | None = None) -> CommandResult:
    """Befehl ohne Shell ausfuehren, Zeitlimit und Ausgabegrenze beachten."""
    try:
        return exec.run(command, timeout=timeout, cwd=cwd)
    except exec.ExecError as error:
        raise RuntimeError_(str(error)) from None


class IncusRuntime:
    """Fuehrt eine statische Analyse in der isolierten Umgebung aus."""

    def __init__(self, container: str = CONTAINER_NAME, runner=None):
        self.container = container
        self._run = runner or _run
        self._container = IncusContainer(container, self._run)

    # --- Zustand ---------------------------------------------------------

    def status(self):
        """Ist der Container vorhanden, laeuft er und ist sein Netz weg?"""
        try:
            return self._container.status()
        except ContainerError:
            raise

    # --- Analyse ---------------------------------------------------------

    def analyze(self, *, analysis_type: str, artifact: Path, artifact_kind: str,
                token: str, timeout: int = DEFAULT_TIMEOUT) -> tuple[dict, CommandResult]:
        """Ein Artefakt statisch analysieren.

        Liefert das geparste Ergebnis und den Rohlauf. Der Aufrufer entscheidet,
        was er daraus macht; der Adapter gibt keine Hostpfade weiter.
        """
        if not analysis_types.is_allowed(artifact_kind, analysis_type):
            raise RuntimeError_("analysis_type_not_allowed")
        if not artifact.is_file():
            raise RuntimeError_("artifact_missing")

        self._ensure_running()
        self._container.disable_network()
        remote_dir = ""
        try:
            remote_dir = self._container.prepare_workdir(token)
            name = f"artifact{Path(artifact).suffix}"
            budget = min(int(timeout), MAX_TIMEOUT)
            self._container.push(artifact, remote_dir, name)
            command = analysis_types.build_command(
                analysis_type, artifact_path=f"{remote_dir}/{name}",
                workdir=remote_dir,
            )
            run = self._exec_analysis(command, remote_dir, budget)
            bundle = self._read_bundle(remote_dir)
        except ContainerError as error:
            raise RuntimeError_(error.code) from None
        finally:
            if remote_dir:
                self._container.cleanup_workdir(remote_dir)
            self._container.enable_network()

        payload = self._read_result(run)
        if bundle:
            payload = {"summary": payload, "evidence": bundle}
        return payload, run

    def _ensure_running(self) -> None:
        """Container starten, wenn er steht."""
        try:
            self._container.ensure_running()
        except ContainerError as error:
            raise RuntimeError_(error.code) from None

    def _exec_analysis(self, command: list[str], remote_dir: str,
                       budget: int) -> CommandResult:
        """Die Analyse im Container starten. Ohne Shell."""
        return self._run(
            ["incus", "exec", self.container, "--cwd", remote_dir,
             "--env", "HOME=/tmp",
             "--env", f"PATH={CONTAINER_PATH}",
             "--env", f"REA_JADX_MCP_JAR={JADX_JAR}",
             "--", *command],
            timeout=budget,
        )

    def _read_bundle(self, remote_dir: str) -> dict:
        """Evidence-Bundle aus dem Container holen. Fehlt es, bleibt es leer."""
        try:
            raw = self._container.read_file(
                f"{remote_dir}/{analysis_types.EVIDENCE_NAME}")
        except ContainerError:
            return {}
        if not raw:
            return {}
        try:
            bundle = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return bundle if isinstance(bundle, dict) else {}

    def _read_result(self, run: CommandResult) -> dict:
        """Ergebnis der Analyse als Dict. Fehlerhafte Ausgabe wird leer."""
        if run.timed_out:
            raise RuntimeError_("analysis_timeout")
        if run.returncode != 0:
            raise RuntimeError_("analysis_failed")
        try:
            payload = json.loads(run.stdout or "{}")
        except json.JSONDecodeError:
            raise RuntimeError_("analysis_output_invalid") from None
        return payload if isinstance(payload, dict) else {"result": payload}
