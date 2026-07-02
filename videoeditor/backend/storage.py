"""Video-Editor — Datei-Ablage: Originale bleiben im Projekt-Workspace.

Wichtig (Till, 2026-07-02): der Editor ist kein Silo. Was zum Projekt gehört,
bleibt im Projekt-Workspace-Root — dort liegen auch Atelier-Videos, generierte
Bilder, Musik. Damit ist alles automatisch über Samba erreichbar, kein
Doppel-Upload nötig.

    <projekt-workspace>/<beliebiger-rel-Pfad>.<ext>   Original (überall im WS)
    <projekt-workspace>/videoeditor/proxies/<hash>.mp4  480p-Proxy (Cache)
    <projekt-workspace>/videoeditor/sprites/<hash>.jpg  Filmstrip-Sprite (Cache)
    <projekt-workspace>/videoeditor/meta/<hash>.json    Probe+Keyframes+EDL
    <projekt-workspace>/videoeditor/exports/<id>.mp4    gerenderte Exports
    <projekt-workspace>/videoeditor/jobs/<id>.json      Job-Status

``file_id`` ist ein stabiler Hash des Original-Pfads (rel zum Workspace) —
so bleibt die Proxy/Meta-Zuordnung erhalten, auch wenn dieselbe Datei erneut
referenziert wird, und Cache-Dateien landen NIE außerhalb von videoeditor/.
"""
from __future__ import annotations

import hashlib
import re
import uuid
from pathlib import Path

from hydrahive.projects._config_io import list_for_user
from hydrahive.projects._paths import ensure_workspace

_PROJECT_ID_RE = re.compile(r"^[A-Za-z0-9-]{8,64}$")
_ID_RE = re.compile(r"^[a-f0-9]{32}$")

MAX_UPLOAD_BYTES = 4 * 1024 * 1024 * 1024  # 4 GiB pro Video
_ALLOWED_VIDEO_EXT = {"mp4", "mov", "mkv", "webm", "avi"}
# Nachvertonung: generierte/vorhandene Audiodateien aus dem Projekt-Workspace.
_ALLOWED_AUDIO_EXT = {"mp3", "wav", "m4a", "ogg", "flac", "aac"}

# Editor-eigene Cache-Unterordner werden NIE als importierbare Quelle gelistet.
_EDITOR_SUBDIR = "videoeditor"


def is_project_id(project_id: str) -> bool:
    return bool(_PROJECT_ID_RE.match(project_id))


def user_can_access(user: str, project_id: str) -> bool:
    return any(p["id"] == project_id for p in list_for_user(user))


def new_id() -> str:
    return uuid.uuid4().hex


def is_valid_id(file_id: str) -> bool:
    return bool(_ID_RE.match(file_id))


def video_ext_from(filename: str) -> str | None:
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()
    return ext if ext in _ALLOWED_VIDEO_EXT else None


def audio_ext_from(filename: str) -> str | None:
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()
    return ext if ext in _ALLOWED_AUDIO_EXT else None


def workspace_root(project_id: str) -> Path:
    """Der ganze Projekt-Workspace — Originale liegen irgendwo darunter."""
    return ensure_workspace(project_id)


def file_id_for(source_rel: str) -> str:
    """Stabile ID aus dem workspace-relativen Original-Pfad (für Cache-Namen)."""
    return hashlib.sha256(source_rel.encode("utf-8")).hexdigest()[:32]


def source_path(project_id: str, source_rel: str) -> Path | None:
    """Validiert einen workspace-relativen Pfad, gibt den absoluten Original-
    Pfad zurück oder None bei Traversal-Versuch / außerhalb des Workspace."""
    if not source_rel or source_rel.startswith("/") or ".." in Path(source_rel).parts:
        return None
    root = workspace_root(project_id).resolve()
    candidate = (root / source_rel).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def _editor_root(project_id: str) -> Path:
    root = workspace_root(project_id) / _EDITOR_SUBDIR
    root.mkdir(parents=True, exist_ok=True)
    return root


def _cache_subdir(project_id: str, name: str) -> Path:
    d = _editor_root(project_id) / name
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cache_path(project_id: str, subdir: str, filename: str) -> Path:
    root = _editor_root(project_id).resolve()
    p = (_cache_subdir(project_id, subdir) / filename).resolve()
    p.relative_to(root)  # wirft ValueError bei Traversal
    return p


def proxy_path(project_id: str, file_id: str) -> Path:
    return _cache_path(project_id, "proxies", f"{file_id}.mp4")


def sprite_path(project_id: str, file_id: str) -> Path:
    return _cache_path(project_id, "sprites", f"{file_id}.jpg")


def meta_path(project_id: str, file_id: str) -> Path:
    return _cache_path(project_id, "meta", f"{file_id}.json")


def audio_meta_path(project_id: str, audio_id: str) -> Path:
    """Sidecar-Meta einer aufbereiteten Audiodatei (Dauer + Peaks-Verweis)."""
    return _cache_path(project_id, "audio_meta", f"{audio_id}.json")


def peaks_path(project_id: str, audio_id: str) -> Path:
    """Vorberechnete Wellenform-Peaks (JSON) einer Audiodatei."""
    return _cache_path(project_id, "peaks", f"{audio_id}.json")


def export_path(project_id: str, export_id: str) -> Path:
    return _cache_path(project_id, "exports", f"{export_id}.mp4")


def jobs_dir(project_id: str) -> Path:
    return _cache_subdir(project_id, "jobs")


# Ordner, die als Upload-Ziel dienen, wenn direkt hochgeladen wird (statt ein
# bestehendes Projekt-Video zu importieren).
def uploads_dir(project_id: str) -> Path:
    d = workspace_root(project_id) / _EDITOR_SUBDIR / "uploads"
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_project_videos(project_id: str) -> list[Path]:
    """Alle Videodateien im gesamten Projekt-Workspace — außer im
    videoeditor/-eigenen Cache-Baum (Proxies/Exports sollen nicht als
    importierbare Quelle erscheinen)."""
    root = workspace_root(project_id)
    out: list[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if _EDITOR_SUBDIR in p.relative_to(root).parts:
            continue
        if p.suffix.lstrip(".").lower() in _ALLOWED_VIDEO_EXT:
            out.append(p)
    return sorted(out)


def list_known_file_ids(project_id: str) -> list[str]:
    """file_ids, für die bereits Meta/Proxy existiert (schon importiert)."""
    d = _cache_subdir(project_id, "meta")
    return [p.stem for p in d.glob("*.json")]


def list_project_audio(project_id: str) -> list[Path]:
    """Alle Audiodateien im gesamten Projekt-Workspace (mp3/wav/m4a/ogg/...) —
    außer im videoeditor/-eigenen Cache-Baum. Deckt generierte Musik/Sprache
    unter generated/ ebenso ab wie sonstwo abgelegte Audiodateien."""
    root = workspace_root(project_id)
    out: list[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if _EDITOR_SUBDIR in p.relative_to(root).parts:
            continue
        if p.suffix.lstrip(".").lower() in _ALLOWED_AUDIO_EXT:
            out.append(p)
    return sorted(out)


def list_known_audio_ids(project_id: str) -> list[str]:
    """audio_ids, für die bereits Peaks/Meta aufbereitet wurden."""
    d = _cache_subdir(project_id, "audio_meta")
    return [p.stem for p in d.glob("*.json")]
