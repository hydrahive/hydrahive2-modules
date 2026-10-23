"""M1b über den echten Kern: Microsoft-App nur Admin, Anmelden je Nutzer, Konto anlegen und neu anmelden.

Kein Token und kein device_code in einer Antwort; fremde Vorgänge = 404.
"""
# ruff: noqa: F811 - pytest-Fixtures aus _routes_base/_ms_base
from __future__ import annotations

import json

from _ms_base import CID, _ms_state, app_set, clock, err, ms  # noqa: F401
from _routes_base import B, _h, alice, client, fake_net, rights  # noqa: F401

M = f"{B}/microsoft"
ADDR = "till@outlook.de"
SECRET_BITS = ("AT-1", "RT-1", "DEV-geheim", "mbx:v1")


def _clean(r):
    for s in SECRET_BITS:
        assert s not in r.text, (s, r.text)
    return r


def _root(client):
    return _h(client, "root")


def _done_flow(client, hdr, clock):
    f = _clean(client.post(f"{M}/flows", headers=hdr)).json()
    clock["now"] += 5
    assert _clean(client.get(f"{M}/flows/{f['flow_id']}", headers=hdr)).json() == {"state": "done"}
    return f["flow_id"]


def test_app_nur_admin(client, alice, clock):
    assert client.get(f"{M}/app", headers=alice).status_code == 403
    assert client.put(f"{M}/app", json={"client_id": CID, "tenant": "common"}, headers=alice).status_code == 403
    root = _root(client)
    assert client.get(f"{M}/app", headers=root).json() == {"client_id": "", "tenant": "common"}
    r = client.put(f"{M}/app", json={"client_id": CID, "tenant": ""}, headers=root)
    assert r.status_code == 200 and r.json() == {"client_id": CID, "tenant": "common"}
    assert client.put(f"{M}/app", json={"client_id": "nein", "tenant": "common"}, headers=root).status_code == 422
    assert client.put(f"{M}/app", json={"client_id": CID, "x": 1}, headers=root).status_code == 422


def test_status_fuer_alle_ohne_client_id(client, alice, app_set):
    r = client.get(f"{M}/status", headers=alice)
    assert r.json() == {"configured": True} and CID not in r.text


def test_app_pruefen(client, ms, clock, app_set):
    root = _root(client)
    r = _clean(client.post(f"{M}/app/check", headers=root))
    assert r.json() == {"ok": True}
    ms.device.append(err("invalid_client", "AADSTS7000218: The request body must contain client_secret"))
    r = client.post(f"{M}/app/check", headers=root)
    assert r.json()["ok"] is False and r.json()["error"] == "invalid_client" and "AADSTS7000218" in r.json()["message"]


def test_ohne_app_klare_meldung(client, alice, ms, clock):
    r = client.post(f"{M}/flows", headers=alice)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "microsoft_not_configured"


def test_konto_anlegen_ueber_microsoft(client, alice, ms, clock, app_set, monkeypatch, fake_net):
    from backend import accounts
    seen = []
    monkeypatch.setattr(accounts, "_test_login", lambda acc, pw: seen.append((acc["auth"], acc["address"])) or {})
    flow = _done_flow(client, alice, clock)
    r = _clean(client.post(f"{M}/accounts", json={"flow_id": flow, "address": ADDR, "label": "Outlook"}, headers=alice))
    assert r.status_code == 201, r.text
    a = r.json()
    assert a["auth"] == "oauth_microsoft" and a["imap_host"] == "outlook.office365.com"
    assert (a["smtp_host"], a["smtp_port"], a["smtp_tls"]) == ("smtp-mail.outlook.com", 587, "starttls")
    assert seen == [("oauth_microsoft", ADDR)], "Anmeldung vor dem Speichern geprüft"
    _clean(client.get(f"{B}/accounts", headers=alice))
    again = client.post(f"{M}/accounts", json={"flow_id": flow, "address": "zwei@outlook.de"}, headers=alice)
    assert again.status_code == 404, "Vorgang verbraucht"
    flow2 = _done_flow(client, alice, clock)
    dup = client.post(f"{M}/accounts", json={"flow_id": flow2, "address": ADDR}, headers=alice)
    assert dup.status_code == 409, "gleiche Adresse zweimal"


def test_eigene_domain_microsoft365(client, alice, ms, clock, app_set, monkeypatch):
    from backend import accounts
    monkeypatch.setattr(accounts, "_test_login", lambda acc, pw: {})
    flow = _done_flow(client, alice, clock)
    a = client.post(f"{M}/accounts", json={"flow_id": flow, "address": "till@firma.de"}, headers=alice).json()
    assert (a["smtp_host"], a["smtp_port"]) == ("smtp.office365.com", 587) and a["label"] == "till@firma.de"


def test_fehlgeschlagene_pruefung_speichert_nichts(client, alice, ms, clock, app_set, monkeypatch):
    from backend import accounts
    def no(acc, pw):
        raise accounts.ConnectError("auth", "Anmeldung fehlgeschlagen: AUTHENTICATE failed")
    monkeypatch.setattr(accounts, "_test_login", no)
    flow = _done_flow(client, alice, clock)
    r = client.post(f"{M}/accounts", json={"flow_id": flow, "address": ADDR}, headers=alice)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "auth"
    assert accounts.list_for("alice") == []


def test_fremder_vorgang_404(client, alice, ms, clock, app_set):
    f = client.post(f"{M}/flows", headers=alice).json()
    bob = _h(client, "bob")
    assert client.get(f"{M}/flows/{f['flow_id']}", headers=bob).status_code == 404
    clock["now"] += 5
    client.get(f"{M}/flows/{f['flow_id']}", headers=alice)
    assert client.post(f"{M}/accounts", json={"flow_id": f["flow_id"], "address": "bob@outlook.de"},
                       headers=bob).status_code == 404


def test_ohne_modulrecht_kein_zugang(client, app_set):
    carol = _h(client, "carol")
    assert client.post(f"{M}/flows", headers=carol).status_code == 403
    assert client.get(f"{M}/status", headers=carol).status_code == 403


def test_vorgang_noch_offen_kein_konto(client, alice, ms, clock, app_set):
    f = client.post(f"{M}/flows", headers=alice).json()
    r = client.post(f"{M}/accounts", json={"flow_id": f["flow_id"], "address": ADDR}, headers=alice)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "flow_not_done"


def test_neu_anmelden(client, alice, ms, clock, app_set, monkeypatch):
    from backend import accounts, secrets
    from hydrahive.db.connection import db
    monkeypatch.setattr(accounts, "_test_login", lambda acc, pw: {})
    a = client.post(f"{M}/accounts", json={"flow_id": _done_flow(client, alice, clock), "address": ADDR},
                    headers=alice).json()
    accounts.set_status(a["id"], "auth_failed", "Microsoft-Anmeldung abgelaufen – bitte erneut anmelden")
    ms.token.append((200, {"access_token": "AT-7", "refresh_token": "RT-7", "expires_in": 3600}))
    flow = _done_flow(client, alice, clock)
    r = _clean(client.post(f"{B}/accounts/{a['id']}/microsoft", json={"flow_id": flow}, headers=alice))
    assert r.status_code == 200 and r.json()["status"] == "ok"
    with db() as c:
        sec = c.execute("SELECT secret FROM module_mailbox_accounts WHERE id=?", (a["id"],)).fetchone()[0]
    assert json.loads(secrets.open_(a["id"], sec)) == {"refresh_token": "RT-7"}
    bob = _h(client, "bob")
    assert client.post(f"{B}/accounts/{a['id']}/microsoft", json={"flow_id": "x" * 22},
                       headers=bob).status_code == 404


def test_neu_anmelden_nur_microsoft_konten(client, alice, ms, clock, app_set, fake_net):
    from _routes_base import NEW
    a = client.post(f"{B}/accounts", json=NEW, headers=alice).json()
    flow = _done_flow(client, alice, clock)
    r = client.post(f"{B}/accounts/{a['id']}/microsoft", json={"flow_id": flow}, headers=alice)
    assert r.status_code == 422


def test_passwort_patch_bei_microsoft_abgelehnt(client, alice, ms, clock, app_set, monkeypatch):
    from backend import accounts
    monkeypatch.setattr(accounts, "_test_login", lambda acc, pw: {})
    a = client.post(f"{M}/accounts", json={"flow_id": _done_flow(client, alice, clock), "address": ADDR},
                    headers=alice).json()
    r = client.patch(f"{B}/accounts/{a['id']}", json={"password": "x"}, headers=alice)
    assert r.status_code == 422
    r = client.patch(f"{B}/accounts/{a['id']}", json={"imap_host": "imap.boese.example"}, headers=alice)
    assert r.status_code == 422, "Server eines Microsoft-Kontos sind fest"
    assert client.patch(f"{B}/accounts/{a['id']}", json={"signature": "Gruß"}, headers=alice).status_code == 200


def test_vorschlag_kennt_microsoft(client, alice):
    r = client.get(f"{B}/suggest", params={"address": "x@hotmail.de"}, headers=alice).json()
    assert r["auth"] == "oauth_microsoft"
    assert client.get(f"{B}/suggest", params={"address": "x@gmx.de"}, headers=alice).json()["auth"] == "password"
