"""M3a Schritt 3: Lese-Werkzeuge für Agenten – nur freigegebene Konten, Fremdinhalt markiert, Protokoll ohne Inhalt."""
# ruff: noqa: F811 - pytest-Fixtures aus _routes_base werden als gleichnamige Parameter genutzt
from __future__ import annotations

import asyncio

import pytest
from _routes_base import acc, alice, client, fake_net, rights  # noqa: F401


@pytest.fixture
def project():
    from hydrahive.projects import config as pc
    p = pc.create("Mail-Projekt", llm_model="m", created_by="alice")
    yield p["id"]
    pc.delete(p["id"])


def _ctx(tmp_path, user="alice", project_id=None):
    from hydrahive.tools.base import ToolContext
    return ToolContext(session_id="s1", agent_id="ag1", user_id=user, workspace=tmp_path, project_id=project_id)


def _run(name, args, ctx):
    from backend import agent_tools
    tool = next(t for t in agent_tools.TOOLS if t.name == name)
    return asyncio.run(tool.execute(args, ctx))


def _share(acc_id, target):
    from backend import shares
    shares.put("alice", acc_id, target, "read")


def test_ohne_freigabe_sieht_der_agent_nichts(acc, project, tmp_path):
    r = _run("mailbox_accounts", {}, _ctx(tmp_path, project_id=project))
    assert r.success and r.output["accounts"] == []
    r = _run("mailbox_search", {"query": "Unterlagen"}, _ctx(tmp_path, project_id=project))
    assert r.success and r.output["items"] == []


def test_freigegebenes_konto_suchen_und_lesen(acc, project, tmp_path):
    _share(acc["id"], f"project:{project}")
    ctx = _ctx(tmp_path, project_id=project)
    accs = _run("mailbox_accounts", {}, ctx).output["accounts"]
    assert [a["address"] for a in accs] == ["alice@example.net"]
    assert "password" not in str(accs) and "secret" not in str(accs)
    assert any(f["role"] == "inbox" for f in accs[0]["folders"])
    hits = _run("mailbox_search", {"query": "betreff:Unterlagen"}, ctx).output
    assert hits["total"] == 1
    item = hits["items"][0]
    assert item["subject"] == "Re: Unterlagen" and item["has_attachments"] is True
    mail = _run("mailbox_read", {"message_id": item["id"]}, ctx)
    assert mail.success
    text = mail.output
    assert text.startswith("<<<MAIL-INHALT") and text.rstrip().endswith("<<<ENDE MAIL-INHALT>>>")
    assert "Anbei" in text or "Unterlagen" in text
    assert "Vertrag ä.pdf" in text                               # Anhangsliste mit Index


def test_anderes_projekt_und_fremde_mail_unsichtbar(acc, project, tmp_path):
    from hydrahive.projects import config as pc
    _share(acc["id"], f"project:{project}")
    mid = _run("mailbox_search", {"query": "Unterlagen"}, _ctx(tmp_path, project_id=project)).output["items"][0]["id"]
    other = pc.create("Anders", llm_model="m", created_by="alice")
    try:
        ctx = _ctx(tmp_path, project_id=other["id"])
        assert _run("mailbox_search", {"query": "Unterlagen"}, ctx).output["items"] == []
        r = _run("mailbox_read", {"message_id": mid}, ctx)
        assert not r.success and "nicht gefunden" in r.error
    finally:
        pc.delete(other["id"])


def test_nichtmitglied_sieht_trotz_freigabe_nichts(acc, project, tmp_path):
    _share(acc["id"], f"project:{project}")
    r = _run("mailbox_search", {"query": "Unterlagen"}, _ctx(tmp_path, user="carol", project_id=project))
    assert r.output["items"] == []


def test_buddy_freigabe_ohne_projekt(acc, tmp_path):
    assert _run("mailbox_accounts", {}, _ctx(tmp_path)).output["accounts"] == []
    _share(acc["id"], "buddy")
    assert len(_run("mailbox_accounts", {}, _ctx(tmp_path)).output["accounts"]) == 1
    assert _run("mailbox_accounts", {}, _ctx(tmp_path, user="bob")).output["accounts"] == []


def test_anhang_in_den_arbeitsordner(acc, project, tmp_path):
    _share(acc["id"], f"project:{project}")
    ctx = _ctx(tmp_path, project_id=project)
    mid = _run("mailbox_search", {"query": "Unterlagen"}, ctx).output["items"][0]["id"]
    detail = _run("mailbox_read", {"message_id": mid}, ctx).metadata["attachments"]
    pdf = next(a for a in detail if a["name"] == "Vertrag ä.pdf")
    r1 = _run("mailbox_attachment", {"message_id": mid, "index": pdf["index"]}, ctx)
    r2 = _run("mailbox_attachment", {"message_id": mid, "index": pdf["index"]}, ctx)
    assert r1.success and r2.success
    p1, p2 = tmp_path / r1.output["path"], tmp_path / r2.output["path"]
    assert p1.parent == tmp_path / "mailbox-anhaenge" and p1 != p2      # nie überschreiben
    assert p1.read_bytes().startswith(b"%PDF")
    bad = _run("mailbox_attachment", {"message_id": mid, "index": 99}, ctx)
    assert not bad.success


def test_anhang_nie_ueber_symlink_nach_draussen(acc, project, tmp_path):
    _share(acc["id"], f"project:{project}")
    ws, outside = tmp_path / "ws", tmp_path / "draussen"
    ws.mkdir()
    outside.mkdir()
    (ws / "mailbox-anhaenge").symlink_to(outside)
    ctx = _ctx(ws, project_id=project)
    mid = _run("mailbox_search", {"query": "Unterlagen"}, ctx).output["items"][0]["id"]
    idx = next(a["index"] for a in _run("mailbox_read", {"message_id": mid}, ctx).metadata["attachments"])
    r = _run("mailbox_attachment", {"message_id": mid, "index": idx}, ctx)
    assert not r.success and list(outside.iterdir()) == []


def test_eingaben_und_grenzen(acc, project, tmp_path):
    _share(acc["id"], f"project:{project}")
    ctx = _ctx(tmp_path, project_id=project)
    assert _run("mailbox_search", {"query": "x", "limit": 500}, ctx).output["limit"] == 50
    assert not _run("mailbox_read", {"message_id": "abc"}, ctx).success
    assert not _run("mailbox_read", {}, ctx).success


def test_protokoll_ohne_mailinhalt(acc, project, tmp_path):
    from hydrahive.db.connection import db
    _share(acc["id"], f"project:{project}")
    ctx = _ctx(tmp_path, project_id=project)
    mid = _run("mailbox_search", {"query": "Unterlagen"}, ctx).output["items"][0]["id"]
    _run("mailbox_read", {"message_id": mid}, ctx)
    _run("mailbox_read", {"message_id": 999999}, ctx)
    with db() as c:
        rows = [dict(r) for r in c.execute("SELECT * FROM module_mailbox_audit ORDER BY id")]
    assert [(r["tool"], r["result"]) for r in rows] == [("mailbox_search", "ok"), ("mailbox_read", "ok"),
                                                        ("mailbox_read", "not_found")]
    assert rows[1]["message_id"] == mid and rows[1]["project_id"] == project and rows[1]["account_id"] == acc["id"]
    assert "Unterlagen" not in str(rows)


def test_registriert_und_im_manifest_privat():
    import json

    import backend
    from backend import agent_tools
    from conftest import MODULE_DIR
    names = {t.name for t in agent_tools.TOOLS}
    assert names == {"mailbox_accounts", "mailbox_search", "mailbox_read", "mailbox_attachment"}
    m = json.loads((MODULE_DIR / "manifest.json").read_text())
    assert m["default_agent_tools"] is True
    assert {k for k, v in m["sensitive_tools"].items() if v == "privat"} >= names
    seen = []

    class Ctx:
        def register_router(self, r): pass
        def register_tool(self, t): seen.append(t.name)
        def register_job(self, *a, **k): pass
        def register_migrations(self, d): pass
    backend.register(Ctx())
    assert set(seen) == names
