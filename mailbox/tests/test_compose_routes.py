"""M2 Schritt 8: Routen Senden/Antworten/Weiterleiten/Entwürfe/Aktionen über den echten Kern.

Besitz: fremde Konten/Mails/Entwürfe = 404. Eingaben 422. Grenze 429. SMTP wird ersetzt (Versand selbst ist in
test_smtp_send.py gegen einen echten Server getestet); IMAP ist das Fake mit Schreibbefehlen.
"""
# ruff: noqa: F811 - pytest-Fixtures aus _routes_base werden als gleichnamige Parameter genutzt
from __future__ import annotations

import pytest
from _fake_imap_write import FakeIMAPW
from _routes_base import B, NEW, _h, _mid, acc, alice, client, fake_net, rights  # noqa: F401 - Fixtures/Hilfen


@pytest.fixture(autouse=True)
def smtp(monkeypatch, fake_net):
    from backend import smtp_send, sync_job
    sent = []
    monkeypatch.setattr(smtp_send, "send", lambda a, pw, raw, env, **kw: sent.append((a["id"], pw, raw, env)) or {})
    monkeypatch.setattr(sync_job, "_open", lambda a: FakeIMAPW(fake_net, caps=("MOVE", "UIDPLUS", "UNSELECT")))
    return sent


def test_senden(client, alice, acc, smtp, fake_net):
    r = client.post(f"{B}/send", headers=alice, data={"account_id": acc["id"], "to": "Anna <anna@example.org>",
                                                      "bcc": "geheim@x.de", "subject": "Hallo", "body": "Hi"})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["sent"] and j["sent_copy"] == "server"
    aid, pw, raw, env = smtp[0]
    assert aid == acc["id"] and pw == "geheim-123" and env == ["anna@example.org", "geheim@x.de"]
    assert b"geheim@x.de" not in raw and b"From: alice@example.net" in raw
    assert len(fake_net.boxes["Gesendet"].msgs) == 2


def test_senden_mit_anhang(client, alice, acc, smtp):
    r = client.post(f"{B}/send", headers=alice, data={"account_id": acc["id"], "to": "a@x.de", "subject": "s", "body": "x"},
                    files=[("files", ("Bericht ä.pdf", b"%PDF-1.4", "application/pdf"))])
    assert r.status_code == 200, r.text
    assert b'filename*=utf-8\'\'Bericht%20%C3%A4.pdf' in smtp[0][2] or "Bericht ä.pdf".encode() in smtp[0][2]


def test_antworten_und_weiterleiten(client, alice, acc, smtp):
    mid = _mid(client, alice, "Re: Unterlagen")
    r = client.post(f"{B}/send", headers=alice, data={"account_id": acc["id"], "mode": "reply_all", "ref_message": mid,
                                                      "body": "Danke"})
    assert r.status_code == 200, r.text
    raw = smtp[-1][2]
    assert b"In-Reply-To: <att-1@kanzlei.example>" in raw and b"Subject: Re: Unterlagen" in raw
    assert "alice@example.net" not in smtp[-1][3]
    r = client.post(f"{B}/send", headers=alice, data={"account_id": acc["id"], "mode": "forward", "ref_message": mid,
                                                      "to": "neu@x.de", "with_attachments": "true", "body": ""})
    assert r.status_code == 200 and b"Subject: WG: Re: Unterlagen" in smtp[-1][2]


def test_vorlage_fuer_antwort(client, alice, acc):
    """Das Schreibfenster holt Empfänger/Betreff/Zitat vom Server (gleiche Logik wie beim Senden)."""
    mid = _mid(client, alice, "Re: Unterlagen")
    j = client.get(f"{B}/compose/prefill", params={"mode": "reply_all", "ref_message": mid, "account_id": acc["id"]},
                   headers=alice).json()
    assert j["to"] == "Kanzlei <post@kanzlei.example>" and "akte@kanzlei.example" in j["cc"]
    assert "alice@example.net" not in j["cc"] and j["subject"] == "Re: Unterlagen" and "> Anbei" in j["quote"]


@pytest.mark.parametrize("data", [{"to": "kaputt"}, {"to": ""}, {"to": "a@x.de", "subject": "a\r\nBcc: x@y.de"},
                                  {"to": "a@x.de", "mode": "boese"}, {"mode": "reply"}])
def test_eingaben_422(client, alice, acc, smtp, data):
    r = client.post(f"{B}/send", headers=alice, data={"account_id": acc["id"], "subject": "s", "body": "x", **data})
    assert r.status_code == 422, r.text
    assert smtp == []


def test_fremdes_konto_und_fremde_mail(client, alice, acc, smtp):
    bob = _h(client, "bob")
    r = client.post(f"{B}/send", headers=bob, data={"account_id": acc["id"], "to": "a@x.de", "subject": "s", "body": "x"})
    assert r.status_code == 404
    rb = client.post(f"{B}/accounts", json={**NEW, "address": "bob@example.net", "username": "bob@example.net"},
                     headers=bob)
    mid = _mid(client, alice, "Re: Unterlagen")
    r = client.post(f"{B}/send", headers=bob, data={"account_id": rb.json()["id"], "mode": "reply", "ref_message": mid,
                                                    "body": "x"})
    assert r.status_code == 404 and smtp == []


def test_ohne_recht_403(client, acc, smtp):
    carol = _h(client, "carol")
    r = client.post(f"{B}/send", headers=carol, data={"account_id": acc["id"], "to": "a@x.de", "subject": "s"})
    assert r.status_code == 403


def test_grenze_429(client, alice, acc, smtp, monkeypatch):
    monkeypatch.setenv("HH_MAILBOX_SEND_PER_HOUR", "1")
    d = {"account_id": acc["id"], "to": "a@x.de", "subject": "s", "body": "x"}
    assert client.post(f"{B}/send", headers=alice, data=d).status_code == 200
    r = client.post(f"{B}/send", headers=alice, data=d)
    assert r.status_code == 429 and int(r.headers["Retry-After"]) > 0 and len(smtp) == 1


def test_versandfehler_502_mit_art(client, alice, acc, monkeypatch):
    from backend import smtp_send

    def boom(*a, **kw):
        raise smtp_send.SendError("auth", "Anmeldung abgelehnt")
    monkeypatch.setattr(smtp_send, "send", boom)
    r = client.post(f"{B}/send", headers=alice, data={"account_id": acc["id"], "to": "a@x.de", "subject": "s", "body": "x"})
    assert r.status_code == 502 and r.json()["detail"]["code"] == "auth"


def test_anhang_zu_gross_413(client, alice, acc, smtp, monkeypatch):
    from backend import compose
    monkeypatch.setattr(compose, "MAX_TOTAL", 10)
    r = client.post(f"{B}/send", headers=alice, data={"account_id": acc["id"], "to": "a@x.de", "subject": "s"},
                    files=[("files", ("a.bin", b"0" * 11, "application/octet-stream"))])
    assert r.status_code == 413 and smtp == []


def test_senden_loescht_entwurf(client, alice, acc, smtp, fake_net):
    d = client.post(f"{B}/drafts", headers=alice, json={"account_id": acc["id"], "to": "a@x.de", "subject": "E"}).json()
    r = client.post(f"{B}/send", headers=alice, data={"account_id": acc["id"], "to": "a@x.de", "subject": "E", "body": "x",
                                                      "draft_id": d["id"]})
    assert r.status_code == 200
    assert client.get(f"{B}/drafts", headers=alice).json() == []


def test_langer_text_mit_umlauten(client, alice, acc, smtp):
    """Starlette begrenzt jedes Formularfeld auf 1 MB (Bytes, nicht Zeichen). Bis dahin geht alles durch, auch mit
    Umlauten; darüber 400 vor der Route (nichts gesendet). Das Schreibfenster warnt vorher (composeFormat.textTooLong)."""
    # wie der Browser (FormData): immer multipart – ohne Datei würde der TestClient urlencoded schicken (ä = 6 Byte)
    mp = [("files", ("leer.txt", b"", "text/plain"))]
    ok = "ä" * 450_000                                      # 0,9 MB in UTF-8
    r = client.post(f"{B}/send", headers=alice, files=mp,
                    data={"account_id": acc["id"], "to": "a@x.de", "subject": "s", "body": ok})
    assert r.status_code == 200, r.text[:200]
    big = "ä" * 600_000                                     # 1,2 MB in UTF-8: Starlette lehnt ab, bevor die Route läuft
    r = client.post(f"{B}/send", headers=alice, files=mp,
                    data={"account_id": acc["id"], "to": "a@x.de", "subject": "s", "body": big})
    assert r.status_code == 400 and len(smtp) == 1, "zweite (zu lange) Mail darf nicht gesendet werden"
