"""S6 Chat am Gehäuse: Nachricht über den Kern-Weg (handle_incoming), eigene Session, Verlauf (SPEC-STATUSZENTRALE.md, S6)."""
from __future__ import annotations

import asyncio
import threading
import time

import pytest

from backend import chat

SECRET = "geheim-token-123456"


class FakeHandle:
    def __init__(self, reply="Hallo Till", exc=None, delay=0.0):
        self.events, self.reply, self.exc, self.delay = [], reply, exc, delay

    async def __call__(self, event):
        self.events.append(event)
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.exc:
            raise self.exc
        return self.reply


class Event:
    def __init__(self, **kw):
        self.__dict__.update(kw)


@pytest.fixture(autouse=True)
def _ohne_kern(monkeypatch):
    """Ereignis-Objekt wie IncomingEvent, ohne den Kern zu brauchen. Der Lock muss nach jedem Test frei sein."""
    monkeypatch.setattr(chat, "_hh_event", lambda **kw: Event(**kw))
    yield
    assert not chat._lock.locked(), "Lock bleibt nach einem Aufruf nie hängen"


def _send(*a, **kw):
    kw.setdefault("make_event", lambda **e: Event(**e))
    return chat.send(*a, **kw)


def test_event_wie_ein_kanal(tmp_path):
    h = FakeHandle()
    r = _send("till", "  Wie warm ist es?  ", handle=h, data_dir=tmp_path)
    assert r == "Hallo Till"
    [e] = h.events
    assert (e.channel, e.external_user_id, e.target_username, e.sender_name, e.text) == \
        ("vitrine", "gehaeuse", "till", "Gehäuse", "Wie warm ist es?")


@pytest.mark.parametrize("text", ["", "   ", "x" * 2001, None, 5])
def test_text_grenzen(tmp_path, text):
    h = FakeHandle()
    with pytest.raises(chat.ChatInvalid):
        _send("till", text, handle=h, data_dir=tmp_path)
    assert h.events == []


def test_lange_antwort_gekuerzt(tmp_path):
    r = _send("till", "x", handle=FakeHandle(reply="a" * 9000), data_dir=tmp_path)
    assert len(r) <= chat.REPLY_MAX and r.endswith("…")


def test_leere_antwort_wird_hinweis(tmp_path):
    assert _send("till", "x", handle=FakeHandle(reply=None), data_dir=tmp_path) == chat.NO_REPLY


def test_zweite_nachricht_waehrend_laufender_ist_busy(tmp_path):
    inside, release = threading.Event(), threading.Event()

    async def slow(event):
        inside.set()                                         # erste Nachricht ist sicher im Lock
        while not release.is_set():
            await asyncio.sleep(0.01)
        return "erste fertig"
    t = threading.Thread(target=_send, args=("till", "erste"), kwargs={"handle": slow, "data_dir": tmp_path})
    t.start()
    assert inside.wait(5)
    other = FakeHandle()
    try:
        with pytest.raises(chat.ChatBusy):
            _send("till", "zweite", handle=other, data_dir=tmp_path)
    finally:
        release.set()
        t.join(5)
    assert other.events == [], "zweite geht gar nicht erst an den Kern"
    assert _send("till", "dritte", handle=other, data_dir=tmp_path) == "Hallo Till", "danach wieder frei"


def test_kern_meldet_laufende_session_busy(tmp_path):
    h = FakeHandle(exc=RuntimeError("Session läuft bereits — Nachricht ignoriert"))
    with pytest.raises(chat.ChatBusy):
        _send("till", "x", handle=h, data_dir=tmp_path)


def test_anderer_fehler_unavailable(tmp_path):
    with pytest.raises(chat.ChatUnavailable):
        _send("till", "x", handle=FakeHandle(exc=RuntimeError("kaputt")), data_dir=tmp_path)


def test_chat_busy_datei_nur_waehrend_der_antwort(tmp_path):
    seen = {}

    async def h(event):
        seen["during"] = (tmp_path / chat.BUSY_FILE).exists()
        return "ok"
    _send("till", "x", handle=h, data_dir=tmp_path)
    assert seen["during"] is True and not (tmp_path / chat.BUSY_FILE).exists()
    with pytest.raises(chat.ChatUnavailable):
        _send("till", "x", handle=FakeHandle(exc=ValueError("weg")), data_dir=tmp_path)
    assert not (tmp_path / chat.BUSY_FILE).exists(), "auch bei Fehler weg"


# --- Verlauf -------------------------------------------------------------------------------------------------------

class Msg:
    def __init__(self, role, content):
        self.role, self.content = role, content


def test_verlauf_nur_text_ohne_werkzeug_und_denken():
    msgs = [Msg("user", "Wie warm?"),
            Msg("assistant", [{"type": "codex_reasoning", "encrypted_content": "x"},
                              {"type": "thinking", "text": "ich denke laut nach"},           # Denken mit text-Feld
                              {"type": "tool_use", "name": "ha_get_state", "input": {}, "text": "intern"}]),
            Msg("user", [{"type": "tool_result", "content": "22,4"}]),
            Msg("assistant", [{"type": "text", "text": "22,4 °C im Wohnzimmer."}]),
            Msg("system", "intern")]
    out = chat.history("till", find=lambda user: "sid", tail=lambda sid, n: msgs, secrets=lambda u: set(), n=20)
    assert out == [{"role": "user", "text": "Wie warm?"}, {"role": "assistant", "text": "22,4 °C im Wohnzimmer."}]


def test_verlauf_geschwaerzt_und_gekuerzt():
    msgs = [Msg("assistant", [{"type": "text", "text": f"Token {SECRET} " + "b" * 9000}])]
    [m] = chat.history("till", find=lambda u: "sid", tail=lambda sid, n: msgs, secrets=lambda u: {SECRET}, n=20)
    assert SECRET not in m["text"] and len(m["text"]) <= chat.REPLY_MAX


def test_verlauf_ohne_session_leer_und_legt_nichts_an():
    calls = []
    out = chat.history("till", find=lambda u: None, tail=lambda sid, n: calls.append(sid) or [], secrets=lambda u: set())
    assert out == [] and calls == []


def test_verlauf_fragt_hoechstens_n_mal_so_viele_nachrichten():
    asked = {}

    def tail(sid, n):
        asked["n"] = n
        return []
    chat.history("till", find=lambda u: "sid", tail=tail, secrets=lambda u: set(), n=20)
    assert 20 <= asked["n"] <= 200, "Werkzeug-Nachrichten dazwischen – aber nie die ganze Session"
