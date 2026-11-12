"""Automatische Anordnung der Bausteine eines Vorschlags (Etappe 3a).

Der Agent liefert nur Inhalte. Wo ein Baustein steht, rechnet layout.arrange aus:
Layout-Bausteine als Stapel links, Ablauf-Bausteine in Spalten entlang der
Verbindungen, Aufbau-Bausteine als eigenes Band darunter.
"""
from __future__ import annotations

from itertools import combinations

from backend import layout


def n(key: str, kind: str = "flow", subtype: str = "action", label: str = "Baustein", note: str = "") -> dict:
    return {"key": key, "kind": kind, "subtype": subtype, "label": label, "note": note}


def e(src: str, dst: str, handle: str | None = None) -> dict:
    return {"from": src, "to": dst, "handle": handle}


def _overlap(a: dict, b: dict) -> bool:
    return (a["x"] < b["x"] + b["width"] and b["x"] < a["x"] + a["width"]
            and a["y"] < b["y"] + b["height"] and b["y"] < a["y"] + a["height"])


def test_leere_eingabe():
    assert layout.arrange([], []) == {}


def test_kette_steht_in_spalten_von_links_nach_rechts():
    boxes = layout.arrange([n("a"), n("b"), n("c")], [e("a", "b"), e("b", "c")])
    assert boxes["a"]["x"] < boxes["b"]["x"] < boxes["c"]["x"]
    assert boxes["a"]["y"] == boxes["b"]["y"] == boxes["c"]["y"]


def test_reihenfolge_der_eingabe_spielt_fuer_die_spalten_keine_rolle():
    boxes = layout.arrange([n("c"), n("a"), n("b")], [e("b", "c"), e("a", "b")])
    assert boxes["a"]["x"] < boxes["b"]["x"] < boxes["c"]["x"]


def test_verzweigung_einer_bedingung_ja_steht_ueber_nein():
    nodes = [n("frage", subtype="condition"), n("fehler", subtype="display"), n("ok", subtype="display")]
    boxes = layout.arrange(nodes, [e("frage", "fehler", "false"), e("frage", "ok", "true")])
    assert boxes["ok"]["x"] == boxes["fehler"]["x"] > boxes["frage"]["x"]
    assert boxes["ok"]["y"] < boxes["fehler"]["y"]


def test_nachfolger_folgen_der_reihenfolge_ihrer_vorgaenger():
    nodes = [n("a"), n("b"), n("zu_b"), n("zu_a")]
    boxes = layout.arrange(nodes, [e("b", "zu_b"), e("a", "zu_a")])
    assert boxes["a"]["y"] < boxes["b"]["y"]
    assert boxes["zu_a"]["y"] < boxes["zu_b"]["y"]


def test_kreis_bricht_nicht_ab():
    boxes = layout.arrange([n("a"), n("b"), n("c")], [e("a", "b"), e("b", "c"), e("c", "a")])
    assert len({boxes[key]["x"] for key in "abc"}) == 3
    assert boxes["a"]["x"] < boxes["b"]["x"] < boxes["c"]["x"]


def test_verbindung_auf_sich_selbst_bricht_nicht_ab():
    boxes = layout.arrange([n("a"), n("b")], [e("a", "a"), e("a", "b")])
    assert boxes["a"]["x"] < boxes["b"]["x"]


def test_layout_bausteine_stehen_als_stapel_links():
    nodes = [n("seite", "layout", "page"), n("start"), n("feld", "layout", "input"), n("knopf", "layout", "button"),
             n("speichern")]
    boxes = layout.arrange(nodes, [e("seite", "feld"), e("seite", "knopf"), e("knopf", "start"), e("start", "speichern")])
    stack = [boxes[key] for key in ("seite", "feld", "knopf")]
    assert len({box["x"] for box in stack}) == 1
    assert [box["y"] for box in stack] == sorted(box["y"] for box in stack)
    assert len({box["y"] for box in stack}) == 3
    right_edge = stack[0]["x"] + stack[0]["width"]
    assert boxes["start"]["x"] > right_edge and boxes["speichern"]["x"] > boxes["start"]["x"]


def test_ohne_layout_bausteine_beginnt_der_ablauf_ganz_links():
    boxes = layout.arrange([n("a"), n("b")], [e("a", "b")])
    assert boxes["a"]["x"] == 0 and boxes["a"]["y"] == 0


def test_aufbau_bausteine_stehen_als_band_unter_dem_ablauf():
    nodes = [n("klick", subtype="event"), n("laden"), n("modul", "build", "module"), n("tabelle", "build", "database")]
    boxes = layout.arrange(nodes, [e("klick", "laden"), e("modul", "tabelle"), e("laden", "modul")])
    flow_bottom = max(boxes[key]["y"] + boxes[key]["height"] for key in ("klick", "laden"))
    assert boxes["modul"]["y"] > flow_bottom and boxes["tabelle"]["y"] > flow_bottom
    assert boxes["modul"]["x"] < boxes["tabelle"]["x"]


def test_keine_zwei_bausteine_ueberlappen():
    lang = "Ein sehr ausführlicher Hinweis, der über mehrere Zeilen läuft. " * 6
    nodes = [n(f"l{i}", "layout", "card", note=lang if i == 1 else "") for i in range(4)]
    nodes += [n("start", subtype="event"), n("frage", subtype="condition", label="Ist die Eingabe vollständig und gültig?")]
    nodes += [n(f"f{i}", note=lang if i % 2 else "") for i in range(6)]
    nodes += [n(f"b{i}", "build", "module", note=lang if i == 0 else "") for i in range(5)]
    edges = [e("start", "frage"), e("frage", "f0", "true"), e("frage", "f1", "false")]
    edges += [e("f0", f"f{i}") for i in range(2, 6)] + [e("b0", f"b{i}") for i in range(1, 5)] + [e("l0", "start")]
    boxes = layout.arrange(nodes, edges)
    assert len(boxes) == len(nodes)
    clashes = [(a, b) for a, b in combinations(boxes, 2) if _overlap(boxes[a], boxes[b])]
    assert clashes == []


def test_lange_texte_machen_den_baustein_hoeher_nicht_breiter():
    kurz = layout.arrange([n("a")], [])["a"]
    lang = layout.arrange([n("a", label="Eine lange Beschriftung, die sicher umbricht", note="Hinweis. " * 40)], [])["a"]
    assert lang["width"] == kurz["width"]
    assert lang["height"] > kurz["height"]


def test_gleiche_eingabe_ergibt_gleiche_positionen():
    nodes = [n("a"), n("b"), n("c", "layout", "page"), n("d", "build", "module")]
    edges = [e("a", "b"), e("c", "a"), e("b", "d")]
    assert layout.arrange(nodes, edges) == layout.arrange(list(nodes), list(edges))


def test_positionen_liegen_auf_dem_raster_des_boards():
    nodes = [n("a", note="x" * 300), n("b"), n("c"), n("s", "layout", "page"), n("m", "build", "module")]
    boxes = layout.arrange(nodes, [e("a", "b"), e("a", "c")])
    for box in boxes.values():
        assert box["x"] % layout.GRID == 0 and box["y"] % layout.GRID == 0


def test_verbindung_zu_einem_unbekannten_baustein_wird_uebergangen():
    boxes = layout.arrange([n("a"), n("b")], [e("a", "gibt_es_nicht"), e("gibt_es_nicht", "b"), e("a", "b")])
    assert set(boxes) == {"a", "b"} and boxes["a"]["x"] < boxes["b"]["x"]
