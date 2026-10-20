"""Fallakte: Beteiligte, Fristen, Notizen, Vorschläge (Plan L2 Schritte 4–5, Datenteil ohne Routen)."""
from __future__ import annotations

import pytest
from backend import casefile, cases, corpus_store
from backend.gii_parse import parse_law
from conftest import fixture_xml

FACTS = {"title": "Mietsache Hitze", "area": "Mietrecht", "state": "NI", "facts": "Seit Juni zu heiß."}


@pytest.fixture
def pid():
    from hydrahive.projects import config as pc
    out = cases.create_case("alice", FACTS, model="claude-sonnet-4-6")
    yield out["project_id"]
    pc.delete(out["project_id"])


@pytest.fixture
def corpus():
    xml = fixture_xml("bgb")
    corpus_store.save_law(parse_law("bgb", xml), xml, fetched_at="2026-10-20T03:30:00Z", pinned=True)


def test_party_add_list_delete(pid):
    p = casefile.add_party(pid, {"role": "opponent", "name": "Hausverwaltung Müller GmbH", "address": "Hauptstr. 1"})
    assert casefile.list_parties(pid) == [p]
    with pytest.raises(cases.CaseError):
        casefile.add_party(pid, {"role": "feind", "name": "X"})
    with pytest.raises(cases.CaseError):
        casefile.add_party(pid, {"role": "lawyer", "name": ""})
    casefile.delete_party(pid, p["id"])
    assert casefile.list_parties(pid) == []


def test_deadline_uses_case_state_and_stores_calc(pid):
    # 30.10.2028 (Mo) + 1 Tag = Di 31.10.2028 = Reformationstag in NI (Fall-Land) → Mi 01.11.2028; in NW wäre es Di
    d = casefile.add_deadline(pid, {"label": "Antwort Vermieter", "event_date": "2028-10-30", "kind": "days",
                                    "amount": 1})
    assert d["due_date"] == "2028-11-01" and d["status"] == "open"
    assert any("Reformationstag" in s for s in d["calc"]["steps"])
    casefile.set_deadline_status(pid, d["id"], "done")
    assert casefile.list_deadlines(pid)[0]["status"] == "done"
    with pytest.raises(cases.CaseError):
        casefile.add_deadline(pid, {"label": "x", "event_date": "kein Datum", "kind": "days", "amount": 1})
    with pytest.raises(cases.CaseError):
        casefile.set_deadline_status(pid, d["id"], "vergessen")


def test_deadline_of_other_case_is_not_touchable(pid):
    from hydrahive.projects import config as pc
    other = cases.create_case("alice", {**FACTS, "title": "Anderer Fall"}, model="claude-sonnet-4-6")["project_id"]
    try:
        d = casefile.add_deadline(other, {"label": "y", "event_date": "2026-11-02", "kind": "weeks", "amount": 2})
        with pytest.raises(cases.CaseError) as e:
            casefile.set_deadline_status(pid, d["id"], "done")
        assert e.value.status == 404
    finally:
        pc.delete(other)


def test_note_checks_citations_against_corpus(pid, corpus):
    n = casefile.add_note(pid, author="agent", author_name="Rechts-Agent", title="Mängelanzeige",
                          body="Pflicht zur Anzeige.", citations=["§ 536c BGB", "§ 999 BGB", "Unsinn"])
    assert n["citations"] == [{"citation": "§ 536c BGB", "found": True},
                              {"citation": "§ 999 BGB", "found": False},
                              {"citation": "Unsinn", "found": False}]
    assert casefile.list_notes(pid)[0]["title"] == "Mängelanzeige"


def test_proposal_does_not_change_file_until_accepted(pid):
    pr = casefile.propose(pid, "party", {"role": "lawyer", "name": "RAin Schmidt"}, author_name="Rechts-Agent")
    assert casefile.list_parties(pid) == []
    assert [p["id"] for p in casefile.list_proposals(pid)] == [pr["id"]]
    casefile.decide(pid, pr["id"], accept=True, by="alice")
    assert [p["name"] for p in casefile.list_parties(pid)] == ["RAin Schmidt"]
    assert casefile.list_proposals(pid) == []                                    # nur offene
    with pytest.raises(cases.CaseError):
        casefile.decide(pid, pr["id"], accept=True, by="alice")                  # schon entschieden


def test_deadline_and_fact_proposals(pid):
    d = casefile.propose(pid, "deadline", {"label": "Widerspruch", "event_date": "2026-11-02", "kind": "months",
                                           "amount": 1}, author_name="Rechts-Agent")
    assert d["payload"]["due_date"] == "2026-12-02"                              # schon beim Vorschlag gerechnet
    f = casefile.propose(pid, "fact", {"text": "Mängelanzeige per Einschreiben am 03.07.2026."},
                         author_name="Rechts-Agent")
    casefile.decide(pid, d["id"], accept=True, by="alice")
    casefile.decide(pid, f["id"], accept=False, by="alice")
    assert [x["label"] for x in casefile.list_deadlines(pid)] == ["Widerspruch"]
    assert "Einschreiben" not in cases.get_case(pid)["facts"]
    f2 = casefile.propose(pid, "fact", {"text": "Mieter zahlt seit August gemindert."}, author_name="A")
    casefile.decide(pid, f2["id"], accept=True, by="alice")
    assert cases.get_case(pid)["facts"].endswith("Mieter zahlt seit August gemindert.")


def test_invalid_proposal_is_refused(pid):
    for kind, payload in (("party", {"role": "x", "name": "y"}), ("deadline", {"label": "z", "kind": "days"}),
                          ("fact", {"text": ""}), ("brief", {"text": "a"})):
        with pytest.raises(cases.CaseError):
            casefile.propose(pid, kind, payload, author_name="A")
    assert casefile.list_proposals(pid) == []


def test_snapshot_contains_everything(pid):
    casefile.add_party(pid, {"role": "opponent", "name": "Vermieter"})
    casefile.add_deadline(pid, {"label": "Frist", "event_date": "2026-11-02", "kind": "weeks", "amount": 2})
    snap = casefile.snapshot(pid)
    assert snap["case"]["title"] == "Mietsache Hitze" and snap["state_name"] == "Niedersachsen"
    assert snap["parties"][0]["name"] == "Vermieter" and snap["deadlines"][0]["due_date"] == "2026-11-16"
    assert snap["notes"] == [] and snap["open_proposals"] == 0
