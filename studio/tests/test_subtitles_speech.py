"""Studio 6a: Untertitel aus den Sprechtexten (Spec „Bauplan Etappe 6“), Zeit von der Sprache bzw. vom Bild."""
from __future__ import annotations

from itertools import pairwise

from _subtitle_helpers import S, cue, film, put
from _timeline_helpers import _code

F = f"{S}/de/from-speech"


def test_time_from_bound_speech_else_from_picture(client, auth_headers, ws) -> None:
    film(client, auth_headers, ws, [{"duration": 4, "speech": "Da ist er.", "voice": 2.5},
                                    {"duration": 3, "speech": "Endlich!"},
                                    {"duration": 2}])
    r = client.post(F, headers=auth_headers, json={})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["source"] == "speech" and out["revision"] == 1 and out["skipped"] == 0
    assert [(c["start"], c["end"], c["text"]) for c in out["cues"]] == [(0, 2.5, "Da ist er."), (4, 7, "Endlich!")]
    assert client.get(f"{S}/de", headers=auth_headers).json()["cues"] == out["cues"]


def test_order_follows_the_timeline_not_the_screenplay(client, auth_headers, ws) -> None:
    from _timeline_helpers import T
    film(client, auth_headers, ws, [{"duration": 2, "speech": "Erst"}, {"duration": 2, "speech": "Dann"}])
    tl = client.get(T, headers=auth_headers).json()
    v1 = tl["tracks"][0]["clips"]
    v1[0]["start"], v1[1]["start"] = 2, 0
    client.put(T, headers=auth_headers, json={"revision": tl["revision"], "fps": 25, "tracks": tl["tracks"]})
    out = client.post(F, headers=auth_headers, json={}).json()
    assert [c["text"] for c in out["cues"]] == ["Dann", "Erst"]


def test_long_text_is_split_at_sentences_and_time_shared(client, auth_headers, ws) -> None:
    text = "Der Sturm kommt näher. Ole zieht das Netz ein. Dann wird es still im Hafen."
    film(client, auth_headers, ws, [{"duration": 9, "speech": text}])
    cues = client.post(F, headers=auth_headers, json={}).json()["cues"]
    assert [c["text"] for c in cues] == ["Der Sturm kommt näher.", "Ole zieht das Netz ein.", "Dann wird es still im Hafen."]
    assert cues[0]["start"] == 0 and abs(cues[-1]["end"] - 9) < 1e-6
    for a, b in pairwise(cues):
        assert abs(a["end"] - b["start"]) < 1e-6                        # lückenlos innerhalb des Shots
    assert cues[2]["end"] - cues[2]["start"] > cues[0]["end"] - cues[0]["start"]   # längerer Text, mehr Zeit


def test_lines_are_wrapped_and_very_long_sentences_split(client, auth_headers, ws) -> None:
    long = ("Ole steht am Ende des alten Holzstegs und schaut lange auf das graue Wasser hinaus, "
            "während hinter ihm die Möwen über den leeren Kuttern kreisen und der Wind auffrischt")
    film(client, auth_headers, ws, [{"duration": 12, "speech": long}])
    cues = client.post(F, headers=auth_headers, json={}).json()["cues"]
    assert len(cues) >= 2
    for c in cues:
        lines = c["text"].split("\n")
        assert len(lines) <= 2 and all(len(x) <= 42 for x in lines), c["text"]
    assert " ".join(" ".join(c["text"].split("\n")) for c in cues) == long


def test_each_cue_at_most_seven_seconds(client, auth_headers, ws) -> None:
    film(client, auth_headers, ws, [{"duration": 20, "speech": "Kurz."}])
    c = client.post(F, headers=auth_headers, json={}).json()["cues"][0]
    assert (c["start"], c["end"]) == (0, 7)


def test_no_part_longer_than_seven_seconds(client, auth_headers, ws) -> None:
    film(client, auth_headers, ws, [{"duration": 14, "speech": "Ja. Ole schaut lange auf das graue Wasser hinaus."}])
    cues = client.post(F, headers=auth_headers, json={}).json()["cues"]
    assert len(cues) == 2 and all(c["end"] - c["start"] <= 7 + 1e-6 for c in cues), cues


def test_too_many_sentences_for_a_short_shot_stay_together(client, auth_headers, ws) -> None:
    film(client, auth_headers, ws, [{"duration": 1, "speech": "Ja. Nein. Doch."}])
    cues = client.post(F, headers=auth_headers, json={}).json()["cues"]
    assert all(c["end"] - c["start"] >= 0.5 - 1e-9 for c in cues)
    assert " ".join(c["text"] for c in cues) == "Ja. Nein. Doch."


def test_shots_not_on_the_timeline_are_counted(client, auth_headers, ws) -> None:
    film(client, auth_headers, ws, [{"duration": 2, "speech": "Da."}, {"duration": 2, "speech": "Weg.", "on_timeline": False}])
    out = client.post(F, headers=auth_headers, json={}).json()
    assert [c["text"] for c in out["cues"]] == ["Da."] and out["skipped"] == 1


def test_split_shot_counts_once_at_its_first_part(client, auth_headers, ws) -> None:
    from _timeline_helpers import T
    film(client, auth_headers, ws, [{"duration": 4, "speech": "Einmal."}])
    tl = client.get(T, headers=auth_headers).json()
    a = tl["tracks"][0]["clips"][0]
    b = {**a, "id": "f" * 32, "start": 2, "in": 2, "out": 4}
    a["out"] = 2
    tl["tracks"][0]["clips"] = [a, b]
    client.put(T, headers=auth_headers, json={"revision": tl["revision"], "fps": 25, "tracks": tl["tracks"]})
    cues = client.post(F, headers=auth_headers, json={}).json()["cues"]
    assert [(c["start"], c["end"]) for c in cues] == [(0, 2)]


def test_nothing_to_do(client, auth_headers, ws) -> None:
    assert _code(client.post(F, headers=auth_headers, json={})) == "400 studio_subtitles_no_speech"
    film(client, auth_headers, ws, [{"duration": 2}])
    assert _code(client.post(F, headers=auth_headers, json={})) == "400 studio_subtitles_no_speech"
    assert not (ws / "studio/subtitles").exists()


def test_existing_subtitles_need_replace(client, auth_headers, ws) -> None:
    film(client, auth_headers, ws, [{"duration": 2, "speech": "Neu."}])
    put(client, auth_headers, [cue(1, 0, 1, "Von Hand")])
    assert _code(client.post(F, headers=auth_headers, json={})) == "409 studio_subtitles_not_empty"
    assert client.get(f"{S}/de", headers=auth_headers).json()["cues"][0]["text"] == "Von Hand"
    out = client.post(F, headers=auth_headers, json={"replace": True}).json()
    assert [c["text"] for c in out["cues"]] == ["Neu."] and out["revision"] == 2
    assert _code(client.post(F, headers=auth_headers, json={"replace": "ja"})) == "409 studio_subtitles_not_empty"
