"""M3b: Stufe „Entwurf“ – mailbox_draft, mailbox_move, mailbox_flag. Agent ändert nur eigene Entwürfe, löscht nie."""
# ruff: noqa: F811 - pytest-Fixtures aus _routes_base werden als gleichnamige Parameter genutzt
from __future__ import annotations

import asyncio

import pytest
from _fake_imap_write import FakeIMAPW
from _routes_base import acc, alice, client, fake_net, rights  # noqa: F401


@pytest.fixture
def project():
    from hydrahive.projects import config as pc
    p = pc.create("Mail-Projekt", llm_model="m", created_by="alice", members=[{"username": "bob", "role": "write"}])
    yield p["id"]
    pc.delete(p["id"])


@pytest.fixture(autouse=True)
def writable(monkeypatch, fake_net):
    from backend import sync_job
    monkeypatch.setattr(sync_job, "_open", lambda a: FakeIMAPW(fake_net, caps=("MOVE", "UIDPLUS", "UNSELECT")))


def _ctx(tmp_path, user="alice", project_id=None):
    from hydrahive.tools.base import ToolContext
    return ToolContext(session_id="s1", agent_id="ag1", user_id=user, workspace=tmp_path, project_id=project_id)


def _run(name, args, ctx):
    from backend import agent_tools
    tool = next(t for t in agent_tools.TOOLS if t.name == name)
    return asyncio.run(tool.execute(args, ctx))


def _share(acc_id, target, level):
    from backend import shares
    shares.put("alice", acc_id, target, level)


def _mid(ctx, subject):
    return _run("mailbox_search", {"query": f'betreff:"{subject}"'}, ctx).output["items"][0]["id"]


def test_stufe_lesen_darf_nichts_aendern(acc, project, tmp_path):
    _share(acc["id"], f"project:{project}", "read")
    ctx = _ctx(tmp_path, project_id=project)
    mid = _mid(ctx, "Re: Unterlagen")
    for name, args in (("mailbox_draft", {"account_id": acc["id"], "to": "a@x.de", "subject": "s", "body": "b"}),
                       ("mailbox_flag", {"message_ids": [mid], "action": "flag"}),
                       ("mailbox_move", {"message_ids": [mid], "folder": "Gesendet"})):
        r = _run(name, args, ctx)
        assert not r.success and "Entwurf" in r.error, name


def test_entwurf_anlegen_erscheint_beim_besitzer(acc, project, tmp_path):
    from backend import drafts
    _share(acc["id"], f"project:{project}", "draft")
    ctx = _ctx(tmp_path, user="bob", project_id=project)              # bob arbeitet im Projekt, Konto gehört alice
    r = _run("mailbox_draft", {"account_id": acc["id"], "to": "Anna <anna@example.org>", "subject": "Termin",
                               "body": "Hallo Anna"}, ctx)
    assert r.success, r.error
    mine = drafts.list_for("alice")
    assert [d["subject"] for d in mine] == ["Termin"] and mine[0]["id"] == r.output["draft_id"]
    assert drafts.list_for("bob") == []
    assert "gesendet" in r.output["note"].lower()                     # Hinweis: nicht gesendet


def test_antwort_entwurf_mit_vorlage(acc, project, tmp_path):
    _share(acc["id"], f"project:{project}", "draft")
    ctx = _ctx(tmp_path, project_id=project)
    mid = _mid(ctx, "Re: Unterlagen")
    r = _run("mailbox_draft", {"account_id": acc["id"], "mode": "reply", "ref_message": mid, "body": "Danke!"}, ctx)
    assert r.success, r.error
    from backend import drafts
    d = drafts.get("alice", r.output["draft_id"])
    assert d["to"].endswith("<post@kanzlei.example>") and d["subject"] == "Re: Unterlagen"
    assert d["body"].startswith("Danke!") and "> " in d["body"]        # Zitat des Originals darunter


def test_nur_eigene_entwuerfe_aendern(acc, project, tmp_path):
    from backend import drafts
    _share(acc["id"], f"project:{project}", "draft")
    own = drafts.save("alice", acc, {"to": "x@y.de", "subject": "Privat", "body": "geheim"})   # vom Menschen
    ctx = _ctx(tmp_path, project_id=project)
    r = _run("mailbox_draft", {"account_id": acc["id"], "draft_id": own["id"], "subject": "überschrieben"}, ctx)
    assert not r.success and drafts.get("alice", own["id"])["subject"] == "Privat"
    made = _run("mailbox_draft", {"account_id": acc["id"], "subject": "v1", "body": "x"}, ctx).output["draft_id"]
    r = _run("mailbox_draft", {"account_id": acc["id"], "draft_id": made, "subject": "v2", "body": "y"}, ctx)
    assert r.success and drafts.get("alice", made)["subject"] == "v2"


def test_anderes_projekt_darf_agenten_entwurf_nicht_aendern(acc, project, tmp_path):
    from hydrahive.projects import config as pc
    _share(acc["id"], f"project:{project}", "draft")
    made = _run("mailbox_draft", {"account_id": acc["id"], "subject": "v1"}, _ctx(tmp_path, project_id=project))
    other = pc.create("Anders", llm_model="m", created_by="alice")
    try:
        _share(acc["id"], f"project:{other['id']}", "draft")
        r = _run("mailbox_draft", {"account_id": acc["id"], "draft_id": made.output["draft_id"], "subject": "x"},
                 _ctx(tmp_path, project_id=other["id"]))
        assert not r.success
    finally:
        pc.delete(other["id"])


def test_markieren_und_verschieben(acc, project, tmp_path, fake_net):
    _share(acc["id"], f"project:{project}", "draft")
    ctx = _ctx(tmp_path, project_id=project)
    mid = _mid(ctx, "Re: Unterlagen")
    r = _run("mailbox_flag", {"message_ids": [mid], "action": "flag"}, ctx)
    assert r.success and r.output == {"done": 1, "skipped": 0}
    assert _run("mailbox_search", {"query": "Unterlagen"}, ctx).output["items"][0]["flagged"] == 1
    r = _run("mailbox_move", {"message_ids": [mid], "folder": "Gesendet"}, ctx)
    assert r.success and r.output["done"] == 1
    assert any(b"Unterlagen" in raw for raw, _ in fake_net.boxes["Gesendet"].msgs.values())
    assert not any(b"Unterlagen" in raw for raw, _ in fake_net.boxes["INBOX"].msgs.values())
    assert fake_net.full_expunges == 0                                  # nie pauschal EXPUNGE


def test_eingaben_und_fremde_mails(acc, project, tmp_path):
    _share(acc["id"], f"project:{project}", "draft")
    ctx = _ctx(tmp_path, project_id=project)
    mid = _mid(ctx, "Re: Unterlagen")
    assert not _run("mailbox_flag", {"message_ids": [mid], "action": "delete"}, ctx).success      # nie löschen
    assert not _run("mailbox_move", {"message_ids": [mid], "folder": "Gibtsnicht"}, ctx).success
    assert not _run("mailbox_move", {"message_ids": [], "folder": "Gesendet"}, ctx).success
    r = _run("mailbox_flag", {"message_ids": [999999], "action": "seen"}, ctx)
    assert r.success and r.output == {"done": 0, "skipped": 1}                                    # fremd = still
    assert not _run("mailbox_draft", {"account_id": "fremd", "subject": "x"}, ctx).success


def test_protokoll(acc, project, tmp_path):
    from hydrahive.db.connection import db
    _share(acc["id"], f"project:{project}", "draft")
    ctx = _ctx(tmp_path, project_id=project)
    mid = _mid(ctx, "Re: Unterlagen")
    _run("mailbox_flag", {"message_ids": [mid], "action": "seen"}, ctx)
    _run("mailbox_draft", {"account_id": acc["id"], "subject": "Geheimer Betreff"}, ctx)
    with db() as c:
        rows = [dict(r) for r in c.execute("SELECT tool, result, account_id FROM module_mailbox_audit "
                                           "WHERE tool IN ('mailbox_flag','mailbox_draft') ORDER BY id")]
    assert [(r["tool"], r["result"]) for r in rows] == [("mailbox_flag", "ok"), ("mailbox_draft", "ok")]
    assert all(r["account_id"] == acc["id"] for r in rows) and "Geheimer" not in str(rows)


def test_webmail_kennzeichnet_agenten_entwurf(client, alice, acc, project, tmp_path):
    from _routes_base import B
    from backend import drafts
    _share(acc["id"], f"project:{project}", "draft")
    made = _run("mailbox_draft", {"account_id": acc["id"], "subject": "Vom Agenten"}, _ctx(tmp_path, project_id=project))
    drafts.save("alice", acc, {"subject": "Von mir"})
    got = {d["subject"]: d["by_agent"] for d in client.get(f"{B}/drafts", headers=alice).json()}
    assert got == {"Vom Agenten": True, "Von mir": False} and made.success


def test_freigabe_stufe_ueber_route_umstellen(client, alice, acc, project):
    from _routes_base import B
    t = f"project:{project}"
    assert client.put(f"{B}/accounts/{acc['id']}/shares", json={"target": t, "level": "draft"}, headers=alice).json()[
        "level"] == "draft"
    assert client.put(f"{B}/accounts/{acc['id']}/shares", json={"target": t, "level": "read"}, headers=alice).json()[
        "level"] == "read"
    assert client.put(f"{B}/accounts/{acc['id']}/shares", json={"target": t, "level": "send"},
                      headers=alice).status_code == 422
