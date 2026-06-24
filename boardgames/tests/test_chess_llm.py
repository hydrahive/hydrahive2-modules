"""LLM-Gegner — Zug-Extraktion, constrained Auswahl, Fallback-Verhalten.

`complete()` wird durchgehend gemockt — keine echten Netz-/LLM-Calls.
"""
from __future__ import annotations

import pytest

from backend import chess_llm

ALLOWED = ["e7e5", "g8f6", "d7d5", "e7e8q"]


# ---------------------------------------------------------------- extract_move
def test_extract_sauberes_json():
    assert chess_llm.extract_move('{"move": "e7e5"}', ALLOWED) == "e7e5"


def test_extract_json_in_codeblock():
    raw = "Hier mein Zug:\n```json\n{\"move\": \"g8f6\"}\n```"
    assert chess_llm.extract_move(raw, ALLOWED) == "g8f6"


def test_extract_strippt_thinking():
    raw = "<think>Ich überlege... e7e5 sieht gut aus</think>{\"move\": \"d7d5\"}"
    assert chess_llm.extract_move(raw, ALLOWED) == "d7d5"


def test_extract_blanker_uci_token():
    # Modell hält sich nicht ans JSON-Format, nennt aber einen erlaubten Zug
    assert chess_llm.extract_move("Ich spiele e7e5.", ALLOWED) == "e7e5"


def test_extract_case_insensitiv_kanonisiert():
    # Großschreibung wird auf die kanonische (Listen-)Form normalisiert
    assert chess_llm.extract_move('{"move": "E7E5"}', ALLOWED) == "e7e5"


def test_extract_promotion():
    assert chess_llm.extract_move('{"move": "e7e8q"}', ALLOWED) == "e7e8q"


def test_extract_illegaler_zug_ist_none():
    # h2h4 ist nicht in der erlaubten Liste → Halluzination
    assert chess_llm.extract_move('{"move": "h2h4"}', ALLOWED) is None


def test_extract_muell_ist_none():
    assert chess_llm.extract_move("Ich kapituliere!", ALLOWED) is None


def test_extract_leerer_text_ist_none():
    assert chess_llm.extract_move("", ALLOWED) is None


# ---------------------------------------------------------------- build_prompt
def test_prompt_enthaelt_alle_zuege_und_fen():
    p = chess_llm.build_prompt("startfen", ALLOWED, ["e2e4"])
    for mv in ALLOWED:
        assert mv in p
    assert "startfen" in p
    assert "e2e4" in p


# ---------------------------------------------------------------- choose_move
@pytest.mark.asyncio
async def test_choose_gueltiger_zug(monkeypatch):
    async def fake_complete(messages, **kw):
        return '{"move": "g8f6"}'
    monkeypatch.setattr(chess_llm, "complete", fake_complete)
    out = await chess_llm.choose_move(model="m", fen="f", moves=ALLOWED, history=[])
    assert out == {"move": "g8f6", "index": 1, "source": "llm"}


@pytest.mark.asyncio
async def test_choose_halluzination_ist_invalid(monkeypatch):
    async def fake_complete(messages, **kw):
        return '{"move": "a1a8"}'  # nicht erlaubt
    monkeypatch.setattr(chess_llm, "complete", fake_complete)
    out = await chess_llm.choose_move(model="m", fen="f", moves=ALLOWED, history=[])
    assert out == {"move": None, "index": -1, "source": "invalid"}


@pytest.mark.asyncio
async def test_choose_llm_exception_ist_invalid(monkeypatch):
    async def boom(messages, **kw):
        raise RuntimeError("provider down")
    monkeypatch.setattr(chess_llm, "complete", boom)
    out = await chess_llm.choose_move(model="m", fen="f", moves=ALLOWED, history=[])
    assert out == {"move": None, "index": -1, "source": "invalid"}


@pytest.mark.asyncio
async def test_choose_leere_zugliste_ist_invalid(monkeypatch):
    called = False

    async def fake_complete(messages, **kw):
        nonlocal called
        called = True
        return '{"move": "e7e5"}'
    monkeypatch.setattr(chess_llm, "complete", fake_complete)
    out = await chess_llm.choose_move(model="m", fen="f", moves=[], history=[])
    assert out == {"move": None, "index": -1, "source": "invalid"}
    assert called is False  # kein LLM-Call bei leerer Liste
