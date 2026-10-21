"""M1 Schritt 4: Rohmail → Kopfdaten, Text, Anhänge, Thread-Schlüssel. Nie eine Ausnahme bei kaputten Mails."""
from __future__ import annotations

import hashlib

import pytest
from conftest import eml


def test_klartext():
    from backend import parse
    p = parse.parse(eml("plain"))
    assert p.subject == "Termin morgen" and p.from_addr == "Anna Beispiel <anna@example.org>"
    assert p.to_addr == "till@example.net" and p.message_id == "<plain-1@example.org>"
    assert p.date == "2026-10-20T07:15:00Z", "immer UTC"
    assert "Termin morgen um 10 Uhr" in p.body and p.snippet.startswith("Hallo Till")
    assert p.attachments == [] and p.has_html is False and p.error == ""
    assert p.sha256 == hashlib.sha256(eml("plain")).hexdigest()


def test_html_text_ohne_skript_und_stil():
    from backend import parse
    p = parse.parse(eml("html_tracking"))
    assert p.has_html is True
    assert "Angebot der Woche" in p.body or "Nur Text-Teil" in p.body
    assert "alert" not in p.body and "color:red" not in p.body


def test_html_ohne_textteil_wird_zu_text():
    from backend import parse
    raw = (b"From: a@b.de\r\nSubject: nur html\r\nContent-Type: text/html; charset=utf-8\r\n\r\n"
           b"<html><style>p{x:1}</style><script>bad()</script><p>Hallo <b>Welt</b></p><p>Zweite&nbsp;Zeile &amp; mehr</p></html>")
    p = parse.parse(raw)
    assert p.body.split() == ["Hallo", "Welt", "Zweite", "Zeile", "&", "mehr"]
    assert "\xa0" not in p.body, "geschütztes Leerzeichen wird normales Leerzeichen (Suche findet „Zweite Zeile“)"


def test_anhaenge_und_inline_bild():
    from backend import parse
    p = parse.parse(eml("attachments"))
    names = [(a["name"], a["type"], a["inline"]) for a in p.attachments]
    assert ("Vertrag ä.pdf", "application/pdf", False) in names
    assert ("logo.png", "image/png", True) in names
    pdf = next(a for a in p.attachments if a["name"] == "Vertrag ä.pdf")
    assert pdf["size"] == len(b"%PDF-1.4 fake pdf") and isinstance(pdf["index"], int)
    assert next(a for a in p.attachments if a["inline"])["cid"] == "logo123"
    assert p.has_attachments is True, "Inline-Logos zählen nicht, die PDF schon"
    assert p.cc_addr == "akte@kanzlei.example" and "frau@example.net" in p.to_addr


def test_thread_aus_references():
    from backend import parse
    p = parse.parse(eml("attachments"))
    assert p.in_reply_to == "<orig-1@example.net>"
    assert p.thread_key == "<orig-0@example.net>", "Wurzel = erste Referenz"


def test_thread_ohne_references_ist_eigene_message_id():
    from backend import parse
    assert parse.parse(eml("plain")).thread_key == "<plain-1@example.org>"


def test_rfc2047_und_latin1():
    from backend import parse
    p = parse.parse(eml("latin1"))
    assert p.subject == "Grüße aus Köln 😃"
    assert p.from_addr == "Jürgen Müller <juergen@example.de>"
    assert "Schöne Grüße aus Köln" in p.body
    assert p.date == "2015-01-01T07:00:00Z"


def test_kaputt_ohne_ausnahme():
    from backend import parse
    p = parse.parse(eml("broken"))
    assert p.subject == "ohne alles" and p.date == "" and p.message_id == ""
    assert "Teil ohne Ende" in p.body


@pytest.mark.parametrize("raw", [b"", b"\x00\x00", None])
def test_muell_ohne_ausnahme(raw):
    from backend import parse
    p = parse.parse(eml("garbage") if raw is None else raw)
    assert isinstance(p.body, str) and isinstance(p.subject, str)


def test_ohne_message_id_thread_aus_hash():
    from backend import parse
    p = parse.parse(eml("broken"))
    assert p.thread_key == "sha:" + p.sha256[:32]


def test_kopf_steuerzeichen_entfernt_und_gekuerzt():
    from backend import parse
    raw = b"From: a@b.de\r\nSubject: =?utf-8?b?" + __import__("base64").b64encode(("X\x07Y\x1b" + "z" * 2000).encode()) + b"?=\r\n\r\nx"
    p = parse.parse(raw)
    assert "\x07" not in p.subject and "\x1b" not in p.subject and len(p.subject) <= 998


def test_text_grenze():
    from backend import parse
    raw = b"From: a@b.de\r\nSubject: gross\r\nContent-Type: text/plain\r\n\r\n" + b"Wort " * 400_000
    p = parse.parse(raw)
    assert len(p.body) <= parse.BODY_MAX and len(p.snippet) <= parse.SNIPPET_MAX


def test_cid_bild_ohne_disposition_ist_inline():
    """Manche Programme setzen beim eingebetteten Logo gar keine Disposition, nur Content-ID."""
    from backend import parse
    raw = (b"From: a@b.de\r\nSubject: s\r\nContent-Type: multipart/related; boundary=B\r\n\r\n--B\r\n"
           b"Content-Type: text/html\r\n\r\n<img src=\"cid:x1\">\r\n--B\r\nContent-Type: image/gif\r\nContent-ID: <x1>\r\n"
           b"Content-Transfer-Encoding: base64\r\n\r\nR0lGODlhAQABAAAAACw=\r\n--B--\r\n")
    p = parse.parse(raw)
    assert [(a["inline"], a["cid"]) for a in p.attachments] == [(True, "x1")] and p.has_attachments is False


def test_angehaengtes_bild_mit_cid_bleibt_anhang():
    """Disposition attachment gewinnt: echte Anhänge zählen, auch wenn sie eine Content-ID tragen."""
    from backend import parse
    raw = (b"From: a@b.de\r\nSubject: s\r\nContent-Type: multipart/mixed; boundary=B\r\n\r\n--B\r\n"
           b"Content-Type: text/plain\r\n\r\nHallo\r\n--B\r\nContent-Type: image/jpeg\r\nContent-ID: <f1>\r\n"
           b"Content-Disposition: attachment; filename=foto.jpg\r\n\r\nxx\r\n--B--\r\n")
    assert parse.parse(raw).has_attachments is True


def test_unerwarteter_fehler_wird_fehlerfeld(monkeypatch):
    """Was auch immer beim Zerlegen schiefgeht: Ergebnis mit error und Kopfdaten, keine Ausnahme."""
    from backend import parse

    def boom(msg, p):
        raise KeyError("kaputter Teil")
    monkeypatch.setattr(parse, "_walk", boom)
    p = parse.parse(eml("plain"))
    assert p.error.startswith("KeyError") and p.subject == "Termin morgen" and p.thread_key


def test_antwort_ohne_references_faedelt_ueber_betreff():
    """Manche Programme lassen References weg: „AW: Termin“ landet trotzdem bei „Re: Termin“."""
    from backend import parse
    a = parse.parse(b"From: a@b.de\r\nSubject: AW: Termin morgen\r\nMessage-ID: <x1@b.de>\r\n\r\nok")
    b = parse.parse(b"From: c@d.de\r\nSubject: Re:  termin MORGEN\r\nMessage-ID: <x2@d.de>\r\n\r\nok")
    assert a.thread_key == b.thread_key == "subj:termin morgen"


def test_ohne_praefix_keine_betreff_faedelung():
    from backend import parse
    a = parse.parse(b"From: a@b.de\r\nSubject: Rechnung\r\nMessage-ID: <r1@b.de>\r\n\r\nx")
    b = parse.parse(b"From: c@d.de\r\nSubject: Rechnung\r\nMessage-ID: <r2@d.de>\r\n\r\ny")
    assert a.thread_key == "<r1@b.de>" and b.thread_key == "<r2@d.de>"


@pytest.mark.parametrize("raw, want", [
    # ohne Content-Type, aber UTF-8-Bytes (häufig bei alten/einfachen Programmen)
    (b"From: a@b.de\r\nSubject: s\r\n\r\nTreffen im B\xc3\xbcro\r\n", "Treffen im Büro"),
    # charset=us-ascii angegeben, Inhalt aber UTF-8
    (b"From: a@b.de\r\nSubject: s\r\nContent-Type: text/plain; charset=us-ascii\r\n\r\nGr\xc3\xbc\xc3\x9fe\r\n", "Grüße"),
    # ohne Angabe, Latin-1-Bytes (kein gültiges UTF-8)
    (b"From: a@b.de\r\nSubject: s\r\n\r\nSch\xf6ne Gr\xfc\xdfe\r\n", "Schöne Grüße"),
    # unbekannter Zeichensatz
    (b"From: a@b.de\r\nSubject: s\r\nContent-Type: text/plain; charset=x-quatsch\r\n\r\nK\xc3\xb6ln\r\n", "Köln"),
    # Windows-1252 mit Euro-Zeichen und Anführungszeichen
    (b"From: a@b.de\r\nSubject: s\r\nContent-Type: text/plain; charset=windows-1252\r\n\r\n\x80 5 \x84ok\x93\r\n", "€ 5 „ok“"),
])
def test_zeichensatz_robust(raw, want):
    from backend import parse
    assert parse.parse(raw).body == want


def test_betreff_8bit_ohne_kodierung():
    from backend import parse
    assert parse.parse(b"From: a@b.de\r\nSubject: Gr\xc3\xbc\xc3\x9fe\r\n\r\nx").subject == "Grüße"


def test_ohne_angabe_windows_1252():
    from backend import parse
    assert parse.parse(b"From: a@b.de\r\nSubject: s\r\n\r\n\x80 5 \x84ok\x93\r\n").body == "€ 5 „ok“"


def test_betreff_8bit_latin1():
    from backend import parse
    assert parse.parse(b"From: a@b.de\r\nSubject: Gr\xfc\xdfe aus K\xf6ln\r\n\r\nx").subject == "Grüße aus Köln"


def test_ascii_angabe_mit_umlauten_wird_nicht_zerstoert():
    """Angabe us-ascii, Inhalt mit Umlauten (UTF-8) → keine Ersatzzeichen, sondern Umlaute."""
    from backend import parse
    assert parse.decode_bytes("Grüße".encode(), "us-ascii") == "Grüße"
    assert parse.decode_bytes(b"Gr\xfc\xdfe", "ascii") == "Grüße"
