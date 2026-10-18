"""Studio 6a: Untertitel als eigene Daten (studio/subtitles/<sprache>.json), Prüfregeln, Konflikt, nur Mitglieder."""
from __future__ import annotations

import json

from _subtitle_helpers import S, cue, put
from _timeline_helpers import _code


def test_empty_until_saved_and_nothing_created(client, auth_headers, ws) -> None:
    r = client.get(f"{S}/de", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == {"language": "de", "source": "", "revision": 0, "cues": []}
    assert not (ws / "studio/subtitles").exists()


def test_save_and_load_sorted(client, auth_headers, ws) -> None:
    r = put(client, auth_headers, [cue(2, 3, 4.5, "Zwei"), cue(1, 0.5, 2, "  Eins  ")])
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["revision"] == 1 and out["source"] == "manual"
    assert [(c["start"], c["end"], c["text"]) for c in out["cues"]] == [(0.5, 2, "Eins"), (3, 4.5, "Zwei")]
    assert client.get(f"{S}/de", headers=auth_headers).json()["cues"] == out["cues"]
    saved = json.loads((ws / "studio/subtitles/de.json").read_text())
    assert saved["revision"] == 1 and len(saved["cues"]) == 2 and saved["language"] == "de"


def test_missing_ids_get_new_ones(client, auth_headers, ws) -> None:
    out = put(client, auth_headers, [{"start": 0, "end": 1, "text": "a"}, {"id": "kaputt", "start": 1, "end": 2, "text": "b"}]).json()
    ids = [c["id"] for c in out["cues"]]
    assert all(len(i) == 32 for i in ids) and ids[0] != ids[1]


def test_rules(client, auth_headers, ws) -> None:
    bad = [
        [cue(1, 0, 2), cue(2, 1.5, 3)],                      # überlappt
        [cue(1, 0, 0.3)],                                    # kürzer als 0,5 s
        [cue(1, 2, 1)],                                      # Ende vor Anfang
        [cue(1, -1, 1)],
        [{"id": "1" * 32, "start": "0", "end": 1, "text": "x"}],
        [{"id": "1" * 32, "start": True, "end": 3, "text": "x"}],    # True wäre sonst 1 s
        [{"id": "1" * 32, "start": 0, "end": True, "text": "x"}],
        [cue(1, 0, 1, "   ")],                               # leer
        [cue(1, 0, 1, "x" * 201)],                           # zu lang
        [cue(1, 0, 5 * 3600)],                               # über die Filmgrenze
        ["kein Objekt"],
        "keine Liste",
    ]
    for cues in bad:
        assert _code(client.put(f"{S}/de", headers=auth_headers, json={"revision": 0, "cues": cues})) == "400 studio_subtitles_invalid", cues
    many = [cue(i, i, i + 0.6) for i in range(5001)]
    assert _code(put(client, auth_headers, many)) == "400 studio_subtitles_invalid"
    assert not (ws / "studio/subtitles").exists()


def test_text_is_cleaned_for_the_file_formats(client, auth_headers, ws) -> None:
    out = put(client, auth_headers, [cue(1, 0, 2, "Zeile eins\n\n\nZeile zwei --> drei\r\n")]).json()
    assert out["cues"][0]["text"] == "Zeile eins\nZeile zwei -> drei"


def test_touching_cues_are_fine(client, auth_headers, ws) -> None:
    assert put(client, auth_headers, [cue(1, 0, 1), cue(2, 1, 2), cue(3, 2.0000001, 3)]).status_code == 200


def test_conflict(client, auth_headers, ws) -> None:
    put(client, auth_headers, [cue(1, 0, 1)])
    assert _code(put(client, auth_headers, [cue(1, 0, 2)], revision=0)) == "409 studio_subtitles_conflict"
    assert _code(client.put(f"{S}/de", headers=auth_headers, json={"revision": True, "cues": []})) == "409 studio_subtitles_conflict"
    assert put(client, auth_headers, [cue(1, 0, 2)], revision=1).json()["revision"] == 2


def test_languages_are_separate_and_checked(client, auth_headers, ws) -> None:
    put(client, auth_headers, [cue(1, 0, 1, "Hallo")])
    put(client, auth_headers, [cue(1, 0, 1, "Hello")], lang="en")
    assert client.get(f"{S}/en", headers=auth_headers).json()["cues"][0]["text"] == "Hello"
    assert client.get(f"{S}/de", headers=auth_headers).json()["cues"][0]["text"] == "Hallo"
    for bad in ("DE", "deu-x", "..", "d"):
        assert client.get(f"{S}/{bad}", headers=auth_headers).status_code == 404, bad


def test_only_members(client, other_headers, auth_headers, ws) -> None:
    put(client, auth_headers, [cue(1, 0, 1)])
    assert client.get(f"{S}/de", headers=other_headers).status_code == 404
    assert put(client, other_headers, [cue(1, 0, 1)]).status_code == 404
    assert client.post(f"{S}/de/from-speech", headers=other_headers, json={}).status_code == 404
    assert client.get(f"{S}/de/export?format=srt", headers=other_headers).status_code == 404


def test_screenplay_has_a_film_language(client, auth_headers, ws) -> None:
    from _subtitle_helpers import P
    assert client.get(f"{P}", headers=auth_headers).json()["screenplay"]["language"] == "de"
    client.put(f"{P}/screenplay", headers=auth_headers, json={"language": "en"})
    assert client.get(f"{P}", headers=auth_headers).json()["screenplay"]["language"] == "en"
    client.put(f"{P}/screenplay", headers=auth_headers, json={"language": "Klingonisch"})
    assert client.get(f"{P}", headers=auth_headers).json()["screenplay"]["language"] == "de"
