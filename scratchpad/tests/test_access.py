"""Projektzugriff: das Projekt ist eine Zuordnung, aber nur zu Projekten, die der Nutzer sehen darf."""
from __future__ import annotations

import pytest
from helpers import PROJECT_A, PROJECT_B


def _check(username: str, role: str, project_id):
    from backend import access
    return access.check_project(username, role, project_id)


def _code(excinfo) -> str:
    return excinfo.value.code


def test_mitglied_darf():
    assert _check("alice", "user", PROJECT_A) == PROJECT_A


def test_fremder_bekommt_project_not_found():
    from backend.store import IdeaError
    with pytest.raises(IdeaError) as excinfo:
        _check("alice", "user", PROJECT_B)
    assert _code(excinfo) == "project_not_found"


def test_system_admin_darf_jedes_projekt():
    assert _check("root", "admin", PROJECT_B) == PROJECT_B


@pytest.mark.parametrize("empty", [None, "", "   "])
def test_ohne_projekt_ist_erlaubt(empty):
    assert _check("alice", "user", empty) is None


@pytest.mark.parametrize("bad", ["gibt-es-nicht-1234", "../../etc/passwd", "a/b/c/d/e/f/g/h", "kurz", "x" * 65, "..%2f..%2fetc"])
def test_unbekannte_oder_ungueltige_projekt_id(bad):
    from backend.store import IdeaError
    with pytest.raises(IdeaError) as excinfo:
        _check("root", "admin", bad)
    assert _code(excinfo) == "project_not_found"


def test_rolle_eines_nutzers_per_name():
    from backend import access
    assert access.system_role("root") == "admin"
    assert access.system_role("alice") == "user"
    assert access.system_role("niemand") == "user"
    assert access.system_role("") == "user"


def test_projektnamen_fuer_die_anzeige():
    from backend import access
    names = access.project_names("alice", "user")
    assert names == {PROJECT_A: "Projekt alice"}
    assert set(access.project_names("root", "admin")) >= {PROJECT_A, PROJECT_B}
