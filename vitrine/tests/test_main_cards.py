"""Dienst + Einblendungen: Karten im Bild, Hydra-Status aus hydra.json in der Leiste."""
from __future__ import annotations

import datetime as dt
import json
import time

from renderer import hydra_state, inbox, main
from renderer.program import Program
from test_main import FakeDisplay
from test_main_program import Uhr, _runner


def test_karten_werden_ins_bild_gelegt(tmp_path, monkeypatch):
    from renderer import cards
    seen = []
    orig = cards.Cards.render

    def spy(self, msgs, now, hint=False):
        seen.append([m["text"] for m in msgs])
        return orig(self, msgs, now, hint=hint)

    monkeypatch.setattr(cards.Cards, "render", spy)
    inbox.post(tmp_path, "Hallo Vitrine", seconds=60)
    r = _runner(tmp_path, [Program(video=None)], Uhr(dt.datetime(2026, 10, 15, 12)), [], [])
    r.inbox_every = 0
    r.run(max_frames=2)
    assert ["Hallo Vitrine"] in seen


def test_ohne_nachrichten_keine_kartenarbeit(tmp_path, monkeypatch):
    from renderer import cards
    calls = []
    monkeypatch.setattr(cards.Cards, "render", lambda self, m, now, hint=False: calls.append(1))
    r = _runner(tmp_path, [Program(video=None)], Uhr(dt.datetime(2026, 10, 15, 12)), [], [])
    r.inbox_every = 0
    r.run(max_frames=3)
    assert calls == [], "keine Nachricht → nichts zeichnen (spart CPU)"


def test_hydra_status_aus_datei(tmp_path):
    now = time.time()
    (tmp_path / "hydra.json").write_text(json.dumps({"agents": 2, "errors_last_hour": 0, "updated": now}))
    assert hydra_state.extra(tmp_path, now=now) == ("2 Agenten aktiv", False)
    (tmp_path / "hydra.json").write_text(json.dumps({"agents": 1, "errors_last_hour": 3, "updated": now}))
    assert hydra_state.extra(tmp_path, now=now) == ("1 Agent aktiv  ·  3 Fehler/h", True)
    (tmp_path / "hydra.json").write_text(json.dumps({"agents": 0, "errors_last_hour": 0, "updated": now}))
    assert hydra_state.extra(tmp_path, now=now) == ("", False)


def test_hydra_status_veraltet_oder_fehlt(tmp_path):
    assert hydra_state.extra(tmp_path, now=1.0) == ("", False)
    (tmp_path / "hydra.json").write_text(json.dumps({"agents": 5, "errors_last_hour": 9, "updated": 100.0}))
    assert hydra_state.extra(tmp_path, now=100.0 + hydra_state.STALE + 1) == ("", False)
    (tmp_path / "hydra.json").write_text("{kaputt")
    assert hydra_state.extra(tmp_path, now=1.0) == ("", False)


def test_leiste_zeigt_agenten_und_wird_rot(tmp_path, monkeypatch):
    from renderer import scene
    seen = []
    orig = scene.Overlay.render

    def spy(self, t, status, holiday=None, alert=False):
        seen.append((status, alert))
        return orig(self, t, status, holiday, alert)

    monkeypatch.setattr(scene.Overlay, "render", spy)
    (tmp_path / "hydra.json").write_text(json.dumps({"agents": 1, "errors_last_hour": 2, "updated": time.time()}))
    r = main.Runner(data_dir=tmp_path, connect=lambda: FakeDisplay(), frames=lambda *a: iter([__import__("PIL.Image").Image.new("RGB", (1080, 1920))] * 10),
                    status=lambda: "Hydra läuft", sleep=lambda s: None, fps=24,
                    program=lambda now: Program(video=None), now=lambda: dt.datetime(2026, 10, 15, 12), check_every=99)
    r.run(max_frames=2)
    assert seen[0] == ("Hydra läuft  ·  1 Agent aktiv  ·  2 Fehler/h", True)


def test_hinweis_nur_wenn_dashboard_bereit(tmp_path, monkeypatch):
    """S3: zweite Zeile „Maus bewegen für Details“ nur, wenn die Statuszentrale bereit ist (state.dashboard)."""
    from renderer import cards
    from test_main_dashboard import FakeDash, SentDisplay
    from test_main_dashboard import _runner as dash_runner
    hints = []
    orig = cards.Cards.render

    def spy(self, msgs, now, hint=False):
        hints.append(hint)
        return orig(self, msgs, now, hint=hint)
    monkeypatch.setattr(cards.Cards, "render", spy)
    inbox.post(tmp_path, "Hallo", seconds=60)
    long_idle = 10 ** 9                                   # Maus lange nicht bewegt → Video bleibt, Dashboard „bereit“
    for dash, erwartet in ((FakeDash([long_idle]), True), (FakeDash([long_idle], fail_after=-1), False), (None, False)):
        hints.clear()
        r = dash_runner(tmp_path, dash, SentDisplay())
        r.inbox_every = 0
        r.run(max_frames=3)
        assert hints and set(hints) == {erwartet}, (r.state.get("dashboard"), hints)
