"""Bildcache: Video einmal in JPEG-Bilder (Restart je Zeile) umrechnen, atomar ablegen, schnell lesen."""
from __future__ import annotations

import json
import os
import time

import pytest
from PIL import Image

from renderer import framecache as fc
from renderer import jpegrows as jr

W, H = 64, 48


def _frames(n=5):
    return [Image.new("RGB", (W, H), (i * 40 % 256, 80, 200 - i * 30)) for i in range(n)]


@pytest.fixture
def src(tmp_path):
    p = tmp_path / "videos" / "herbst.mp4"
    p.parent.mkdir()
    p.write_bytes(b"VIDEO")
    return p


def _build(src, tmp_path, n=5, **kw):
    return fc.build(src, tmp_path / "cache", W, H, 24, 80, frames=lambda: iter(_frames(n)), **kw)


def test_bauen_und_lesen(src, tmp_path):
    d = _build(src, tmp_path)
    c = fc.open_cache(src, tmp_path / "cache", W, H, 24, 80)
    assert c is not None and c.path == d and len(c) == 5
    for i, img in enumerate(_frames()):
        assert c[i] == jr.encode(img, 80)
        jr.split(c[i])                                   # zeilenweise bearbeitbar
    c.close()


def test_schleife(src, tmp_path):
    _build(src, tmp_path, n=3)
    c = fc.open_cache(src, tmp_path / "cache", W, H, 24, 80)
    it = c.loop()
    assert [next(it) for _ in range(7)] == [c[0], c[1], c[2], c[0], c[1], c[2], c[0]]


@pytest.mark.parametrize("change", [
    {"w": 32}, {"fps": 12}, {"quality": 70},
])
def test_schluessel_haengt_an_parametern(src, tmp_path, change):
    _build(src, tmp_path)
    args = {"w": W, "h": H, "fps": 24, "quality": 80, **change}
    assert fc.open_cache(src, tmp_path / "cache", args["w"], args["h"], args["fps"], args["quality"]) is None


def test_quelle_geaendert_ist_neuer_schluessel(src, tmp_path):
    _build(src, tmp_path)
    src.write_bytes(b"ANDERES VIDEO")
    os.utime(src, (time.time() + 5, time.time() + 5))
    assert fc.open_cache(src, tmp_path / "cache", W, H, 24, 80) is None


def test_alte_fassungen_derselben_quelle_werden_geloescht(src, tmp_path):
    old = _build(src, tmp_path)
    other = tmp_path / "videos" / "winter.mp4"
    other.write_bytes(b"W")
    keep = fc.build(other, tmp_path / "cache", W, H, 24, 80, frames=lambda: iter(_frames(2)))
    new = fc.build(src, tmp_path / "cache", W, H, 12, 80, frames=lambda: iter(_frames(2)))
    assert not old.exists() and new.exists() and keep.exists()


def test_halber_cache_wird_nicht_benutzt(src, tmp_path):
    def broken():
        yield from _frames(2)
        raise RuntimeError("ffmpeg weg")
    with pytest.raises(RuntimeError):
        fc.build(src, tmp_path / "cache", W, H, 24, 80, frames=broken)
    assert fc.open_cache(src, tmp_path / "cache", W, H, 24, 80) is None
    assert not list((tmp_path / "cache").glob("*.tmp*")), "Reste aufgeräumt"


@pytest.mark.parametrize("damage", ["index_kaputt", "index_fehlt", "daten_kuerzer", "anzahl_falsch", "offsets_falsch",
                                    "daten_laenger", "offsets_rueckwaerts", "version_alt", "fps_im_index_falsch"])
def test_beschaedigter_cache_wird_verworfen(src, tmp_path, damage):
    d = _build(src, tmp_path)
    idx = json.loads((d / "index.json").read_text())
    if damage == "index_kaputt":
        (d / "index.json").write_text("{kaputt")
    elif damage == "index_fehlt":
        (d / "index.json").unlink()
    elif damage == "daten_kuerzer":
        b = (d / "frames.bin").read_bytes()
        (d / "frames.bin").write_bytes(b[:-10])
    elif damage == "anzahl_falsch":
        idx["count"] = 99
        (d / "index.json").write_text(json.dumps(idx))
    elif damage == "offsets_falsch":
        idx["offsets"][1] += 3
        (d / "index.json").write_text(json.dumps(idx))
    elif damage == "daten_laenger":
        with open(d / "frames.bin", "ab") as fh:
            fh.write(b"MUELL")
    elif damage == "offsets_rueckwaerts":
        idx["offsets"][2], idx["offsets"][3] = idx["offsets"][3], idx["offsets"][2]
        (d / "index.json").write_text(json.dumps(idx))
    elif damage == "version_alt":
        idx["version"] = 0
        (d / "index.json").write_text(json.dumps(idx))
    elif damage == "fps_im_index_falsch":
        idx["fps"] = 30
        (d / "index.json").write_text(json.dumps(idx))
    assert fc.open_cache(src, tmp_path / "cache", W, H, 24, 80) is None


def test_leeres_video_ergibt_keinen_cache(src, tmp_path):
    with pytest.raises(fc.CacheError):
        fc.build(src, tmp_path / "cache", W, H, 24, 80, frames=lambda: iter([]))
    assert fc.open_cache(src, tmp_path / "cache", W, H, 24, 80) is None


def test_falsche_bildgroesse_abgelehnt(src, tmp_path):
    with pytest.raises(fc.CacheError):
        fc.build(src, tmp_path / "cache", W, H, 24, 80, frames=lambda: iter([Image.new("RGB", (10, 10))]))


def test_fortschritt_wird_gemeldet(src, tmp_path):
    seen = []
    _build(src, tmp_path, n=4, progress=seen.append)
    assert seen == [1, 2, 3, 4]


def test_abbrechen(src, tmp_path):
    stop = {"n": 0}

    def cancel():
        stop["n"] += 1
        return stop["n"] > 2
    with pytest.raises(fc.Cancelled):
        _build(src, tmp_path, n=10, cancelled=cancel)
    assert fc.open_cache(src, tmp_path / "cache", W, H, 24, 80) is None
    assert not list((tmp_path / "cache").glob("*.tmp*"))
