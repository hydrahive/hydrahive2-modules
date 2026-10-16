"""JPEG zeilenweise – Gegenprüfung mit ffmpeg als unabhängigem Dekoder (nicht nur Pillow)."""
from __future__ import annotations

import pytest

from renderer import jpegrows as jr
from test_jpegrows import H, W, _img, _plain


def _ffmpeg_decode(path):
    import subprocess
    r = subprocess.run(["ffmpeg", "-v", "warning", "-i", str(path), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       capture_output=True, timeout=30)
    # „deprecated pixel format“ ist ein Hinweis von swscale zu yuvj420p, kein Dekodierfehler
    errs = [ln for ln in r.stderr.decode(errors="replace").splitlines() if "deprecated pixel format" not in ln]
    return r.returncode, errs, r.stdout


def test_zusammengesetztes_jpeg_dekodiert_auch_ffmpeg(tmp_path):
    """Unabhängiger Dekoder: ffmpeg liest das zusammengesetzte JPEG fehlerfrei und mit denselben Pixeln wie die
    volle Kodierung. (ffmpeg und Pillow rechnen die Farben verschieden hoch – deshalb ffmpeg gegen ffmpeg.)"""
    import shutil
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg fehlt")
    rows = jr.split(jr.encode(_img(1), 80))
    strip = jr.split(jr.encode(_img(77).crop((0, 5 * jr.MCU, W, 9 * jr.MCU)), 80))
    (tmp_path / "zus.jpg").write_bytes(jr.join(jr.replace(rows, 5, strip)))
    ref = _img(1)
    ref.paste(_img(77).crop((0, 5 * jr.MCU, W, 9 * jr.MCU)), (0, 5 * jr.MCU))
    (tmp_path / "voll.jpg").write_bytes(_plain(ref))
    rc, errs, pix = _ffmpeg_decode(tmp_path / "zus.jpg")
    assert rc == 0 and errs == [], errs[:3]
    _, _, ref_pix = _ffmpeg_decode(tmp_path / "voll.jpg")
    assert len(pix) == W * H * 3 and pix == ref_pix


def test_ffmpeg_pruefung_erkennt_kaputte_bilder(tmp_path):
    """Gegenprobe für den Test oben: ein beschädigtes JPEG muss ffmpeg als Fehler melden."""
    import shutil
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg fehlt")
    j = bytearray(jr.encode(_img(1), 80))
    mid = len(j) // 2
    j[mid:mid + 40] = b"\x12" * 40
    (tmp_path / "k.jpg").write_bytes(bytes(j))
    _, errs, _ = _ffmpeg_decode(tmp_path / "k.jpg")
    assert errs
