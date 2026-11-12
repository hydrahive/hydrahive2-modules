"""Textdarstellung für den Agenten: Zeiten müssen eindeutig sein."""
from __future__ import annotations

STAMP = "2026-11-12T02:00:15.123456Z"


def _idea(**over) -> dict:
    return {
        "id": "aaaa1111-0000-4000-8000-000000000001", "title": "Wetterstation", "body": "Text",
        "status": "new", "origin": "user", "project_id": None, "created_at": STAMP, "updated_at": STAMP, **over,
    }


def test_zeiten_sind_als_utc_gekennzeichnet():
    from backend import render

    notes = [{"author": "agent", "agent_name": None, "body": "Hinweis", "created_at": STAMP}]
    text = render.render_idea(_idea(), notes, None)
    assert "Angelegt: 2026-11-12 02:00 UTC, geändert: 2026-11-12 02:00 UTC" in text
    assert "- [2026-11-12 02:00 UTC] Agent: Hinweis" in text


def test_listenzeile_nennt_nur_das_datum():
    from backend import render

    line = render.summary_line({**_idea(), "note_count": 0}, None)
    assert line.endswith("geändert 2026-11-12")
    assert "UTC" not in line
