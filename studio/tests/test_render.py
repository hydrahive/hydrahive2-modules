"""Studio 4d: Film als MP4 – echter ffmpeg-Lauf, Auftrag, Liste, Bibliothek (studio/SPEC.md „Bauplan 4d“)."""
from __future__ import annotations

import json
import time
from pathlib import Path

from _render_helpers import (
    R,
    clip,
    make_image,
    make_video,
    needs_ffmpeg,
    probe,
    put_timeline,
    wait_render,
)
from conftest import MOD_PREFIX, OTHER_PROJECT_ID, PROJECT_ID


@needs_ffmpeg
def test_render_real_film(client, auth_headers, ws) -> None:
    client.put(f"{R}/plan/screenplay", headers=auth_headers, json={"aspect_ratio": "9:16"})
    v = make_video(ws, "a.mp4", 3)
    s = make_video(ws, "stumm.mp4", 2, audio=False)
    b = make_image(ws, "b.png")
    put_timeline(client, auth_headers, [clip("video", 0, 0.5, 2.5, v), clip("image", 3, 0, 1.5, b),
                                        clip("placeholder", 4.5, 0, 1, label="Sturm · Shot 2"), clip("video", 5.5, 0, 1, s)])
    r = client.post(f"{R}/render", headers=auth_headers, json={})
    assert r.status_code == 202, r.text
    assert r.json()["kind"] == "render"
    job = wait_render(client, auth_headers)
    assert job["status"] == "done", job
    rel = job["result"]["rel"]
    assert rel.startswith("studio/renders/") and rel.endswith(".mp4")
    info = probe(ws / rel)
    v_st = next(x for x in info["streams"] if x["codec_type"] == "video")
    a_st = [x for x in info["streams"] if x["codec_type"] == "audio"]
    assert (v_st["width"], v_st["height"]) == (720, 1280) and v_st["codec_name"] == "h264" and v_st["r_frame_rate"] == "25/1"
    assert a_st and a_st[0]["codec_name"] == "aac"
    assert abs(float(info["format"]["duration"]) - 6.5) < 0.25                    # 2 + Lücke 0,5 + 1,5 + 1 + 1 + … = 6,5
    meta = json.loads((ws / f"{rel}.json").read_text())
    assert abs(meta["duration"] - 6.5) < 0.01 and meta["width"] == 720 and meta["revision"] >= 1 and meta["missing"] == 0
    lst = client.get(f"{R}/renders", headers=auth_headers).json()["renders"]
    assert [x["rel"] for x in lst] == [rel] and lst[0]["abs"].endswith(rel) and lst[0]["duration"] == meta["duration"]
    lib = client.get(f"{MOD_PREFIX}/projects/{PROJECT_ID}/library", headers=auth_headers).json()["items"]
    mine = [i for i in lib if i["rel"] == rel]
    assert mine and mine[0]["source"] == "studio_render" and mine[0]["kind"] == "video"


@needs_ffmpeg
def test_missing_media_still_renders(client, auth_headers, ws) -> None:
    v = make_video(ws, "a.mp4", 2)
    put_timeline(client, auth_headers, [clip("video", 0, 0, 2, v)])
    (ws / v).unlink()                                                                 # nach dem Speichern verschwunden
    client.post(f"{R}/render", headers=auth_headers, json={})
    job = wait_render(client, auth_headers)
    assert job["status"] == "done" and job["result"]["missing"] == 1


def test_empty_timeline(client, auth_headers, ws) -> None:
    r = client.post(f"{R}/render", headers=auth_headers, json={})
    assert r.status_code == 400 and r.json()["detail"]["code"] == "studio_render_empty"
    assert client.get(f"{R}/renders", headers=auth_headers).json() == {"renders": []}


def test_second_click_waits_in_line(client, auth_headers, ws, monkeypatch) -> None:
    """7c: ein zweiter Klick ist kein Fehler mehr, der Film wartet (Platz 2)."""
    import threading

    from backend import render
    gate = threading.Event()
    monkeypatch.setattr(render, "_run_ffmpeg", lambda cmd, seconds, progress, **_: gate.wait(5) and None)
    b = ws / "studio/media/images"
    b.mkdir(parents=True)
    (b / "x.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\0" * 32)
    put_timeline(client, auth_headers, [clip("image", 0, 0, 2, "studio/media/images/x.png")])
    assert client.post(f"{R}/render", headers=auth_headers, json={}).status_code == 202
    r = client.post(f"{R}/render", headers=auth_headers, json={})
    assert r.status_code == 202 and r.json()["status"] == "queued" and r.json()["position"] == 2
    gate.set()
    end = time.time() + 10                                                            # beide fertig, bevor ffmpeg zurückkommt
    while time.time() < end and any(j["status"] in ("queued", "running") for j in client.get(f"{R}/plan/jobs", headers=auth_headers).json()["jobs"]):
        time.sleep(0.05)


def test_ffmpeg_failure_is_failed_job(client, auth_headers, ws, monkeypatch) -> None:
    from backend import render

    def boom(cmd, seconds, progress, **_):
        raise render.RenderFailed()
    monkeypatch.setattr(render, "_run_ffmpeg", boom)
    b = ws / "studio/media/images"
    b.mkdir(parents=True)
    (b / "x.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\0" * 32)
    put_timeline(client, auth_headers, [clip("image", 0, 0, 2, "studio/media/images/x.png")])
    client.post(f"{R}/render", headers=auth_headers, json={})
    job = wait_render(client, auth_headers)
    assert job["status"] == "failed" and job["error"] == "render_failed"
    assert not list((ws / "studio/renders").glob("*.mp4")) if (ws / "studio/renders").exists() else True


def test_keep_last_ten(client, auth_headers, ws) -> None:
    from backend import render
    d = ws / "studio/renders"
    d.mkdir(parents=True)
    for i in range(12):
        (d / f"{i:032x}.mp4").write_bytes(b"x")
        (d / f"{i:032x}.mp4.json").write_text(json.dumps({"created_at": f"2026-10-18T10:{i:02d}:00Z", "duration": 1}))
    (d / "fremd.txt").write_text("bleibt")
    render.prune(PROJECT_ID)
    left = sorted(p.name for p in d.glob("*.mp4"))
    assert left == [f"{i:032x}.mp4" for i in range(2, 12)]                            # die 10 neuesten
    assert not (d / f"{0:032x}.mp4.json").exists() and (d / "fremd.txt").exists()


def test_foreign_project(client, auth_headers) -> None:
    assert client.post(f"{MOD_PREFIX}/projects/{OTHER_PROJECT_ID}/render", headers=auth_headers, json={}).status_code == 404
    assert client.get(f"{MOD_PREFIX}/projects/{OTHER_PROJECT_ID}/renders", headers=auth_headers).status_code == 404


@needs_ffmpeg
def test_tricky_placeholder_texts_render(client, auth_headers, ws) -> None:
    """Shot-Namen sind Nutzertext: Doppelpunkt, Apostroph, Prozent, Klammern, Backslash, Semikolon, Komma, Zeilenumbruch."""
    labels = ["Der Sturm: 'Shot' 2 – 100% [x]", "a\\b;c,d", "Zeile1\nZeile2", "Äöü ß € 🙂", "'''", ""]
    put_timeline(client, auth_headers, [clip("placeholder", i, 0, 1, label=t) for i, t in enumerate(labels)])
    client.post(f"{R}/render", headers=auth_headers, json={})
    job = wait_render(client, auth_headers)
    assert job["status"] == "done", job
    assert abs(float(probe(ws / job["result"]["rel"])["format"]["duration"]) - 6) < 0.25


def test_placeholder_text_file_is_wrapped(client, auth_headers, ws, monkeypatch) -> None:
    """Die Textdatei für die Platzhalter-Karte enthält den umbrochenen Text (hochkant schmal)."""
    from backend import render
    seen: list[str] = []

    def fake(cmd, seconds, progress, **_):
        graph = cmd[cmd.index("-filter_complex") + 1]
        path = graph.split("textfile='", 1)[1].split("'", 1)[0]
        seen.append(Path(path).read_text(encoding="utf-8"))
        raise render.RenderFailed()
    monkeypatch.setattr(render, "_run_ffmpeg", fake)
    client.put(f"{R}/plan/screenplay", headers=auth_headers, json={"aspect_ratio": "9:16"})
    put_timeline(client, auth_headers, [clip("placeholder", 0, 0, 1, label="Ankunft im Hafen · Shot 3 – Kapitän Ole an der Reling")])
    client.post(f"{R}/render", headers=auth_headers, json={})
    wait_render(client, auth_headers)
    assert seen and "\n" in seen[0] and seen[0].replace("\n", " ") == "Ankunft im Hafen · Shot 3 – Kapitän Ole an der Reling"
