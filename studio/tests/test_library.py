"""Studio Etappe 1: Bibliothek liest Medien aller alten Module – nur lesend (studio/SPEC.md „Bauplan Etappe 1“)."""
from __future__ import annotations

import json
import os
from pathlib import Path

from conftest import MOD_PREFIX, OTHER_PROJECT_ID, PROJECT_ID


def _put(path: Path, data: bytes = b"x", meta: dict | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    if meta is not None:
        path.with_name(path.name + ".json").write_text(json.dumps(meta))
    return path


def _lib(client, headers, pid: str = PROJECT_ID):
    return client.get(f"{MOD_PREFIX}/projects/{pid}/library", headers=headers)


def _by_rel(items: list[dict]) -> dict[str, dict]:
    return {i["rel"]: i for i in items}


def _snapshot(root: Path) -> dict[str, tuple[int, float]]:
    return {str(p.relative_to(root)): (p.stat().st_size, p.stat().st_mtime) for p in root.rglob("*")}


def test_reads_all_old_modules(client, auth_headers, ws) -> None:
    _put(ws / "atelier/images/hafen.png", meta={"prompt": "Hafen am Morgen", "created_at": "2026-10-01T10:00:00Z"})
    _put(ws / "atelier/output/abc.jpg", meta={"prompt": "Titelbild"})
    _put(ws / "atelier/videos/v1.mp4")
    (ws / "atelier/videos/job1.json").write_text(json.dumps({
        "job_id": "job1", "status": "completed", "video_rel": "videos/v1.mp4", "prompt": "Mira am Steg",
        "model": "google/veo-3.1-fast", "duration": "4", "created_at": "2026-10-02T10:00:00Z"}))
    _put(ws / "atelier/videos/v2.mp4")
    (ws / "atelier/videos/job2.json").write_text(json.dumps({"job_id": "job2", "status": "failed", "video_rel": "videos/v2.mp4"}))
    _put(ws / "atelier/films/film.mp4")
    _put(ws / "atelier/audio/song.mp3", meta={"prompt": "Technosong", "model": "google/lyria-3-pro-preview"})
    char = ws / "atelier/characters/c1"
    _put(char / "a.png")
    (char / "character.json").write_text(json.dumps({"id": "c1", "name": "Mira"}))
    _put(ws / "videoeditor/originals/drohne.mp4")
    _put(ws / "tonstudio/clips/s1.mp3", meta={"name": "folk rock", "prompt": "folk rock", "model": "lyria"})

    r = _lib(client, auth_headers)

    assert r.status_code == 200, r.text
    items = _by_rel(r.json()["items"])
    img = items["atelier/images/hafen.png"]
    assert img["kind"] == "image" and img["origin"] == "ai" and img["source"] == "atelier" and img["prompt"] == "Hafen am Morgen"
    assert items["atelier/output/abc.jpg"]["kind"] == "image"
    vid = items["atelier/videos/v1.mp4"]
    assert vid["kind"] == "video" and vid["prompt"] == "Mira am Steg" and vid["model"] == "google/veo-3.1-fast" and vid["duration"] == 4
    assert "atelier/videos/v2.mp4" not in items                       # fehlgeschlagener Auftrag
    assert items["atelier/films/film.mp4"]["kind"] == "video"
    song = items["atelier/audio/song.mp3"]
    assert song["kind"] == "music" and song["model"] == "google/lyria-3-pro-preview"
    mira = next(i for i in r.json()["items"] if i["kind"] == "element")
    assert mira["name"] == "Mira" and mira["thumb_abs"].endswith("atelier/characters/c1/a.png")
    up = items["videoeditor/originals/drohne.mp4"]
    assert up["kind"] == "video" and up["origin"] == "upload" and up["source"] == "videoeditor"
    ton = items["tonstudio/clips/s1.mp3"]
    assert ton["kind"] == "music" and ton["source"] == "tonstudio" and ton["name"] == "folk rock"
    for i in r.json()["items"]:
        assert Path(i["abs"]).is_absolute() and Path(i["abs"]).exists() and i["id"] and i["size"] >= 0
    assert not any(k.endswith(".json") for k in items)               # Begleitdateien erscheinen nie selbst


def test_ids_are_stable_and_newest_first(client, auth_headers, ws) -> None:
    old = _put(ws / "atelier/images/alt.png")
    new = _put(ws / "atelier/images/neu.png")
    os.utime(old, (1_700_000_000, 1_700_000_000))
    os.utime(new, (1_800_000_000, 1_800_000_000))
    first = [i for i in _lib(client, auth_headers).json()["items"] if i["rel"].startswith("atelier/images/")]
    second = [i for i in _lib(client, auth_headers).json()["items"] if i["rel"].startswith("atelier/images/")]
    assert [i["id"] for i in first] == [i["id"] for i in second]
    assert [i["rel"] for i in first] == ["atelier/images/neu.png", "atelier/images/alt.png"]


def test_reading_changes_nothing(client, auth_headers, ws) -> None:
    _put(ws / "atelier/images/a.png", meta={"prompt": "p"})
    _put(ws / "tonstudio/clips/s.mp3", meta={"name": "n"})
    before = _snapshot(ws)
    assert _lib(client, auth_headers).status_code == 200
    assert _snapshot(ws) == before
    assert not (ws / "studio").exists()                               # Etappe 1 legt nichts an


def test_broken_sidecar_and_odd_files(client, auth_headers, ws) -> None:
    _put(ws / "atelier/images/kaputt.png").with_name("kaputt.png.json").write_text("{nicht json")
    _put(ws / "atelier/images/notiz.txt")                            # keine Medien-Endung
    _put(ws / "atelier/images/halb.png.part")
    (ws / "atelier/videos").mkdir(parents=True, exist_ok=True)
    (ws / "atelier/videos/kaputt.json").write_text("[]")
    items = _by_rel(_lib(client, auth_headers).json()["items"])
    assert items["atelier/images/kaputt.png"]["name"] == "kaputt"
    assert "atelier/images/notiz.txt" not in items and "atelier/images/halb.png.part" not in items


def test_symlinks_out_of_the_project_are_skipped(client, auth_headers, ws, setup_test_env) -> None:
    outside = _put(setup_test_env / "geheim" / "pass.png")
    (ws / "atelier/images").mkdir(parents=True, exist_ok=True)
    (ws / "atelier/images/link.png").symlink_to(outside)
    (ws / "atelier/videos").mkdir(parents=True, exist_ok=True)
    (ws / "atelier/videos/j.json").write_text(json.dumps({"status": "completed", "video_rel": "../../../geheim/pass.png"}))
    items = _lib(client, auth_headers).json()["items"]
    assert not any("geheim" in i["abs"] or i["rel"].endswith("link.png") for i in items)


def test_only_members(client, auth_headers, other_headers, ws) -> None:
    _put(ws / "atelier/images/privat.png")
    r = _lib(client, other_headers)
    assert r.status_code == 404 and r.json()["detail"]["code"] == "studio_project_not_found"
    assert _lib(client, auth_headers, "../etc").status_code in (404, 422)
    assert _lib(client, auth_headers, "gibt-es-nicht-1234").status_code == 404
    assert client.get(f"{MOD_PREFIX}/projects/{PROJECT_ID}/library").status_code == 401
    assert _lib(client, other_headers, OTHER_PROJECT_ID).json()["items"] == []


def test_limit_keeps_the_newest(client, auth_headers, ws, monkeypatch) -> None:
    from backend import library
    monkeypatch.setattr(library, "MAX_ITEMS", 3)
    for n in range(5):
        p = _put(ws / f"atelier/images/b{n}.png")
        os.utime(p, (1_700_000_000 + n, 1_700_000_000 + n))
    body = _lib(client, auth_headers).json()
    assert [i["rel"] for i in body["items"]] == ["atelier/images/b4.png", "atelier/images/b3.png", "atelier/images/b2.png"]
    assert body["truncated"] is True


def test_projects_of_the_user(client, auth_headers) -> None:
    r = client.get(f"{MOD_PREFIX}/projects", headers=auth_headers)
    assert r.status_code == 200
    assert [p["id"] for p in r.json()["projects"]] == [PROJECT_ID]
