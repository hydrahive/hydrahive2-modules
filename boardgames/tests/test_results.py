"""Brettspiele — Ergebnis-Speicherung, eigene Bilanz, Bestenliste, Validierung."""
from __future__ import annotations

PREFIX = "/api/modules/boardgames"


def _post(client, headers, game="chess", mode="ai", result="win", opp=""):
    return client.post(f"{PREFIX}/results",
                       json={"game_id": game, "mode": mode, "result": result, "opponent": opp},
                       headers=headers)


# ---------------------------------------------------------------- Auth
def test_results_braucht_auth(client):
    assert client.post(f"{PREFIX}/results", json={"game_id": "chess", "mode": "ai", "result": "win"}).status_code == 401
    assert client.get(f"{PREFIX}/results/leaderboard?game_id=chess").status_code == 401


# ---------------------------------------------------------------- Submit + Bilanz
def test_submit_und_record(client, auth_headers):
    _post(client, auth_headers, result="win")
    _post(client, auth_headers, result="win")
    _post(client, auth_headers, result="loss")
    _post(client, auth_headers, result="draw")
    rec = client.get(f"{PREFIX}/results/mine?game_id=chess", headers=auth_headers).json()
    assert rec == {"win": 2, "loss": 1, "draw": 1, "total": 4}


def test_record_nach_modus_gefiltert(client, auth_headers):
    _post(client, auth_headers, mode="ai", result="win")
    _post(client, auth_headers, mode="hotseat", result="loss")
    ai = client.get(f"{PREFIX}/results/mine?game_id=chess&mode=ai", headers=auth_headers).json()
    assert ai["win"] == 1 and ai["loss"] == 0 and ai["total"] == 1


# ---------------------------------------------------------------- Validierung
def test_unbekanntes_spiel_400(client, auth_headers):
    assert _post(client, auth_headers, game="go").status_code == 400


def test_unbekannter_modus_400(client, auth_headers):
    assert _post(client, auth_headers, mode="online").status_code == 400


def test_unbekanntes_ergebnis_400(client, auth_headers):
    assert _post(client, auth_headers, result="maybe").status_code == 400


def test_mine_unbekanntes_spiel_400(client, auth_headers):
    assert client.get(f"{PREFIX}/results/mine?game_id=go", headers=auth_headers).status_code == 400


# ---------------------------------------------------------------- Per-User-Isolation
def test_record_user_scoped(client, auth_headers, other_headers):
    _post(client, auth_headers, result="win")
    rec = client.get(f"{PREFIX}/results/mine?game_id=chess", headers=other_headers).json()
    assert rec["total"] == 0


# ---------------------------------------------------------------- Bestenliste (global, Siege)
def test_leaderboard_meiste_siege(client, auth_headers, other_headers, third_headers):
    # testuser 2 Siege, other 3 Siege, third 1 Sieg + 2 Niederlagen
    for _ in range(2): _post(client, auth_headers, result="win")
    for _ in range(3): _post(client, other_headers, result="win")
    _post(client, third_headers, result="win")
    _post(client, third_headers, result="loss")
    _post(client, third_headers, result="loss")
    lb = client.get(f"{PREFIX}/results/leaderboard?game_id=chess", headers=auth_headers).json()
    assert [(e["rank"], e["user"], e["wins"]) for e in lb] == [
        (1, "other", 3), (2, "testuser", 2), (3, "third", 1),
    ]


def test_leaderboard_nur_mit_siegen(client, auth_headers, other_headers):
    # other hat nur Niederlagen → taucht nicht auf
    _post(client, auth_headers, result="win")
    _post(client, other_headers, result="loss")
    lb = client.get(f"{PREFIX}/results/leaderboard?game_id=chess", headers=auth_headers).json()
    assert len(lb) == 1 and lb[0]["user"] == "testuser"


def test_leaderboard_leer(client, auth_headers):
    assert client.get(f"{PREFIX}/results/leaderboard?game_id=chess", headers=auth_headers).json() == []
