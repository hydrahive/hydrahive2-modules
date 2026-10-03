"""Rig-Konfiguration: eine JSON-Datei, nur für den Dienst-Nutzer lesbar (0600)."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

DEFAULT_PATH = Path(os.environ.get("HH_RIG_CONFIG", "/etc/hydrahive-rig/config.json"))


@dataclass
class RigConfig:
    server: str
    token: str
    name: str
    rig_id: str
    pin: str | None = None

    def save(self, path: Path = DEFAULT_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(asdict(self), f, indent=2)
        os.replace(tmp, path)

    @classmethod
    def load(cls, path: Path = DEFAULT_PATH) -> RigConfig:
        if path.stat().st_mode & 0o077:
            raise PermissionError(f"{path} ist für andere lesbar — erwartet 0600")
        data = json.loads(path.read_text())
        return cls(**{k: data.get(k) for k in ("server", "token", "name", "rig_id", "pin")})
