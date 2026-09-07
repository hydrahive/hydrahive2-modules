from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


class AdapterUnavailable(RuntimeError):
    pass


class OpenTorAdapter:
    """Run the reviewed OpenTor checkout behind a one-shot worker boundary.

    The checkout path and interpreter are server configuration only. Request
    data is passed as JSON on stdin, never interpolated into a shell command.
    """

    def __init__(self, root: str | None = None, python: str | None = None) -> None:
        configured = root or os.getenv("HYDRAHIVE_OPENTOR_ROOT")
        self.root = Path(configured).resolve() if configured else None
        self.python = python or os.getenv("HYDRAHIVE_OPENTOR_PYTHON") or sys.executable
        self.worker = Path(__file__).with_name("worker.py")

    def _run(self, command: str, payload: dict[str, Any]) -> dict:
        if self.root is None or not (self.root / "scripts").is_dir() or not self.worker.is_file():
            raise AdapterUnavailable("opentor_unavailable")
        env = os.environ.copy()
        env["HYDRAHIVE_OPENTOR_ROOT"] = str(self.root)
        try:
            completed = subprocess.run(
                [self.python, str(self.worker), command],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                timeout=60,
                env=env,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise AdapterUnavailable("opentor_unavailable") from exc
        if completed.returncode != 0:
            raise AdapterUnavailable("opentor_unavailable")
        try:
            result = json.loads(completed.stdout)
        except (TypeError, json.JSONDecodeError) as exc:
            raise AdapterUnavailable("opentor_unavailable") from exc
        if not isinstance(result, dict):
            raise AdapterUnavailable("opentor_unavailable")
        return result

    def status(self) -> dict:
        return self._run("status", {})

    def search(self, query: str, engines: list[str], limit: int, mode: str) -> dict:
        return self._run("search", {
            "query": query, "engines": engines, "limit": limit, "mode": mode,
        })

    def fetch(self, url: str) -> dict:
        return self._run("fetch", {"url": url})

    @staticmethod
    def extract_iocs(text: str) -> dict:
        # IOC extraction is local and has no network or worker requirement.
        return {
            "emails": sorted(set(re.findall(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text))),
            "onion_links": sorted(set(re.findall(r"https?://[a-z2-7]{16,56}\.onion[^\s<>'\"]*", text))),
            "ips": sorted(set(re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text))),
            "pgp_keys": bool(re.search(r"BEGIN PGP|END PGP|-----BEGIN", text)),
        }
