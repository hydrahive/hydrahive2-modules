"""Overlay: Uhr/Datum oben, Status unten, deutsch, Zwischenspeicher."""
from __future__ import annotations

import time

from PIL import Image

from renderer import scene

DO_15_OKT = time.struct_time((2026, 10, 15, 20, 7, 33, 3, 288, 1))


def test_datum_deutsch():
    assert scene.date_text(DO_15_OKT) == "Donnerstag, 15. Oktober"
    so = time.struct_time((2026, 3, 1, 9, 0, 0, 6, 60, 0))
    assert scene.date_text(so) == "Sonntag, 1. März"


def test_uhr_ohne_sekunden():
    assert scene.clock_text(DO_15_OKT) == "20:07"


def _alpha_rows(img: Image.Image) -> list[int]:
    a = img.getchannel("A")
    w, h = a.size
    return [y for y in range(0, h, 8) if a.crop((0, y, w, y + 1)).getbbox()]


def test_overlay_groesse_und_bereiche():
    o = scene.Overlay(1080, 1920)
    img = o.render(DO_15_OKT, "Hydra läuft · Last 0.4 · RAM 12%")
    assert img.size == (1080, 1920) and img.mode == "RGBA"
    rows = _alpha_rows(img)
    oben = [y for y in rows if y < 600]
    unten = [y for y in rows if y > 1700]
    mitte = [y for y in rows if 700 < y < 1650]
    assert oben and unten, "Uhr oben und Status-Leiste unten müssen gezeichnet sein"
    assert not mitte, "die Mitte bleibt frei für das Video und die Figuren"


def test_zwischenspeicher_bei_gleichem_text():
    o = scene.Overlay(1080, 1920)
    a = o.render(DO_15_OKT, "x")
    b = o.render(time.struct_time((2026, 10, 15, 20, 7, 59, 3, 288, 1)), "x")   # andere Sekunde, gleiche Minute
    c = o.render(DO_15_OKT, "y")
    assert a is b
    assert c is not a


def test_ohne_status_keine_leiste():
    o = scene.Overlay(1080, 1920)
    img = o.render(DO_15_OKT, "")
    assert not [y for y in _alpha_rows(img) if y > 1700]


def test_compose_legt_overlay_auf_video():
    o = scene.Overlay(1080, 1920)
    ov = o.render(DO_15_OKT, "Status")
    frame = Image.new("RGB", (1080, 1920), (0, 120, 0))
    out = scene.compose(frame, ov)
    assert out.mode == "RGB" and out.size == (1080, 1920)
    assert out.getpixel((540, 1000)) == (0, 120, 0)             # Mitte unverändert
    assert out.getpixel((540, 1000)) != out.getpixel((540, 230))  # oben liegt die Uhr drüber


def test_compose_identisch_zum_vollen_alpha_composite():
    """Die schnelle Variante (nur Bereiche mit Overlay) muss pixelgleich zur vollen Verrechnung sein."""
    from PIL import Image
    o = scene.Overlay(1080, 1920)
    ov = o.render(DO_15_OKT, "Hydra läuft  ·  Last 0.4")
    frame = Image.effect_noise((1080, 1920), 50).convert("RGB")
    voll = Image.alpha_composite(frame.convert("RGBA"), ov).convert("RGB")
    assert scene.compose(frame, ov).tobytes() == voll.tobytes()


def test_compose_veraendert_das_videobild_nicht():
    from PIL import Image
    o = scene.Overlay(1080, 1920)
    frame = Image.new("RGB", (1080, 1920), (1, 2, 3))
    scene.compose(frame, o.render(DO_15_OKT, "x"))
    assert frame.getpixel((540, 200)) == (1, 2, 3)
