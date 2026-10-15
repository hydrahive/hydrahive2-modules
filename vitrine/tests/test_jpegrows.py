"""JPEG zeilenweise: zerlegen, Zeilen tauschen, zusammensetzen – byteidentisch zur vollen Kodierung."""
from __future__ import annotations

import io

import pytest
from PIL import Image, ImageDraw

from renderer import jpegrows as jr

W, H = 320, 240


def _img(seed=0, w=W, h=H):
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        d.line([(0, y), (w, y)], fill=((y * 3 + seed) % 256, (y + 2 * seed) % 256, (255 - y + seed) % 256))
    for x in range(0, w, 17):
        d.line([(x, 0), (x, h)], fill=(255, 255, 255))
    return img


def _plain(img, q=80):
    b = io.BytesIO()
    img.save(b, "JPEG", quality=q, subsampling=2, restart_marker_rows=1)
    return b.getvalue()


def test_zerlegen_und_zusammensetzen_ist_identisch():
    j = jr.encode(_img(), 80)
    rows = jr.split(j)
    assert len(rows.segments) == H // jr.MCU
    assert jr.join(rows) == j


def test_encode_entspricht_pillow_mit_restart():
    assert jr.encode(_img(3), 80) == _plain(_img(3))


@pytest.mark.parametrize(("r0", "r1"), [(0, 2), (5, 9), (13, 15), (0, 15)])
def test_zeilen_tauschen_byteidentisch(r0, r1):
    base, other = _img(1), _img(77)
    rows = jr.split(jr.encode(base, 80))
    y0, y1 = r0 * jr.MCU, r1 * jr.MCU
    strip = jr.split(jr.encode(other.crop((0, y0, W, y1)), 80))
    out = jr.join(jr.replace(rows, r0, strip))
    ref = base.copy()
    ref.paste(other.crop((0, y0, W, y1)), (0, y0))
    assert out == _plain(ref)


@pytest.mark.parametrize(("r0", "r1"), [(4, 7), (0, 3), (12, 15), (0, 15), (7, 8)])
def test_streifen_dekodieren_liefert_genau_diese_zeilen(r0, r1):
    """Gleiche Pixel wie das ganze Bild dekodiert – auch am Streifenrand (Farb-Hochrechnung braucht die Nachbarzeile)."""
    img = _img(5)
    rows = jr.split(jr.encode(img, 80))
    strip = jr.decode_rows(rows, r0, r1)
    assert strip.size == (W, (r1 - r0) * jr.MCU) and strip.mode == "RGB"
    full = Image.open(io.BytesIO(jr.join(rows))).convert("RGB")
    assert strip.tobytes() == full.crop((0, r0 * jr.MCU, W, r1 * jr.MCU)).tobytes()


def test_rst_nummern_zyklisch():
    rows = jr.split(jr.encode(_img(), 80))
    out = jr.join(rows)
    found = [out[i + 1] for i in range(len(out) - 1) if out[i] == 0xFF and 0xD0 <= out[i + 1] <= 0xD7]
    assert found == [0xD0 + (k % 8) for k in range(len(rows.segments) - 1)]


def test_hoehe_kein_vielfaches_von_16():
    img = _img(2, w=200, h=100)                         # 6 volle Zeilen + 4 px Rest
    j = jr.encode(img, 80)
    rows = jr.split(j)
    assert len(rows.segments) == 7 and rows.height == 100
    assert jr.join(rows) == j


def test_fuellbytes_und_marker_im_datenstrom():
    # sehr viel Kontrast → im Entropiecode kommen FF 00 vor; split darf sie nicht als Marker lesen
    img = Image.effect_noise((W, H), 120).convert("RGB")
    j = jr.encode(img, 95)
    assert b"\xff\x00" in j
    rows = jr.split(j)
    assert len(rows.segments) == H // jr.MCU and jr.join(rows) == j


@pytest.mark.parametrize("bad", [
    b"",
    b"kein jpeg",
    b"\xff\xd8\xff\xd9",
])
def test_kaputte_daten(bad):
    with pytest.raises(jr.RowsError):
        jr.split(bad)


def _save(**kw):
    b = io.BytesIO()
    _img().save(b, "JPEG", quality=80, **kw)
    return b.getvalue()


def _rst(j, nth):
    """Position des n-ten Restart-Markers im Bild."""
    pos = -1
    for _ in range(nth + 1):
        pos = next(i for i in range(pos + 1, len(j) - 1) if j[i] == 0xFF and 0xD0 <= j[i + 1] <= 0xD7)
    return pos


@pytest.mark.parametrize(("name", "make", "msg"), [
    ("ohne Restart", lambda: _save(subsampling=2), "Restart"),
    ("Restart alle 4 Blöcke", lambda: _save(subsampling=2, restart_marker_blocks=4), "Restart"),
    ("4:4:4", lambda: _save(subsampling=0, restart_marker_rows=1), "4:2:0"),
    ("progressiv", lambda: _save(subsampling=2, restart_marker_rows=1, progressive=True), "Baseline"),
    ("Ende fehlt", lambda: jr.encode(_img(), 80)[:-2], "Ende"),
    ("abgeschnitten", lambda: (lambda j: j[: len(j) // 2] + b"\xff\xd9")(jr.encode(_img(), 80)), "Zeilen"),
    ("Restart-Nummer falsch", lambda: (lambda j, i: j[:i + 1] + b"\xd3" + j[i + 2:])(jr.encode(_img(), 80), _rst(jr.encode(_img(), 80), 0)), "Marker"),
    ("Kopf abgeschnitten", lambda: jr.encode(_img(), 80)[:40], "Kopf"),
    ("Kopf abgeschnitten im Segment", lambda: jr.encode(_img(), 80)[:12], "Kopf"),
])
def test_fremde_oder_kaputte_jpegs_abgelehnt(name, make, msg):
    with pytest.raises(jr.RowsError, match=msg):
        jr.split(make())


def test_decode_rows_ausserhalb():
    rows = jr.split(jr.encode(_img(), 80))
    with pytest.raises(jr.RowsError):
        jr.decode_rows(rows, 3, 3)
    with pytest.raises(jr.RowsError):
        jr.decode_rows(rows, 0, len(rows.segments) + 1)


def test_streifen_mit_halber_zeile_nur_am_ende():
    rows = jr.split(jr.encode(_img(), 80))
    half = jr.split(jr.encode(_img().crop((0, 0, W, jr.MCU + 8)), 80))   # 2 Segmente, aber nur 24 px hoch
    with pytest.raises(jr.RowsError, match="volle Zeilen"):
        jr.replace(rows, 3, half)


def test_streifen_passt_nicht():
    rows = jr.split(jr.encode(_img(), 80))
    strip = jr.split(jr.encode(_img().crop((0, 0, W, 2 * jr.MCU)), 80))
    with pytest.raises(jr.RowsError):
        jr.replace(rows, len(rows.segments) - 1, strip)        # ragt über das Bild hinaus
    other = jr.split(jr.encode(_img(w=160).crop((0, 0, 160, 2 * jr.MCU)), 80))
    with pytest.raises(jr.RowsError, match="passt nicht"):
        jr.replace(rows, 0, other)                              # andere Breite
    q50 = jr.split(jr.encode(_img().crop((0, 0, W, 2 * jr.MCU)), 50))
    with pytest.raises(jr.RowsError, match="passt nicht"):
        jr.replace(rows, 0, q50)                                # andere Qualität = andere Tabellen


def test_letzter_streifen_mit_resthoehe():
    """Bildhöhe 100 = 6 volle Zeilen + 4 px: Streifen der letzten Zeile ist nur 4 px hoch."""
    img = _img(2, w=200, h=100)
    rows = jr.split(jr.encode(img, 80))
    last = Image.open(io.BytesIO(jr.strip_jpeg(rows, 6, 7)))
    assert last.size == (200, 4)
    assert jr.decode_rows(rows, 5, 7).size == (200, 20)


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
