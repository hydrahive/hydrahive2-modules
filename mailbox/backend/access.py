"""Wem gehört was (M1: nur persönliche Konten; M3 ergänzt Gruppen und Projektfreigaben an genau dieser Stelle)."""
from __future__ import annotations

from . import accounts, index_db


def accounts_map(user: str) -> dict[str, str]:
    """Konto-ID → Adresse aller Konten, die der Nutzer sehen darf."""
    return {a["id"]: a["address"] for a in accounts.list_for(user)}


def folder_owned(accs: dict[str, str], folder_id: int) -> bool:
    if not accs:          # nur Abkürzung: ohne Konten besteht auch „in accs“ unten nie
        return False
    with index_db.connect() as c:
        r = c.execute("SELECT account_id FROM folders WHERE id=?", (int(folder_id),)).fetchone()
    return bool(r) and r[0] in accs


def folders_for(user: str) -> list[dict]:
    accs = accounts_map(user)
    if not accs:
        return []
    with index_db.connect() as c:
        rows = c.execute(f"SELECT id, account_id, name, role, total, unread, gone FROM folders WHERE account_id IN "
                         f"({','.join('?' * len(accs))}) ORDER BY account_id, name", list(accs)).fetchall()
    return [{**dict(r), "account": accs[r["account_id"]]} for r in rows]


def message_owned(user: str, mid: int) -> dict | None:
    """Mail-Datensatz, wenn sie zu einem Konto des Nutzers gehört – sonst None (Route antwortet 404)."""
    return message_in(accounts_map(user), mid)


def message_in(accs: dict[str, str], mid: int) -> dict | None:
    """Mail-Datensatz, wenn sie zu einem der Konten ``accs`` gehört (Webmail: eigene; Werkzeug: freigegebene)."""
    if not accs:          # nur Abkürzung: ohne Konten besteht auch „in accs“ unten nie
        return None
    with index_db.connect() as c:
        r = c.execute("SELECT m.*, f.name AS folder, f.role AS folder_role FROM messages m JOIN folders f "
                      "ON f.id=m.folder_id WHERE m.id=?",
                      (int(mid),)).fetchone()
    if not r or r["account_id"] not in accs:
        return None
    return {**dict(r), "account": accs[r["account_id"]]}
