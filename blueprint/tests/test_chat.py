"""Chat neben dem Board (Etappe 3b): Agent, Rechte, Sitzung je Board, fehlende Werkzeuge, Einstiegstext."""
from __future__ import annotations

import json

import pytest
from backend import chat, store
from conftest import PROJECT_A, PROJECT_B

BASE = "/api/modules/blueprint/boards"
TOOLS = ["blueprint_read", "blueprint_propose", "idea_read"]


def _h(client, user="other"):
    r = client.post("/api/auth/login", json={"username": user, "password": "testpass123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _code(response) -> str:
    return response.json()["detail"]["code"]


@pytest.fixture(autouse=True)
def _sessions_cleanup():
    from _hh_isolation import only_own_rows

    with only_own_rows("sessions"):
        yield


@pytest.fixture
def project_agent(setup_test_env, monkeypatch):
    """Projekt-Agent für PROJECT_A mit den drei Werkzeugen; ``other`` ist dort Mitglied mit Leserecht."""
    from hydrahive.agents import config as agent_config
    from hydrahive.tools import REGISTRY

    for name in TOOLS:
        monkeypatch.setitem(REGISTRY, name, REGISTRY.get(name) or object())
    agent = agent_config.create(agent_type="project", name="Projekt-Agent A", llm_model="test/model", tools=list(TOOLS),
                                owner="testuser", created_by="testuser", project_id=PROJECT_A,
                                temperature=1.0, max_tokens=16000, thinking_budget=0)
    path = setup_test_env / "data" / "projects" / PROJECT_A / "config.json"
    before = path.read_text(encoding="utf-8")
    config = json.loads(before)
    config.update(agent_id=agent["id"], members=[{"username": "testuser", "role": "admin"},
                                                 {"username": "other", "role": "read"}])
    path.write_text(json.dumps(config), encoding="utf-8")
    yield agent
    path.write_text(before, encoding="utf-8")
    agent_config.delete(agent["id"])


def _board(user="testuser", project=PROJECT_A, name="Admin-Seite") -> int:
    return store.create(user, name, project_id=project)["id"]


def test_board_ohne_projekt_hat_keinen_chat(client, auth_headers, project_agent):
    bid = _board(project=None)
    info = client.get(f"{BASE}/{bid}/chat", headers=auth_headers).json()
    assert info == {"agent": None, "reason": "no_project", "can_start": False, "tools_missing": []}
    r = client.post(f"{BASE}/{bid}/chat", headers=auth_headers)
    assert r.status_code == 409 and _code(r) == "board_without_project"


def test_mit_projekt_antwortet_der_projekt_agent(client, auth_headers, project_agent):
    info = client.get(f"{BASE}/{_board()}/chat", headers=auth_headers).json()
    assert info == {"agent": {"id": project_agent["id"], "name": "Projekt-Agent A"}, "reason": None,
                    "can_start": True, "tools_missing": []}


def test_sitzung_je_board_wird_wiederverwendet(client, auth_headers, project_agent):
    from hydrahive.db import sessions as sessions_db

    bid, second_board = _board(), _board(name="Zweites Board")
    first = client.post(f"{BASE}/{bid}/chat", headers=auth_headers)
    assert first.status_code == 200, first.text
    data = first.json()
    assert data["reused"] is False and data["agent"]["id"] == project_agent["id"]
    session = sessions_db.get(data["session_id"])
    assert (session.agent_id, session.user_id, session.project_id) == (project_agent["id"], "testuser", PROJECT_A)
    assert session.metadata == {"blueprint_board": bid, "embedded_in": "blueprint"}
    assert session.title == "Blueprint: Admin-Seite"
    again = client.post(f"{BASE}/{bid}/chat", headers=auth_headers).json()
    assert again["reused"] is True and again["session_id"] == data["session_id"]
    other = client.post(f"{BASE}/{second_board}/chat", headers=auth_headers).json()
    assert other["reused"] is False and other["session_id"] != data["session_id"]


def test_ohne_schreibrecht_im_projekt_kein_start(client, project_agent):
    headers = _h(client)
    bid = _board(user="other")
    info = client.get(f"{BASE}/{bid}/chat", headers=headers).json()
    assert info["agent"]["id"] == project_agent["id"] and info["can_start"] is False and info["reason"] == "read_only"
    r = client.post(f"{BASE}/{bid}/chat", headers=headers)
    assert r.status_code == 403 and _code(r) == "project_read_only"


def test_projekt_ohne_zugriff_oder_ohne_agent(client, auth_headers, project_agent):
    # Das Board trägt noch ein Projekt, das der Nutzer nicht (mehr) sehen darf.
    foreign = _board(project=PROJECT_B)
    info = client.get(f"{BASE}/{foreign}/chat", headers=auth_headers).json()
    assert (info["agent"], info["reason"], info["can_start"]) == (None, "project_missing", False)
    assert client.post(f"{BASE}/{foreign}/chat", headers=auth_headers).status_code == 409
    # PROJECT_B hat keinen Agenten: sein Besitzer bekommt das gesagt.
    headers = _h(client)
    own = _board(user="other", project=PROJECT_B)
    info = client.get(f"{BASE}/{own}/chat", headers=headers).json()
    assert (info["agent"], info["reason"], info["can_start"]) == (None, "no_agent", False)
    r = client.post(f"{BASE}/{own}/chat", headers=headers)
    assert r.status_code == 409 and _code(r) == "project_agent_missing"


def test_fehlende_werkzeuge_werden_gemeldet(client, auth_headers, project_agent, monkeypatch):
    from hydrahive.agents import config as agent_config
    from hydrahive.tools import REGISTRY

    agent_config.update(project_agent["id"], tools=["blueprint_read"])
    bid = _board()
    missing = client.get(f"{BASE}/{bid}/chat", headers=auth_headers).json()["tools_missing"]
    assert missing == ["blueprint_propose", "idea_read"]
    # Ist das Ideen-Modul nicht installiert, gibt es idea_read nicht: dann fehlt es auch nicht.
    monkeypatch.delitem(REGISTRY, "idea_read")
    assert client.get(f"{BASE}/{bid}/chat", headers=auth_headers).json()["tools_missing"] == ["blueprint_propose"]


def test_fremdes_board_und_ohne_anmeldung(client, auth_headers, project_agent):
    bid = _board()
    other = _h(client)
    for response in (client.get(f"{BASE}/{bid}/chat", headers=other), client.post(f"{BASE}/{bid}/chat", headers=other)):
        assert response.status_code == 404 and _code(response) == "board_not_found"
    assert client.get(f"{BASE}/{bid}/chat").status_code in (401, 403)
    assert client.post(f"{BASE}/{bid}/chat").status_code in (401, 403)


def test_einstiegstext_nennt_board_und_werkzeuge(client, auth_headers, project_agent):
    bid = _board(name="Admin-Seite\nzweite Zeile")
    intro = client.post(f"{BASE}/{bid}/chat", headers=auth_headers).json()["intro"]
    assert f"Board „Admin-Seite zweite Zeile“ (ID {bid})" in intro
    assert "blueprint_read" in intro and "blueprint_propose" in intro
    assert "Idee" not in intro and intro.rstrip().endswith("Meine Bitte:")


def test_einstiegstext_nennt_die_idee_zum_board(auth_headers):
    from hydrahive.db.connection import db

    board = store.get("testuser", _board())
    table = "module_scratchpad_ideas"
    assert chat.linked_idea("testuser", board["id"]) is None  # ohne Ideen-Modul gibt es die Tabelle nicht
    with db() as conn:
        conn.execute(f"CREATE TABLE {table} (id TEXT PRIMARY KEY, username TEXT, title TEXT, board_id INTEGER)")
        conn.execute(f"INSERT INTO {table} VALUES ('idee-eins', 'testuser', 'Alles\nzentral', ?)", (board["id"],))
        conn.execute(f"INSERT INTO {table} VALUES ('idee-fremd', 'other', 'Geheim', ?)", (board["id"],))
    try:
        assert chat.linked_idea("testuser", board["id"]) == {"id": "idee-eins", "title": "Alles zentral"}
        intro = chat.intro(board, chat.linked_idea("testuser", board["id"]))
        assert "Idee „Alles zentral“ (idea_id idee-eins)" in intro and "idea_read" in intro
        assert "Geheim" not in intro
        assert chat.linked_idea("other", board["id"]) == {"id": "idee-fremd", "title": "Geheim"}
    finally:
        with db() as conn:
            conn.execute(f"DROP TABLE {table}")


def test_projektrechte_fuer_den_chat(project_agent):
    """PROJECT_A: testuser hat es angelegt, other liest nur. PROJECT_B gehört other, testuser ist kein Mitglied."""
    from backend import access

    def state(user: str, role: str, project: str | None) -> str:
        return access.project_state(user, role, project)[1]

    assert state("testuser", "user", PROJECT_A) == "ok"
    assert state("other", "user", PROJECT_A) == "read_only"
    assert state("testuser", "user", PROJECT_B) == "missing"
    # Der System-Admin darf in jedem Projekt, auch ohne Mitglied zu sein (wie im Kern).
    assert state("testuser", "admin", PROJECT_B) == "ok"
    assert state("other", "admin", PROJECT_A) == "ok"
    # Unbekannte und unsaubere IDs sehen aus wie fehlender Zugriff, auch für den Admin.
    for project in ("gibt-es-nicht-projekt", "../../etc", "", None):
        assert access.project_state("testuser", "admin", project) == (None, "missing"), project
    assert access.project_state("testuser", "user", PROJECT_B)[0] is None  # nichts über fremde Projekte verraten
