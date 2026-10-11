"""Song-Format v1 und Speicherung (SPEC.md §4, §5.1)."""
from __future__ import annotations

import json

import pytest

from conftest import PROJECT_ID


def _songs():
    from backend import songs
    return songs


# ── Modell ─────────────────────────────────────────────────────────────────────

def test_clip_und_spurfelder_heissen_wie_im_videoeditor():
    """E3: Media-Studio soll Spuren 1:1 übernehmen können – gleiche Feldnamen wie videoeditor AudioClip/AudioTrack."""
    from backend.song_model import Clip, Track
    for f in ("id", "source_rel", "t_start", "src_start", "src_end", "gain_db", "fade_in", "fade_out"):
        assert f in Clip.model_fields
    for f in ("id", "name", "mute", "solo", "gain_db", "clips"):
        assert f in Track.model_fields
    assert {"pan", "role"} <= set(Track.model_fields)


def test_neuer_song_hat_format_und_version_eins():
    s = _songs().create(PROJECT_ID, {"title": "Die Klans V"})
    assert s["format"] == "hydrahive.song" and s["format_version"] == 1
    assert s["version"] == 1 and s["title"] == "Die Klans V"
    assert s["tracks"] == [] and s["sections"] == []
    assert s["lyrics"] == {"ref": None} and s["score"] == {"ref": None}


def test_unbekannte_formatversion_wird_abgelehnt(ws):
    s = _songs().create(PROJECT_ID, {"title": "x"})
    path = ws / "tonstudio" / "songs" / s["id"] / "song.json"
    data = json.loads(path.read_text())
    data["format_version"] = 99
    path.write_text(json.dumps(data))
    with pytest.raises(_songs().SongFormatError):
        _songs().get(PROJECT_ID, s["id"])


def test_clip_ende_vor_anfang_ist_ungueltig():
    from pydantic import ValidationError

    from backend.song_model import Clip
    with pytest.raises(ValidationError):
        Clip(id="c1", source_rel="tonstudio/clips/a.mp3", t_start=0, src_start=5, src_end=4)


def test_pan_nur_zwischen_minus_eins_und_eins():
    from pydantic import ValidationError

    from backend.song_model import Track
    with pytest.raises(ValidationError):
        Track(id="t1", pan=1.5)


# ── Speichern, Versionen, 409 ──────────────────────────────────────────────────

def test_speichern_erhoeht_version_und_legt_schnappschuss_an(ws):
    S = _songs()
    s = S.create(PROJECT_ID, {"title": "a"})
    s2 = S.save(PROJECT_ID, s["id"], {**s, "bpm": 132}, expected_version=1)
    assert s2["version"] == 2 and s2["bpm"] == 132
    snaps = sorted((ws / "tonstudio" / "songs" / s["id"] / "versions").iterdir())
    assert [p.name for p in snaps] == ["1.json"]
    assert json.loads(snaps[0].read_text())["bpm"] is None


def test_veraltete_version_gibt_konflikt():
    S = _songs()
    s = S.create(PROJECT_ID, {"title": "a"})
    S.save(PROJECT_ID, s["id"], {**s, "bpm": 100}, expected_version=1)
    with pytest.raises(S.VersionConflict):
        S.save(PROJECT_ID, s["id"], {**s, "bpm": 120}, expected_version=1)
    assert S.get(PROJECT_ID, s["id"])["bpm"] == 100


def test_speichern_ohne_aenderung_erzeugt_keine_neue_version():
    S = _songs()
    s = S.create(PROJECT_ID, {"title": "a"})
    again = S.save(PROJECT_ID, s["id"], s, expected_version=1)
    assert again["version"] == 1


def test_id_und_format_lassen_sich_nicht_ueberschreiben():
    S = _songs()
    s = S.create(PROJECT_ID, {"title": "a"})
    s2 = S.save(PROJECT_ID, s["id"], {**s, "id": "anders", "format": "x", "title": "b"}, expected_version=1)
    assert s2["id"] == s["id"] and s2["format"] == "hydrahive.song" and s2["title"] == "b"


# ── Liste, Papierkorb ──────────────────────────────────────────────────────────

def test_liste_neueste_zuerst_ohne_papierkorb():
    S = _songs()
    a = S.create(PROJECT_ID, {"title": "a"})
    b = S.create(PROJECT_ID, {"title": "b"})
    S.trash(PROJECT_ID, a["id"])
    ids = [x["id"] for x in S.list_songs(PROJECT_ID)]
    assert ids == [b["id"]]
    assert [x["id"] for x in S.list_trash(PROJECT_ID)] == [a["id"]]


def test_wiederherstellen_aus_dem_papierkorb():
    S = _songs()
    a = S.create(PROJECT_ID, {"title": "a"})
    S.trash(PROJECT_ID, a["id"])
    S.restore(PROJECT_ID, a["id"])
    assert [x["id"] for x in S.list_songs(PROJECT_ID)] == [a["id"]]
    assert S.list_trash(PROJECT_ID) == []


def test_unbekannte_oder_boese_id_gibt_none():
    S = _songs()
    assert S.get(PROJECT_ID, "0" * 32) is None
    assert S.get(PROJECT_ID, "../../etc") is None
    assert S.trash(PROJECT_ID, "../x") is False


def test_videoeditor_spur_laesst_sich_eins_zu_eins_lesen():
    """Akzeptanz §11: Eine Spur im Video-Editor-Format wird ohne Umbau als Tonstudio-Spur gelesen und zurück."""
    from backend.song_model import Track
    ve_track = {"id": "a1", "name": "Musik", "mute": False, "solo": True, "gain_db": -3.0,
                "clips": [{"id": "c1", "source_rel": "generated/x.mp3", "t_start": 2.0, "src_start": 0.5,
                           "src_end": 30.0, "gain_db": 1.5, "fade_in": 0.2, "fade_out": 1.0}]}
    t = Track.model_validate(ve_track).model_dump()
    for k, v in ve_track.items():
        if k != "clips":
            assert t[k] == v
    assert {k: t["clips"][0][k] for k in ve_track["clips"][0]} == ve_track["clips"][0]
    assert t["pan"] == 0.0 and t["role"] == "full"          # neue Felder mit neutralem Standard
