"""Minigames — Score-Speicherung, eigene Bestleistung, Bestenliste, Validierung."""
from __future__ import annotations

PREFIX = "/api/modules/minigames"


# ---------------------------------------------------------------- Auth
def test_scores_braucht_auth(client):
    assert client.post(f"{PREFIX}/scores", json={"game_id": "snake", "score": 10}).status_code == 401
    assert client.get(f"{PREFIX}/scores/leaderboard?game_id=snake").status_code == 401


# ---------------------------------------------------------------- Submit + persönlicher Rekord
def test_submit_und_personal_best(client, auth_headers):
    r = client.post(f"{PREFIX}/scores", json={"game_id": "snake", "score": 50}, headers=auth_headers)
    assert r.status_code == 200 and r.json()["is_personal_best"] is True

    # niedriger → kein neuer Rekord
    r = client.post(f"{PREFIX}/scores", json={"game_id": "snake", "score": 30}, headers=auth_headers)
    assert r.json()["is_personal_best"] is False

    # höher → neuer Rekord
    r = client.post(f"{PREFIX}/scores", json={"game_id": "snake", "score": 90}, headers=auth_headers)
    assert r.json()["is_personal_best"] is True


def test_mine_liefert_best_und_recent(client, auth_headers):
    for s in (10, 40, 25):
        client.post(f"{PREFIX}/scores", json={"game_id": "snake", "score": s}, headers=auth_headers)
    data = client.get(f"{PREFIX}/scores/mine?game_id=snake", headers=auth_headers).json()
    assert data["best"] == 40
    assert [r["score"] for r in data["recent"]] == [25, 40, 10]  # neueste zuerst


# ---------------------------------------------------------------- Validierung
def test_unbekanntes_spiel_400(client, auth_headers):
    r = client.post(f"{PREFIX}/scores", json={"game_id": "doom", "score": 10}, headers=auth_headers)
    assert r.status_code == 400


def test_implausibler_score_400(client, auth_headers):
    r = client.post(f"{PREFIX}/scores", json={"game_id": "snake", "score": 999999999}, headers=auth_headers)
    assert r.status_code == 400


def test_negativer_score_abgelehnt(client, auth_headers):
    # pydantic ge=0 → 422
    r = client.post(f"{PREFIX}/scores", json={"game_id": "snake", "score": -5}, headers=auth_headers)
    assert r.status_code == 422


def test_mine_unbekanntes_spiel_400(client, auth_headers):
    assert client.get(f"{PREFIX}/scores/mine?game_id=doom", headers=auth_headers).status_code == 400


# ---------------------------------------------------------------- Per-User-Isolation
def test_best_ist_user_scoped(client, auth_headers, other_headers):
    client.post(f"{PREFIX}/scores", json={"game_id": "snake", "score": 80}, headers=auth_headers)
    # 'other' hat noch nichts gespielt
    data = client.get(f"{PREFIX}/scores/mine?game_id=snake", headers=other_headers).json()
    assert data["best"] == 0 and data["recent"] == []


# ---------------------------------------------------------------- Bestenliste (global)
def test_leaderboard_top_score_je_user(client, auth_headers, other_headers, third_headers):
    # testuser: bester 70 (zwei Einträge), other: 90, third: 40
    client.post(f"{PREFIX}/scores", json={"game_id": "snake", "score": 30}, headers=auth_headers)
    client.post(f"{PREFIX}/scores", json={"game_id": "snake", "score": 70}, headers=auth_headers)
    client.post(f"{PREFIX}/scores", json={"game_id": "snake", "score": 90}, headers=other_headers)
    client.post(f"{PREFIX}/scores", json={"game_id": "snake", "score": 40}, headers=third_headers)

    lb = client.get(f"{PREFIX}/scores/leaderboard?game_id=snake", headers=auth_headers).json()
    # ein Eintrag je User, absteigend, mit Rang
    assert [(e["rank"], e["user"], e["score"]) for e in lb] == [
        (1, "other", 90), (2, "testuser", 70), (3, "third", 40),
    ]


def test_leaderboard_limit(client, auth_headers, other_headers, third_headers):
    client.post(f"{PREFIX}/scores", json={"game_id": "snake", "score": 10}, headers=auth_headers)
    client.post(f"{PREFIX}/scores", json={"game_id": "snake", "score": 20}, headers=other_headers)
    client.post(f"{PREFIX}/scores", json={"game_id": "snake", "score": 30}, headers=third_headers)
    lb = client.get(f"{PREFIX}/scores/leaderboard?game_id=snake&limit=2", headers=auth_headers).json()
    assert len(lb) == 2 and lb[0]["score"] == 30 and lb[1]["score"] == 20


def test_leaderboard_leer_wenn_keine_scores(client, auth_headers):
    assert client.get(f"{PREFIX}/scores/leaderboard?game_id=snake", headers=auth_headers).json() == []
