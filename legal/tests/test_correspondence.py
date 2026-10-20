"""Schriftverkehr + Brief-Vorschlag (Plan L3 Schritt 4). Kein automatischer Versand: „versendet“ trägt der Mensch ein."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from backend import casefile, cases, correspondence, orphans
from conftest import fixture_xml

LETTER = {"letter_type": "mangelanzeige", "sender": "Till Muster\nMusterweg 1\n30159 Hannover",
          "recipient": "Hausverwaltung Müller GmbH\nHauptstraße 1\n30159 Hannover", "date": "2026-10-20",
          "subject": "Mangelanzeige", "body": "Gemäß § 536c BGB … bis zum 10.11.2026.", "delivery": "einwurf_einschreiben",
          "attachments": [], "their_ref": "", "our_ref": ""}


@pytest.fixture(autouse=True)
def _tools(monkeypatch):
    from backend.tools import TOOLS
    from hydrahive.tools import REGISTRY
    for t in TOOLS:
        monkeypatch.setitem(REGISTRY, t.name, t)


@pytest.fixture
def pid():
    from hydrahive.projects import config as pc
    out = cases.create_case("alice", {"title": "Mietsache Hitze", "state": "NI"}, model="claude-sonnet-4-6")
    yield out["project_id"]
    pc.delete(out["project_id"])


@pytest.fixture
def corpus():
    from backend import corpus_store
    from backend.gii_parse import parse_law
    xml = fixture_xml("bgb")
    corpus_store.save_law(parse_law("bgb", xml), xml, fetched_at="2026-10-20T03:30:00Z", pinned=True)


def test_incoming_letter_is_recorded(pid):
    e = correspondence.add(pid, {"direction": "in", "date": "2026-10-15", "sender": "Hausverwaltung Müller GmbH",
                                 "subject": "Ihre Beschwerde", "body": "Kurzfassung: lehnen ab."}, by="alice")
    assert e["direction"] == "in" and e["status"] == "received" and e["created_by"] == "alice"
    assert correspondence.list_for(pid) == [e]


def test_outgoing_draft_then_sent(pid):
    e = correspondence.add(pid, {"direction": "out", **LETTER}, by="alice")
    assert e["status"] == "draft" and e["letter_type"] == "mangelanzeige" and e["attachments"] == []
    s = correspondence.mark_sent(pid, e["id"], {"date": "2026-10-21", "delivery": "einwurf_einschreiben",
                                                "proof": "RT 1234 5678 9DE"})
    assert s["status"] == "sent" and s["date"] == "2026-10-21" and s["proof"] == "RT 1234 5678 9DE"
    with pytest.raises(cases.CaseError):
        correspondence.update(pid, e["id"], {"body": "geändert"})       # versendet = nicht mehr änderbar


def test_draft_can_be_edited(pid):
    e = correspondence.add(pid, {"direction": "out", **LETTER}, by="alice")
    u = correspondence.update(pid, e["id"], {"body": "Neuer Text § 536c BGB", "attachments": ["Messprotokoll"]})
    assert u["body"] == "Neuer Text § 536c BGB" and u["attachments"] == ["Messprotokoll"]


@pytest.mark.parametrize("bad", [
    {"direction": "seitwärts"}, {"direction": "in", "date": "gestern"}, {"direction": "out", "delivery": "taube"},
    {"direction": "out", "subject": "x" * 301}, {"direction": "out", "attachments": "kein Array"},
])
def test_invalid_entries(pid, bad):
    with pytest.raises(cases.CaseError):
        correspondence.add(pid, {**LETTER, **bad}, by="alice")


def test_ids_of_other_case_are_404(pid):
    from hydrahive.projects import config as pc
    other = cases.create_case("alice", {"title": "Anderer", "state": "NW"}, model="claude-sonnet-4-6")["project_id"]
    try:
        e = correspondence.add(other, {"direction": "out", **LETTER}, by="alice")
        for fn in (lambda: correspondence.update(pid, e["id"], {"body": "x"}),
                   lambda: correspondence.mark_sent(pid, e["id"], {"date": "2026-10-21", "delivery": "bote"}),
                   lambda: correspondence.delete(pid, e["id"])):
            with pytest.raises(cases.CaseError) as err:
                fn()
            assert err.value.status == 404
    finally:
        pc.delete(other)


def test_letter_proposal_carries_check_and_does_not_touch_file(pid, corpus):
    pr = casefile.propose(pid, "letter", LETTER, author_name="Rechts-Agent")
    assert pr["payload"]["check"]["norms"] == [{"raw": "§ 536c BGB", "citation": "§ 536c BGB", "found": True}]
    assert correspondence.list_for(pid) == []
    casefile.decide(pid, pr["id"], accept=True, by="alice")
    entries = correspondence.list_for(pid)
    assert len(entries) == 1 and entries[0]["status"] == "draft" and entries[0]["direction"] == "out"
    assert entries[0]["body"] == LETTER["body"] and entries[0]["created_by"] == "alice"


def test_invalid_letter_proposal_refused(pid):
    with pytest.raises(cases.CaseError):
        casefile.propose(pid, "letter", {**LETTER, "body": ""}, author_name="A")
    with pytest.raises(cases.CaseError):
        casefile.propose(pid, "letter", {**LETTER, "delivery": "taube"}, author_name="A")


def test_snapshot_lists_correspondence(pid):
    correspondence.add(pid, {"direction": "out", **LETTER}, by="alice")
    snap = casefile.snapshot(pid)
    assert [e["subject"] for e in snap["correspondence"]] == ["Mangelanzeige"]


def test_orphan_archive_includes_correspondence(pid, setup_test_env):
    import json

    from hydrahive.projects import config as pc
    correspondence.add(pid, {"direction": "out", **LETTER}, by="alice")
    pc.delete(pid)
    t0 = datetime(2026, 10, 20, tzinfo=UTC)
    orphans.sweep(now=t0)
    orphans.sweep(now=t0 + timedelta(days=31))
    f = next((setup_test_env / "data" / "legal" / "archive").glob(f"*{pid}*.json"))
    assert json.loads(f.read_text())["correspondence"][0]["subject"] == "Mangelanzeige"
    from hydrahive.db.connection import db
    with db() as c:
        assert c.execute("SELECT count(*) FROM module_legal_correspondence WHERE project_id=?", (pid,)).fetchone()[0] == 0


def test_migration_keeps_old_proposals_and_allows_letter():
    """003 baut module_legal_proposals neu (CHECK um 'letter' erweitert). Vorhandene Zeilen müssen bleiben."""
    import sqlite3
    from pathlib import Path
    mig = Path(__file__).resolve().parents[1] / "migrations"
    c = sqlite3.connect(":memory:")
    c.executescript((mig / "002_cases.sql").read_text())
    c.execute("INSERT INTO module_legal_cases(project_id,title,state,created_by,created_at,updated_at) "
              "VALUES ('p','T','NW','a','x','x')")
    c.execute("INSERT INTO module_legal_proposals(project_id,kind,payload,created_at) VALUES ('p','fact','{}','x')")
    c.commit()
    c.executescript((mig / "003_letters.sql").read_text())
    assert c.execute("SELECT kind FROM module_legal_proposals").fetchall() == [("fact",)]
    c.execute("INSERT INTO module_legal_proposals(project_id,kind,payload,created_at) VALUES ('p','letter','{}','x')")
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("INSERT INTO module_legal_proposals(project_id,kind,payload,created_at) VALUES ('p','quatsch','{}','x')")
