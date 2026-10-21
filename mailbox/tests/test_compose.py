"""M2 Schritt 2: Mail bauen – neu, Antwort, Allen antworten, Weiterleiten, Signatur, Anhänge, Bcc verborgen."""
from __future__ import annotations

import email
import email.policy

import pytest
from conftest import eml

ACC = {"address": "till@example.net", "sender_name": "Till Beispiel", "signature": "Gruß\nTill"}


def _msg(raw: bytes):
    return email.message_from_bytes(raw, policy=email.policy.default)


def test_neue_mail():
    from backend import compose
    r = compose.build(ACC, to="Anna <anna@example.org>", cc="b@x.de", bcc="geheim@x.de", subject="Hallo",
                      text="Hi Anna")
    m = _msg(r.raw)
    assert m["From"] == "Till Beispiel <till@example.net>" and m["To"] == "Anna <anna@example.org>" and m["Cc"] == "b@x.de"
    assert m["Bcc"] is None and b"geheim@x.de" not in r.raw, "Bcc nie in der Mail selbst"
    assert r.envelope == ["anna@example.org", "b@x.de", "geheim@x.de"]
    assert m["Message-ID"].endswith("@example.net>") and m["Date"]
    body = m.get_body(("plain",)).get_content()
    assert body.startswith("Hi Anna") and body.rstrip().endswith("-- \nGruß\nTill")


def test_html_teil_ist_maskiert():
    from backend import compose
    m = _msg(compose.build(ACC, to="a@x.de", subject="s", text="<b>nicht fett</b> & mehr").raw)
    html = m.get_body(("html",)).get_content()
    assert "&lt;b&gt;nicht fett&lt;/b&gt; &amp; mehr" in html and "<b>nicht fett</b>" not in html


def test_ohne_empfaenger_fehler():
    from backend import compose
    with pytest.raises(compose.ComposeError):
        compose.build(ACC, to="", cc="", bcc="", subject="s", text="x")


@pytest.mark.parametrize("subject", ["a\r\nBcc: x@y.de", "a\nb", "x\x00"])
def test_betreff_ohne_kopfzeilen_injektion(subject):
    from backend import compose
    with pytest.raises(compose.ComposeError):
        compose.build(ACC, to="a@x.de", subject=subject, text="x")


def test_antwort():
    from backend import compose
    orig = eml("attachments")          # Re: Unterlagen, In-Reply-To orig-1, References orig-0 orig-1
    r = compose.reply(ACC, orig, text="Danke!", reply_all=False)
    m = _msg(r.raw)
    assert m["Subject"] == "Re: Unterlagen", "kein doppeltes Re:"
    assert m["To"] == "Kanzlei <post@kanzlei.example>" and m["Cc"] is None
    assert m["In-Reply-To"] == "<att-1@kanzlei.example>"
    assert m["References"].split() == ["<orig-0@example.net>", "<orig-1@example.net>", "<att-1@kanzlei.example>"]
    body = m.get_body(("plain",)).get_content()
    assert body.startswith("Danke!") and "schrieb Kanzlei" in body and "> Anbei die Unterlagen." in body


def test_antwort_an_alle_ohne_mich():
    from backend import compose
    r = compose.reply(ACC, eml("attachments"), text="ok", reply_all=True)
    m = _msg(r.raw)
    assert m["To"] == "Kanzlei <post@kanzlei.example>"
    assert sorted(x.strip() for x in m["Cc"].split(",")) == ["akte@kanzlei.example", "frau@example.net"]
    assert "till@example.net" not in r.envelope


def test_antwort_nutzt_reply_to():
    from backend import compose
    orig = b"From: news@shop.example\r\nReply-To: Support <help@shop.example>\r\nSubject: Frage\r\nMessage-ID: <q1@shop>\r\n\r\nx"
    m = _msg(compose.reply(ACC, orig, text="x", reply_all=False).raw)
    assert m["To"] == "Support <help@shop.example>" and m["Subject"] == "Re: Frage"


@pytest.mark.parametrize("subj, want", [("AW: Termin", "AW: Termin"), ("Termin", "Re: Termin"), ("re: x", "re: x"),
                                        ("WG: x", "Re: WG: x"), ("", "Re: (ohne Betreff)")])
def test_antwort_praefix(subj, want):
    from backend import compose
    orig = f"From: a@x.de\r\nSubject: {subj}\r\nMessage-ID: <p@x>\r\n\r\nx".encode()
    assert _msg(compose.reply(ACC, orig, text="x", reply_all=False).raw)["Subject"] == want


def test_weiterleiten_mit_anhaengen():
    from backend import compose
    r = compose.forward(ACC, eml("attachments"), to="neu@x.de", text="FYI", with_attachments=True)
    m = _msg(r.raw)
    assert m["Subject"] == "WG: Re: Unterlagen" and m["In-Reply-To"] is None
    names = [p.get_filename() for p in m.iter_attachments()]
    assert "Vertrag ä.pdf" in names
    body = m.get_body(("plain",)).get_content()
    assert "---------- Weitergeleitete Nachricht ----------" in body and "Von: Kanzlei <post@kanzlei.example>" in body


def test_weiterleiten_ohne_anhaenge():
    from backend import compose
    m = _msg(compose.forward(ACC, eml("attachments"), to="neu@x.de", text="", with_attachments=False).raw)
    assert list(m.iter_attachments()) == []


def test_eigene_anhaenge_und_grenze():
    from backend import compose
    m = _msg(compose.build(ACC, to="a@x.de", subject="s", text="x",
                           attachments=[("../../etc/Bericht ä.pdf", "application/pdf", b"%PDF-1.4 x")]).raw)
    att = list(m.iter_attachments())
    assert [a.get_filename() for a in att] == ["Bericht ä.pdf"] and att[0].get_content() == b"%PDF-1.4 x"
    with pytest.raises(compose.ComposeError):
        compose.build(ACC, to="a@x.de", subject="s", text="x",
                      attachments=[("gross.bin", "application/octet-stream", b"0" * (compose.MAX_TOTAL + 1))])


@pytest.mark.parametrize("ctype", ["text/html", "nicht/gültig\r\nX: 1", "", "application/x-msdownload"])
def test_anhang_typ_wird_harmlos(ctype):
    from backend import compose
    m = _msg(compose.build(ACC, to="a@x.de", subject="s", text="x", attachments=[("d.bin", ctype, b"x")]).raw)
    a = list(m.iter_attachments())[0]
    assert "\n" not in a.get_content_type() and a.get_content_type() in ("application/octet-stream", "application/x-msdownload")


def test_ohne_absendername_und_signatur():
    from backend import compose
    m = _msg(compose.build({"address": "a@x.de", "sender_name": "", "signature": ""}, to="b@x.de", subject="s",
                           text="x").raw)
    assert m["From"] == "a@x.de" and "-- \n" not in m.get_body(("plain",)).get_content()


@pytest.mark.parametrize("val", ["<a@b>\r\nBcc: opfer@x.de", "<a@b>\nX: 1", "<a\x00@b>"])
def test_extra_kopfzeilen_ohne_injektion(val):
    from backend import compose
    with pytest.raises(compose.ComposeError):
        compose.build(ACC, to="a@x.de", subject="s", text="x", extra_headers={"In-Reply-To": val})


def test_boese_message_id_im_original_landet_nicht_roh():
    """Gefaltete/kaputte Message-ID im Original: Antwort entsteht, ohne zusätzliche Kopfzeile."""
    from backend import compose
    orig = (b"From: a@x.de\r\nSubject: s\r\nMessage-ID: <ok@x>\r\nReferences: <r1@x>\r\n <r2@x>\r\n\tBcc: opfer@x.de\r\n"
            b"\r\nbody")
    r = compose.reply(ACC, orig, text="x", reply_all=False)
    m = _msg(r.raw)
    assert m["Bcc"] is None and "opfer@x.de" not in r.envelope
    assert m["References"].split() == ["<r1@x>", "<r2@x>", "<ok@x>"]
