"""Einblendungs-Karten: Farbe je Art, Umbruch, Animation, Position über der Status-Leiste."""
from __future__ import annotations

import pytest
from PIL import Image

from renderer import cards

W, H = 1080, 1920


def _msg(kind="info", text="Backup fertig", title="", count=1, created=100.0):
    return {"id": "abc", "kind": kind, "text": text, "title": title, "count": count, "created": created, "expires": created + 15}


def _alpha_rows(img):
    a = img.getchannel("A")
    return [y for y in range(0, img.height, 4) if a.crop((0, y, img.width, y + 1)).getbbox()]


@pytest.mark.parametrize(("kind", "farbe"), [("info", cards.COLORS["info"]), ("success", cards.COLORS["success"]),
                                            ("warning", cards.COLORS["warning"]), ("error", cards.COLORS["error"])])
def test_farbbalken_je_art(kind, farbe):
    img = cards.Cards(W, H).render([_msg(kind)], now=105.0)
    rows = _alpha_rows(img)
    y = rows[len(rows) // 2]
    px = img.getpixel((int(48 * W / 1080) + 3, y))
    assert px[:3] == farbe[:3]


def test_karten_liegen_ueber_der_statusleiste_mitte_bleibt_frei():
    img = cards.Cards(W, H).render([_msg(), _msg(text="zweite"), _msg(text="dritte")], now=105.0)
    rows = _alpha_rows(img)
    assert rows and max(rows) < H - 130, "nicht über der Status-Leiste"
    assert min(rows) > H // 2, "obere Hälfte (Uhr, Video) bleibt frei"


def test_umbruch_hoechstens_drei_zeilen():
    c = cards.Cards(W, H)
    lines = c.wrap("Wort " * 200)
    assert len(lines) == 3 and lines[-1].endswith("…")
    assert all(c.font.getlength(line) <= c.text_width for line in lines)


def test_zaehler_und_titel():
    c = cards.Cards(W, H)
    assert c.headline(_msg(title="Hydra", count=3)) == "Hydra  ×3"
    assert c.headline(_msg(kind="error", title="")) == "Fehler"
    assert c.headline(_msg(kind="info", title="", count=2)) == "Info  ×2"


def test_einblenden_animiert():
    c = cards.Cards(W, H)
    m = _msg(created=100.0)
    fast = c.render([m], now=100.05)
    voll = c.render([m], now=101.0)
    a_fast = fast.getchannel("A").getextrema()[1]
    a_voll = voll.getchannel("A").getextrema()[1]
    assert a_fast < a_voll, "am Anfang noch durchsichtiger"


def test_ausblenden_vor_ablauf():
    c = cards.Cards(W, H)
    m = _msg(created=100.0)
    assert c.render([m], now=114.9).getchannel("A").getextrema()[1] < c.render([m], now=110.0).getchannel("A").getextrema()[1]


def test_leer_ist_durchsichtig():
    img = cards.Cards(W, H).render([], now=1.0)
    assert img.size == (W, H) and img.getbbox() is None


def test_status_leiste_rot_bei_fehler():
    from renderer import scene
    o = scene.Overlay(W, H)
    import time
    t = time.localtime()
    normal = o.render(t, "Hydra läuft")
    fehler = scene.Overlay(W, H).render(t, "Hydra Fehler", alert=True)
    y = H - 60
    assert normal.getpixel((60, y)) != fehler.getpixel((60, y))
    assert fehler.getpixel((60, y))[0] > fehler.getpixel((60, y))[2], "rötlich"


@pytest.mark.parametrize("status", [
    "Hydra läuft  ·  Last 0.5  ·  RAM 6%  ·  GPU 53°C  ·  1 Fehler/h",
    "Hydra läuft  ·  Last 0.5  ·  RAM 6%  ·  GPU 53°C  ·  12 Agenten aktiv  ·  14 Fehler/h",
    "x" * 300,
])
@pytest.mark.parametrize(("w", "h"), [(1080, 1920), (480, 854)])
def test_status_text_bleibt_in_der_leiste(status, w, h):
    from renderer import scene
    import time
    o = scene.Overlay(w, h)
    img = o.render(time.localtime(), status, alert=True)
    m = int(40 * w / 1080)
    band = img.crop((0, h - int(120 * w / 1080), w, h - m))
    a = band.getchannel("A")
    assert a.crop((0, 0, m, band.height)).getbbox() is None, "links über den Rand"
    assert a.crop((w - m + 1, 0, w, band.height)).getbbox() is None, "rechts über den Rand (Leiste endet bei w-m inklusive)"
    font, text = o.fit_status(status)
    assert font.getlength(text) <= w - 2 * m - 2 * int(24 * w / 1080)
    assert font.size >= int(26 * w / 1080), "nicht unlesbar klein"


def test_kurzer_status_bleibt_unveraendert():
    from renderer import scene
    o = scene.Overlay(W, H)
    font, text = o.fit_status("Hydra läuft  ·  Last 0.5")
    assert text == "Hydra läuft  ·  Last 0.5" and font.size == int(38 * W / 1080)
