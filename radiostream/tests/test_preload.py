"""Vorgeladenen Titel verwerfen, wenn sich Warteschlange oder Programm ändern (PLAN-PROGRAMM.md „Als Nächstes“).

Liquidsoap lädt einen Titel vor (prefetch=1). Ändert sich das Programm, schickt das Modul `autodj.flush`: Liquidsoap
wirft den vorgeladenen weg und nennt dessen Spiel-Kennung (rs_play). Das Modul nimmt den Eintrag in der Gespielt-Liste
zurück (Sperren) und stellt eine Playlist-Stelle bzw. einen Warteschlangen-Eintrag wieder her.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
from backend import choose, preload, program, rotation


def _track(tid, artist=None):
    from hydrahive.db.connection import db
    with db() as conn:
        conn.execute("INSERT INTO module_radiostream_tracks (track_id, source_id, rel_path, size, mtime, artist, title, "
                     "genre, format, duration_s, state, first_seen, last_seen) VALUES (?, 'main', ?, 1, 1, ?, 'T', "
                     "'Pop', 'mp3', 200, 'ok', 'x', 'x')", (tid, f"{tid}/{tid}.mp3", artist or tid))
        conn.commit()


@pytest.fixture
def sock(monkeypatch):
    sent: list[str] = []
    answer = {"text": ""}

    def send(cmd):
        sent.append(cmd)
        return answer["text"]
    monkeypatch.setattr(preload, "_send", send)
    monkeypatch.setattr(preload, "_running", lambda: True)
    return sent, answer


def _pick_and_record():
    t = choose.next_track()
    pid = rotation.record(t["track_id"], t["artist"], source=t["source"], ref=t.get("ref", ""))
    return t, pid


def test_flush_nimmt_gespielt_eintrag_zurueck(db_ready, sock):
    _track("a")
    t, pid = _pick_and_record()
    sock[1]["text"] = f"{pid}\r\nEND"
    preload.flush()
    assert sock[0] == ["autodj.flush"]
    assert rotation.recent(limit=5) == []


@pytest.mark.parametrize("front,want", [(True, ["b", "a"]), (False, ["a", "b"])])
def test_aenderung_erst_nach_dem_zuruecknehmen(db_ready, sock, front, want):
    """„Als Nächstes: b“, während a schon vorgeladen ist → b, dann a. „Ans Ende: b“ → a, dann b."""
    _track("a")
    _track("b")
    program.enqueue("a", user="boss")
    t, pid = _pick_and_record()
    assert t["track_id"] == "a" and program.queue() == []
    sock[1]["text"] = f"{pid}\r\nEND"
    with preload.changing():
        program.enqueue("b", user="boss", front=front)
    assert [q["track_id"] for q in program.queue()] == want


def test_zurueckgenommener_kommt_vor_die_uebrigen(db_ready, sock):
    for t in ("a", "c"):
        _track(t)
    program.enqueue("a", user="boss")
    program.enqueue("c", user="boss")
    t, pid = _pick_and_record()
    assert t["track_id"] == "a"
    sock[1]["text"] = f"{pid}\r\nEND"
    preload.flush()
    assert [q["track_id"] for q in program.queue()] == ["a", "c"]


def test_sender_wartet_bis_die_aenderung_steht(db_ready, sock):
    """Liquidsoap fragt direkt nach dem Verwerfen neu (/feed/next). Das muss warten, bis die Änderung gespeichert ist."""
    import threading
    _track("a")
    _track("b")
    got: list[str] = []
    with preload.changing():
        th = threading.Thread(target=lambda: got.append(preload.locked_next()["track_id"]))
        th.start()
        th.join(0.3)
        assert th.is_alive()                                             # wartet noch
        program.enqueue("b", user="boss")
    th.join(2)
    assert got == ["b"]


def test_flush_stellt_playlist_stelle_wieder_her(db_ready, sock):
    for t in ("p1", "p2"):
        _track(t)
    pl = program.create_playlist("A", user="boss")
    program.add_items(pl["id"], ["p1", "p2"])
    program.set_program("playlist", pl["id"], user="boss")
    _pick_and_record()
    t, pid = _pick_and_record()                                          # p2 vorgeladen
    assert t["track_id"] == "p2"
    sock[1]["text"] = f"{pid}\r\nEND"
    preload.flush()
    assert choose.next_track()["track_id"] == "p2"


def test_flush_gemischte_playlist_titel_wieder_offen(db_ready, sock):
    for t in ("s1", "s2"):
        _track(t)
    pl = program.create_playlist("A", user="boss")
    program.add_items(pl["id"], ["s1", "s2"])
    program.update_playlist(pl["id"], order_mode="shuffle")
    program.set_program("playlist", pl["id"], user="boss")
    t, pid = _pick_and_record()
    sock[1]["text"] = f"{pid}\r\nEND"
    preload.flush()
    assert program.get_program()["played"] == []


def test_flush_nach_programmwechsel_laesst_neues_programm_in_ruhe(db_ready, sock):
    """Der vorgeladene kam aus Playlist A; inzwischen läuft Playlist B – B beginnt vorn, nichts wird verstellt."""
    for t in ("a1", "a2", "b1"):
        _track(t)
    a = program.create_playlist("A", user="boss")
    program.add_items(a["id"], ["a1", "a2"])
    b = program.create_playlist("B", user="boss")
    program.add_items(b["id"], ["b1"])
    program.set_program("playlist", a["id"], user="boss")
    _pick_and_record()
    t, pid = _pick_and_record()
    program.set_program("playlist", b["id"], user="boss")
    sock[1]["text"] = f"{pid}\r\nEND"
    preload.flush()
    assert program.get_program()["cursor"] == 0 and choose.next_track()["track_id"] == "b1"


@pytest.mark.parametrize("answer", ["", "END", "\r\nEND", "abc\r\nEND", "999999\r\nEND", "1;DROP\r\nEND"])
def test_flush_ohne_oder_mit_unbrauchbarer_antwort(db_ready, sock, answer):
    _track("a")
    _pick_and_record()
    sock[1]["text"] = answer
    preload.flush()
    assert len(rotation.recent(limit=5)) == 1


def test_flush_wenn_sender_aus_nichts_senden(db_ready, monkeypatch):
    monkeypatch.setattr(preload, "_running", lambda: False)
    monkeypatch.setattr(preload, "_send", lambda cmd: pytest.fail("nicht senden"))
    preload.flush()


def test_flush_sender_antwortet_nicht(db_ready, monkeypatch):
    monkeypatch.setattr(preload, "_running", lambda: True)

    def boom(cmd):
        raise OSError("weg")
    monkeypatch.setattr(preload, "_send", boom)
    preload.flush()                                                      # kein Fehler nach außen


def test_gespielt_liste_merkt_herkunft(db_ready):
    _track("a")
    pid = rotation.record("a", "a", source="playlist", ref="pl1:4", at=datetime(2026, 10, 31, tzinfo=UTC))
    r = rotation.recent(limit=1)[0]
    assert r["play_id"] == pid
    assert rotation.play_origin(pid) == {"track_id": "a", "source": "playlist", "ref": "pl1:4"}
