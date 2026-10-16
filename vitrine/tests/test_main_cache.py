"""Dienst mit Bildcache: ohne Cache bisheriger Weg, mit Cache gespeicherte JPEGs (+ eingesetztes Overlay)."""
from __future__ import annotations

import datetime as dt
import json

from PIL import Image

from renderer import jpegrows as jr, main
from renderer.program import Program


class FakeDisplay:
    width, height, fps = 1080, 1920, 60

    def __init__(self):
        self.sent, self.closed = [], False

    def send_jpeg(self, jpeg):
        assert jpeg[:2] == b"\xff\xd8"
        self.sent.append(bytes(jpeg))

    def close(self):
        self.closed = True


class FakeCache:
    def __init__(self, jpegs):
        self.jpegs, self.closed = jpegs, False

    def __len__(self):
        return len(self.jpegs)

    def loop(self):
        while True:
            yield from self.jpegs

    def close(self):
        self.closed = True


class FakeWarmer:
    def __init__(self, cache=None, ready_after=None):
        self.cache, self.ready_after, self.calls = cache, ready_after, 0

    def get(self, src, w, h, fps, quality):
        self.calls += 1
        if self.ready_after is not None and self.calls <= self.ready_after:
            return None
        return self.cache

    def status(self):
        return {"state": "ready" if self.cache else "building", "video": "herbst.mp4", "done": 3, "error": None}


def _jpegs(n=3, w=1080, h=1920):
    return [jr.encode(Image.new("RGB", (w, h), (40 * i, 90, 30)), 80) for i in range(n)]


def _runner(tmp_path, warmer, *, status="", decoded=None, **kw):
    video = tmp_path / "videos" / "herbst.mp4"
    video.parent.mkdir(exist_ok=True)
    video.write_bytes(b"V")
    disp = FakeDisplay()

    def frames(src, w, h, fps):
        while True:
            if decoded is not None:
                decoded.append(src)
            yield Image.new("RGB", (w, h), (1, 2, 3))

    r = main.Runner(data_dir=tmp_path, connect=lambda: disp, frames=frames, status=lambda: status,
                    sleep=lambda s: None, fps=24, program=lambda now: Program(video=video),
                    now=lambda: dt.datetime(2026, 10, 15, 12), check_every=0, warmer=warmer, **kw)
    r.inbox_every = 0
    return r, disp


def test_mit_cache_werden_gespeicherte_bilder_gesendet(tmp_path, monkeypatch):
    from renderer import scene
    monkeypatch.setattr(scene.Overlay, "render", lambda self, *a, **k: Image.new("RGBA", (1080, 1920), (0, 0, 0, 0)))
    jp = _jpegs()
    decoded = []
    r, disp = _runner(tmp_path, FakeWarmer(FakeCache(jp)), decoded=decoded)
    r.run(max_frames=4)
    assert disp.sent == [jp[0], jp[1], jp[2], jp[0]], "ohne sichtbares Overlay unverändert"
    assert decoded == [], "nichts dekodiert"


def test_mit_cache_und_overlay_wird_eingesetzt(tmp_path):
    jp = _jpegs()
    r, disp = _runner(tmp_path, FakeWarmer(FakeCache(jp)), status="Hydra läuft")
    r.run(max_frames=2)
    assert disp.sent[0] != jp[0]
    rows_sent, rows_cache = jr.split(disp.sent[0]).segments, jr.split(jp[0]).segments
    same = sum(a == b for a, b in zip(rows_sent, rows_cache))
    assert 0 < same < len(rows_cache), "nur Overlay-Zeilen ersetzt"


def test_ohne_cache_bisheriger_weg(tmp_path):
    decoded = []
    r, disp = _runner(tmp_path, FakeWarmer(None), decoded=decoded, status="ok")
    r.run(max_frames=3)
    assert len(disp.sent) == 3 and decoded
    st = json.loads((tmp_path / "state.json").read_text())
    assert st["cache"]["state"] == "building"


def test_wechsel_auf_cache_sobald_fertig(tmp_path, monkeypatch):
    from renderer import scene
    monkeypatch.setattr(scene.Overlay, "render", lambda self, *a, **k: Image.new("RGBA", (1080, 1920), (0, 0, 0, 0)))
    jp = _jpegs()
    decoded = []
    w = FakeWarmer(FakeCache(jp), ready_after=1)
    r, disp = _runner(tmp_path, w, decoded=decoded)
    r.cache_check_every = 0
    r.run(max_frames=6)
    assert decoded, "erst bisheriger Weg"
    assert disp.sent[-1] in jp, "dann aus dem Cache"


def test_cache_wird_beim_wechsel_geschlossen(tmp_path, monkeypatch):
    cache = FakeCache(_jpegs())
    video_a = tmp_path / "videos" / "a.mp4"
    video_b = tmp_path / "videos" / "b.mp4"
    video_a.parent.mkdir()
    video_a.write_bytes(b"A")
    video_b.write_bytes(b"B")
    progs = iter([Program(video=video_a)] * 3 + [Program(video=video_b)] * 100)
    disp = FakeDisplay()
    r = main.Runner(data_dir=tmp_path, connect=lambda: disp, frames=lambda *a: iter([]), status=lambda: "",
                    sleep=lambda s: None, fps=24, program=lambda now: next(progs),
                    now=lambda: dt.datetime(2026, 10, 15, 12), check_every=0, warmer=FakeWarmer(cache))
    r.run(max_frames=5)
    assert cache.closed


def test_kaputtes_cache_bild_faellt_auf_bisherigen_weg_zurueck(tmp_path):
    decoded = []
    r, disp = _runner(tmp_path, FakeWarmer(FakeCache([b"\xff\xd8kaputt\xff\xd9"])), decoded=decoded, status="ok")
    r.run(max_frames=3)
    assert len(disp.sent) == 3 and decoded, "Dienst läuft weiter"
    st = json.loads((tmp_path / "state.json").read_text())
    assert "Bildcache" in (st.get("error") or "")


def test_bisheriger_weg_legt_overlay_auf(tmp_path):
    """Ohne Cache muss die Uhr/Leiste trotzdem im Bild sein (Pixel unten in der Leiste ≠ Videobild)."""
    import io
    r, disp = _runner(tmp_path, FakeWarmer(None), status="Hydra läuft")
    r.run(max_frames=1)
    img = Image.open(io.BytesIO(disp.sent[0])).convert("RGB")
    assert img.getpixel((540, 1920 - 60)) != img.getpixel((540, 960)), "Status-Leiste fehlt"


def test_cache_wird_nicht_bei_jedem_bild_gefragt(tmp_path):
    w = FakeWarmer(None)
    r, disp = _runner(tmp_path, w, status="ok")
    r.cache_check_every = 3600
    r.run(max_frames=10)
    assert w.calls == 1, "einmal beim Start, danach erst nach cache_check_every"


def test_vorschau_aus_dem_cache_bild(tmp_path, monkeypatch):
    """Cache-Weg: preview.jpg entsteht aus dem gesendeten JPEG, verkleinert dekodiert (draft) – nicht in voller Größe."""
    from renderer import frames as fr
    sizes = []
    orig = Image.Image.resize
    monkeypatch.setattr(Image.Image, "resize", lambda self, size, *a, **k: sizes.append(self.size) or orig(self, size, *a, **k))
    r, disp = _runner(tmp_path, FakeWarmer(FakeCache(_jpegs())), status="ok")
    r.preview_every = 0
    r.run(max_frames=1)
    assert (tmp_path / "preview.jpg").exists()
    assert Image.open(tmp_path / "preview.jpg").size == fr.PREVIEW_SIZE
    assert sizes and max(sizes)[0] <= fr.PREVIEW_SIZE[0] * 2, f"voll dekodiert: {sizes}"
