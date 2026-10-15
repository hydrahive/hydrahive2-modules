"""Overlay auf ein gespeichertes JPEG legen, ohne das ganze Bild neu zu kodieren."""
from __future__ import annotations

import io
import time

import pytest
from PIL import Image, ImageDraw

from renderer import cards, jpegrows as jr, scene, splice

W, H = 1080, 1920


def _video_frame(seed=0):
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(0, H, 4):
        d.rectangle([0, y, W, y + 3], fill=((y + seed) % 256, (2 * y + seed) % 256, (255 - y // 8) % 256))
    return img


def _overlay(alert=False, status="Hydra läuft  ·  Last 0.5"):
    return scene.Overlay(W, H).render(time.localtime(), status, None, alert)


def _check(jpeg, out, *overlays):
    """Erwartung, Zeile für Zeile:
    - Zeilen ohne Overlay: unverändert die gespeicherten Bytes (kein zweites Kodieren → keine Qualitätsverluste)
    - Zeilen mit Overlay: genau die Kodierung von „ganzes Bild dekodiert + Overlay aufgelegt“ an dieser Stelle
    """
    full = Image.open(io.BytesIO(jpeg)).convert("RGB")
    for ov in overlays:
        full = scene.compose(full, ov)
    want = jr.split(jr.encode(full, 80)).segments
    orig, got = jr.split(jpeg).segments, jr.split(out).segments
    touched = set()
    for ov in overlays:
        a = ov.getchannel("A")
        for r in range(len(orig)):
            if a.crop((0, r * jr.MCU, W, min(H, (r + 1) * jr.MCU))).getbbox():
                touched.add(r)
    assert touched, "Test braucht ein sichtbares Overlay"
    for r in range(len(orig)):
        if r in touched:
            assert got[r] == want[r], f"Zeile {r} mit Overlay weicht ab"
        elif got[r] != orig[r]:
            # Lücken zwischen Bändern (≤ 1 Zeile) werden mitkodiert – dort muss es die Kodierung der dekodierten Zeile sein
            assert got[r] == want[r], f"Zeile {r} ohne Overlay verändert und nicht korrekt"
    untouched_changed = [r for r in range(len(orig)) if r not in touched and got[r] != orig[r]]
    return touched, untouched_changed


def test_ohne_overlay_kommen_die_gespeicherten_bytes():
    j = jr.encode(_video_frame(), 80)
    assert splice.apply(j, [], 80) == j


def test_mit_overlay_byteidentisch_zur_vollen_kodierung():
    j = jr.encode(_video_frame(3), 80)
    ov = _overlay()
    touched, changed = _check(j, splice.apply(j, [ov], 80), ov)
    assert len(changed) <= 2, f"nur Lückenzeilen dürfen mitkodiert werden: {changed}"


def test_mit_karten_und_alarm():
    j = jr.encode(_video_frame(9), 80)
    ov = _overlay(alert=True, status="Hydra Fehler  ·  2 Fehler/h")
    msgs = [{"id": "a", "kind": "error", "text": "Fehler X", "title": "", "count": 1, "created": 100.0, "expires": 200.0},
            {"id": "b", "kind": "success", "text": "Backup fertig", "title": "", "count": 2, "created": 100.0, "expires": 200.0}]
    card = cards.Cards(W, H).render(msgs, now=150.0)
    _check(j, splice.apply(j, [ov, card], 80), ov, card)


def test_zeilen_ohne_overlay_bleiben_byteidentisch():
    j = jr.encode(_video_frame(5), 80)
    ov = _overlay()
    out = jr.split(splice.apply(j, [ov], 80)).segments
    orig = jr.split(j).segments
    groups = splice.row_groups(splice.bands_of(ov), H)
    inside = {r for a, b in groups for r in range(a, b)}
    assert all(out[r] == orig[r] for r in range(len(orig)) if r not in inside)


def test_ergebnis_dekodiert_wie_erwartet():
    """Pixelvergleich mit dem Weg ohne Cache (Original-Videobild + Overlay): nur JPEG-Rauschen, keine Fehler."""
    from PIL import ImageChops
    frame = _video_frame(7)
    ov = _overlay()
    got = Image.open(io.BytesIO(splice.apply(jr.encode(frame, 80), [ov], 80))).convert("RGB")
    ref = scene.compose(frame, ov)
    diff = ImageChops.difference(got, ref).convert("L")
    mean = sum(i * n for i, n in enumerate(diff.histogram())) / (W * H)
    assert mean < 3.0, f"mittlere Abweichung {mean:.2f}"


def test_nur_betroffene_zeilen_werden_neu_kodiert(monkeypatch):
    j = jr.encode(_video_frame(), 80)
    ov = _overlay()
    calls = []
    orig = jr.encode
    monkeypatch.setattr(jr, "encode", lambda img, q: calls.append(img.size) or orig(img, q))
    splice.apply(j, [ov], 80)
    rows = sum(h for _, h in calls) // jr.MCU
    assert 0 < rows < (H // jr.MCU) // 3, f"{rows} Zeilen neu kodiert"


def test_zeilengruppen_aus_baendern():
    assert splice.row_groups([(0, 158, W, 428), (0, 1800, W, 1881)], H) == [(9, 27), (112, 118)]
    assert splice.row_groups([(0, 0, W, 16)], H) == [(0, 1)]
    assert splice.row_groups([(0, 10, W, 40), (0, 30, W, 70)], H) == [(0, 5)], "überlappend → zusammengefasst"
    assert splice.row_groups([(0, 10, W, 20), (0, 48, W, 60)], H) == [(0, 4)], "genau 1 Zeile Lücke → zusammen"
    assert splice.row_groups([(0, 10, W, 20), (0, 64, W, 70)], H) == [(0, 2), (4, 5)], "2 Zeilen Lücke → getrennt"
    assert splice.row_groups([(0, 1900, W, 1999)], H) == [(118, 120)], "nie über das Bild hinaus"
    assert splice.row_groups([(0, 1910, W, 1920)], H) == [(119, 120)]
    assert splice.row_groups([], H) == []


def test_ohne_overlay_keine_arbeit(monkeypatch):
    j = jr.encode(_video_frame(), 80)
    monkeypatch.setattr(jr, "split", lambda *a: (_ for _ in ()).throw(AssertionError("split ohne Overlay")))
    assert splice.apply(j, [], 80) is j


def test_durchsichtiges_overlay_aendert_nichts():
    j = jr.encode(_video_frame(), 80)
    assert splice.apply(j, [Image.new("RGBA", (W, H), (0, 0, 0, 0))], 80) is j, "Original zurück, nicht neu zusammengesetzt"


def test_baender_werden_zwischengespeichert():
    ov = _overlay()
    a = splice.bands_of(ov)
    assert splice.bands_of(ov) is a


def test_falsche_groesse_abgelehnt():
    j = jr.encode(_video_frame(), 80)
    with pytest.raises(ValueError):
        splice.apply(j, [Image.new("RGBA", (100, 100))], 80)
