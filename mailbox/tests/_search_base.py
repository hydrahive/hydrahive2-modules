"""Gemeinsame Hilfen der Such-Tests (Testmails in zwei Konten)."""
from __future__ import annotations

import pytest
from conftest import eml

A1, A2 = "acc1", "acc2"
ADDR = {A1: "till@example.net", A2: "frau@example.net"}


def _mail(n, subject, frm="anna@example.org", to="till@example.net", date="Tue, 20 Oct 2026 09:00:00 +0000",
          body="Text", attach=False):
    head = (f"From: {frm}\r\nTo: {to}\r\nSubject: {subject}\r\nMessage-ID: <s{n}@x>\r\nDate: {date}\r\n")
    if not attach:
        return (head + f"\r\n{body}\r\n").encode()
    return (head + "Content-Type: multipart/mixed; boundary=B\r\n\r\n--B\r\nContent-Type: text/plain\r\n\r\n"
            f"{body}\r\n--B\r\nContent-Type: application/pdf\r\nContent-Disposition: attachment; filename=r.pdf\r\n\r\n"
            "xx\r\n--B--\r\n").encode()


@pytest.fixture
def mails(archive):
    from backend import parse, store
    inbox, sent = store.folder(A1, "INBOX", role="inbox"), store.folder(A1, "Gesendet", role="sent")
    other = store.folder(A2, "INBOX", role="inbox")
    items = [
        (A1, inbox, 1, _mail(1, "Termin morgen", body="Treffen im Büro um zehn")),
        (A1, inbox, 2, _mail(2, "Rechnung Oktober", frm="buchhaltung@firma.de", attach=True,
                             date="Mon, 05 Jan 2015 10:00:00 +0000")),
        (A1, sent, 3, _mail(3, "Re: Termin morgen", frm="till@example.net", to="anna@example.org", body="Passt mir",
                            date="Tue, 20 Oct 2026 09:30:00 +0000")),
        (A1, inbox, 4, eml("latin1")),
        (A2, other, 1, _mail(5, "Termin geheim", body="nur für Frau")),
    ]
    ids = {}
    for acc, fid, uid, raw in items:
        p = parse.parse(raw)
        ids[p.subject] = store.add_message(acc, fid, uid, p, path=f"x/{uid}.eml", size=len(raw), flags=set())
    return {"ids": ids, "inbox": inbox, "sent": sent}


def _q(q, accounts=(A1,), **kw):
    from backend import search
    return [r["subject"] for r in search.search({a: ADDR[a] for a in accounts}, q, **kw)["items"]]

