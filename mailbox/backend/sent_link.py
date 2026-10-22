"""Selbst gesendete Mails mit der Server-Fassung verknüpfen (0.3.0, Befund Prod 22.10.2026).

Manche Server (Yahoo) schreiben die per APPEND abgelegte Gesendet-Kopie um: andere Bytes, gleiche Message-ID. Der
Abgleich archiviert sie dann als eigene Mail. Ohne Verknüpfung erschien die Mail doppelt, und die eigene Kopie stand
fälschlich unter „Nur im Archiv“.

Regel: Die eigene Kopie (sent_local) wird zurückgestellt (superseded=1), solange eine Mail mit derselben Message-ID
im Gesendet-Ordner desselben Kontos auf dem Server liegt. Nur Gesendet-Ordner – eine empfangene Mail mit gefälschter
Message-ID im Posteingang stellt nichts zurück. Verschwindet die Server-Fassung, gilt wieder die Archiv-Regel.
Dateien werden nie gelöscht.
"""
from __future__ import annotations

from . import index_db

# Liste/Suche: zurückgestellte eigene Kopien ausblenden (SQL-Bedingung, m = messages)
VISIBLE = "m.id NOT IN (SELECT message_id FROM sent_local WHERE superseded=1)"


def mark(mid: int) -> None:
    """Archivkopie einer selbst gesendeten Mail kennzeichnen (outbox)."""
    with index_db.connect() as c:
        c.execute("INSERT OR IGNORE INTO sent_local(message_id) VALUES (?)", (mid,))


def adopt_legacy(account_id: str) -> int:
    """Bestand aus 0.2.0: eigene Kopien ohne Kennzeichen erkennen – nur Archiv, kein Fundort, und eine weitere Mail
    mit gleicher Message-ID liegt im Gesendet-Ordner. Kennzeichen kommt aus dem Manifest-Status „sent“ nicht in den
    Index, deshalb über diese engen Merkmale."""
    with index_db.connect() as c:
        cur = c.execute(
            "INSERT OR IGNORE INTO sent_local(message_id) SELECT m.id FROM messages m WHERE m.account_id=? "
            "AND m.deleted_on_server=1 AND m.message_id<>'' "   # doppelt mit „kein Fundort“ (gewollt)
            "AND NOT EXISTS (SELECT 1 FROM locations l WHERE l.message_id=m.id) "
            "AND EXISTS (SELECT 1 FROM messages o JOIN folders f ON f.id=o.folder_id WHERE o.account_id=m.account_id "
            "            AND o.message_id=m.message_id AND o.id<>m.id AND f.role='sent' "
            "            AND o.id NOT IN (SELECT message_id FROM sent_local)) "
            "AND (SELECT f.role FROM folders f WHERE f.id=m.folder_id)='sent'", (account_id,))
        return cur.rowcount


def refresh(account_id: str) -> None:
    """Nach dem Abgleich: je eigene Kopie prüfen, ob es die Server-Fassung gibt – eine andere archivierte Mail mit
    gleicher Message-ID, die selbst keine eigene Kopie ist und im Gesendet-Ordner lag oder liegt.
    Da → eigene Kopie zurückstellen; die Server-Fassung trägt Fundort bzw. „Nur im Archiv“ (genau eine Mail).
    Nie gesehen → eigene Kopie zeigen (dann ist sie die einzige Fassung)."""
    on_server = ("EXISTS (SELECT 1 FROM messages o JOIN folders f ON f.id=o.folder_id WHERE o.account_id=m.account_id "
                 "AND o.message_id=m.message_id AND o.id<>m.id AND f.role='sent' "
                 "AND o.id NOT IN (SELECT message_id FROM sent_local))")
    with index_db.connect() as c:
        c.execute(f"UPDATE sent_local SET superseded=1 WHERE message_id IN (SELECT m.id FROM messages m WHERE "
                  f"m.account_id=? AND m.message_id<>'' AND {on_server})", (account_id,))
        c.execute(f"UPDATE sent_local SET superseded=0 WHERE message_id IN (SELECT m.id FROM messages m WHERE "
                  f"m.account_id=? AND NOT ({on_server}))", (account_id,))
