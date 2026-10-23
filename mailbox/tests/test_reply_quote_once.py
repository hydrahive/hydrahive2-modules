"""Befund 23.10.: Das Schreibfenster legt das Zitat schon in den Text (compose/prefill), reply/forward hängten es beim
Senden noch einmal an → Original doppelt zitiert. Ab M3b: Zitat nur anhängen, wenn der Text es nicht schon enthält."""
from __future__ import annotations

import email
import email.policy

from conftest import eml

ACC = {"address": "till@example.net", "sender_name": "", "signature": ""}


def _text(built) -> str:
    return email.message_from_bytes(built.raw, policy=email.policy.default).get_body(("plain",)).get_content()


def test_antwort_aus_dem_schreibfenster_zitiert_einmal():
    from backend import reply
    raw = eml("attachments")
    pre = reply.prefill(ACC, raw, "reply")
    txt = _text(reply.reply(ACC, raw, text="Danke\n\n" + pre["quote"], reply_all=False))
    assert txt.count(pre["quote"].splitlines()[0]) == 1 and txt.startswith("Danke")


def test_antwort_ohne_zitat_im_text_bekommt_es_angehaengt():
    from backend import reply
    raw = eml("attachments")
    pre = reply.prefill(ACC, raw, "reply")
    txt = _text(reply.reply(ACC, raw, text="Nur kurz: danke!", reply_all=False))
    assert txt.count(pre["quote"].splitlines()[0]) == 1


def test_gekuerztes_zitat_bleibt_wie_geschrieben():
    """Wer im Zitat kürzt, will nicht das ganze Original noch einmal darunter."""
    from backend import reply
    raw = eml("attachments")
    head = reply.prefill(ACC, raw, "reply")["quote"].splitlines()[0]
    txt = _text(reply.reply(ACC, raw, text=f"Ok\n\n{head}\n> (gekürzt)", reply_all=False))
    assert txt.count(head) == 1 and "(gekürzt)" in txt


def test_weiterleiten_aus_dem_schreibfenster_einmal():
    from backend import reply
    raw = eml("attachments")
    pre = reply.prefill(ACC, raw, "forward")
    built = reply.forward(ACC, raw, to="neu@x.de", text="Zur Info\n\n" + pre["quote"], with_attachments=False)
    assert _text(built).count("Weitergeleitete Nachricht") == 1
    built = reply.forward(ACC, raw, to="neu@x.de", text="Zur Info", with_attachments=False)
    assert _text(built).count("Weitergeleitete Nachricht") == 1
