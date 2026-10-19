"""Nachrichten-Warteschlange (Dateien) zwischen HydraHive und Dienst."""
from __future__ import annotations

import json

import pytest

from renderer import inbox


def test_ablegen_und_lesen(tmp_path):
    m = inbox.post(tmp_path, "Hallo Till", kind="success", title="Hydra", seconds=20, source="test", now=1000.0)
    assert m["id"] and (tmp_path / "inbox").is_dir()
    vis = inbox.visible(tmp_path, now=1001.0)
    assert [(x["title"], x["text"], x["kind"]) for x in vis] == [("Hydra", "Hallo Till", "success")]
    assert not list((tmp_path / "inbox").glob("*.tmp"))


def test_abgelaufene_verschwinden_vom_video_bleiben_aber_24h(tmp_path):
    """S3: abgelaufen = weg vom Video, aber 24 h unter „Neu“ in der Statuszentrale (vorher sofort gelöscht)."""
    inbox.post(tmp_path, "kurz", seconds=5, now=1000.0)
    assert inbox.visible(tmp_path, now=1004.0)
    assert inbox.visible(tmp_path, now=1006.0) == []
    new, hist = inbox.recent(tmp_path, now=1006.0)
    assert [m["text"] for m in new] == ["kurz"] and hist == []
    assert len(list((tmp_path / "inbox").glob("*.json"))) == 1


def test_nach_24h_geloescht(tmp_path):
    inbox.post(tmp_path, "alt", seconds=5, now=1000.0)
    assert inbox.recent(tmp_path, now=1000.0 + inbox.KEEP_SECONDS - 1)[0]
    assert inbox.recent(tmp_path, now=1000.0 + inbox.KEEP_SECONDS + 1) == ([], [])
    assert list((tmp_path / "inbox").glob("*.json")) == []


def test_fehler_bleibt_ohne_dauer_zehn_minuten(tmp_path):
    inbox.post(tmp_path, "kaputt", kind="error", now=1000.0)
    assert inbox.visible(tmp_path, now=1000.0 + 599)
    assert not inbox.visible(tmp_path, now=1000.0 + 601)


def test_hoechstens_drei_sichtbar_neueste_zuerst(tmp_path):
    for i in range(5):
        inbox.post(tmp_path, f"n{i}", seconds=60, now=1000.0 + i)
    vis = inbox.visible(tmp_path, now=1010.0)
    assert [m["text"] for m in vis] == ["n4", "n3", "n2"]
    assert len(inbox.active(tmp_path, now=1010.0)) == 5, "die anderen warten, sind nicht weg"


def test_gleiche_nachricht_wird_zusammengefasst(tmp_path):
    inbox.post(tmp_path, "Backup fertig", kind="success", seconds=600, now=1000.0)
    inbox.post(tmp_path, "Backup fertig", kind="success", seconds=600, now=1010.0)
    inbox.post(tmp_path, "Backup fertig", kind="info", seconds=600, now=1011.0)
    act = inbox.active(tmp_path, now=1012.0)
    assert sorted((m["kind"], m["count"]) for m in act) == [("info", 1), ("success", 2)]
    inbox.post(tmp_path, "Backup fertig", kind="success", seconds=600, now=1100.0)
    assert len(inbox.active(tmp_path, now=1101.0)) == 3, "nach 60 s gilt es als neue Nachricht"


@pytest.mark.parametrize(("text", "erwartet"), [
    ("a\x00b\x1bc\nd", "abc d"),
    ("x" * 400, "x" * 279 + "…"),
    ("  leer  ", "leer"),
])
def test_text_wird_gesaeubert(tmp_path, text, erwartet):
    m = inbox.post(tmp_path, text, now=1.0)
    assert m["text"] == erwartet


@pytest.mark.parametrize(("args", "fehler"), [
    ({"text": ""}, "text"),
    ({"text": "x", "kind": "disco"}, "kind"),
    ({"text": "x", "seconds": 1}, "seconds"),
    ({"text": "x", "seconds": 9999}, "seconds"),
])
def test_ungueltig(tmp_path, args, fehler):
    with pytest.raises(inbox.InboxError, match=fehler):
        inbox.post(tmp_path, **args, now=1.0)


def test_kaputte_datei_wird_entfernt(tmp_path):
    inbox.post(tmp_path, "gut", now=1.0)
    (tmp_path / "inbox" / "0000-kaputt.json").write_text("{nein")
    assert [m["text"] for m in inbox.visible(tmp_path, now=2.0)] == ["gut"]
    assert not (tmp_path / "inbox" / "0000-kaputt.json").exists()


def test_ordner_begrenzt(tmp_path):
    for i in range(inbox.MAX_FILES + 10):
        inbox.post(tmp_path, f"n{i}", seconds=600, now=1000.0 + i)
    files = list((tmp_path / "inbox").iterdir())
    assert len(files) == inbox.MAX_FILES
    texte = {json.loads(f.read_text())["text"] for f in files}
    assert "n0" not in texte and f"n{inbox.MAX_FILES + 9}" in texte


def test_bestaetigen_entfernt(tmp_path):
    m = inbox.post(tmp_path, "weg damit", kind="error", now=1.0)
    assert inbox.dismiss(tmp_path, m["id"], now=2.0) is True
    assert inbox.active(tmp_path, now=2.0) == [] and inbox.recent(tmp_path, now=2.0) == ([], []), "Cockpit löscht ganz"
    assert inbox.dismiss(tmp_path, m["id"], now=2.0) is False
    assert inbox.dismiss(tmp_path, "../config", now=2.0) is False


def test_gelesen_geht_in_den_verlauf_und_vom_video(tmp_path):
    a = inbox.post(tmp_path, "erste", kind="error", now=1000.0)
    inbox.post(tmp_path, "zweite", now=1001.0)
    assert inbox.mark_read(tmp_path, a["id"], now=1002.0) is True
    assert [m["text"] for m in inbox.visible(tmp_path, now=1003.0)] == ["zweite"], "gelesen → sofort weg vom Video"
    new, hist = inbox.recent(tmp_path, now=1003.0)
    assert [m["text"] for m in new] == ["zweite"] and [m["text"] for m in hist] == ["erste"]
    assert hist[0]["read"] == 1002.0


def test_gelesen_unbekannt_oder_pfad(tmp_path):
    inbox.post(tmp_path, "x", now=1.0)
    assert inbox.mark_read(tmp_path, "0" * 12, now=2.0) is False
    assert inbox.mark_read(tmp_path, "../config", now=2.0) is False
    assert inbox.mark_read(tmp_path, "", now=2.0) is False, "leere ID darf nichts treffen"
    m = inbox.recent(tmp_path, now=2.0)[0][0]
    assert inbox.mark_read(tmp_path, m["id"][:6], now=2.0) is False, "nur die volle ID"
    assert inbox.recent(tmp_path, now=2.0)[1] == []


def test_gleiche_meldung_nach_dem_lesen_wieder_neu(tmp_path):
    m = inbox.post(tmp_path, "Backup kaputt", kind="error", now=1000.0)
    inbox.mark_read(tmp_path, m["id"], now=1010.0)
    again = inbox.post(tmp_path, "Backup kaputt", kind="error", now=1020.0)
    assert again["id"] == m["id"] and again["count"] == 2 and again["read"] is None
    new, hist = inbox.recent(tmp_path, now=1021.0)
    assert [x["id"] for x in new] == [m["id"]] and hist == []


def test_alte_datei_ohne_read_gilt_als_ungelesen(tmp_path):
    (tmp_path / "inbox").mkdir()
    (tmp_path / "inbox" / "0000001000.000000-abcdefabcdef.json").write_text(json.dumps(
        {"id": "abcdefabcdef", "text": "alt", "title": "", "kind": "info", "count": 1, "created": 1000.0,
         "expires": 1015.0, "source": ""}))
    new, hist = inbox.recent(tmp_path, now=1100.0)
    assert [m["id"] for m in new] == ["abcdefabcdef"] and hist == []


def test_recent_neueste_zuerst(tmp_path):
    for i in range(4):
        inbox.post(tmp_path, f"m{i}", now=1000.0 + i)
    assert [m["text"] for m in inbox.recent(tmp_path, now=1010.0)[0]] == ["m3", "m2", "m1", "m0"]
