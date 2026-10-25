"""Ablauf eines ausgehenden Anrufs (PLAN-ANRUFEN-3): Wählen bis zur Endantwort, dann Gespräch.

Getrennt von ``outbound.py`` (Zustand, SIP-Bausteine), damit beide Dateien klein bleiben.
"""
from __future__ import annotations

import queue
import threading
import time
from typing import TYPE_CHECKING

from . import digest, message, sdp

if TYPE_CHECKING:
    from .outbound import OutboundCall

_T1, _T2 = 0.5, 4.0


def _next(call: OutboundCall, timeout: float) -> message.Message | None:
    try:
        return call._responses.get(timeout=max(0.0, timeout))
    except queue.Empty:
        return None


def _cancel(call: OutboundCall, result: str) -> None:
    """CANCEL (gleicher Branch/CSeq) und auf 487 bzw. die Endantwort warten; ACK dafür."""
    raw = call._cancel()
    end, wait, nxt = time.monotonic() + 8.0, _T1, 0.0
    while time.monotonic() < end:
        if time.monotonic() >= nxt:
            call._send(raw)
            nxt, wait = time.monotonic() + wait, min(wait * 2, _T2)
        r = _next(call, 0.05)
        if r is None:
            continue
        cseq = r.header("cseq") or ""
        if cseq.endswith(" INVITE") and r.status >= 300:
            call._ack_error(r)
            break
        if cseq.endswith(" INVITE") and r.status == 200:           # Abgenommen, während wir abbrechen
            _confirm(call, r)
            call._bye()
            break
    call._end(result)


def _confirm(call: OutboundCall, ok: message.Message) -> None:
    from .outbound import _tag

    call.remote_tag = _tag(ok.header("to"))
    contact = (ok.header("contact") or "").strip().lstrip("<").split(">")[0]
    if contact.startswith("sip:"):
        call.remote_uri = contact
    headers = call._base("ACK", call.cseq, "z9hG4bK" + call.call_id[:8] + "ack", call.remote_tag)
    call._ack_raw = message.build_request("ACK", call.remote_uri, headers)
    call._send(call._ack_raw)


def dial(call: OutboundCall) -> message.Message | None:
    """Bis zur Endantwort. Gibt das 200 OK zurück (Gespräch beginnt) oder None (Ergebnis steht in ``call.result``)."""
    raw, tried_auth = call._invite(None), False
    start = time.monotonic()
    nxt, wait, provisional = 0.0, _T1, False
    ring_deadline = start + call._ring_timeout
    while True:
        now = time.monotonic()
        if call._hangup.is_set():
            if provisional:
                _cancel(call, "cancelled")
            else:
                call._end("cancelled")
            return None
        if not provisional and now - start >= call._invite_timeout:
            call._end("unreachable")
            return None
        if provisional and now >= ring_deadline:
            _cancel(call, "no_answer")
            return None
        if not provisional and now >= nxt:
            call._send(raw)
            nxt, wait = now + wait, min(wait * 2, _T2)
        r = _next(call, 0.05)
        if r is None or not (r.header("cseq") or "").endswith(" INVITE"):
            continue
        if int((r.header("cseq") or "0").split()[0]) != call.cseq:
            continue
        if r.status < 200:
            provisional = True
            if r.status in (180, 183):
                call.state = "ringing"
            continue
        if r.status == 200:
            call.state = "answered"
            _confirm(call, r)
            return r
        call._ack_error(r)
        if r.status in (401, 407) and not tried_auth:
            try:
                auth = call.digest_header(r)
            except digest.Unsupported:
                call._end("auth_failed")
                return None
            raw, tried_auth = call._invite(auth), True
            start, nxt, wait, provisional = time.monotonic(), 0.0, _T1, False
            ring_deadline = start + call._ring_timeout
            continue
        call._end("auth_failed" if r.status in (401, 407) else call.final_result(r.status))
        return None


def talk(call: OutboundCall, ok: message.Message) -> None:
    try:
        offer = sdp.parse_offer(ok.body)
        pt, call.codec = sdp.choose(offer)
    except sdp.SdpError:
        call._end("codec")
        call._bye()
        return
    threading.Thread(target=call._listen, args=(offer.address,), daemon=True).start()
    if call._assistant is not None:
        _converse(call, offer, pt)
        return
    call._stream(offer, pt)
    if call._ended.is_set():
        return                                                  # Gegenseite hat aufgelegt (BYE schon beantwortet)
    if call._hangup.is_set():
        call._end("hung_up")
    elif not call._ended.wait(0.5):
        call._end("answered")
    if call.result != "remote_hangup":
        call._bye()


def _converse(call: OutboundCall, offer: sdp.Offer, pt: int) -> None:
    """Gespräch mit Auftrag (3b): Gesprächsschleife aus 2b mit ausgehendem Systemtext (agent/prompt_out.py)."""
    from ..agent import conversation, prompt_out
    from ..media import g711, rtp

    a = call._assistant
    limit = call._max

    def say(text: str, interrupted) -> bool:
        audio = a["tts"](text, call.codec)[: int(limit * 8000)]
        sent = rtp.send_stream(call.rtp_sock, (offer.address, offer.port), audio, payload_type=pt,
                               stop=lambda: interrupted() or call._ended.is_set() or call._hangup.is_set(),
                               silence=g711.SILENCE[call.codec])
        call.rtp_out += sent
        return sent * 160 >= len(audio)

    options = {"max_seconds": conversation.ASSISTANT_MAX_SECONDS, "messages": prompt_out.build_messages,
               "greet": prompt_out.greeting, "opening": True, **a.get("options", {})}
    conv = conversation.Conversation(cfg=a["cfg"], llm=a["llm"], stt=a["stt"], say=say, frames=call._voice,
                                     hangup=lambda: call._ended.is_set() or call._hangup.is_set(), **options)
    result = conv.run()
    call.turns, call.notes = result.turns, result.notes
    if call._ended.is_set():
        return                                                  # Gegenseite hat aufgelegt (BYE schon beantwortet)
    call._end("hung_up" if call._hangup.is_set() else result.reason)
    call._bye()
