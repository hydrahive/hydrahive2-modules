"""PUT /config speichert die neuen Feiertagsarten vollständig (Felder gehen nicht verloren) und lehnt Unsinn ab."""
from __future__ import annotations

import pytest

pytest.importorskip("pydantic")
from backend.schemas import Config  # noqa: E402

from renderer import calendar as cal  # noqa: E402


def _rule(**kw):
    return {"id": "a", "name": "X", "enabled": True, "priority": 45, "videos": ["x.mp4"], **kw}


def test_neue_arten_bleiben_vollstaendig_erhalten():
    rules = [_rule(kind="advent_sunday", n=2),
             _rule(kind="nth_weekday", month=5, weekday=6, n=2),
             _rule(kind="nth_weekday", month=5, weekday=0, n=-1, days=2),
             _rule(kind="dates", dates=[{"from": "2026-12-04", "to": "2026-12-12"}])]
    saved = Config(rules=rules).dump()["rules"]
    assert saved[0]["n"] == 2
    assert {k: saved[1][k] for k in ("month", "weekday", "n")} == {"month": 5, "weekday": 6, "n": 2} and "days" not in saved[1]
    assert saved[2]["days"] == 2 and saved[2]["n"] == -1
    assert saved[3]["dates"] == [{"from": "2026-12-04", "to": "2026-12-12"}]


def test_fremde_felder_werden_nicht_gespeichert():
    saved = Config(rules=[_rule(kind="advent_sunday", n=1, boese="x", dates=[{"from": "x"}])]).dump()["rules"][0]
    assert "boese" not in saved and "dates" not in saved


@pytest.mark.parametrize("bad", [
    _rule(kind="advent_sunday", n=9),
    _rule(kind="nth_weekday", month=5, weekday=6, n=0),
    _rule(kind="dates", dates=[{"from": "2026-12-12", "to": "2026-12-04"}]),
])
def test_ungueltig_abgelehnt(bad):
    with pytest.raises(ValueError):
        Config(rules=[bad])


def test_alle_vorlagen_lassen_sich_speichern():
    rules = [{**t, "id": str(i), "enabled": True, "videos": []} for i, t in enumerate(cal.TEMPLATES)]
    saved = Config(rules=rules).dump()["rules"]
    for t, s in zip(cal.TEMPLATES, saved):
        for k, v in t.items():
            assert s[k] == v, (t["name"], k)
