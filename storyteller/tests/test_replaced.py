"""A2: Vorschlags-Verlauf – ersetzte und verworfene Vorschläge bleiben erhalten (Spec nichts-geht-verloren.md §2)."""
from __future__ import annotations

import pytest
from conftest import PROJECT_ID

from backend import _replaced, proposals, storage
from backend._files import StoryError


def _book_with_text(text="Mein Text."):
    b = storage.create_book(PROJECT_ID, {"title": "T", "kind": "novel", "language": "de"})
    sid = storage.get_structure(PROJECT_ID, b["id"])["parts"][0]["chapters"][0]["scenes"][0]
    s = storage.save_scene(PROJECT_ID, b["id"], sid, {"text": text}, base_version=1)
    return b["id"], sid, s


def _store(bid, sid, s, text, **kw):
    return proposals.store(PROJECT_ID, bid, sid, text, run_id=kw.pop("run_id", ""), model="m",
                           base_version=s["version"], **kw)


def test_replacing_keeps_the_old_proposal_and_says_from_whom():
    bid, sid, s = _book_with_text()
    _store(bid, sid, s, "Fassung des Laufs.", run_id="r1")
    new = _store(bid, sid, s, "Fassung des Lektors.", source="agent", author="Buch — Lektor")
    assert new["replaced_from"]["source"] == "run" and new["replaced_from"]["at"]
    assert proposals.get(PROJECT_ID, bid, sid)["replaced_from"]["author"] == "Ghostwriter-Lauf"       # für den Hinweis
    assert proposals.list_for_book(PROJECT_ID, bid)[0]["replaced_from"]["author"] == "Ghostwriter-Lauf"
    assert proposals.get(PROJECT_ID, bid, sid)["text"] == "Fassung des Lektors."
    hist = _replaced.history(PROJECT_ID, bid, "text", sid)
    assert len(hist) == 1 and hist[0]["words"] == 3 and hist[0]["source"] == "run" and hist[0]["author"] == "Ghostwriter-Lauf"
    assert hist[0]["reason"] == "replaced" and hist[0]["replaced_by"] == "Buch — Lektor"
    assert _replaced.get(PROJECT_ID, bid, "text", sid, hist[0]["id"])["text"] == "Fassung des Laufs."


def test_old_proposal_without_author_is_named_by_its_source():
    """Vorschläge vor 0.16.0 haben kein author-Feld: Lauf → „Ghostwriter-Lauf“, Agent → „Agent“."""
    from backend.proposals import origin_of
    assert origin_of({"source": "run"}) == "Ghostwriter-Lauf"
    assert origin_of({}) == "Ghostwriter-Lauf"
    assert origin_of({"source": "agent"}) == "Agent"
    assert origin_of({"source": "agent", "author": "B — Lektor"}) == "B — Lektor"


def test_first_proposal_replaces_nothing():
    bid, sid, s = _book_with_text()
    assert _store(bid, sid, s, "Erste.")["replaced_from"] is None
    assert _replaced.history(PROJECT_ID, bid, "text", sid) == []


def test_discard_also_keeps_it():
    bid, sid, s = _book_with_text()
    _store(bid, sid, s, "Verworfen, aber da.")
    proposals.discard(PROJECT_ID, bid, sid)
    with pytest.raises(StoryError):
        proposals.get(PROJECT_ID, bid, sid)
    hist = _replaced.history(PROJECT_ID, bid, "text", sid)
    assert [h["reason"] for h in hist] == ["discarded"]


def test_accept_does_not_put_it_into_history():
    """Übernommen ist nicht verloren – der alte Szenentext steht im Schnappschuss."""
    bid, sid, s = _book_with_text()
    _store(bid, sid, s, "Übernommen.")
    proposals.accept(PROJECT_ID, bid, sid, base_version=s["version"])
    assert _replaced.history(PROJECT_ID, bid, "text", sid) == []


def test_history_is_newest_first_and_bounded_to_ten():
    """Spec §2: je Szene/Art höchstens 10 ersetzte Vorschläge, älteste fallen weg."""
    bid, sid, s = _book_with_text()
    for i in range(13):
        _store(bid, sid, s, f"Fassung {i}.")
    hist = _replaced.history(PROJECT_ID, bid, "text", sid)
    assert len(hist) == 10
    texts = [_replaced.get(PROJECT_ID, bid, "text", sid, h["id"])["text"] for h in hist]
    assert texts[0] == "Fassung 11." and texts[-1] == "Fassung 2."


def test_only_well_formed_entry_names_are_read():
    """Nur Einträge im Format <Zeitstempel> – eine fremde Datei im Verlaufsordner wird nie geliefert."""
    bid, sid, s = _book_with_text()
    _store(bid, sid, s, "Eins.")
    _store(bid, sid, s, "Zwei.")
    d = storage.book_dir(PROJECT_ID, bid) / "proposals" / "_replaced" / "text" / sid
    real = next(d.glob("*.json"))
    (d / "fremd.json").write_text(real.read_text())
    with pytest.raises(StoryError) as e:
        _replaced.get(PROJECT_ID, bid, "text", sid, "fremd")
    assert e.value.status == 404


def test_restore_makes_it_open_again_and_keeps_the_current_one():
    bid, sid, s = _book_with_text()
    _store(bid, sid, s, "Alt.", run_id="r1")
    _store(bid, sid, s, "Neu.", source="agent", author="Buch — Lektor")
    old = _replaced.history(PROJECT_ID, bid, "text", sid)[0]
    back = proposals.restore(PROJECT_ID, bid, sid, old["id"])
    assert back["text"] == "Alt." and back["source"] == "run"
    assert proposals.get(PROJECT_ID, bid, sid)["text"] == "Alt."
    hist = _replaced.history(PROJECT_ID, bid, "text", sid)
    assert len(hist) == 1 and _replaced.get(PROJECT_ID, bid, "text", sid, hist[0]["id"])["text"] == "Neu."
    assert hist[0]["reason"] == "replaced" and hist[0]["replaced_by"] == "zurückgeholt"


def test_restore_without_open_proposal():
    bid, sid, s = _book_with_text()
    _store(bid, sid, s, "Weg und wieder da.")
    proposals.discard(PROJECT_ID, bid, sid)
    h = _replaced.history(PROJECT_ID, bid, "text", sid)[0]
    proposals.restore(PROJECT_ID, bid, sid, h["id"])
    assert proposals.get(PROJECT_ID, bid, sid)["text"] == "Weg und wieder da."
    assert _replaced.history(PROJECT_ID, bid, "text", sid) == []


@pytest.mark.parametrize("bad", ["../x", "20261008T", "x" * 30, "", "20261008T220000000000/.."])
def test_bad_history_ids_are_404(bad):
    bid, sid, _s = _book_with_text()
    with pytest.raises(StoryError) as e:
        _replaced.get(PROJECT_ID, bid, "text", sid, bad)
    assert e.value.status == 404


def test_unknown_kind_is_rejected():
    bid, sid, _s = _book_with_text()
    with pytest.raises(StoryError):
        _replaced.history(PROJECT_ID, bid, "../etc", sid)
