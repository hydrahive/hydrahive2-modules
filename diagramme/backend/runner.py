"""Archify aufrufen (Spec §4, §5): feste Argumente, kein Shell, Zeitgrenze, kein Update-Check, nur eigener Ordner.

Archify (vendor/archify, MIT) prüft die Beschreibung, baut die HTML-Seite und prüft sie – mit Chromium – im Browser.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import chrome

KINDS = ("architecture", "workflow", "sequence", "dataflow", "lifecycle", "erd", "class", "tree", "timeline",
         "waterfall", "explainer")
ARCHIFY_BIN = Path(__file__).resolve().parents[1] / "vendor" / "archify" / "bin" / "archify.mjs"
TIMEOUT_SECONDS = 180
MAX_INPUT_BYTES = 512 * 1024
MAX_DETAIL_CHARS = 2000
OUTPUT = "diagramm.html"
# Nur das Nötigste an den Unterprozess weitergeben – keine Geheimnisse des Dienstes.
_PASS_ENV = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR")


@dataclass
class BuildResult:
    ok: bool
    html: str | None = None
    code: str = ""
    detail: str = ""


def input_name(kind: str) -> str:
    return "candidate.archify.md" if kind == "explainer" else "eingabe.json"


def _env() -> dict[str, str]:
    env = {k: os.environ[k] for k in _PASS_ENV if k in os.environ}
    env["ARCHIFY_UPDATE_CHECK_DISABLED"] = "1"
    path = chrome.find()
    if path:
        env["ARCHIFY_CHROME"] = path
        env["ARCHIFY_CHROME_NO_SANDBOX"] = "1"
    return env


def _run_process(argv: list[str], *, cwd: Path, env: dict[str, str], timeout: int) -> tuple[int, str]:
    done = subprocess.run(argv, cwd=cwd, env=env, timeout=timeout, capture_output=True, text=True,
                          stdin=subprocess.DEVNULL, check=False)
    return done.returncode, done.stdout


def _hints(stdout: str, work: Path) -> str:
    """Archify-Meldungen kurz und ohne Server-Pfade – der Agent soll damit nachbessern können."""
    try:
        data = json.loads(stdout)
    except (ValueError, TypeError):
        return ""
    lines = []
    for d in (data.get("diagnostics") or [])[:12]:
        if not isinstance(d, dict):
            continue
        fixes = "; ".join(str(f) for f in (d.get("supportedFixes") or [])[:2])
        lines.append(f"{d.get('code', '?')}: {str(d.get('message', ''))[:240]}" + (f" → {fixes}" if fixes else ""))
    return "\n".join(lines).replace(str(work), ".")[:MAX_DETAIL_CHARS]


def build(kind: str, source: str, *, work: Path, repo_root: Path | None = None) -> BuildResult:
    if kind not in KINDS:
        return BuildResult(False, code="diagram_kind_unknown")
    if len(source.encode("utf-8")) > MAX_INPUT_BYTES:
        return BuildResult(False, code="diagram_input_too_large")
    name = input_name(kind)
    (work / name).write_text(source, encoding="utf-8")
    argv = [shutil.which("node") or "node", str(ARCHIFY_BIN), "finalize", kind, name, OUTPUT,
            "--quality", "showcase", "--json"]
    if repo_root is not None:
        argv += ["--repo-root", str(repo_root)]
    try:
        code, stdout = _run_process(argv, cwd=work, env=_env(), timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        return BuildResult(False, code="diagram_timeout")
    except FileNotFoundError:
        return BuildResult(False, code="diagram_node_missing")
    if code != 0:
        return BuildResult(False, code="diagram_invalid", detail=_hints(stdout, work))
    out = work / OUTPUT
    if not out.is_file():
        return BuildResult(False, code="diagram_failed")
    return BuildResult(True, html=out.read_text(encoding="utf-8"))
