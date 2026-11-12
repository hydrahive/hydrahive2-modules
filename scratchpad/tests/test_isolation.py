"""Das Test-Gerüst darf nie auf echte Daten zeigen."""
from __future__ import annotations

from _hh_isolation import TEST_ROOT


def test_data_dir_liegt_im_testverzeichnis():
    from hydrahive.settings import settings

    assert TEST_ROOT.resolve() in settings.data_dir.resolve().parents
    assert TEST_ROOT.resolve() in settings.sessions_db.resolve().parents


def test_tabellen_sind_angelegt():
    from hydrahive.db.connection import db

    with db() as conn:
        names = {
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'module_scratchpad_%'"
            )
        }
    assert names == {"module_scratchpad_ideas", "module_scratchpad_idea_notes"}
