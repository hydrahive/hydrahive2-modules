"""Sicherer Scanner für die festen Mediaplayer-Quellen eines Projekts."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from . import source_metadata, storage, tracks_store
from .media_formats import MediaKind, format_for

MAX_SOURCES = 500


@dataclass(frozen=True, slots=True)
class SourceSpec:
    source: str
    group: str
    directory: str
    kinds: tuple[MediaKind, ...]
    nested: bool = False


SOURCE_SPECS = (
    SourceSpec("generated", "Agent (generiert)", "generated", ("audio", "video"), True),
    SourceSpec("atelier_audio", "Atelier · Musik", "atelier/audio", ("audio",)),
    SourceSpec("atelier_videos", "Atelier · Szenen-Clips", "atelier/videos", ("video",)),
    SourceSpec("atelier_films", "Atelier · Filme", "atelier/films", ("video",)),
    SourceSpec("media_audio", "Hochgeladen (Medienordner)", "media/audio", ("audio",)),
    SourceSpec("media_video", "Hochgeladen (Medienordner)", "media/video", ("video",)),
)


def source_key(project_id: str, relative: str) -> str:
    return f"projects/{project_id}/{relative}"


def _safe_relative(relative: str) -> PurePosixPath | None:
    """Nur kanonische relative Pfade. Am Rohtext prüfen: PurePosixPath macht
    aus „a/./b“ stillschweigend „a/b“ (sonst zwei Namen für denselben Clip)."""
    if "\\" in relative or relative.startswith("/"):
        return None
    if any(part in ("", ".", "..") for part in relative.split("/")):
        return None
    return PurePosixPath(relative)


def _matching_spec(pure: PurePosixPath) -> SourceSpec | None:
    for spec in SOURCE_SPECS:
        prefix = PurePosixPath(spec.directory).parts
        if pure.parts[:len(prefix)] != prefix:
            continue
        depth = len(pure.parts) - len(prefix)
        if depth == 1 or (spec.nested and depth == 2):
            return spec
    return None


def _has_symlink(root: Path, pure: PurePosixPath) -> bool:
    current = root
    for part in pure.parts:
        current /= part
        if current.is_symlink():
            return True
    return False


def safe_source_file(project_id: str, relative: str) -> tuple[Path, SourceSpec] | None:
    pure = _safe_relative(relative)
    if pure is None:
        return None
    spec = _matching_spec(pure)
    media_format = format_for(pure.name)
    if spec is None or media_format is None or media_format.kind not in spec.kinds:
        return None
    root = storage.project_workspace(project_id)
    candidate = root.joinpath(*pure.parts)
    if _has_symlink(root, pure) or not candidate.is_file():
        return None
    try:
        if not candidate.resolve().is_relative_to(root.resolve()):
            return None
    except OSError:
        return None
    return candidate, spec


def _iter_source_files(project_id: str, spec: SourceSpec):
    root = storage.project_workspace(project_id)
    pure_dir = PurePosixPath(spec.directory)
    directory = root.joinpath(*pure_dir.parts)
    if _has_symlink(root, pure_dir) or not directory.is_dir():
        return
    try:
        children = list(directory.iterdir())
    except OSError:
        return
    for child in children:
        if child.is_file() and not child.is_symlink():
            yield child
        elif spec.nested and child.is_dir() and not child.is_symlink():
            try:
                yield from (item for item in child.iterdir() if item.is_file() and not item.is_symlink())
            except OSError:
                continue


def _entry(project_id: str, candidate: Path, spec: SourceSpec, sidecars, imported, library) -> dict | None:
    root = storage.project_workspace(project_id)
    try:
        relative = candidate.relative_to(root).as_posix()
    except ValueError:
        return None
    media_format = format_for(candidate.name)
    if media_format is None or media_format.kind not in spec.kinds:
        return None
    if spec.source.startswith("media_") and candidate.name in library:
        return None
    by_stem, by_filename = sidecars
    sidecar = by_filename.get(candidate.name) or by_stem.get(candidate.stem) or {}
    meta = source_metadata.trimmed(sidecar)
    title = meta.get("prompt", candidate.name)
    if spec.source == "atelier_films" and "created_at" in meta:
        title = f"Film vom {meta['created_at']}"
    try:
        stat = candidate.stat()
    except OSError:
        return None
    return {
        "source": spec.source,
        "group": spec.group,
        "path": relative,
        "kind": media_format.kind,
        "title": str(title)[:200],
        "meta": meta,
        "size_bytes": stat.st_size,
        "mtime": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        "already_imported": source_key(project_id, relative) in imported,
        "_mtime": stat.st_mtime,
    }


def list_sources(project_id: str, kind: MediaKind | None = None, source: str | None = None) -> list[dict]:
    found: list[dict] = []
    imported = tracks_store.imported_sources(project_id)
    library = tracks_store.library_filenames(project_id)
    for spec in SOURCE_SPECS:
        if source is not None and spec.source != source:
            continue
        directory = storage.project_workspace(project_id) / spec.directory
        sidecars = source_metadata.load(directory) if spec.source.startswith("atelier_") else ({}, {})
        for candidate in _iter_source_files(project_id, spec):
            entry = _entry(project_id, candidate, spec, sidecars, imported, library)
            if entry is not None and (kind is None or entry["kind"] == kind):
                found.append(entry)
    found.sort(key=lambda item: (item["_mtime"], item["path"]), reverse=True)
    for item in found[:MAX_SOURCES]:
        item.pop("_mtime", None)
    return found[:MAX_SOURCES]


def source_entry(project_id: str, relative: str) -> dict | None:
    safe = safe_source_file(project_id, relative)
    if safe is None:
        return None
    candidate, spec = safe
    library = tracks_store.library_filenames(project_id)
    if spec.source.startswith("media_") and candidate.name in library:
        return None
    sidecars = source_metadata.load(candidate.parent) if spec.source.startswith("atelier_") else ({}, {})
    return _entry(
        project_id, candidate, spec, sidecars,
        tracks_store.imported_sources(project_id), library,
    )
