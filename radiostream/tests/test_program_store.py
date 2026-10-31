"""Programm (PLAN-PROGRAMM.md): Playlisten, Mixe, Warteschlange, gewähltes Programm, „Ausgeschlossen von Alles“."""
from __future__ import annotations

import pytest
from backend import program, rules
from backend.program import ProgramError


def _track(tid, artist="A", state="ok", genre="Pop", rel=None):
    from hydrahive.db.connection import db
    with db() as conn:
        conn.execute("INSERT INTO module_radiostream_tracks (track_id, source_id, rel_path, size, mtime, artist, title, "
                     "genre, format, state, first_seen, last_seen) VALUES (?, 'main', ?, 1, 1, ?, ?, ?, 'mp3', ?, 'x', 'x')",
                     (tid, rel or f"{artist}/{tid}.mp3", artist, f"Titel {tid}", genre, state))
        conn.commit()


# --- Playlisten --------------------------------------------------------------------------------------------------------

def test_playlist_anlegen_und_lesen(db_ready):
    pl = program.create_playlist("Party", user="boss")
    assert pl["name"] == "Party" and pl["order_mode"] == "ordered" and pl["at_end"] == "repeat" and pl["count"] == 0
    assert [p["id"] for p in program.playlists()] == [pl["id"]]


@pytest.mark.parametrize("name", ["", "   ", "x" * 81])
def test_playlist_name_pruefen(db_ready, name):
    with pytest.raises(ProgramError, match="^radiostream_name_invalid$"):
        program.create_playlist(name, user="boss")


def test_playlist_aendern(db_ready):
    pl = program.create_playlist("A", user="boss")
    out = program.update_playlist(pl["id"], name="B", order_mode="shuffle", at_end="back")
    assert (out["name"], out["order_mode"], out["at_end"]) == ("B", "shuffle", "back")


@pytest.mark.parametrize("kw", [{"order_mode": "zufall"}, {"at_end": "stop"}])
def test_playlist_aendern_ungueltig(db_ready, kw):
    pl = program.create_playlist("A", user="boss")
    with pytest.raises(ProgramError, match="^radiostream_playlist_invalid$"):
        program.update_playlist(pl["id"], **kw)


def test_unbekannte_playlist(db_ready):
    with pytest.raises(ProgramError, match="^radiostream_playlist_not_found$"):
        program.update_playlist("gibt-es-nicht", name="x")


def test_titel_hinzufuegen_reihenfolge_und_doppelt(db_ready):
    for t in ("t1", "t2", "t3"):
        _track(t)
    pl = program.create_playlist("A", user="boss")
    program.add_items(pl["id"], ["t1", "t2"])
    program.add_items(pl["id"], ["t3", "t1"])                       # doppelt erlaubt (Lieblingstitel zweimal)
    assert [i["track_id"] for i in program.items(pl["id"])] == ["t1", "t2", "t3", "t1"]
    assert program.playlists()[0]["count"] == 4


def test_unbekannte_titel_werden_nicht_aufgenommen(db_ready):
    _track("t1")
    pl = program.create_playlist("A", user="boss")
    added = program.add_items(pl["id"], ["t1", "gibt-es-nicht"])
    assert added == 1 and [i["track_id"] for i in program.items(pl["id"])] == ["t1"]


def test_hoechstens_500_auf_einmal_und_2000_insgesamt(db_ready):
    pl = program.create_playlist("A", user="boss")
    with pytest.raises(ProgramError, match="^radiostream_too_many$"):
        program.add_items(pl["id"], [f"t{i}" for i in range(501)])
    assert program.MAX_ITEMS == 2000


def test_umsortieren_und_entfernen(db_ready):
    for t in ("t1", "t2", "t3"):
        _track(t)
    pl = program.create_playlist("A", user="boss")
    program.add_items(pl["id"], ["t1", "t2", "t3"])
    program.move_item(pl["id"], 2, 0)                                # t3 nach vorn
    assert [i["track_id"] for i in program.items(pl["id"])] == ["t3", "t1", "t2"]
    program.remove_item(pl["id"], 1)
    assert [(i["pos"], i["track_id"]) for i in program.items(pl["id"])] == [(0, "t3"), (1, "t2")]


@pytest.mark.parametrize("args", [(5, 0), (0, 5), (-1, 0)])
def test_umsortieren_ungueltig(db_ready, args):
    _track("t1")
    pl = program.create_playlist("A", user="boss")
    program.add_items(pl["id"], ["t1"])
    with pytest.raises(ProgramError, match="^radiostream_playlist_invalid$"):
        program.move_item(pl["id"], *args)


def test_fehlende_titel_grau(db_ready):
    _track("t1")
    _track("t2", state="missing")
    pl = program.create_playlist("A", user="boss")
    program.add_items(pl["id"], ["t1", "t2"])
    assert [(i["track_id"], i["available"]) for i in program.items(pl["id"])] == [("t1", True), ("t2", False)]
    assert program.items(pl["id"])[0]["title"] == "Titel t1"


def test_playlist_loeschen_raeumt_eintraege_und_programm(db_ready):
    _track("t1")
    pl = program.create_playlist("A", user="boss")
    program.add_items(pl["id"], ["t1"])
    program.set_program("playlist", pl["id"], user="boss")
    program.delete_playlist(pl["id"])
    assert program.playlists() == [] and program.items(pl["id"]) == []
    assert program.get_program()["mode"] == "all"


# --- Mixe --------------------------------------------------------------------------------------------------------------

def test_mix_anlegen_regel_bereinigt(db_ready):
    m = program.save_mix(None, name="Rock", rules_={"genres": [" Rock "]}, allow_long=False, user="boss")
    assert m["rules"] == {"genres": ["Rock"]} and m["allow_long"] is False
    assert program.mixes()[0]["name"] == "Rock"


def test_mix_aendern(db_ready):
    m = program.save_mix(None, name="Rock", rules_={"genres": ["Rock"]}, allow_long=False, user="boss")
    m2 = program.save_mix(m["id"], name="Rock 80er", rules_={"genres": ["Rock"], "decades": [1980]}, allow_long=True,
                          user="boss")
    assert m2["id"] == m["id"] and m2["rules"]["decades"] == [1980] and m2["allow_long"] is True
    assert len(program.mixes()) == 1


def test_mix_ungueltige_regel(db_ready):
    with pytest.raises(ProgramError, match="^radiostream_rule_invalid$"):
        program.save_mix(None, name="x", rules_={"genres": "Rock"}, allow_long=False, user="boss")


def test_mix_loeschen_setzt_programm_zurueck(db_ready):
    m = program.save_mix(None, name="Rock", rules_={}, allow_long=False, user="boss")
    program.set_program("mix", m["id"], user="boss")
    program.delete_mix(m["id"])
    assert program.mixes() == [] and program.get_program()["mode"] == "all"


def test_mix_vorschau(db_ready):
    _track("r1", genre="Rock")
    _track("r2", genre="Pop;Rock")
    _track("p1", genre="Pop")
    out = program.preview({"genres": ["Rock"]}, allow_long=False)
    assert out["count"] == 2 and {e["track_id"] for e in out["examples"]} == {"r1", "r2"}
    assert len(program.preview({}, allow_long=False)["examples"]) <= 5


# --- Programm wählen ---------------------------------------------------------------------------------------------------

def test_programm_voreinstellung_alles(db_ready):
    assert program.get_program()["mode"] == "all"


def test_programm_waehlen_setzt_stelle_zurueck(db_ready):
    pl = program.create_playlist("A", user="boss")
    program.set_program("playlist", pl["id"], user="boss")
    from hydrahive.db.connection import db
    with db() as conn:
        conn.execute("UPDATE module_radiostream_program SET cursor = 5, played = '[1,2]' WHERE id = 1")
        conn.commit()
    program.set_program("playlist", pl["id"], user="boss")
    p = program.get_program()
    assert (p["mode"], p["ref_id"], p["cursor"], p["played"]) == ("playlist", pl["id"], 0, [])


@pytest.mark.parametrize("mode,ref", [("playlist", "gibt-es-nicht"), ("mix", "gibt-es-nicht"), ("zufall", "")])
def test_programm_ungueltig(db_ready, mode, ref):
    with pytest.raises(ProgramError):
        program.set_program(mode, ref, user="boss")


# --- Warteschlange -----------------------------------------------------------------------------------------------------

def test_warteschlange_als_naechstes_und_ans_ende(db_ready):
    for t in ("t1", "t2", "t3"):
        _track(t)
    program.enqueue("t1", user="boss")
    program.enqueue("t2", user="boss")
    program.enqueue("t3", user="boss", front=True)
    assert [q["track_id"] for q in program.queue()] == ["t3", "t1", "t2"]


def test_warteschlange_entfernen_umsortieren(db_ready):
    for t in ("t1", "t2", "t3"):
        _track(t)
    for t in ("t1", "t2", "t3"):
        program.enqueue(t, user="boss")
    q = program.queue()
    program.move_queue(q[2]["id"], 0)
    assert [x["track_id"] for x in program.queue()] == ["t3", "t1", "t2"]
    program.dequeue(q[0]["id"])
    assert [x["track_id"] for x in program.queue()] == ["t3", "t2"]


def test_warteschlange_unbekannter_titel(db_ready):
    with pytest.raises(ProgramError, match="^radiostream_track_not_found$"):
        program.enqueue("gibt-es-nicht", user="boss")


def test_warteschlange_hoechstens_100(db_ready):
    _track("t1")
    for _ in range(program.MAX_QUEUE):
        program.enqueue("t1", user="boss")
    with pytest.raises(ProgramError, match="^radiostream_too_many$"):
        program.enqueue("t1", user="boss")


# --- Ausgeschlossen von Alles ------------------------------------------------------------------------------------------

def test_ausschluss_voreinstellung(db_ready):
    ex = program.get_exclude()
    assert ex["rules"] == rules.DEFAULT_EXCLUDE and ex["allow_long"] is False


def test_ausschluss_speichern(db_ready):
    program.save_exclude({"genres": ["Comedy"], "genre_parts": [], "folders": ["Bibi Blocksberg"]}, allow_long=True,
                         user="boss")
    ex = program.get_exclude()
    assert ex["rules"] == {"genres": ["Comedy"], "genre_parts": [], "folders": ["Bibi Blocksberg"]}
    assert ex["allow_long"] is True


@pytest.mark.parametrize("bad", [{"genres": "x"}, {"genres": [], "unbekannt": []}, {"folders": ["a/b"]}])
def test_ausschluss_ungueltig(db_ready, bad):
    with pytest.raises(ProgramError, match="^radiostream_rule_invalid$"):
        program.save_exclude(bad, allow_long=False, user="boss")


def test_ordner_vorschlaege(db_ready):
    for i in range(25):
        _track(f"b{i}", artist="Bibi", genre="Kids; Audiobooks", rel=f"Bibi Blocksberg/{i}.mp3")
    for i in range(25):
        _track(f"d{i}", artist="Drei", genre="Speech" if i < 10 else "", rel=f"Die drei/{i}.mp3")
    for i in range(25):
        _track(f"q{i}", artist="Queen", genre="Rock", rel=f"Queen/{i}.mp3")
    for i in range(5):
        _track(f"k{i}", artist="Klein", genre="Hörspiel", rel=f"Klein/{i}.mp3")
    sug = program.folder_suggestions()
    assert [s["folder"] for s in sug] == ["Bibi Blocksberg", "Die drei"]
    assert sug[0]["count"] == 25 and sug[1]["share"] == 40
