"""Suche im Index (PLAN-M1 Schritt 8). Nur die übergebenen Konten (Rechte prüft der Aufrufer); neueste zuerst.

Mit FTS5: Volltext über Betreff, Absender, Empfänger und den ganzen Text.
Ohne FTS5 (manches Python auf dem Mac): Filter in SQL, Wörter in Python mit derselben Faltung wie FTS (Akzente weg,
Wortanfang) – aber nur über Kopfdaten + Kurztext, nicht den ganzen Text. Die Antwort meldet das (`fulltext: false`).
"""
from __future__ import annotations

import json
import re

from . import index_db, query

LIMIT_DEFAULT, LIMIT_MAX = 50, 200
_COLS = ("m.id, m.account_id, m.date, m.from_addr, m.to_addr, m.cc_addr, m.subject, m.snippet, m.seen, m.flagged, "
         "m.answered, m.thread_key, m.attachments, m.size, m.deleted_on_server, f.name AS folder, f.id AS folder_id")


def _has_fts(c) -> bool:
    return c.execute("SELECT 1 FROM sqlite_master WHERE name='messages_fts'").fetchone() is not None


def _like(v: str) -> str:
    return "%" + v.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def _post_filter(items: list[dict], q: query.Query) -> list[dict]:
    """Wörter/Phrasen wie FTS (unicode61, remove_diacritics) prüfen – „koln“ findet „Köln“, „Rechn“ „Rechnung“."""
    import unicodedata

    def fold(s):
        return "".join(ch for ch in unicodedata.normalize("NFKD", s.casefold()) if not unicodedata.combining(ch))
    out = []
    for it in items:
        toks = query.words_of(fold(" ".join([it["subject"], it["from_addr"], it["to_addr"], it["cc_addr"], it["snippet"]])))
        ok = all(any(t.startswith(fold(w)) for t in toks) for w in q.words)
        joined = " " + " ".join(toks) + " "
        ok = ok and all(" " + " ".join(fold(x) for x in ph) + " " in joined for ph in q.phrases)
        if ok:
            out.append(it)
    return out


ROLES = {"inbox", "sent", "drafts", "trash", "junk", "archive", "all"}


def search(accounts: dict[str, str], text: str, *, folder_id: int | None = None, only_deleted: bool = False,
           role: str | None = None, limit: int = LIMIT_DEFAULT, offset: int = 0) -> dict:
    limit = max(1, min(int(limit), LIMIT_MAX))
    offset = max(0, int(offset))
    if not accounts:
        return {"items": [], "total": 0, "limit": limit, "offset": offset, "fulltext": True}
    q = query.parse(text)
    acc_ids = list(accounts)
    for a in q.filters.get("account", []):
        acc_ids = [i for i in acc_ids if a in accounts[i].casefold()]
    if not acc_ids:
        return {"items": [], "total": 0, "limit": limit, "offset": offset, "fulltext": True}
    where = [f"m.account_id IN ({','.join('?' * len(acc_ids))})"]
    args: list = list(acc_ids)
    for col, key in (("m.from_addr", "from"), ("m.to_addr || ' ' || m.cc_addr", "to"), ("m.subject", "subject"),
                     ("f.name", "folder")):
        for v in q.filters.get(key, []):
            where.append(f"lower({col}) LIKE ? ESCAPE '\\'")
            args.append(_like(v))
    if q.attachment:
        where.append("m.attachments LIKE '%\"inline\": false%'")
    if q.before:
        where.append("m.date <> '' AND m.date < ?")
        args.append(q.before)
    if q.after:
        where.append("m.date >= ?")
        args.append(q.after)
    if folder_id is not None:
        where.append("m.id IN (SELECT message_id FROM locations WHERE folder_id=?)")
        args.append(int(folder_id))
    if only_deleted:
        where.append("m.deleted_on_server=1")
    if role in ROLES:
        where.append("m.id IN (SELECT l.message_id FROM locations l JOIN folders r ON r.id=l.folder_id WHERE r.role=?)")
        args.append(role)
    with index_db.connect() as c:
        fts = _has_fts(c)
        if q.has_text and fts:
            where.append("m.id IN (SELECT rowid FROM messages_fts WHERE messages_fts MATCH ?)")
            args.append(query.fts_expr(q))
        sql = f"FROM messages m JOIN folders f ON f.id=m.folder_id WHERE {' AND '.join(where)}"
        rows = [dict(r) for r in c.execute(f"SELECT {_COLS} {sql} ORDER BY m.date DESC, m.id DESC", args)]
    if q.has_text and not fts:
        rows = _post_filter(rows, q)
    total = len(rows)
    items = [_item(r, accounts) for r in rows[offset:offset + limit]]
    return {"items": items, "total": total, "limit": limit, "offset": offset, "fulltext": fts}


def _item(r: dict, accounts: dict[str, str]) -> dict:
    att = json.loads(r.pop("attachments") or "[]")
    r["has_attachments"] = any(not a.get("inline") for a in att)
    r["account"] = accounts.get(r["account_id"], "")
    r["subject"] = re.sub(r"\s+", " ", r["subject"])
    return r
