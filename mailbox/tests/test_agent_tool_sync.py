"""Befund 23.10.: default_agent_tools hängt Modul-Werkzeuge nur an Master-Agenten. Ein Projekt-Agent (z. B. der
Rechts-Agent) bekam die Mailbox-Werkzeuge trotz Freigabe nie. Ab 0.7.1: Freigabe ändert die Werkzeuge des
Projekt-Agenten passend zur höchsten Stufe aller Freigaben dieses Projekts; ohne Freigabe kommen sie wieder weg."""
from __future__ import annotations

import pytest

READ = {"mailbox_accounts", "mailbox_search", "mailbox_read", "mailbox_attachment"}
DRAFT = {"mailbox_draft", "mailbox_move", "mailbox_flag"}


def _acc(user: str, address: str) -> str:
    from hydrahive.db._utils import now_iso
    from hydrahive.db.connection import db
    aid = "acc-" + address.split("@")[0]
    with db() as c:
        c.execute("INSERT INTO module_mailbox_accounts(id, owner, label, address, imap_host, username, secret, "
                  "status, created_at, updated_at) VALUES (?,?,?,?,?,?,?, 'ok', ?, ?)",
                  (aid, f"user:{user}", address, address, "imap.example.net", address, "x", now_iso(), now_iso()))
    return aid


@pytest.fixture
def project():
    from hydrahive.projects import config as pc
    p = pc.create("Mail-Projekt", llm_model="m", created_by="alice", members=[{"username": "bob", "role": "write"}])
    yield p
    pc.delete(p["id"])


def _tools(project) -> set[str]:
    from hydrahive.agents import config as ac
    return set(ac.get(project["agent_id"])["tools"])


@pytest.fixture(autouse=True)
def registered():
    """Die Werkzeuge müssen im Kern bekannt sein (wie nach dem Laden des Moduls)."""
    from backend.agent_tools import TOOLS
    from hydrahive.tools import REGISTRY
    added = [t for t in TOOLS if t.name not in REGISTRY]
    for t in added:
        REGISTRY[t.name] = t
    yield
    for t in added:
        REGISTRY.pop(t.name, None)


def test_freigabe_lesen_gibt_lesewerkzeuge(project):
    from backend import shares
    before = _tools(project)
    shares.put("alice", _acc("alice", "alice@example.net"), f"project:{project['id']}", "read")
    after = _tools(project)
    assert READ <= after and not (DRAFT & after) and before <= after      # nichts Bestehendes entfernt


def test_stufe_entwurf_und_zurueck(project):
    from backend import shares
    aid = _acc("alice", "alice@example.net")
    t = f"project:{project['id']}"
    shares.put("alice", aid, t, "draft")
    assert (READ | DRAFT) <= _tools(project)
    shares.put("alice", aid, t, "read")
    assert READ <= _tools(project) and not (DRAFT & _tools(project))


def test_zuruecknehmen_entfernt_nur_wenn_keine_freigabe_mehr(project):
    from backend import shares
    from hydrahive.projects import config as pc
    t = f"project:{project['id']}"
    a1, a2 = _acc("alice", "alice@example.net"), _acc("bob", "bob@example.net")
    shares.put("alice", a1, t, "draft")
    shares.put("bob", a2, t, "read")
    shares.remove("alice", a1, t)
    assert READ <= _tools(project) and not (DRAFT & _tools(project))      # bobs Freigabe zählt noch
    shares.remove("bob", a2, t)
    assert not ((READ | DRAFT) & _tools(project))
    assert pc.get(project["id"])                                            # Projekt unberührt


def test_konto_entfernen_raeumt_werkzeuge_ab(project):
    from backend import accounts, shares
    aid = _acc("alice", "alice@example.net")
    shares.put("alice", aid, f"project:{project['id']}", "draft")
    accounts.remove("alice", aid)
    assert not ((READ | DRAFT) & _tools(project))


def test_handgesetzte_fremde_werkzeuge_bleiben(project):
    from backend import shares
    from hydrahive.agents import config as ac
    ac.update(project["agent_id"], tools=[*ac.get(project["agent_id"])["tools"], "web_search"])
    aid = _acc("alice", "alice@example.net")
    t = f"project:{project['id']}"
    shares.put("alice", aid, t, "read")
    shares.remove("alice", aid, t)
    assert "web_search" in _tools(project)


def test_buddy_freigabe_aendert_keinen_projektagenten(project):
    from backend import shares
    before = _tools(project)
    shares.put("alice", _acc("alice", "alice@example.net"), "buddy", "draft")
    assert _tools(project) == before


def test_resync_beim_start_fuer_bestehende_freigaben(project):
    """Freigaben aus 0.6/0.7.0 bekommen ihre Werkzeuge beim nächsten Laden des Moduls nachgetragen."""
    from backend import agent_tool_sync
    from hydrahive.db._utils import now_iso
    from hydrahive.db.connection import db
    aid = _acc("alice", "alice@example.net")
    with db() as c:                                                         # wie vor dem Fix: nur die Zeile
        c.execute("INSERT INTO module_mailbox_shares(account_id, target, level, created_by, created_at) "
                  "VALUES (?,?,?,?,?)", (aid, f"project:{project['id']}", "draft", "alice", now_iso()))
    assert not ((READ | DRAFT) & _tools(project))
    agent_tool_sync.sync_all()
    assert (READ | DRAFT) <= _tools(project)


def test_geloeschtes_projekt_stoert_nicht(project):
    from backend import agent_tool_sync
    from hydrahive.db._utils import now_iso
    from hydrahive.db.connection import db
    aid = _acc("alice", "alice@example.net")
    with db() as c:
        c.execute("INSERT INTO module_mailbox_shares(account_id, target, level, created_by, created_at) "
                  "VALUES (?,?,?,?,?)", (aid, "project:00000000-dead-beef-0000-000000000000", "read", "alice", now_iso()))
    agent_tool_sync.sync_all()                                              # darf nicht werfen


def test_wie_der_runner_projekt_agent_sieht_die_werkzeuge(project, monkeypatch):
    """Genau der Weg aus runner.py: Agent-Config → scope_tools → access_filter_tools → schemas_for.
    Dieser Weg fehlte im Test von 0.6.0 – deshalb blieb der Fehler unentdeckt."""
    from backend import shares
    from conftest import MODULE_DIR
    from hydrahive.access import check
    from hydrahive.access.capabilities import catalog
    from hydrahive.access.tool_filter import filter_tools
    from hydrahive.agents import config as ac
    from hydrahive.modules.manifest import ModuleManifest
    from hydrahive.runner._project_tool_scope import scope_tools
    from hydrahive.tools import REGISTRY, schemas_for
    catalog().register_module(ModuleManifest.load(MODULE_DIR / "manifest.json"))
    for name in READ | DRAFT:
        REGISTRY[name].module_id = "mailbox"
    alice = check.user_id_for("alice")
    monkeypatch.setattr(check, "_levels", lambda uid: {"module.mailbox": "use"} if uid == alice else {})
    try:
        shares.put("alice", _acc("alice", "alice@example.net"), f"project:{project['id']}", "read")
        agent = ac.get(project["agent_id"])
        local, _ = scope_tools(project, list(agent["tools"]), [])
        seen = {s["name"] for s in schemas_for(filter_tools("alice", local))}
        assert READ <= seen and not (DRAFT & seen)
        assert not (READ & {s["name"] for s in schemas_for(filter_tools("bob", local))})   # bob ohne Modulrecht
    finally:
        catalog().unregister_module("mailbox")
