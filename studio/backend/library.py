"""Studio-Bibliothek (Etappe 1): alle Medien eines Projekts als eine Liste, neueste zuerst. Liest nur."""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

from hydrahive.projects._paths import workspace_path

from . import _sources
from . import media as media_rules

logger = logging.getLogger(__name__)

MAX_ITEMS = 5000


def _created(p: Path, meta: dict) -> str:
    v = meta.get("created_at")
    if isinstance(v, str) and v:
        return v
    return datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _entry(root: Path, p: Path, kind: str, origin: str, source: str, meta: dict,
           *, name: str | None = None, thumb: Path | None = None) -> dict:
    rel = p.relative_to(root).as_posix()
    st = p.stat()
    item = {
        "id": hashlib.sha256(rel.encode("utf-8")).hexdigest()[:16],
        "kind": kind, "origin": origin, "source": source, "rel": rel, "abs": str(p),
        "name": (name or "").strip() or p.stem, "size": st.st_size, "mtime": st.st_mtime,
        "created_at": _created(p, meta),
        "deletable": media_rules.is_own(rel),                                      # nur eigene Dateien (C1)
    }
    for key in ("prompt", "model"):
        if isinstance(meta.get(key), str) and meta[key].strip():
            item[key] = meta[key].strip()
    if isinstance(meta.get("duration"), (int, float)) and meta["duration"] > 0:
        item["duration"] = meta["duration"]
    if thumb is not None:
        item["thumb_abs"] = str(thumb)
    return item


def list_items(project_id: str) -> dict:
    """Alle Medien des Projekts. Ohne Projektordner: leer (nichts wird angelegt)."""
    root = workspace_path(project_id)
    if not root.is_dir():
        return {"items": [], "truncated": False}

    def make(p: Path, kind: str, origin: str, source: str, meta: dict, **kw) -> dict:
        return _entry(root, p, kind, origin, source, meta, **kw)

    items: list[dict] = []
    for reader in _sources.READERS:
        try:
            items += reader(root, make)
        except OSError:
            logger.warning("Studio-Bibliothek: Quelle %s in %s nicht lesbar", reader.__name__, project_id, exc_info=True)
    items.sort(key=lambda i: i["mtime"], reverse=True)
    for i in items:
        del i["mtime"]
    return {"items": items[:MAX_ITEMS], "truncated": len(items) > MAX_ITEMS}
