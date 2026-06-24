"""Schach-LLM-Route — Auth, Validierung, Durchreichen an choose_move."""
from __future__ import annotations

PREFIX = "/api/modules/boardgames"
MOVES = ["e7e5", "g8f6"]


def _body(**over):
    body = {"model": "test-model", "fen": "startfen", "moves": MOVES, "history": ["e2e4"]}
    body.update(over)
    return body


def test_llm_move_braucht_auth(client):
    assert client.post(f"{PREFIX}/chess/llm-move", json=_body()).status_code == 401


def test_llm_move_gueltiger_zug(client, auth_headers, monkeypatch):
    import backend.chess_routes as routes

    async def fake_choose(*, model, fen, moves, history):
        assert model == "test-model"
        assert moves == ["e7e5", "g8f6"]  # lowercased + getrimmt
        return {"move": "e7e5", "index": 0, "source": "llm"}

    monkeypatch.setattr(routes, "choose_move", fake_choose)
    r = client.post(f"{PREFIX}/chess/llm-move", json=_body(), headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == {"move": "e7e5", "index": 0, "source": "llm"}


def test_llm_move_invalid_kein_fehlerstatus(client, auth_headers, monkeypatch):
    import backend.chess_routes as routes

    async def fake_choose(*, model, fen, moves, history):
        return {"move": None, "index": -1, "source": "invalid"}

    monkeypatch.setattr(routes, "choose_move", fake_choose)
    r = client.post(f"{PREFIX}/chess/llm-move", json=_body(), headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["source"] == "invalid"


def test_llm_move_leere_zugliste_422(client, auth_headers):
    # moves min_length=1 → Pydantic-Validierungsfehler
    r = client.post(f"{PREFIX}/chess/llm-move", json=_body(moves=[]), headers=auth_headers)
    assert r.status_code == 422
