"""Projekt-Audio aus festen Quellordnern (SPEC §4, wie der Musicplayer), mit Anzeige-Namen, Duplikaten, Umbenennen.

- Quellordner: ``generated/`` (mit Unterordnern), ``atelier/audio/``, ``media/audio/``. Symlinks werden nicht verfolgt.
- Namen: eigener Name (Umbenennen) → Sidecar ``<datei>.json`` → Titel-Tag → Dateiname (dann ``named=False``).
  Eigene Namen liegen in ``<workspace>/tonstudio/labels.json``. Projektdateien werden NIE verändert.
- Duplikate: gleicher Inhalt (Größe + SHA-256) erscheint einmal; weitere Fundorte stehen in ``copies``. Vorrang hat
  die frühere Gruppe (tonstudio, atelier, generated, media). Live 11.10.: media/audio enthielt Kopien von generated/.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from . import storage
from ._meta import enrich

SOURCE_DIRS: tuple[tuple[str, bool, str], ...] = (
    ("generated", True, "generated"), ("atelier/audio", False, "atelier"), ("media/audio", False, "media"),
)
GROUP_ORDER = ("tonstudio", "atelier", "generated", "media")
_LABELS = "labels.json"


class LabelError(ValueError):
    pass


def files_in(root: Path, rel_dir: str, nested: bool) -> list[Path]:
    """Dateien in einem Quellordner. Kein Teil des Pfads darf ein Symlink sein (sonst ginge es aus dem Projekt)."""
    base = root
    for part in rel_dir.split("/"):
        base = base / part
        if base.is_symlink() or not base.is_dir():
            return []
    out: list[Path] = []
    stack = [base]
    while stack:
        d = stack.pop()
        for p in d.iterdir():
            if p.is_symlink() or p.name.startswith("."):
                continue
            if p.is_dir():
                if nested:
                    stack.append(p)
            elif p.is_file() and storage.audio_ext(p.name):
                out.append(p)
    return out


def load_labels(project_id: str) -> dict[str, str]:
    try:
        data = json.loads((storage.tonstudio_root(project_id) / _LABELS).read_text("utf-8"))
    except (OSError, ValueError):
        return {}
    return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}


def _in_library(project_id: str, rel: str) -> bool:
    root = storage.workspace_root(project_id)
    path = storage.safe_under(root, rel)
    if path is None or not path.is_file() or path.is_symlink() or not storage.audio_ext(path.name):
        return False
    if path.parent.resolve() == storage.clips_dir(project_id).resolve():
        return True
    return any(path in files_in(root, d, nested) for d, nested, _ in SOURCE_DIRS)


def set_label(project_id: str, rel: str, name: str) -> None:
    """Eigenen Anzeigenamen setzen (leer = zurücksetzen). Nur für Dateien, die in der Bibliothek erscheinen."""
    name = (name or "").strip()
    if len(name) > 200:
        raise LabelError("Name zu lang (höchstens 200 Zeichen)")
    if not _in_library(project_id, rel):
        raise LabelError("Datei gehört nicht zur Bibliothek")
    labels = load_labels(project_id)
    if name:
        labels[rel] = name
    else:
        labels.pop(rel, None)
    target = storage.tonstudio_root(project_id) / _LABELS
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(labels, ensure_ascii=False, indent=1), "utf-8")
    tmp.replace(target)


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return f"{path.stat().st_size}:{h.hexdigest()}"


async def project_audio(project_id: str) -> tuple[list[dict], dict[str, Path]]:
    root = storage.workspace_root(project_id)
    out: list[dict] = []
    paths: dict[str, Path] = {}
    for rel_dir, nested, group in SOURCE_DIRS:
        for p in files_in(root, rel_dir, nested):
            rel = str(p.relative_to(root))
            st = p.stat()
            paths[rel] = p
            out.append({"source_rel": rel, "origin": "project", "group": group, "name": p.name, "duration": None,
                        "model": None, "backend": None, "prompt": None, "copies": [],
                        "created_at": datetime.fromtimestamp(st.st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "size_bytes": st.st_size})
    await enrich(project_id, out, paths)
    return out, paths


def dedupe(items: list[dict], paths: dict[str, Path]) -> list[dict]:
    """Gleicher Inhalt → ein Eintrag (frühere Gruppe gewinnt), Kopien in ``copies``. Hash nur bei gleicher Größe."""
    by_size: dict[int, list[dict]] = {}
    for it in items:
        by_size.setdefault(it.get("size_bytes") or 0, []).append(it)
    drop: set[str] = set()
    for same in by_size.values():
        if len(same) < 2:
            continue
        keep: dict[str, dict] = {}
        for it in sorted(same, key=lambda i: (GROUP_ORDER.index(i["group"]), i["source_rel"])):
            p = paths.get(it["source_rel"])
            if p is None:
                continue
            d = _digest(p)
            if d in keep:
                keep[d].setdefault("copies", []).append(it["source_rel"])
                drop.add(it["source_rel"])
            else:
                keep[d] = it
    return [i for i in items if i["source_rel"] not in drop]
