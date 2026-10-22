"""0.3.0: Aktionen „archivieren“ und „Spam“ (Spec §6) – verschieben in den Ordner mit Rolle archive bzw. junk des
jeweiligen Kontos. Ohne solchen Ordner: übersprungen, nichts passiert."""
from __future__ import annotations

import pytest
from _fake_imap import FakeServer
from _fake_imap_write import FakeIMAPW
from test_actions import _mid, _run, _subjects, _sync


@pytest.fixture
def srv():
    s = FakeServer()
    s.box("Archive", special="\\Archive")
    s.box("Bulk", special="\\Junk")
    for n in range(2):
        from _fetch_base import _mail
        s.boxes["INBOX"].add(_mail(n))
    return s


@pytest.mark.parametrize("action, box", [("archive", "Archive"), ("junk", "Bulk")])
def test_in_rollen_ordner(archive, srv, action, box):
    _sync(srv)
    r, _ = _run(srv, action, _mid(0))
    assert r == {"done": 1, "skipped": 0}
    assert _subjects(srv.boxes[box]) == ["Mail 0"] and _subjects(srv.boxes["INBOX"]) == ["Mail 1"]


def test_ohne_rollen_ordner_uebersprungen(archive):
    from _fetch_base import _mail
    s = FakeServer()
    s.boxes["INBOX"].add(_mail(0))
    _sync(s)
    r, _ = _run(s, "archive", _mid(0))
    assert r == {"done": 0, "skipped": 1} and len(s.boxes["INBOX"].msgs) == 1


def test_schon_im_archiv_kein_doppel(archive, srv):
    from _fetch_base import _mail
    srv.boxes["Archive"].add(_mail(5))
    _sync(srv)
    r, _ = _run(srv, "archive", _mid(5))
    assert r["done"] == 1 and len(srv.boxes["Archive"].msgs) == 1


def test_schema_kennt_die_neuen_aktionen():
    from backend.schemas_m2 import ActionIn
    for a in ("archive", "junk"):
        assert ActionIn(ids=[1], action=a).action == a
