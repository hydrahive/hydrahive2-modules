"""HydraHive-App G1: Kopplung, Geräte-Routen (ohne Login), Admin-Routen. Ohne echtes Gerät."""
from __future__ import annotations

import pytest
from backend import app_pairing, app_tls

M = "/api/modules/tvwerkstatt"
D = "/api/module-device/tvwerkstatt"


@pytest.fixture
def code(client, admin_headers):
    r = client.post(M + "/app/pairing", json={"name": "Küche Tablet"}, headers=admin_headers)
    assert r.status_code == 201, r.text
    return r.json()


def _enroll(client, code: str, info: dict | None = None):
    return client.post(D + "/app/enroll", json={"info": info or {"kind": "tablet", "model": "Tab A"}},
                       headers={"X-Pairing-Code": code})


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_code_format_und_nur_admins(client, admin_headers, user_headers, code):
    assert len(code["code"]) == 14 and code["code"].count("-") == 2
    assert set(code["code"].replace("-", "")) <= set(app_pairing.ALPHABET)
    assert code["name"] == "Küche Tablet" and code["server"].startswith("https://")
    assert client.post(M + "/app/pairing", json={"name": "x"}, headers=user_headers).status_code == 403
    assert client.get(M + "/app/devices", headers=user_headers).status_code == 403


def test_koppeln_einmalig_name_vom_code(client, code):
    r = _enroll(client, code["code"].lower(), {"kind": "tablet", "model": "Tab\nA", "name": "Böse"})
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Küche Tablet" and body["token"].startswith("hhtvw_")
    assert _enroll(client, code["code"]).status_code == 401                       # zweites Mal: verbraucht
    dev = app_pairing.by_token(body["token"])
    assert dev["kind"] == "tablet" and dev["model"] == "Tab A"


def test_ohne_oder_falscher_nachweis(client, code):
    assert client.post(D + "/app/enroll", json={}).status_code == 401
    assert _enroll(client, "AAAA-BBBB-CCCC").status_code == 401
    assert client.post(D + "/app/hello", json={}, headers=_bearer("hhtvw_falsch")).status_code == 401
    assert client.post(D + "/app/hello", json={}, headers={"X-Pairing-Code": code["code"]}).status_code == 401


def test_hello_ereignis_einblendung_antwort(client, admin_headers, code):
    tok = _enroll(client, code["code"]).json()["token"]
    h = _bearer(tok)
    assert client.post(D + "/app/hello", json={"state": {"screen": "on"}}, headers=h).json()["poll_seconds"] == 25
    assert client.post(D + "/app/events", json={"kind": "foreground", "data": {"package": "com.plexapp.android"}},
                       headers=h).status_code == 202
    assert client.post(D + "/app/events", json={"kind": "boese"}, headers=h).status_code == 400
    app_id = app_pairing.by_token(tok)["app_id"]
    r = client.post(M + f"/app/devices/{app_id}/notices",
                    json={"title": "Es hat geklingelt", "body": "Haustür", "buttons": ["Ansehen", "Später", "a", "b"]},
                    headers=admin_headers)
    nid = r.json()["notice_id"]
    got = client.get(D + "/app/notices?after=0&wait=0", headers=h).json()["notices"]
    assert [(n["notice_id"], n["title"], n["buttons"]) for n in got] == [(nid, "Es hat geklingelt",
                                                                        ["Ansehen", "Später", "a"])]
    assert client.post(D + f"/app/notices/{nid}", json={"answer": "Gibtsnicht"}, headers=h).status_code == 400
    assert client.post(D + f"/app/notices/{nid}", json={"answer": "Ansehen"}, headers=h).status_code == 200
    assert client.get(D + "/app/notices?after=0", headers=h).json()["notices"] == []
    act = client.get(M + f"/app/devices/{app_id}/activity", headers=admin_headers).json()
    assert act["notices"][0]["answer"] == "Ansehen"
    assert [e["kind"] for e in act["events"]][:2] == ["answer", "foreground"]
    devs = client.get(M + "/app/devices", headers=admin_headers).json()["devices"]
    assert devs[0]["state"] == {"screen": "on"} and "token_hash" not in devs[0]


def test_fremde_einblendung_nicht_beantwortbar(client, admin_headers, code):
    a = _enroll(client, code["code"]).json()
    c2 = client.post(M + "/app/pairing", json={"name": "Bad"}, headers=admin_headers).json()
    b = _enroll(client, c2["code"]).json()
    nid = client.post(M + f"/app/devices/{a['app_id']}/notices", json={"title": "nur für A"},
                      headers=admin_headers).json()["notice_id"]
    assert client.get(D + "/app/notices", headers=_bearer(b["token"])).json()["notices"] == []
    assert client.post(D + f"/app/notices/{nid}", json={}, headers=_bearer(b["token"])).status_code == 404


def test_sperren_entfernen(client, admin_headers, code):
    a = _enroll(client, code["code"]).json()
    assert client.delete(M + f"/app/devices/{a['app_id']}", headers=admin_headers).status_code == 400  # erst sperren
    assert client.post(M + f"/app/devices/{a['app_id']}/revoke", headers=admin_headers).status_code == 200
    assert client.post(D + "/app/hello", json={}, headers=_bearer(a["token"])).status_code == 401
    assert client.delete(M + f"/app/devices/{a['app_id']}", headers=admin_headers).status_code == 200
    assert client.get(M + "/app/devices", headers=admin_headers).json()["devices"] == []


def test_name_doppelt_und_ungueltig(client, admin_headers, code):
    _enroll(client, code["code"])
    r = client.post(M + "/app/pairing", json={"name": "Küche Tablet"}, headers=admin_headers)
    assert r.status_code == 409
    for bad in ("", "a\nb", "x" * 41):
        assert client.post(M + "/app/pairing", json={"name": bad}, headers=admin_headers).status_code == 400
    assert client.post(M + "/app/pairing", json={"name": "TV", "device_id": "gibtsnicht"},
                       headers=admin_headers).status_code == 404


def test_einblendung_texte_begrenzt(client, admin_headers, code):
    a = _enroll(client, code["code"]).json()
    r = client.post(M + f"/app/devices/{a['app_id']}/notices",
                    json={"title": "T" * 200 + "\x07", "body": "B" * 500, "buttons": ["X" * 50]}, headers=admin_headers)
    n = client.get(D + "/app/notices", headers=_bearer(a["token"])).json()["notices"][0]
    assert r.status_code == 201 and len(n["title"]) == 80 and len(n["body"]) == 300 and n["buttons"] == ["X" * 20]
    assert client.post(M + f"/app/devices/{a['app_id']}/notices", json={"title": "  "},
                       headers=admin_headers).status_code == 400


def test_ereignis_zu_gross(client, code):
    tok = _enroll(client, code["code"]).json()["token"]
    r = client.post(D + "/app/events", json={"kind": "input", "data": {"x": "y" * 3000}}, headers=_bearer(tok))
    assert r.status_code == 400 and r.json()["detail"]["code"] == "tvw_app_event_too_large"


def test_pin_nur_fuer_lokale_adressen():
    assert app_tls.is_local("192.168.178.2") and app_tls.is_local("hydra.fritz.box") and app_tls.is_local("nas")
    assert not app_tls.is_local("hydra.example.com") and not app_tls.is_local("8.8.8.8")
    assert app_tls.pin_for("hydra.example.com") is None


def test_geraete_routen_haengen_am_kern_mit_ratelimit_und_pruefung():
    from hydrahive.api import main
    routes = [r for r in main.app.routes if getattr(r, "path", "").startswith(D + "/app/")]
    assert {r.path for r in routes} >= {D + "/app/enroll", D + "/app/hello", D + "/app/events", D + "/app/notices"}
    for r in routes:
        names = [d.call.__name__ for d in r.dependant.dependencies]
        assert any(n.startswith("device_rate_limit") for n in names) and "app_auth" in names, (r.path, names)


def test_gesperrt_zaehlt_auch_wenn_schluessel_noch_in_der_tabelle(client, code):
    a = _enroll(client, code["code"]).json()
    from hydrahive.db.connection import db
    with db() as conn:                                  # nur Status setzen, Schlüssel bleibt (zweite Schutzschicht)
        conn.execute("UPDATE module_tvwerkstatt_app_devices SET status = 'revoked' WHERE app_id = ?", (a["app_id"],))
    assert app_pairing.by_token(a["token"]) is None


def test_enroll_braucht_code_auch_mit_gueltigem_schluessel(client, admin_headers, code):
    a = _enroll(client, code["code"]).json()
    c2 = client.post(M + "/app/pairing", json={"name": "Flur"}, headers=admin_headers).json()
    r = client.post(D + "/app/enroll", json={}, headers={**_bearer(a["token"]), "X-Pairing-Code": c2["code"]})
    assert r.status_code == 401                          # Schlüssel hat Vorrang, ein Gerät koppelt kein zweites
    assert app_pairing.code_valid(c2["code"])


def test_enroll_ohne_code_scheitert_auch_in_der_zweiten_schicht():
    with pytest.raises(app_pairing.AppError) as e:
        app_pairing.enroll(None, {}, "192.0.2.1")
    assert e.value.code == "tvw_app_code_invalid"


@pytest.mark.parametrize("asked", [1e9, float("inf"), float("nan"), -5])
def test_lange_abfrage_hoechstens_30_s(monkeypatch, asked):
    import asyncio

    from backend import app_messages
    clock = {"t": 1000.0}
    monkeypatch.setattr(app_messages.time, "monotonic", lambda: clock["t"])

    async def fake_sleep(s):
        clock["t"] += s
    monkeypatch.setattr(app_messages.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(app_messages, "pending", lambda a, b: [])
    assert asyncio.run(app_messages.wait_pending("x", 0, asked)) == []
    assert clock["t"] - 1000.0 <= 30.0 + app_messages.POLL_STEP
