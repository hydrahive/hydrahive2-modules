"""Schnittstellen „Programm“ (PLAN-PROGRAMM.md): lesen alle mit Modul, ändern nur mit radiostream.moderate
(Entscheidung B), „Ausgeschlossen von Alles“ nur radiostream.control. Jede Änderung nimmt erst den vorgeladenen Titel
zurück (preload.changing)."""
from __future__ import annotations

import pytest
from backend import preload, program
from conftest import MOD_PREFIX as P


def _track(tid, genre="Pop", artist=None, rel=None):
    from hydrahive.db.connection import db
    with db() as conn:
        conn.execute("INSERT INTO module_radiostream_tracks (track_id, source_id, rel_path, size, mtime, artist, title, "
                     "genre, format, duration_s, state, first_seen, last_seen) VALUES (?, 'main', ?, 1, 1, ?, 'T', ?, "
                     "'mp3', 200, 'ok', 'x', 'x')", (tid, rel or f"{artist or tid}/{tid}.mp3", artist or tid, genre))
        conn.commit()


@pytest.fixture
def flushes(monkeypatch):
    calls: list[int] = []
    monkeypatch.setattr(preload, "flush", lambda: calls.append(1))
    return calls


@pytest.fixture
def moderator(db_ready):
    from hydrahive.access import grants
    from hydrahive.api.middleware.users import get_by_username
    uid = get_by_username("testuser")["user_id"]
    grants.grant("radiostream.moderate", "user", uid, "use", actor_id="test")
    yield
    grants.revoke("radiostream.moderate", "user", uid, actor_id="test")


CHANGES = [
    ("post", "/playlists", {"name": "A"}),
    ("post", "/mixes", {"name": "M", "rules": {}, "allow_long": False}),
    ("put", "/program", {"mode": "all"}),
    ("post", "/queue", {"track_id": "t1"}),
]


@pytest.mark.parametrize("method,path,body", CHANGES)
def test_aendern_ohne_moderieren_403(client, user_headers, flushes, db_ready, method, path, body):
    _track("t1")
    r = getattr(client, method)(f"{P}{path}", headers=user_headers, json=body)
    assert r.status_code == 403 and flushes == []


@pytest.mark.parametrize("method,path,body", CHANGES)
def test_aendern_mit_moderieren(client, user_headers, flushes, moderator, method, path, body):
    _track("t1")
    r = getattr(client, method)(f"{P}{path}", headers=user_headers, json=body)
    assert r.status_code in (200, 201), r.text


def _setup_everything(client, admin_headers):
    _track("t1")
    pl = client.post(f"{P}/playlists", headers=admin_headers, json={"name": "A"}).json()
    client.post(f"{P}/playlists/{pl['id']}/items", headers=admin_headers, json={"track_ids": ["t1", "t1"]})
    m = client.post(f"{P}/mixes", headers=admin_headers, json={"name": "M", "rules": {}, "allow_long": False}).json()
    client.post(f"{P}/queue", headers=admin_headers, json={"track_id": "t1"})
    q = client.get(f"{P}/queue", headers=admin_headers).json()["items"][0]["id"]
    return pl["id"], m["id"], q


def test_jede_aenderung_braucht_moderieren(client, user_headers, admin_headers, flushes, db_ready):
    """Alle Änderungs-Wege – keiner darf ohne radiostream.moderate (nur mit Modul-Freigabe) durchgehen."""
    pid, mid, qid = _setup_everything(client, admin_headers)
    flushes.clear()
    calls = [
        ("put", "/program", {"mode": "playlist", "ref_id": pid}),
        ("put", f"/playlists/{pid}", {"name": "B"}), ("delete", f"/playlists/{pid}", None),
        ("post", f"/playlists/{pid}/items", {"track_ids": ["t1"]}), ("post", f"/playlists/{pid}/add-search", {}),
        ("post", f"/playlists/{pid}/move", {"from": 0, "to": 1}), ("delete", f"/playlists/{pid}/items/0", None),
        ("put", f"/mixes/{mid}", {"name": "X", "rules": {}, "allow_long": False}), ("delete", f"/mixes/{mid}", None),
        ("post", "/queue", {"track_id": "t1"}), ("put", f"/queue/{qid}", {"pos": 0}), ("delete", f"/queue/{qid}", None),
        ("put", "/exclude", {"rules": {}, "allow_long": False}),
    ]
    for method, path, body in calls:
        kw = {"json": body} if body is not None else {}
        r = getattr(client, method)(f"{P}{path}", headers=user_headers, **kw)
        assert r.status_code == 403, (method, path, r.status_code)
    assert flushes == [] and len(program.queue()) == 1 and len(program.items(pid)) == 2


def test_programm_sagt_ob_man_moderieren_darf(client, user_headers, admin_headers, db_ready):
    assert client.get(f"{P}/program", headers=user_headers).json()["can_moderate"] is False
    assert client.get(f"{P}/program", headers=admin_headers).json()["can_moderate"] is True


def test_programm_position_gemischt_zaehlt_gespielte(client, admin_headers, flushes, db_ready):
    from backend import choose
    for t in ("s1", "s2", "s3"):
        _track(t)
    pl = client.post(f"{P}/playlists", headers=admin_headers, json={"name": "A"}).json()
    client.post(f"{P}/playlists/{pl['id']}/items", headers=admin_headers, json={"track_ids": ["s1", "s2", "s3"]})
    client.put(f"{P}/playlists/{pl['id']}", headers=admin_headers, json={"order_mode": "shuffle"})
    client.put(f"{P}/program", headers=admin_headers, json={"mode": "playlist", "ref_id": pl["id"]})
    choose.next_track()
    choose.next_track()
    assert client.get(f"{P}/program", headers=admin_headers).json()["position"] == 2


def test_unbekannte_playlist_lesen_404(client, user_headers, db_ready):
    r = client.get(f"{P}/playlists/gibt-es-nicht", headers=user_headers)
    assert r.status_code == 404 and r.json()["detail"]["code"] == "radiostream_playlist_not_found"


@pytest.mark.parametrize("path", ["/program", "/playlists", "/mixes", "/queue"])
def test_lesen_alle_mit_modul(client, user_headers, db_ready, path):
    assert client.get(f"{P}{path}", headers=user_headers).status_code == 200


@pytest.mark.parametrize("path", ["/program", "/playlists", "/queue", "/exclude"])
def test_ohne_anmeldung_401(client, db_ready, path):
    assert client.get(f"{P}{path}").status_code == 401


def test_programm_lesen_mit_erklaerung(client, admin_headers, flushes, db_ready):
    _track("t1")
    _track("t2")
    pl = client.post(f"{P}/playlists", headers=admin_headers, json={"name": "Party"}).json()
    client.post(f"{P}/playlists/{pl['id']}/items", headers=admin_headers, json={"track_ids": ["t1", "t2"]})
    client.put(f"{P}/program", headers=admin_headers, json={"mode": "playlist", "ref_id": pl["id"]})
    d = client.get(f"{P}/program", headers=admin_headers).json()
    assert d["mode"] == "playlist" and d["name"] == "Party" and d["count"] == 2 and d["position"] == 0
    assert d["can_moderate"] is True and d["notice"] == ""


def test_programm_mix_zeigt_anzahl(client, admin_headers, flushes, db_ready):
    _track("r1", genre="Rock")
    _track("p1", genre="Pop")
    m = client.post(f"{P}/mixes", headers=admin_headers, json={"name": "Rock", "rules": {"genres": ["Rock"]},
                                                              "allow_long": False}).json()
    client.put(f"{P}/program", headers=admin_headers, json={"mode": "mix", "ref_id": m["id"]})
    d = client.get(f"{P}/program", headers=admin_headers).json()
    assert d["name"] == "Rock" and d["count"] == 1


def test_jede_aenderung_nimmt_erst_den_vorgeladenen_zurueck(client, admin_headers, flushes, db_ready):
    _track("t1")
    pl = client.post(f"{P}/playlists", headers=admin_headers, json={"name": "A"}).json()
    assert flushes == []                                         # neue Playlist ändert nichts am Gesendeten
    client.put(f"{P}/program", headers=admin_headers, json={"mode": "playlist", "ref_id": pl["id"]})
    client.post(f"{P}/queue", headers=admin_headers, json={"track_id": "t1", "front": True})
    q = client.get(f"{P}/queue", headers=admin_headers).json()["items"]
    client.put(f"{P}/queue/{q[0]['id']}", headers=admin_headers, json={"pos": 0})
    client.delete(f"{P}/queue/{q[0]['id']}", headers=admin_headers)
    client.post(f"{P}/playlists/{pl['id']}/items", headers=admin_headers, json={"track_ids": ["t1"]})
    assert len(flushes) == 5


def test_playlist_bearbeiten_ablauf(client, admin_headers, flushes, db_ready):
    for t in ("t1", "t2", "t3"):
        _track(t)
    pl = client.post(f"{P}/playlists", headers=admin_headers, json={"name": "A"}).json()
    r = client.post(f"{P}/playlists/{pl['id']}/items", headers=admin_headers, json={"track_ids": ["t1", "t2", "t3"]})
    assert r.json()["added"] == 3
    client.post(f"{P}/playlists/{pl['id']}/move", headers=admin_headers, json={"from": 2, "to": 0})
    client.delete(f"{P}/playlists/{pl['id']}/items/1", headers=admin_headers)
    items = client.get(f"{P}/playlists/{pl['id']}", headers=admin_headers).json()["items"]
    assert [i["track_id"] for i in items] == ["t3", "t2"]
    client.put(f"{P}/playlists/{pl['id']}", headers=admin_headers, json={"name": "B", "order_mode": "shuffle"})
    assert client.get(f"{P}/playlists", headers=admin_headers).json()["items"][0]["name"] == "B"
    assert client.delete(f"{P}/playlists/{pl['id']}", headers=admin_headers).status_code == 200
    assert client.get(f"{P}/playlists", headers=admin_headers).json()["items"] == []


def test_alle_treffer_hinzufuegen(client, admin_headers, flushes, db_ready):
    for i in range(5):
        _track(f"r{i}", genre="Rock")
    _track("p1", genre="Pop")
    pl = client.post(f"{P}/playlists", headers=admin_headers, json={"name": "A"}).json()
    r = client.post(f"{P}/playlists/{pl['id']}/add-search", headers=admin_headers, json={"genre": "Rock"})
    assert r.json()["added"] == 5


def test_mix_vorschau(client, user_headers, db_ready):
    _track("r1", genre="Rock")
    r = client.post(f"{P}/mixes/preview", headers=user_headers, json={"rules": {"genres": ["Rock"]}, "allow_long": False})
    assert r.status_code == 200 and r.json()["count"] == 1


def test_mix_ungueltige_regel_400(client, admin_headers, flushes, db_ready):
    r = client.post(f"{P}/mixes", headers=admin_headers, json={"name": "x", "rules": {"genres": "Rock"},
                                                              "allow_long": False})
    assert r.status_code == 400 and r.json()["detail"]["code"] == "radiostream_rule_invalid"


@pytest.mark.parametrize("method,path,code,http", [
    ("put", "/playlists/nix", "radiostream_playlist_not_found", 404),
    ("delete", "/mixes/nix", None, 200),
])
def test_unbekannt(client, admin_headers, flushes, db_ready, method, path, code, http):
    r = getattr(client, method)(f"{P}{path}", headers=admin_headers, **({"json": {"name": "x"}} if method == "put" else {}))
    assert r.status_code == http
    if code:
        assert r.json()["detail"]["code"] == code


def test_ausschluss_nur_control(client, user_headers, moderator, db_ready):
    r = client.put(f"{P}/exclude", headers=user_headers, json={"rules": {"genres": []}, "allow_long": False})
    assert r.status_code == 403


def test_ausschluss_admin_mit_vorschlaegen(client, admin_headers, db_ready):
    for i in range(25):
        _track(f"b{i}", genre="Kids; Audiobooks", rel=f"Bibi/{i}.mp3")
    d = client.get(f"{P}/exclude", headers=admin_headers).json()
    assert d["rules"]["genre_parts"] and d["suggestions"][0]["folder"] == "Bibi"
    r = client.put(f"{P}/exclude", headers=admin_headers, json={"rules": {"genres": [], "genre_parts": [],
                                                                          "folders": ["Bibi"]}, "allow_long": True})
    assert r.status_code == 200 and r.json()["rules"]["folders"] == ["Bibi"]


def test_warteschlange_unbekannter_titel_404(client, admin_headers, flushes, db_ready):
    r = client.post(f"{P}/queue", headers=admin_headers, json={"track_id": "nix"})
    assert r.status_code == 404 and r.json()["detail"]["code"] == "radiostream_track_not_found"


def test_name_zu_lang_400(client, admin_headers, flushes, db_ready):
    r = client.post(f"{P}/playlists", headers=admin_headers, json={"name": "x" * 81})
    assert r.status_code in (400, 422)


def test_aenderungen_bleiben_auch_wenn_sender_aus(client, admin_headers, db_ready, monkeypatch):
    monkeypatch.setattr(preload, "_running", lambda: False)
    _track("t1")
    assert client.post(f"{P}/queue", headers=admin_headers, json={"track_id": "t1"}).status_code == 200
    assert len(program.queue()) == 1


def test_ordnerliste_fuer_mixe(client, user_headers, db_ready):
    for i in range(3):
        _track(f"q{i}", rel=f"Queen/{i}.mp3")
    _track("a1", rel="ABBA/x.mp3")
    _track("lose", rel="einzeln.mp3")
    from hydrahive.db.connection import db
    with db() as conn:
        conn.execute("UPDATE module_radiostream_tracks SET state = 'missing' WHERE track_id = 'a1'")
        conn.commit()
    r = client.get(f"{P}/folders", headers=user_headers)
    assert r.status_code == 200 and r.json()["items"] == [{"folder": "Queen", "count": 3}]
