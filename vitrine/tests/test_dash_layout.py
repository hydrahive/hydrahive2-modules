"""S4 Anordnung der Statuszentrale: eine Prüfung für Server, Dienst und Seite (SPEC-STATUSZENTRALE.md, S4)."""
from __future__ import annotations

import json

import pytest

from renderer import config, dash_layout as dl

S2 = {"tasks_user": "till", "github_project": "Hydrahive DEV", "github_repos": ["hydrahive/hydrahive2.0"]}


def test_standard():
    d = dl.normalize({})
    assert d["order"] == ["messages", "home", "hydra", "tasks", "github", "machine", "mining"]
    assert d["hidden"] == [] and d["messages_max"] == 3 and d["home_rooms"] == [] and d["mining_in_machine"] is True
    assert d["tasks_user"] == "till" and d["github_project"] == "Hydrahive DEV"


def test_alte_s2_config_bleibt_gueltig_und_wird_ergaenzt(tmp_path):
    (tmp_path / "config.json").write_text(json.dumps({"dashboard": dict(S2, tasks_user="anna")}))
    d = config.load(tmp_path)["dashboard"]
    assert d["tasks_user"] == "anna" and d["github_repos"] == ["hydrahive/hydrahive2.0"]
    assert d["messages_max"] == 3 and d["order"][0] == "messages"


def test_fehlende_bereiche_werden_hinten_angehaengt():
    d = dl.normalize(dict(S2, order=["machine", "messages"]))
    assert d["order"][:2] == ["machine", "messages"] and set(d["order"]) == set(dl.AREAS) and len(d["order"]) == len(dl.AREAS)


@pytest.mark.parametrize("bad", [
    {"order": ["messages", "messages"]},
    {"order": ["messages", "laser"]},
    {"hidden": ["laser"]},
    {"hidden": "home"},
    {"messages_max": 0}, {"messages_max": 6}, {"messages_max": True}, {"messages_max": "3"},
    {"home_rooms": ["x" * 61]}, {"home_rooms": ["a"] * 21}, {"home_rooms": "Küche"}, {"home_rooms": ["<b>"]},
    {"mining_in_machine": "ja"},
    {"token": "x"},
    {"tasks_user": "a b"},
])
def test_ungueltig(bad):
    assert dl.layout_ok(dict(S2, **bad)) is False


def test_gueltig_voll():
    d = dict(S2, order=list(reversed(dl.AREAS)), hidden=["mining", "github"], messages_max=5,
             home_rooms=["Wohnzimmer", "Alex Zimmer"], mining_in_machine=False)
    assert dl.layout_ok(d) is True and dl.normalize(d)["hidden"] == ["mining", "github"]


def test_ungueltige_datei_faellt_auf_standard(tmp_path):
    (tmp_path / "config.json").write_text(json.dumps({"dashboard": dict(S2, order=["messages", "messages"])}))
    assert config.load(tmp_path)["dashboard"] == dl.normalize({})


def test_schema_prueft_gleich():
    pytest.importorskip("pydantic")
    from pydantic import ValidationError
    from backend.schemas import Config
    ok = Config(dashboard=dict(S2, order=["home", "messages"], messages_max=2)).dump()["dashboard"]
    assert ok["order"][:2] == ["home", "messages"] and ok["messages_max"] == 2 and len(ok["order"]) == len(dl.AREAS)
    for bad in ({"messages_max": 9}, {"order": ["x"]}, {"hidden": ["x"]}, {"token": "x"}):
        with pytest.raises(ValidationError):
            Config(dashboard=dict(S2, **bad))
