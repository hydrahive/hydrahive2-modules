"""Studio 7a: eigenes Material hochladen (Spec „Bauplan Etappe 7“) – Bibliothek und Referenzbilder für Bausteine."""
from __future__ import annotations

import io
import json
import struct
import zlib

from _render_helpers import make_audio, make_video, needs_ffmpeg
from _timeline_helpers import _code
from conftest import MOD_PREFIX, PROJECT_ID

U = f"{MOD_PREFIX}/projects/{PROJECT_ID}/uploads"
P = f"{MOD_PREFIX}/projects/{PROJECT_ID}/plan"
L = f"{MOD_PREFIX}/projects/{PROJECT_ID}/library"


def png(w: int = 4, h: int = 3) -> bytes:
    raw = b"".join(b"\x00" + b"\xff\x00\x00" * w for _ in range(h))
    def chunk(t: bytes, d: bytes) -> bytes:
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


JPG = b"\xff\xd8\xff\xe0" + b"\0" * 200 + b"\xff\xd9"


def _files(*items: tuple[str, bytes]) -> list:
    return [("files", (name, io.BytesIO(data), "application/octet-stream")) for name, data in items]


def test_upload_images_into_the_library(client, auth_headers, ws) -> None:
    r = client.post(U, headers=auth_headers, files=_files(("Ole am Steg.png", png()), ("foto.JPG", JPG)))
    assert r.status_code == 200, r.text
    out = r.json()["files"]
    assert [(x["name"], x["kind"], x["ok"]) for x in out] == [("Ole am Steg.png", "image", True), ("foto.JPG", "image", True)]
    rel = out[0]["rel"]
    assert rel.startswith("studio/media/uploads/") and rel.endswith(".png") and "Ole" not in rel   # Name nie als Pfad
    assert (ws / rel).read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    meta = json.loads((ws / f"{rel}.json").read_text())
    assert meta["name"] == "Ole am Steg.png" and meta["kind"] == "image" and meta["size"] > 0
    lib = [i for i in client.get(L, headers=auth_headers).json()["items"] if i["source"] == "studio_upload"]
    assert {i["rel"] for i in lib} == {x["rel"] for x in out}
    mine = next(i for i in lib if i["rel"] == rel)
    assert mine["kind"] == "image" and mine["origin"] == "upload" and mine["name"] == "Ole am Steg"


@needs_ffmpeg
def test_upload_video_and_sound_with_length(client, auth_headers, ws, tmp_path) -> None:
    v = (ws / make_video(ws, "clip.mp4", 2)).read_bytes()
    a = (ws / make_audio(ws, "ton.wav", 1.5)).read_bytes()
    out = client.post(U, headers=auth_headers, files=_files(("Film.mp4", v), ("Stimme.wav", a))).json()["files"]
    assert [(x["kind"], x["ok"]) for x in out] == [("video", True), ("audio", True)]
    assert abs(out[0]["duration"] - 2) < 0.2 and abs(out[1]["duration"] - 1.5) < 0.2
    lib = {i["rel"]: i for i in client.get(L, headers=auth_headers).json()["items"]}
    assert abs(lib[out[0]["rel"]]["duration"] - 2) < 0.2 and lib[out[1]["rel"]]["kind"] == "audio"


@needs_ffmpeg
def test_wrong_content_is_refused_per_file(client, auth_headers, ws) -> None:
    out = client.post(U, headers=auth_headers, files=_files(
        ("ok.png", png()), ("kein-bild.png", b"<html>kaputt</html>"), ("kein-film.mp4", b"\0" * 500),
        ("leer.png", b""), ("programm.exe", b"MZ\0\0"), ("../../etc/passwd.png", png()))).json()["files"]
    assert [(x["ok"], x.get("error")) for x in out] == [(True, None), (False, "studio_upload_invalid"), (False, "studio_upload_invalid"),
                                                       (False, "studio_upload_empty"), (False, "studio_upload_invalid"), (True, None)]
    assert out[5]["rel"].startswith("studio/media/uploads/") and out[5]["name"] == "passwd.png"
    d = ws / "studio/media/uploads"
    assert len([p for p in d.iterdir() if p.suffix != ".json"]) == 2                   # nur die guten liegen da


def test_size_limits(client, auth_headers, ws, monkeypatch) -> None:
    monkeypatch.setattr("backend.uploads.LIMITS", {"image": 1000, "video": 10, "audio": 10})
    out = client.post(U, headers=auth_headers, files=_files(("gross.png", png() + b"\0" * 2000))).json()["files"]
    assert (out[0]["ok"], out[0]["error"]) == (False, "studio_upload_too_large")
    assert not (ws / "studio/media/uploads").exists() or not [p for p in (ws / "studio/media/uploads").iterdir() if p.suffix != ".json"]


def test_too_many_files_or_none(client, auth_headers, ws) -> None:
    many = _files(*[(f"{i}.png", png()) for i in range(21)])
    assert _code(client.post(U, headers=auth_headers, files=many)) == "400 studio_upload_too_many"
    assert client.post(U, headers=auth_headers).status_code in (400, 422)


def test_reference_image_for_an_element(client, auth_headers, ws) -> None:
    ole = client.post(f"{P}/elements", headers=auth_headers, json={"kind": "character", "name": "Ole"}).json()
    R = f"{P}/elements/{ole['id']}/references"
    r = client.post(R, headers=auth_headers, files=_files(("ole-gesicht.png", png())))
    assert r.status_code == 200, r.text
    el = r.json()
    assert len(el["references"]) == 1 and el["references"][0].startswith("studio/media/uploads/")
    got = next(e for e in client.get(P, headers=auth_headers).json()["elements"] if e["id"] == ole["id"])
    assert got["references"] == el["references"]
    lib = [i for i in client.get(L, headers=auth_headers).json()["items"] if i["rel"] == el["references"][0]]
    assert lib and lib[0]["source"] == "studio_upload"                                  # auch in der Bibliothek
    for _ in range(7):
        client.post(R, headers=auth_headers, files=_files(("x.png", png())))
    assert _code(client.post(R, headers=auth_headers, files=_files(("x.png", png())))) == "400 studio_references_full"
    assert len(next(e for e in client.get(P, headers=auth_headers).json()["elements"] if e["id"] == ole["id"])["references"]) == 8


def test_reference_rules(client, auth_headers, ws) -> None:
    ole = client.post(f"{P}/elements", headers=auth_headers, json={"kind": "character", "name": "Ole"}).json()
    R = f"{P}/elements/{ole['id']}/references"
    assert _code(client.post(R, headers=auth_headers, files=_files(("kaputt.png", b"<html>")))) == "400 studio_upload_invalid"
    assert _code(client.post(R, headers=auth_headers, files=_files(("film.mp4", b"\0" * 10)))) == "400 studio_upload_invalid"
    assert _code(client.post(f"{P}/elements/{'f' * 32}/references", headers=auth_headers, files=_files(("a.png", png())))) == "404 studio_not_found"
    assert not (ws / "studio/media/uploads").exists() or not [p for p in (ws / "studio/media/uploads").iterdir() if p.suffix != ".json"]


def test_uploaded_references_go_to_the_image_ai(client, auth_headers, ws) -> None:
    from backend import generate
    ole = client.post(f"{P}/elements", headers=auth_headers, json={"kind": "character", "name": "Ole"}).json()
    rel = client.post(f"{P}/elements/{ole['id']}/references", headers=auth_headers, files=_files(("ole.png", png()))).json()["references"][0]
    sc = client.post(f"{P}/scenes", headers=auth_headers, json={"title": "Hafen", "element_ids": [ole["id"]]}).json()
    s = client.post(f"{P}/scenes/{sc['id']}/shots", headers=auth_headers, json={"prompt": "x", "element_ids": [ole["id"]]}).json()
    urls = generate.reference_urls(PROJECT_ID, s)
    assert len(urls) == 1 and urls[0].startswith("data:image/png;base64,")
    assert rel


def test_only_members(client, other_headers, auth_headers) -> None:
    assert client.post(U, headers=other_headers, files=_files(("a.png", png()))).status_code == 404
    ole = client.post(f"{P}/elements", headers=auth_headers, json={"kind": "character", "name": "Ole"}).json()
    assert client.post(f"{P}/elements/{ole['id']}/references", headers=other_headers, files=_files(("a.png", png()))).status_code == 404
