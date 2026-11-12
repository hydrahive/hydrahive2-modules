"""Speicher der Ideen: Besitz, Filter, Zählung, Grenzen."""
from __future__ import annotations

import pytest

from helpers import PROJECT_A, PROJECT_B


def _store():
    from backend import store
    return store


def _err(excinfo) -> str:
    return excinfo.value.code


def test_anlegen_und_lesen():
    s = _store()
    idea = s.create("alice", title="  Ideen-Modul  ", body="Kopfzeile und Beschreibung", project_id=PROJECT_A)
    assert idea["title"] == "Ideen-Modul"
    assert idea["status"] == "new"
    assert idea["origin"] == "user"
    assert idea["project_id"] == PROJECT_A
    assert idea["task_id"] is None and idea["board_id"] is None
    assert s.get("alice", idea["id"])["body"] == "Kopfzeile und Beschreibung"


def test_fremde_idee_ist_unsichtbar():
    s = _store()
    idea = s.create("alice", title="Geheim")
    assert s.get("bob", idea["id"]) is None
    assert s.list_ideas("bob") == []
    assert s.update("bob", idea["id"], title="Gekapert") is None
    assert s.delete("bob", idea["id"]) is False
    assert s.get("alice", idea["id"])["title"] == "Geheim"


def test_liste_filtert_nach_projekt_und_ohne_projekt():
    s = _store()
    s.create("alice", title="A", project_id=PROJECT_A)
    s.create("alice", title="B", project_id=PROJECT_B)
    s.create("alice", title="Frei")
    assert {i["title"] for i in s.list_ideas("alice")} == {"A", "B", "Frei"}
    assert [i["title"] for i in s.list_ideas("alice", project=PROJECT_A)] == ["A"]
    assert [i["title"] for i in s.list_ideas("alice", project=s.NO_PROJECT)] == ["Frei"]


def test_liste_filtert_nach_status_und_liefert_keine_volle_beschreibung():
    s = _store()
    a = s.create("alice", title="Offen", body="x" * 500)
    b = s.create("alice", title="Fertig")
    s.update("alice", b["id"], status="done")
    offene = s.list_ideas("alice", statuses=s.OPEN_STATUSES)
    assert [i["id"] for i in offene] == [a["id"]]
    assert "body" not in offene[0]
    assert len(offene[0]["body_preview"]) <= 160
    assert [i["title"] for i in s.list_ideas("alice", statuses=("done",))] == ["Fertig"]


def test_neueste_aenderung_zuerst():
    s = _store()
    a = s.create("alice", title="Erste")
    s.create("alice", title="Zweite")
    s.update("alice", a["id"], body="geändert")
    assert [i["title"] for i in s.list_ideas("alice")] == ["Erste", "Zweite"]


def test_zaehlung_je_status():
    s = _store()
    s.create("alice", title="1", project_id=PROJECT_A)
    two = s.create("alice", title="2", project_id=PROJECT_A)
    s.create("alice", title="3")
    s.update("alice", two["id"], status="planned")
    counts = s.count_by_status("alice")
    assert counts["new"] == 2 and counts["planned"] == 1 and counts["done"] == 0
    assert set(counts) == set(s.STATUSES)
    assert s.count_by_status("alice", project=PROJECT_A) == {**dict.fromkeys(s.STATUSES, 0), "new": 1, "planned": 1}
    assert s.count_by_status("bob")["new"] == 0


def test_aendern_setzt_felder_und_zeitstempel():
    s = _store()
    idea = s.create("alice", title="Alt", project_id=PROJECT_A)
    changed = s.update("alice", idea["id"], title="Neu", body="Text", status="review", project_id=None)
    assert (changed["title"], changed["body"], changed["status"], changed["project_id"]) == ("Neu", "Text", "review", None)
    assert changed["updated_at"] >= idea["updated_at"]
    assert changed["created_at"] == idea["created_at"]


def test_aendern_ohne_projektangabe_laesst_projekt_stehen():
    s = _store()
    idea = s.create("alice", title="Bleibt", project_id=PROJECT_A)
    assert s.update("alice", idea["id"], title="Bleibt hier")["project_id"] == PROJECT_A


def test_loeschen_entfernt_anmerkungen_mit():
    s = _store()
    from backend import notes
    from hydrahive.db.connection import db

    idea = s.create("alice", title="Weg damit")
    notes.add("alice", idea["id"], author="agent", body="Hinweis", agent_name="Buddy")
    assert s.delete("alice", idea["id"]) is True
    assert s.get("alice", idea["id"]) is None
    with db() as conn:
        left = conn.execute(
            "SELECT COUNT(*) FROM module_scratchpad_idea_notes WHERE idea_id = ?", (idea["id"],)
        ).fetchone()[0]
    assert left == 0


@pytest.mark.parametrize("title,code", [("", "title_required"), ("   ", "title_required"), ("x" * 201, "title_too_long")])
def test_titel_grenzen(title, code):
    s = _store()
    with pytest.raises(s.IdeaError) as excinfo:
        s.create("alice", title=title)
    assert _err(excinfo) == code


def test_beschreibung_zu_lang():
    s = _store()
    with pytest.raises(s.IdeaError) as excinfo:
        s.create("alice", title="Lang", body="x" * 50_001)
    assert _err(excinfo) == "body_too_long"
    idea = s.create("alice", title="Passt", body="x" * 50_000)
    with pytest.raises(s.IdeaError) as excinfo:
        s.update("alice", idea["id"], body="x" * 50_001)
    assert _err(excinfo) == "body_too_long"


def test_ungueltiger_status_und_herkunft():
    s = _store()
    idea = s.create("alice", title="Status")
    with pytest.raises(s.IdeaError) as excinfo:
        s.update("alice", idea["id"], status="fertig")
    assert _err(excinfo) == "invalid_status"
    with pytest.raises(s.IdeaError) as excinfo:
        s.create("alice", title="Herkunft", origin="fremd")
    assert _err(excinfo) == "invalid_origin"


def test_obergrenze_je_nutzer(monkeypatch):
    s = _store()
    monkeypatch.setattr(s, "MAX_IDEAS", 2)
    s.create("alice", title="1")
    s.create("alice", title="2")
    with pytest.raises(s.IdeaError) as excinfo:
        s.create("alice", title="3")
    assert _err(excinfo) == "ideas_full"
    assert s.create("bob", title="Eigene Grenze")["title"] == "Eigene Grenze"


def test_anmerkungen_anlegen_lesen_loeschen():
    s = _store()
    from backend import notes

    idea = s.create("alice", title="Mit Anmerkung")
    first = notes.add("alice", idea["id"], author="agent", body="Erst prüfen", agent_name="Buddy")
    notes.add("alice", idea["id"], author="system", body="Status: Neu → Geplant")
    listed = notes.list_for("alice", idea["id"])
    assert [n["body"] for n in listed] == ["Erst prüfen", "Status: Neu → Geplant"]
    assert listed[0]["agent_name"] == "Buddy" and listed[1]["author"] == "system"
    assert notes.add("bob", idea["id"], author="agent", body="fremd") is None
    assert notes.list_for("bob", idea["id"]) == []
    assert notes.remove("bob", idea["id"], first["id"]) is False
    assert notes.remove("alice", idea["id"], first["id"]) is True
    assert [n["body"] for n in notes.list_for("alice", idea["id"])] == ["Status: Neu → Geplant"]


def test_anmerkung_grenzen():
    s = _store()
    from backend import notes

    idea = s.create("alice", title="Grenzen")
    with pytest.raises(s.IdeaError) as excinfo:
        notes.add("alice", idea["id"], author="agent", body="  ")
    assert _err(excinfo) == "note_required"
    with pytest.raises(s.IdeaError) as excinfo:
        notes.add("alice", idea["id"], author="agent", body="x" * 10_001)
    assert _err(excinfo) == "note_too_long"


def test_anmerkung_zaehlt_als_aenderung_der_idee():
    s = _store()
    from backend import notes

    a = s.create("alice", title="Ältere")
    s.create("alice", title="Jüngere")
    notes.add("alice", a["id"], author="agent", body="Neu angemerkt")
    listed = s.list_ideas("alice")
    assert listed[0]["title"] == "Ältere"
    assert listed[0]["note_count"] == 1 and listed[1]["note_count"] == 0
