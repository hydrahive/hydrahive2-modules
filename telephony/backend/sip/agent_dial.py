"""Wählen über eine laufende Anmeldung (PLAN-ANRUFEN-3): gleicher SIP-Socket, eigener RTP-Port, Leitung belegt.

Ausgelagert aus ``agent.py`` (Dateigröße). Die Nummer muss vorher durch ``dialrules.check`` gegangen sein.
"""
from __future__ import annotations

import time
from collections.abc import Callable
from typing import TYPE_CHECKING

from .outbound import OutboundCall

if TYPE_CHECKING:
    from .agent import SipAgent


class NotReady(RuntimeError):
    """Nicht angemeldet – über die Anlage kann gerade nicht gewählt werden."""


class LineBusy(RuntimeError):
    """Es läuft schon ein Anruf (rein oder raus)."""


def dial(agent: SipAgent, number: str, audio: Callable[[str], bytes], *, record: Callable[[dict], None],
         on_end: Callable[[OutboundCall], None] | None = None, **options) -> OutboundCall:
    sock = agent._sock
    if agent.status != "registered" or sock is None or not agent.alive:
        raise NotReady(agent.status)
    if agent.calls.busy():
        raise LineBusy()                                       # früh, damit kein RTP-Port belegt wird
    rtp_sock = agent.calls._bind_rtp(agent._state.local[0])
    if rtp_sock is None:
        raise LineBusy()
    st = agent._state
    local = st.contact or st.local

    def finished(call: OutboundCall) -> None:
        agent.calls.finish_outbound(call)
        extra = {"turns": call.turns, "notes": call.notes, "kind": "assistant"} if call._assistant is not None \
            else {"kind": "greeting"}
        record({"direction": "out", "number": "•••" + call.number[-3:], "result": call.result or "failed",
                "codec": call.codec, "rtp_out": call.rtp_out, "rtp_in": call.rtp_in, "started_at": time.time(),
                **extra})
        if on_end is not None:
            on_end(call)

    call = OutboundCall(sock=sock, target=st.target, local=local, user=st.user, password=st.password,
                        domain=st.domain, number=number, rtp_sock=rtp_sock, audio=audio, on_finish=finished,
                        display_name=st.display_name, **options)
    if not agent.calls.add_outbound(call):
        rtp_sock.close()
        raise LineBusy()
    call.start()
    return call
