"""Songs anlegen, lesen, speichern (mit Versionen), Papierkorb (SPEC.md §4, §5.1).

- Jedes Speichern mit Änderung erhöht ``version`` und legt den alten Stand unter ``versions/<n>.json`` ab.
- Speichern mit veralteter ``expected_version`` → ``VersionConflict`` (Route: 409). Nichts wird still überschrieben.
- Unbekannte ``format_version`` → ``SongFormatError``. Kein Raten.
- Schreiben atomar (tmp + replace), damit ein Absturz keine halbe Datei hinterlässt.
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from . import storage
from .song_model import FORMAT, FORMAT_VERSION, SongIn

_SERVER_FIELDS = ("id", "format", "format_version", "version", "created_at", "updated_at")


class SongFormatError(ValueError):
    """song.json hat ein Format, das dieses Modul nicht kennt."""


class VersionConflict(RuntimeError):
    def __init__(self, current: int):
        super().__init__(f"Song wurde inzwischen geändert (Version {current})")
        self.current = current


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _dir(project_id: str, song_id: str, *, trash: bool = False) -> Path | None:
    if not storage.is_valid_id(song_id):
        return None
    base = storage.trash_dir(project_id) if trash else storage.songs_dir(project_id)
    return base / song_id


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
    tmp.replace(path)


def _read(d: Path) -> dict | None:
    f = d / "song.json"
    if not f.is_file():
        return None
    data = json.loads(f.read_text("utf-8"))
    if data.get("format") != FORMAT or data.get("format_version") != FORMAT_VERSION:
        raise SongFormatError(f"Unbekanntes Song-Format: {data.get('format')} v{data.get('format_version')}")
    return data


def _normalize(body: dict) -> dict:
    """Client-Daten prüfen und auf das Modell bringen (unbekannte Felder fallen weg)."""
    clean = {k: v for k, v in (body or {}).items() if k not in _SERVER_FIELDS}
    return SongIn.model_validate(clean).model_dump()


def create(project_id: str, body: dict) -> dict:
    song_id = storage.new_id()
    now = _now()
    song = {"format": FORMAT, "format_version": FORMAT_VERSION, "id": song_id, "version": 1,
            "created_at": now, "updated_at": now, **_normalize(body)}
    _write_json(storage.songs_dir(project_id) / song_id / "song.json", song)
    return song


def get(project_id: str, song_id: str) -> dict | None:
    d = _dir(project_id, song_id)
    return _read(d) if d else None


def save(project_id: str, song_id: str, body: dict, *, expected_version: int) -> dict | None:
    d = _dir(project_id, song_id)
    current = _read(d) if d else None
    if current is None:
        return None
    if int(expected_version) != int(current["version"]):
        raise VersionConflict(int(current["version"]))
    content = _normalize(body)
    if all(current.get(k) == v for k, v in content.items()):
        return current
    _write_json(d / "versions" / f"{current['version']}.json", current)
    song = {**current, **content, "version": int(current["version"]) + 1, "updated_at": _now()}
    _write_json(d / "song.json", song)
    return song


def _summaries(base: Path) -> list[dict]:
    out = []
    for d in base.iterdir():
        if not (d.is_dir() and storage.is_valid_id(d.name)):
            continue
        try:
            s = _read(d)
        except (SongFormatError, json.JSONDecodeError, OSError):
            continue
        if s:
            out.append({k: s.get(k) for k in ("id", "title", "version", "bpm", "key", "updated_at", "created_at")}
                       | {"tracks": len(s.get("tracks") or [])})
    out.sort(key=lambda x: (x.get("updated_at") or "", x["id"]), reverse=True)
    return out


def list_songs(project_id: str) -> list[dict]:
    return _summaries(storage.songs_dir(project_id))


def list_trash(project_id: str) -> list[dict]:
    return _summaries(storage.trash_dir(project_id))


def _move(project_id: str, song_id: str, *, to_trash: bool) -> bool:
    src = _dir(project_id, song_id, trash=not to_trash)
    dst = _dir(project_id, song_id, trash=to_trash)
    if not src or not dst or not (src / "song.json").is_file() or dst.exists():
        return False
    shutil.move(str(src), str(dst))
    return True


def trash(project_id: str, song_id: str) -> bool:
    return _move(project_id, song_id, to_trash=True)


def restore(project_id: str, song_id: str) -> bool:
    return _move(project_id, song_id, to_trash=False)
