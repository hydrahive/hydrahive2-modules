"""Anzeige-Infos für Projekt-Audio (Name, Dauer, Modell), damit die Bibliothek nicht nur UUID-Dateinamen zeigt.

Reihenfolge für den Namen: Sidecar ``<datei>.json`` (Atelier: ``prompt``/``scene``; generisch: ``title``/``name``)
→ Titel-Tag der Datei (ffprobe) → Dateiname. Dauer per ffprobe.

ffprobe kostet ~60 ms je Datei; deshalb ein kleiner Cache je Datei, Schlüssel (Pfad, Größe, mtime). Er liegt unter
``<workspace>/tonstudio/.meta-cache.json`` und wird bei Änderungen neu geschrieben (atomar, wie die Sidecars).
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from . import storage

_CACHE = ".meta-cache.json"


async def _probe(path: Path) -> dict:
    proc = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "error", "-show_entries", "format=duration:format_tags=title", "-of", "json", str(path),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
    )
    out, _ = await proc.communicate()
    try:
        fmt = json.loads(out.decode("utf-8", "replace")).get("format") or {}
    except ValueError:
        return {}
    tags = {str(k).lower(): v for k, v in (fmt.get("tags") or {}).items()}
    try:
        duration = round(float(fmt.get("duration") or 0), 3) or None
    except (TypeError, ValueError):
        duration = None
    return {"duration": duration, "title": str(tags.get("title") or "").strip()[:200] or None}


def _sidecar(path: Path) -> dict:
    side = path.with_name(path.name + ".json")
    if side.is_symlink() or not side.is_file():
        return {}
    try:
        data = json.loads(side.read_text("utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _first_line(text: object, n: int = 120) -> str | None:
    s = str(text or "").strip()
    return s.splitlines()[0][:n] if s else None


def _load(project_id: str) -> dict:
    try:
        data = json.loads((storage.tonstudio_root(project_id) / _CACHE).read_text("utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(project_id: str, cache: dict) -> None:
    target = storage.tonstudio_root(project_id) / _CACHE
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(cache, ensure_ascii=False), "utf-8")
    tmp.replace(target)


async def enrich(project_id: str, items: list[dict], paths: dict[str, Path]) -> None:
    """Ergänzt ``name``, ``duration``, ``model``, ``prompt`` der Projekt-Einträge (in place)."""
    cache = _load(project_id)
    fresh: dict = {}
    todo = []
    for it in items:
        p = paths[it["source_rel"]]
        st = p.stat()
        key = f'{it["source_rel"]}|{st.st_size}|{int(st.st_mtime)}'
        if key in cache:
            fresh[key] = cache[key]
        else:
            todo.append((key, p))
    for (key, _), info in zip(todo, await asyncio.gather(*(_probe(p) for _, p in todo)), strict=True):
        fresh[key] = info
    for it in items:
        p = paths[it["source_rel"]]
        st = p.stat()
        info = fresh[f'{it["source_rel"]}|{st.st_size}|{int(st.st_mtime)}']
        side = _sidecar(p)
        label = _first_line(side.get("title") or side.get("name") or side.get("prompt") or side.get("scene"))
        it["name"] = label or info.get("title") or p.name
        it["named"] = bool(label or info.get("title"))
        it["duration"] = info.get("duration")
        it["model"] = side.get("model") if isinstance(side.get("model"), str) else None
        it["prompt"] = _first_line(side.get("prompt"), 400)
    if fresh != cache:
        _save(project_id, fresh)
