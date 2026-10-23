"""Werkzeuge der Stufe „Entwurf“ (Spec §8, PLAN-M3b): mailbox_draft, mailbox_move, mailbox_flag.

Nur Konten mit Freigabe „Entwurf“ für das aktive Projekt. Ein Agent sendet nie und löscht nie. Entwürfe gehören dem
Kontobesitzer (sie erscheinen in seinem Webmail unter „Entwürfe“); ändern darf der Agent nur eigene Agenten-Entwürfe
desselben Projekts. Verschieben/Markieren laufen über denselben Weg wie das Webmail (action_routes._run_account).
"""
from __future__ import annotations

import asyncio

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from . import (
    access,
    accounts,
    action_routes,
    actions,
    agent_audit,
    agent_drafts,
    archive,
    drafts,
    index_db,
    reply,
    shares,
    sync_job,
)

MAX_IDS = 100
FLAGS = ("seen", "unseen", "flag", "unflag")
MODES = ("new", "reply", "reply_all", "forward")
_NO_LEVEL = "Kein Konto mit Stufe „Entwurf“ für dieses Projekt freigegeben (Mailbox → Zahnrad → Freigaben)."
_FIELDS = ("to", "cc", "bcc", "subject", "body")


def _str(args: dict, k: str) -> str:
    v = args.get(k)
    return v if isinstance(v, str) else ""


def _visible(ctx: ToolContext) -> dict[str, str]:
    return shares.visible(ctx.user_id or "", ctx.project_id or None, "draft")


def _template(owner: str, acc: dict, accs: dict, mode: str, ref) -> dict:
    m = access.message_in(accs, ref) if isinstance(ref, int) and not isinstance(ref, bool) else None
    if not m or m["account_id"] != acc["id"]:
        raise drafts.DraftError("ref_message: Mail nicht gefunden (muss zum selben Konto gehören)")
    p = reply.prefill(acc, archive.read(m["path"]), mode)
    return {"to": p["to"], "cc": p["cc"], "subject": p["subject"], "quote": p["quote"], "ref_message": m["id"]}


def _draft_sync(ctx: ToolContext, args: dict, accs: dict) -> dict:
    aid = _str(args, "account_id")
    owner = shares.owner_of(aid) if aid in accs else None
    acc = accounts.get_own(owner, aid) if owner else None
    if not acc:
        raise drafts.DraftError("account_id: Konto nicht mit Stufe „Entwurf“ freigegeben")
    scope, did = shares.scope_of(ctx.project_id or None), _str(args, "draft_id") or None
    if did:
        if not agent_drafts.owned(did, aid, scope) or not drafts.get(owner, did):
            raise drafts.DraftError("draft_id: nur eigene Agenten-Entwürfe dieses Projekts lassen sich ändern")
        data = {**drafts.get(owner, did), **{k: _str(args, k) for k in _FIELDS if k in args}}
    else:
        mode = args.get("mode") or "new"
        if mode not in MODES:
            raise drafts.DraftError("mode ungültig")
        data = {k: _str(args, k) for k in _FIELDS} | {"mode": mode}
        if mode != "new":
            t = _template(owner, acc, accs, mode, args.get("ref_message"))
            data |= {"ref_message": t["ref_message"], "subject": data["subject"] or t["subject"],
                     "body": f"{data['body'].rstrip()}\n\n{t['quote']}", "with_attachments": mode == "forward"}
            if mode != "forward":
                data |= {"to": data["to"] or t["to"], "cc": data["cc"] or t["cc"]}
    saved = drafts.save(owner, acc, data, draft_id=did, password=accounts.password_of(aid), open_imap=sync_job._open)
    agent_drafts.remember(saved["id"], aid, scope)
    return {"draft_id": saved["id"], "account": acc["address"], "to": saved["to"], "subject": saved["subject"],
            "server_copy": saved.get("server", "local_only"),
            "note": "Nur als Entwurf gespeichert – NICHT gesendet. Der Nutzer sieht ihn im Webmail unter „Entwürfe“."}


async def _draft(args: dict, ctx: ToolContext) -> ToolResult:
    accs = _visible(ctx)
    if not accs:
        agent_audit.record(ctx, "mailbox_draft", "denied")
        return ToolResult.fail(_NO_LEVEL)
    try:
        out = await asyncio.to_thread(_draft_sync, ctx, args, accs)
    except (drafts.DraftError, archive.ArchiveError) as e:
        agent_audit.record(ctx, "mailbox_draft", "denied", account_id=_str(args, "account_id")[:64])
        return ToolResult.fail(str(e))
    agent_audit.record(ctx, "mailbox_draft", "ok", account_id=_str(args, "account_id"))
    return ToolResult.ok(out)


def _ids(args: dict) -> list[int] | None:
    v = args.get("message_ids")
    if not isinstance(v, list) or not 1 <= len(v) <= MAX_IDS or not all(
            isinstance(x, int) and not isinstance(x, bool) for x in v):
        return None
    return list(dict.fromkeys(v))


def _act_sync(accs: dict, ids: list[int], action: str, target: str | None) -> dict:
    q = ",".join("?" * len(ids))
    with index_db.connect() as c:
        rows = c.execute(f"SELECT id, account_id FROM messages WHERE id IN ({q})", ids).fetchall()
    groups: dict[str, list[int]] = {}
    for mid, aid in rows:
        if aid in accs:
            groups.setdefault(aid, []).append(mid)
    done, touched = 0, []
    for aid, mids in groups.items():
        n = action_routes._run_account(shares.owner_of(aid) or "", aid, mids, action, target)["done"]
        done += n
        if n:
            touched.append(aid)
    return {"done": done, "skipped": len(ids) - done, "accounts": touched}


async def _act(ctx: ToolContext, tool: str, ids: list[int] | None, action: str, target: str | None) -> ToolResult:
    if ids is None:
        return ToolResult.fail(f"message_ids: 1 bis {MAX_IDS} Mail-IDs aus mailbox_search")
    accs = _visible(ctx)
    if not accs:
        agent_audit.record(ctx, tool, "denied")
        return ToolResult.fail(_NO_LEVEL)
    try:
        out = await asyncio.to_thread(_act_sync, accs, ids, action, target)
    except actions.ActionError as e:
        agent_audit.record(ctx, tool, "denied")
        return ToolResult.fail(str(e))
    except action_routes.ServerError as e:
        agent_audit.record(ctx, tool, "error")
        return ToolResult.fail(f"Mailserver: {e.code}")
    for aid in out.pop("accounts"):
        agent_audit.record(ctx, tool, "ok", account_id=aid)
    if out["skipped"]:
        agent_audit.record(ctx, tool, "not_found")
    return ToolResult.ok(out)


async def _flag(args: dict, ctx: ToolContext) -> ToolResult:
    action = args.get("action")
    if action not in FLAGS:
        return ToolResult.fail(f"action: nur {', '.join(FLAGS)} (Löschen gibt es für Agenten nicht)")
    return await _act(ctx, "mailbox_flag", _ids(args), action, None)


async def _move(args: dict, ctx: ToolContext) -> ToolResult:
    folder = _str(args, "folder").strip()
    if not folder:
        return ToolResult.fail("folder: Name eines Ordners aus mailbox_accounts")
    return await _act(ctx, "mailbox_move", _ids(args), "move", folder)


_IDS = {"type": "array", "items": {"type": "integer"}, "minItems": 1, "maxItems": MAX_IDS,
        "description": "IDs aus mailbox_search"}
_S = {"type": "string"}
TOOLS = [
    Tool(name="mailbox_draft", category="data", execute=_draft,
         description="Legt einen Mail-ENTWURF an oder ändert einen eigenen (draft_id). Sendet NIE. Antwort/Weiterleitung "
                     "über mode + ref_message: Empfänger, Betreff und Zitat kommen dann aus dem Original. Der Nutzer "
                     "prüft und sendet selbst im Webmail.",
         schema={"type": "object", "additionalProperties": False, "required": ["account_id"], "properties": {
             "account_id": {"type": "string", "description": "aus mailbox_accounts"},
             "draft_id": {"type": "string", "description": "nur zum Ändern eines eigenen Entwurfs"},
             "mode": {"type": "string", "enum": list(MODES), "default": "new"},
             "ref_message": {"type": "integer", "description": "Mail-ID bei reply/reply_all/forward"},
             "to": _S, "cc": _S, "bcc": _S, "subject": _S, "body": {"type": "string", "description": "Text ohne Zitat"}}}),
    Tool(name="mailbox_flag", category="data", execute=_flag,
         description="Setzt gelesen/ungelesen oder Markierung auf dem Mailserver. Löschen gibt es nicht.",
         schema={"type": "object", "additionalProperties": False, "required": ["message_ids", "action"],
                 "properties": {"message_ids": _IDS, "action": {"type": "string", "enum": list(FLAGS)}}}),
    Tool(name="mailbox_move", category="data", execute=_move,
         description="Verschiebt Mails in einen anderen Ordner desselben Kontos (Name aus mailbox_accounts). Die Mail "
                     "bleibt immer im Archiv. Löschen gibt es nicht.",
         schema={"type": "object", "additionalProperties": False, "required": ["message_ids", "folder"],
                 "properties": {"message_ids": _IDS, "folder": _S}}),
]
