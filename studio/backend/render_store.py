"""Fertige Filme (Spec „Bauplan 4d“, 7b): Liste und Aufräumen in studio/renders/. Ausgelagert aus render.py."""
from __future__ import annotations

from ._store import is_id, project_root, read_json, root

KEEP = 10
RENDER_DIR = "studio/renders"


def _list(pid: str) -> list[tuple[str, dict]]:
    d = root(pid) / "renders"
    out = []
    for p in d.glob("*.mp4") if d.is_dir() else []:
        if is_id(p.stem) and p.is_file() and not p.is_symlink():
            meta = read_json(p.with_name(p.name + ".json"), {})
            out.append((p.name, meta if isinstance(meta, dict) else {}))
    return sorted(out, key=lambda x: str(x[1].get("created_at") or ""), reverse=True)


def list_renders(pid: str) -> dict:
    base = project_root(pid)
    return {"renders": [{"rel": f"{RENDER_DIR}/{n}", "abs": str(base / RENDER_DIR / n), "name": n,
                         **{k: m.get(k) for k in ("duration", "width", "height", "aspect", "quality", "created_at", "missing", "clips")},
                         "subtitles": m.get("subtitles") or []}
                        for n, m in _list(pid)]}


def prune(pid: str) -> None:
    """Nur die KEEP neuesten Filme behalten; nur eigene Dateien in studio/renders/."""
    for name, _ in _list(pid)[KEEP:]:
        d = root(pid) / "renders"
        (d / name).unlink(missing_ok=True)
        (d / f"{name}.json").unlink(missing_ok=True)
