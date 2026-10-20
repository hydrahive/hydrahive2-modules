"""Aufräumen verwaister Fälle (Plan L2 Schritt 6, Spec §4.2): Projekt gelöscht → Fall verwaist; nach 30 Tagen JSON-
Sicherung nach data_dir/legal/archive/ und Löschen der Fallzeilen – vorher nicht."""
from __future__ import annotations

import json
import stat
from datetime import UTC, datetime, timedelta

import pytest
from backend import casefile, cases, orphans


@pytest.fixture(autouse=True)
def _tools(monkeypatch):
    from backend.tools import TOOLS
    from hydrahive.tools import REGISTRY
    for t in TOOLS:
        monkeypatch.setitem(REGISTRY, t.name, t)


def _rows(pid: str) -> int:
    from hydrahive.db.connection import db
    with db() as c:
        return sum(c.execute(f"SELECT count(*) FROM {t} WHERE project_id = ?", (pid,)).fetchone()[0]
                   for t in ("module_legal_cases", "module_legal_parties", "module_legal_deadlines",
                             "module_legal_notes", "module_legal_proposals"))


def _orphan_case():
    from hydrahive.projects import config as pc
    pid = cases.create_case("alice", {"title": "Alter Fall", "state": "BY"}, model="claude-sonnet-4-6")["project_id"]
    casefile.add_party(pid, {"role": "opponent", "name": "Gegner"})
    casefile.add_deadline(pid, {"label": "F", "event_date": "2026-11-02", "kind": "weeks", "amount": 1})
    casefile.propose(pid, "fact", {"text": "X"}, author_name="A")
    pc.delete(pid)
    return pid


def test_live_case_is_left_alone():
    from hydrahive.projects import config as pc
    pid = cases.create_case("alice", {"title": "Lebt", "state": "NW"}, model="claude-sonnet-4-6")["project_id"]
    try:
        assert orphans.sweep(now=datetime.now(UTC) + timedelta(days=400)) == {"marked": 0, "archived": 0}
        assert cases.get_case(pid) is not None
    finally:
        pc.delete(pid)


def test_deleted_project_is_marked_then_archived_after_30_days(setup_test_env):
    pid = _orphan_case()
    t0 = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
    assert orphans.sweep(now=t0) == {"marked": 1, "archived": 0}
    assert cases.get_case(pid) is None                                       # verwaist = für Routen/Werkzeuge weg
    assert _rows(pid) == 4                                                   # Daten noch da
    assert orphans.sweep(now=t0 + timedelta(days=29, hours=23)) == {"marked": 0, "archived": 0}
    assert _rows(pid) == 4
    assert orphans.sweep(now=t0 + timedelta(days=30, seconds=1)) == {"marked": 0, "archived": 1}
    assert _rows(pid) == 0
    files = list((setup_test_env / "data" / "legal" / "archive").glob(f"*{pid}*.json"))
    assert len(files) == 1
    assert stat.S_IMODE(files[0].stat().st_mode) == 0o600
    data = json.loads(files[0].read_text())
    assert data["case"]["title"] == "Alter Fall" and data["parties"][0]["name"] == "Gegner"
    assert len(data["deadlines"]) == 1 and len(data["proposals"]) == 1


def test_recreated_project_id_unmarks(monkeypatch):
    """Taucht das Projekt wieder auf (z. B. aus dem Archiv zurückgeholt), wird die Markierung aufgehoben."""
    from hydrahive.db.connection import db
    pid = _orphan_case()
    orphans.sweep(now=datetime(2026, 10, 20, tzinfo=UTC))
    monkeypatch.setattr(orphans, "_project_exists", lambda p: p == pid)
    assert orphans.sweep(now=datetime(2026, 12, 1, tzinfo=UTC)) == {"marked": 0, "archived": 0}
    with db() as c:
        assert c.execute("SELECT orphaned_at FROM module_legal_cases WHERE project_id = ?", (pid,)).fetchone()[0] is None
    monkeypatch.undo()
    orphans.sweep(now=datetime(2026, 12, 1, tzinfo=UTC))
    orphans.sweep(now=datetime(2027, 1, 2, tzinfo=UTC))
    assert _rows(pid) == 0


def test_archive_write_failure_keeps_rows(monkeypatch):
    pid = _orphan_case()
    orphans.sweep(now=datetime(2026, 10, 20, tzinfo=UTC))

    def boom(*a, **k):
        raise OSError("Platte voll")
    monkeypatch.setattr(orphans, "_write_archive", boom)
    with pytest.raises(OSError):
        orphans.sweep(now=datetime(2026, 12, 1, tzinfo=UTC))
    assert _rows(pid) == 4
