"""Game-design documents stored as Markdown files in the project workspace."""

from __future__ import annotations

import hashlib
import os
import re
import secrets
import unicodedata
from pathlib import Path

from hydrahive.projects._paths import ensure_workspace

_DESIGN_DIR = ("game-studio", "design")
_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
MAX_BYTES = 256 * 1024
MAX_DOCS = 200

STARTER_DOCS: tuple[tuple[str, str, str], ...] = (
    ("spielidee", "Spielidee", "- Worum geht es in einem Satz?\n- Was ist das Besondere daran?\n- Für wen ist das Spiel?\n"),
    ("mechaniken", "Mechaniken", "- Was tut der Spieler die meiste Zeit?\n- Welche Regeln gelten?\n- Wie gewinnt oder verliert man?\n"),
    ("figuren", "Figuren", "- Wen steuert der Spieler?\n- Welche Gegner und Nebenfiguren gibt es?\n- Was können sie?\n"),
    ("welt-und-story", "Welt und Story", "- Wo und wann spielt das Spiel?\n- Was ist die Geschichte?\n- Welche Stimmung soll entstehen?\n"),
    ("level", "Level", "- Welche Level oder Gebiete gibt es?\n- In welcher Reihenfolge?\n- Was passiert jeweils?\n"),
)


class DesignDocError(RuntimeError):
    pass


def slugify(title: str) -> str:
    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_title).strip("-")[:64].strip("-")
    if not slug or not _SLUG.match(slug):
        raise DesignDocError("game_studio_design_title_invalid")
    return slug


def _directory(project_id: str) -> Path:
    root = ensure_workspace(project_id)
    current = root
    for part in _DESIGN_DIR:
        current = current / part
        if current.is_symlink():
            raise DesignDocError("game_studio_design_symlink")
        current.mkdir(mode=0o2775, exist_ok=True)
    if not current.resolve().is_relative_to(root.resolve()):
        raise DesignDocError("game_studio_design_escape")
    return current


def _path(project_id: str, slug: str) -> Path:
    if not _SLUG.match(slug):
        raise DesignDocError("game_studio_design_slug_invalid")
    path = _directory(project_id) / f"{slug}.md"
    if path.is_symlink():
        raise DesignDocError("game_studio_design_symlink")
    return path


def etag(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:32]


def _title(slug: str, content: str) -> str:
    for line in content.splitlines():
        if line.startswith("# "):
            return line[2:].strip()[:120] or slug
    return slug


def _write(path: Path, content: str) -> None:
    encoded = content.encode("utf-8")
    if len(encoded) > MAX_BYTES:
        raise DesignDocError("game_studio_design_too_large")
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o664)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o664)
    finally:
        temporary.unlink(missing_ok=True)


def _read(path: Path) -> str:
    if path.stat().st_size > MAX_BYTES:
        raise DesignDocError("game_studio_design_too_large")
    return path.read_text(encoding="utf-8")


def ensure_starters(project_id: str) -> None:
    for slug, title, prompts in STARTER_DOCS:
        path = _path(project_id, slug)
        if not path.exists():
            _write(path, f"# {title}\n\n{prompts}")


def list_docs(project_id: str) -> list[dict]:
    order = {slug: index for index, (slug, _, _) in enumerate(STARTER_DOCS)}
    docs: list[dict] = []
    for path in sorted(_directory(project_id).glob("*.md"))[:MAX_DOCS]:
        slug = path.stem
        if path.is_symlink() or not _SLUG.match(slug):
            continue
        try:
            content = _read(path)
        except (OSError, UnicodeDecodeError, DesignDocError):
            continue
        docs.append({"slug": slug, "title": _title(slug, content), "etag": etag(content), "size": len(content.encode("utf-8"))})
    docs.sort(key=lambda doc: (order.get(doc["slug"], len(order)), doc["title"].lower()))
    return docs


def get_doc(project_id: str, slug: str) -> dict:
    path = _path(project_id, slug)
    if not path.is_file():
        raise DesignDocError("game_studio_design_not_found")
    try:
        content = _read(path)
    except UnicodeDecodeError as exc:
        raise DesignDocError("game_studio_design_unreadable") from exc
    return {"slug": slug, "title": _title(slug, content), "etag": etag(content), "content": content}


def save_doc(project_id: str, slug: str, content: str, expected_etag: str | None) -> dict:
    path = _path(project_id, slug)
    if path.exists():
        current = _read(path)
        if expected_etag != etag(current):
            raise DesignDocError("game_studio_design_conflict")
    elif expected_etag is not None:
        raise DesignDocError("game_studio_design_conflict")
    _write(path, content)
    return {"slug": slug, "title": _title(slug, content), "etag": etag(content), "content": content}


def create_doc(project_id: str, title: str) -> dict:
    slug = slugify(title)
    path = _path(project_id, slug)
    if path.exists():
        raise DesignDocError("game_studio_design_exists")
    if len(list(_directory(project_id).glob("*.md"))) >= MAX_DOCS:
        raise DesignDocError("game_studio_design_limit")
    clean_title = " ".join(title.split())[:120]
    return save_doc(project_id, slug, f"# {clean_title}\n\n", None)
