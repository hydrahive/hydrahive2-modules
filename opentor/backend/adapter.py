from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from typing import Any


class AdapterUnavailable(RuntimeError):
    pass


class OpenTorAdapter:
    """Thin, server-configured bridge to a reviewed OpenTor checkout.

    The checkout path is never accepted from a request. The adapter intentionally
    fails closed when HYDRAHIVE_OPENTOR_ROOT is missing or malformed.
    """

    def __init__(self, root: str | None = None) -> None:
        configured = root or os.getenv("HYDRAHIVE_OPENTOR_ROOT")
        self.root = Path(configured).resolve() if configured else None
        self._loaded = False
        self._osint: Any = None
        self._torcore: Any = None

    def _load(self) -> None:
        if self._loaded:
            return
        if self.root is None or not (self.root / "scripts").is_dir():
            raise AdapterUnavailable("opentor_unavailable")
        root = str(self.root)
        scripts = str(self.root / "scripts")
        for path in (root, scripts):
            if path not in sys.path:
                sys.path.insert(0, path)
        try:
            self._osint = importlib.import_module("scripts.osint")
            self._torcore = importlib.import_module("scripts.torcore")
        except (ImportError, OSError) as exc:
            raise AdapterUnavailable("opentor_unavailable") from exc
        self._loaded = True

    def status(self) -> dict:
        self._load()
        result = self._torcore.check_tor()
        return {
            "tor_reachable": bool(result.get("tor_active")),
            "worker_ready": True,
            "last_error": None if result.get("tor_active") else "tor_unreachable",
        }

    def search(self, query: str, engines: list[str], limit: int, mode: str) -> dict:
        self._load()
        return self._osint.search_darkweb(
            query, engines=engines or None, max_results=limit, mode=mode,
        )

    def fetch(self, url: str) -> dict:
        self._load()
        return self._torcore.fetch(url)

    @staticmethod
    def extract_iocs(text: str) -> dict:
        try:
            module = importlib.import_module("scripts.osint")
            return module.extract_entities(text)
        except ImportError:
            # Safe fallback keeps extraction useful in tests and when only the
            # module adapter is installed; it performs no network access.
            import re
            return {
                "emails": sorted(set(re.findall(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text))),
                "onion_links": sorted(set(re.findall(r"https?://[a-z2-7]{16,56}\.onion[^\s<>'\"]*", text))),
                "ips": sorted(set(re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text))),
            }
