"""Studio 7b: Vorlagen für die Ausgabe – Format + Qualität (studio/SPEC.md „7b im Detail“)."""
from __future__ import annotations

import json

import pytest
from _render_helpers import R, clip, make_image, make_video, needs_ffmpeg, probe, put_timeline, wait_render

from backend import render_preset as rp


@pytest.mark.parametrize(("aspect", "quality", "size"), [
    ("16:9", "preview", (854, 480)), ("16:9", "standard", (1280, 720)), ("16:9", "high", (1920, 1080)),
    ("9:16", "preview", (480, 854)), ("9:16", "standard", (720, 1280)), ("9:16", "high", (1080, 1920)),
    ("1:1", "preview", (480, 480)), ("1:1", "standard", (720, 720)), ("1:1", "high", (1080, 1080)),
    ("4:3", "preview", (640, 480)), ("4:3", "standard", (960, 720)), ("21:9", "standard", (1680, 720)),
    ("21:9", "high", (2520, 1080)), ("unsinn", "standard", (1280, 720)),
])
def test_size(aspect, quality, size) -> None:
    w, h = rp.size(aspect, quality)
    assert (w, h) == size and w % 2 == 0 and h % 2 == 0


def test_resolve_screenplay_and_defaults() -> None:
    assert rp.resolve(None, None, "9:16") == {"aspect": "9:16", "quality": "standard", "size": (720, 1280), "crf": 23}
    assert rp.resolve("screenplay", "high", "4:3") == {"aspect": "4:3", "quality": "high", "size": (1440, 1080), "crf": 20}
    assert rp.resolve("1:1", "preview", "16:9") == {"aspect": "1:1", "quality": "preview", "size": (480, 480), "crf": 28}
    assert rp.resolve(None, None, "kaputt")["aspect"] == "16:9"                     # unbekanntes Drehbuch-Format


@pytest.mark.parametrize(("aspect", "quality"), [("4:3", None), ("21:9", "standard"), ("x", None), (None, "ultra"),
                                                  (169, None), (None, 720), ("", None), (None, "")])
def test_resolve_rejects(aspect, quality) -> None:
    """Wählbar sind nur „wie im Drehbuch“, 16:9, 9:16, 1:1 und die drei Qualitäten."""
    with pytest.raises(ValueError):
        rp.resolve(aspect, quality, "16:9")


def test_crf_per_quality() -> None:
    assert [rp.resolve(None, q, "16:9")["crf"] for q in rp.QUALITIES] == [28, 23, 20]
    assert list(rp.QUALITIES) == ["preview", "standard", "high"]
    assert rp.ASPECTS == ("screenplay", "16:9", "9:16", "1:1")


def _image_timeline(client, h, ws) -> None:
    b = ws / "studio/media/images"
    b.mkdir(parents=True, exist_ok=True)
    (b / "x.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\0" * 32)
    put_timeline(client, h, [clip("image", 0, 0, 2, "studio/media/images/x.png")])


@pytest.mark.parametrize("body", [{"aspect": "4:3"}, {"quality": "ultra"}, {"aspect": 1}, {"quality": None, "aspect": []}])
def test_bad_preset_400(client, auth_headers, ws, body) -> None:
    _image_timeline(client, auth_headers, ws)
    r = client.post(f"{R}/render", headers=auth_headers, json=body)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "studio_render_bad_preset"
    assert not client.get(f"{R}/plan/jobs", headers=auth_headers).json()["jobs"]   # kein Auftrag angelegt


def test_preset_reaches_ffmpeg(client, auth_headers, ws, monkeypatch) -> None:
    from backend import render
    seen: list[list[str]] = []

    def fake(cmd, seconds, progress):
        seen.append(cmd)
        raise render.RenderFailed()
    monkeypatch.setattr(render, "_run_ffmpeg", fake)
    _image_timeline(client, auth_headers, ws)
    assert client.post(f"{R}/render", headers=auth_headers, json={"aspect": "9:16", "quality": "preview"}).status_code == 202
    wait_render(client, auth_headers)
    cmd = seen[0]
    assert cmd[cmd.index("-crf") + 1] == "28"
    assert "scale=480:854:force_original_aspect_ratio=decrease,pad=480:854:" in cmd[cmd.index("-filter_complex") + 1]


@needs_ffmpeg
def test_real_film_portrait_from_landscape(client, auth_headers, ws) -> None:
    """Derselbe 16:9-Schnitt als 9:16 „Hoch“: 1080×1920, Bild eingepasst; Begleitdatei + Liste nennen die Vorlage."""
    client.put(f"{R}/plan/screenplay", headers=auth_headers, json={"aspect_ratio": "16:9"})
    v = make_video(ws, "a.mp4", 1.5, size="320x180")
    put_timeline(client, auth_headers, [clip("video", 0, 0, 1, v), clip("image", 1, 0, 0.5, make_image(ws, "b.png"))])
    assert client.post(f"{R}/render", headers=auth_headers, json={"aspect": "9:16", "quality": "high"}).status_code == 202
    job = wait_render(client, auth_headers)
    assert job["status"] == "done", job
    rel = job["result"]["rel"]
    st = next(x for x in probe(ws / rel)["streams"] if x["codec_type"] == "video")
    assert (st["width"], st["height"]) == (1080, 1920)
    meta = json.loads((ws / f"{rel}.json").read_text())
    assert (meta["aspect"], meta["quality"], meta["width"], meta["height"]) == ("9:16", "high", 1080, 1920)
    assert job["result"]["aspect"] == "9:16" and job["result"]["quality"] == "high"
    item = client.get(f"{R}/renders", headers=auth_headers).json()["renders"][0]
    assert (item["aspect"], item["quality"]) == ("9:16", "high")


def test_without_preset_like_before(client, auth_headers, ws, monkeypatch) -> None:
    """Ohne Angaben: Format des Drehbuchs, Standard (wie 4d); Begleitdatei nennt das tatsächliche Format."""
    from backend import render
    monkeypatch.setattr(render, "_run_ffmpeg", lambda cmd, seconds, progress: (cmd[-1] and open(cmd[-1], "wb").close()))
    client.put(f"{R}/plan/screenplay", headers=auth_headers, json={"aspect_ratio": "21:9"})
    _image_timeline(client, auth_headers, ws)
    assert client.post(f"{R}/render", headers=auth_headers, json={}).status_code == 202
    job = wait_render(client, auth_headers)
    assert job["status"] == "done", job
    meta = json.loads((ws / f"{job['result']['rel']}.json").read_text())
    assert (meta["aspect"], meta["quality"], meta["width"], meta["height"]) == ("21:9", "standard", 1680, 720)


def test_old_films_without_preset_listed(client, auth_headers, ws) -> None:
    d = ws / "studio/renders"
    d.mkdir(parents=True)
    name = f"{1:032x}.mp4"
    (d / name).write_bytes(b"x")
    (d / f"{name}.json").write_text(json.dumps({"created_at": "2026-10-18T10:00:00Z", "width": 1280, "height": 720}))
    item = client.get(f"{R}/renders", headers=auth_headers).json()["renders"][0]
    assert item["aspect"] is None and item["quality"] is None and item["width"] == 1280
