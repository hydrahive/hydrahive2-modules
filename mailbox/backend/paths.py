"""Wo das Archiv liegt (Spec §5a). Standard <data_dir>/mailbox/archiv; später einstellbar (eigene Platte)."""
from __future__ import annotations

from pathlib import Path

from hydrahive.settings import settings


def archive_root() -> Path:
    return settings.data_dir / "mailbox" / "archiv"
