"""Vorschlag des Agenten prüfen und in einen Board-Graphen umsetzen (Etappe 3a).

Der Agent liefert nur Inhalte: Bausteine mit Kürzel, Art, Beschriftung, Notiz und
Verbindungen. proposal.build_graph prüft sie und baut daraus den Graphen im
Format der Zeichenfläche, samt Positionen aus layout.arrange.
"""
from __future__ import annotations

import json

import pytest

from backend import proposal
from backend.render import render_board


def n(key: str, kind: str = "action", label: str = "Baustein", **extra) -> dict:
    return {"key": key, "type": kind, "label": label, **extra}


def e(src: str, dst: str, branch: str | None = None) -> dict:
    return {"from": src, "to": dst, **({"branch": branch} if branch is not None else {})}


def _code(nodes, edges=None) -> str:
    with pytest.raises(proposal.ProposalError) as excinfo:
        proposal.build_graph(nodes, edges or [])
    assert excinfo.value.message.strip(), "Fehler ohne Text für den Agenten"
    return excinfo.value.code


LOGIN = [
    n("seite", "page", "Einstellungen"),
    n("mail", "input", "E-Mail", placeholder="name@example.org"),
    n("knopf", "button", "Speichern", note="Nur aktiv,\nwenn Feld gefüllt"),
    n("klick", "event", "Klick"),
    n("frage", "condition", "Adresse gültig?"),
    n("speichern", "action", "Daten speichern"),
    n("ok", "display", "Gespeichert"),
    n("fehler", "display", "Fehlermeldung"),
    n("modul", "module", "Einstellungen-Modul"),
]
# Ein Event hat keinen Eingang, eine Anzeige keinen Ausgang: Knopf und Klick führen beide zur Bedingung.
LOGIN_EDGES = [
    e("seite", "mail"), e("seite", "knopf"), e("knopf", "frage"), e("klick", "frage"),
    e("frage", "speichern", "yes"), e("frage", "fehler", "no"), e("speichern", "ok"), e("speichern", "modul"),
]


def test_baut_bausteine_im_format_der_zeichenflaeche():
    graph = proposal.build_graph(LOGIN, LOGIN_EDGES)
    by_id = {node["id"]: node for node in graph["nodes"]}
    assert list(by_id) == [node["key"] for node in LOGIN]
    assert by_id["seite"]["type"] == "layoutNode" and by_id["klick"]["type"] == "flowNode"
    assert by_id["modul"]["type"] == "buildNode"
    assert by_id["knopf"]["data"] == {"kind": "layout", "subtype": "button", "label": "Speichern",
                                      "note": "Nur aktiv,\nwenn Feld gefüllt"}
    assert by_id["mail"]["data"]["placeholder"] == "name@example.org"
    assert by_id["modul"]["data"]["kind"] == "build"
    for node in graph["nodes"]:
        assert set(node["position"]) == {"x", "y"} and node["width"] > 0
        assert isinstance(node["position"]["x"], int) and isinstance(node["position"]["y"], int)


def test_baut_verbindungen_mit_den_anschluessen_der_bausteine():
    graph = proposal.build_graph(LOGIN, LOGIN_EDGES)
    edges = {(edge["source"], edge["target"]): edge for edge in graph["edges"]}
    assert len(edges) == len(LOGIN_EDGES)
    assert edges[("seite", "mail")]["sourceHandle"] == "out" and edges[("seite", "mail")]["targetHandle"] == "in"
    assert edges[("frage", "speichern")]["sourceHandle"] == "true"
    assert edges[("frage", "fehler")]["sourceHandle"] == "false"
    assert len({edge["id"] for edge in graph["edges"]}) == len(graph["edges"])


def test_ergebnis_ist_als_board_text_lesbar():
    text = render_board({"name": "Login"}, json.dumps(proposal.build_graph(LOGIN, LOGIN_EDGES)))
    assert "9 Bausteine, 8 Verbindungen" in text
    assert "## Layout" in text and "## Ablauf" in text and "## Aufbau" in text
    assert "„Adresse gültig?“ [ja] → B6 „Daten speichern“" in text
    assert "(fehlt)" not in text


def test_eingabefeld_ohne_platzhalter_bekommt_ein_leeres_feld():
    graph = proposal.build_graph([n("a", "input", "Name")], [])
    assert graph["nodes"][0]["data"]["placeholder"] == ""


def test_ja_und_nein_gehen_deutsch_und_englisch():
    for yes, no in (("yes", "no"), ("ja", "nein"), ("JA", "Nein")):
        graph = proposal.build_graph([n("f", "condition"), n("a"), n("b")], [e("f", "a", yes), e("f", "b", no)])
        assert [edge["sourceHandle"] for edge in graph["edges"]] == ["true", "false"]


def test_gleiche_eingabe_ergibt_denselben_graphen():
    assert proposal.build_graph(LOGIN, LOGIN_EDGES) == proposal.build_graph(list(LOGIN), list(LOGIN_EDGES))


def test_doppelte_verbindung_zaehlt_einmal():
    graph = proposal.build_graph([n("a"), n("b")], [e("a", "b"), e("a", "b")])
    assert len(graph["edges"]) == 1


def test_unbekannte_art_wird_abgelehnt_und_nennt_die_bekannten():
    with pytest.raises(proposal.ProposalError) as excinfo:
        proposal.build_graph([n("a", "sonderding")], [])
    assert excinfo.value.code == "unknown_type"
    assert "sonderding" in excinfo.value.message and "agent_tool" in excinfo.value.message


def test_doppeltes_kuerzel_wird_abgelehnt():
    assert _code([n("a"), n("a")]) == "duplicate_key"


@pytest.mark.parametrize("key", ["", "  ", "mit leer", "a/b", "x" * 41, None, 7])
def test_ungueltiges_kuerzel_wird_abgelehnt(key):
    assert _code([n(key)]) == "invalid_key"


def test_verbindung_ins_leere_wird_abgelehnt():
    assert _code([n("a")], [e("a", "gibt_es_nicht")]) == "unknown_edge_node"
    assert _code([n("a")], [e("gibt_es_nicht", "a")]) == "unknown_edge_node"


def test_verbindung_auf_sich_selbst_wird_abgelehnt():
    assert _code([n("a")], [e("a", "a")]) == "self_edge"


def test_hoechstens_80_bausteine():
    proposal.build_graph([n(f"b{i}") for i in range(80)], [])
    assert _code([n(f"b{i}") for i in range(81)]) == "too_many_nodes"


def test_ohne_bausteine_wird_abgelehnt():
    assert _code([]) == "no_nodes"


@pytest.mark.parametrize("nodes", [None, "text", {"key": "a"}, ["kein Objekt"], [None]])
def test_falsche_form_der_bausteine_wird_abgelehnt(nodes):
    assert _code(nodes) == "invalid_shape"


@pytest.mark.parametrize("edges", ["text", {"from": "a"}, ["kein Objekt"]])
def test_falsche_form_der_verbindungen_wird_abgelehnt(edges):
    with pytest.raises(proposal.ProposalError) as excinfo:
        proposal.build_graph([n("a"), n("b")], edges)
    assert excinfo.value.code == "invalid_shape"


def test_beschriftung_ist_pflicht_und_begrenzt():
    assert _code([{"key": "a", "type": "action"}]) == "invalid_label"
    assert _code([n("a", label="   ")]) == "invalid_label"
    assert _code([n("a", label="x" * 201)]) == "invalid_label"
    assert _code([n("a", note="x" * 2001)]) == "invalid_note"
    assert _code([n("a", "input", placeholder="x" * 201)]) == "invalid_placeholder"


def test_platzhalter_gibt_es_nur_beim_eingabefeld():
    assert _code([n("a", "button", placeholder="Text")]) == "invalid_placeholder"


def test_bedingung_braucht_ja_oder_nein():
    assert _code([n("f", "condition"), n("a")], [e("f", "a")]) == "branch_required"
    assert _code([n("f", "condition"), n("a")], [e("f", "a", "vielleicht")]) == "invalid_branch"


def test_ja_nein_gibt_es_nur_an_bedingungen():
    assert _code([n("a"), n("b")], [e("a", "b", "yes")]) == "branch_not_allowed"


def test_anschluesse_die_es_nicht_gibt_werden_abgelehnt():
    # Die Oberfläche könnte solche Verbindungen nicht zeichnen: sie blieben unsichtbar.
    assert _code([n("a"), n("ev", "event")], [e("a", "ev")]) == "no_input"
    assert _code([n("a"), n("z", "note")], [e("a", "z")]) == "no_input"
    assert _code([n("d", "display"), n("a")], [e("d", "a")]) == "no_output"
    assert _code([n("z", "note"), n("a")], [e("z", "a")]) == "no_output"


def test_groesster_erlaubter_vorschlag_bleibt_unter_2_mb():
    nodes = [n(f"b{i}", "input", "x" * 200, note="y" * 2000, placeholder="z" * 200) for i in range(80)]
    edges = [e(f"b{i}", f"b{j}") for i in range(80) for j in range(80) if i != j][:proposal.MAX_EDGES]
    graph = proposal.build_graph(nodes, edges)
    assert len(json.dumps(graph, ensure_ascii=False).encode("utf-8")) < 2 * 1024 * 1024


def test_zu_viele_verbindungen_werden_abgelehnt():
    nodes = [n(f"b{i}") for i in range(40)]
    edges = [e(f"b{i}", f"b{j}") for i in range(40) for j in range(40) if i != j][:proposal.MAX_EDGES + 1]
    assert _code(nodes, edges) == "too_many_edges"
