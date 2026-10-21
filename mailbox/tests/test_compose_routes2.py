"""M2 Schritt 8 (Teil 2): Routen Entwürfe und Aktionen."""
# ruff: noqa: F811 - pytest-Fixtures aus _routes_base werden als gleichnamige Parameter genutzt
from __future__ import annotations

import pytest
from _fake_imap_write import FakeIMAPW
from _routes_base import B, _h, _mid, acc, alice, client, fake_net, rights  # noqa: F401 - Fixtures/Hilfen


@pytest.fixture(autouse=True)
def imapw(monkeypatch, fake_net):
    from backend import sync_job
    fake_net.box("Papierkorb", special="\\Trash")
    fake_net.box("Entwürfe", special="\\Drafts")
    fake_net.box("Projekte")
    monkeypatch.setattr(sync_job, "_open", lambda a: FakeIMAPW(fake_net, caps=("MOVE", "UIDPLUS", "UNSELECT")))


def test_entwurf_anlegen_aendern_loeschen(client, alice, acc, fake_net):
    r = client.post(f"{B}/drafts", headers=alice, json={"account_id": acc["id"], "to": "a@x", "subject": "E", "body": "x"})
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["server"] == "ok" and len(fake_net.boxes["Entwürfe"].msgs) == 1
    r = client.patch(f"{B}/drafts/{d['id']}", headers=alice, json={"account_id": acc["id"], "subject": "E2"})
    assert r.status_code == 200 and r.json()["subject"] == "E2"
    assert [x["subject"] for x in client.get(f"{B}/drafts", headers=alice).json()] == ["E2"]
    assert client.delete(f"{B}/drafts/{d['id']}", headers=alice).status_code == 204
    assert client.get(f"{B}/drafts", headers=alice).json() == []
    assert all("\\Deleted" in fl for _, fl in fake_net.boxes["Entwürfe"].msgs.values()) or not fake_net.boxes["Entwürfe"].msgs


def test_entwurf_fremd_404(client, alice, acc):
    d = client.post(f"{B}/drafts", headers=alice, json={"account_id": acc["id"], "subject": "E"}).json()
    bob = _h(client, "bob")
    assert client.patch(f"{B}/drafts/{d['id']}", headers=bob, json={"account_id": acc["id"]}).status_code == 404
    assert client.delete(f"{B}/drafts/{d['id']}", headers=bob).status_code == 404
    assert client.get(f"{B}/drafts", headers=bob).json() == []
    assert client.post(f"{B}/drafts", headers=bob, json={"account_id": acc["id"]}).status_code == 404


def test_entwurf_eingaben_422(client, alice, acc):
    r = client.post(f"{B}/drafts", headers=alice, json={"account_id": acc["id"], "subject": "a\nb"})
    assert r.status_code == 422


@pytest.mark.parametrize("action", ["seen", "unseen", "flag", "unflag"])
def test_aktion_flags(client, alice, acc, fake_net, action):
    mid = _mid(client, alice, "Re: Unterlagen")
    r = client.post(f"{B}/messages/actions", headers=alice, json={"ids": [mid], "action": action})
    assert r.status_code == 200 and r.json() == {"done": 1, "skipped": 0}


def test_aktion_verschieben_und_loeschen(client, alice, acc, fake_net):
    mid = _mid(client, alice, "Re: Unterlagen")
    r = client.post(f"{B}/messages/actions", headers=alice, json={"ids": [mid], "action": "move", "target": "Projekte"})
    assert r.status_code == 200 and r.json()["done"] == 1 and len(fake_net.boxes["Projekte"].msgs) == 1
    client.post(f"{B}/accounts/{acc['id']}/sync", headers=alice)
    r = client.post(f"{B}/messages/actions", headers=alice, json={"ids": [mid], "action": "delete"})
    assert r.json()["done"] == 1 and len(fake_net.boxes["Papierkorb"].msgs) == 1
    assert client.get(f"{B}/messages/{mid}", headers=alice).status_code == 200, "Archiv bleibt"


def test_aktion_mehrere_konten_getrennt_und_fremde_ids_still(client, alice, acc):
    mid = _mid(client, alice, "Re: Unterlagen")
    bob = _h(client, "bob")
    r = client.post(f"{B}/messages/actions", headers=bob, json={"ids": [mid], "action": "delete"})
    assert r.status_code == 200 and r.json() == {"done": 0, "skipped": 1}


@pytest.mark.parametrize("body", [{"ids": [], "action": "seen"}, {"ids": [1] * 501, "action": "seen"},
                                  {"ids": [1], "action": "expunge"}, {"ids": [1], "action": "move"},
                                  {"ids": ["x"], "action": "seen"}])
def test_aktion_eingaben_422(client, alice, acc, body):
    assert client.post(f"{B}/messages/actions", headers=alice, json=body).status_code == 422


def test_aktion_server_weg_502(client, alice, acc, monkeypatch):
    from backend import sync_job

    def boom(a):
        raise OSError("Connection refused")
    monkeypatch.setattr(sync_job, "_open", boom)
    mid = _mid(client, alice, "Re: Unterlagen")
    r = client.post(f"{B}/messages/actions", headers=alice, json={"ids": [mid], "action": "seen"})
    assert r.status_code == 502 and r.json()["detail"]["code"] == "connect"


@pytest.fixture
def bob_konto(client, fake_net, monkeypatch):
    """Bob mit EIGENEM Konto – sonst greift nur die Abkürzung „keine Konten“ und die eigentliche Prüfung bleibt ungetestet."""
    from _fake_imap import FakeServer
    from backend import sync_job
    from conftest import eml
    from _routes_base import NEW
    bob = _h(client, "bob")
    srv_b = FakeServer(user="bob@example.net", password="pw-b")
    srv_b.box("Papierkorb", special="\\Trash")
    srv_b.boxes["INBOX"].add(eml("latin1"))
    servers = {"alice@example.net": fake_net, "bob@example.net": srv_b}
    monkeypatch.setattr(sync_job, "_open", lambda a: FakeIMAPW(servers[a["address"]], caps=("MOVE", "UIDPLUS", "UNSELECT")))
    r = client.post(f"{B}/accounts", json={**NEW, "address": "bob@example.net", "username": "bob@example.net",
                                           "password": "pw-b"}, headers=bob)
    client.post(f"{B}/accounts/{r.json()['id']}/sync", headers=bob)
    return bob, r.json(), srv_b


def test_aktion_fremde_mail_trotz_eigenem_konto(client, alice, acc, fake_net, bob_konto):
    bob, _, srv_b = bob_konto
    mid = _mid(client, alice, "Re: Unterlagen")
    own = client.get(f"{B}/messages", headers=bob).json()["items"][0]["id"]
    inbox_before = len(fake_net.boxes["INBOX"].msgs)
    r = client.post(f"{B}/messages/actions", headers=bob, json={"ids": [mid, own], "action": "delete"})
    assert r.status_code == 200 and r.json() == {"done": 1, "skipped": 1}
    assert len(fake_net.boxes["INBOX"].msgs) == inbox_before and len(srv_b.boxes["Papierkorb"].msgs) == 1


def test_entwurf_fremd_trotz_eigenem_konto(client, alice, acc, bob_konto):
    bob, bacc, _ = bob_konto
    d = client.post(f"{B}/drafts", headers=alice, json={"account_id": acc["id"], "subject": "E"}).json()
    r = client.patch(f"{B}/drafts/{d['id']}", headers=bob, json={"account_id": bacc["id"], "subject": "geklaut"})
    assert r.status_code == 404
    assert client.delete(f"{B}/drafts/{d['id']}", headers=bob).status_code == 404
    assert [x["subject"] for x in client.get(f"{B}/drafts", headers=alice).json()] == ["E"]


def test_eigener_entwurf_anderes_eigenes_konto_404(client, alice, acc, fake_net):
    """Entwurf gehört Konto A; PATCH mit Konto B (auch eigenes) → 404, kein stilles Umhängen."""
    from _routes_base import NEW
    b = client.post(f"{B}/accounts", json={**NEW, "label": "Zweit", "address": "alice2@example.net",
                                           "username": "alice2@example.net"}, headers=alice).json()
    d = client.post(f"{B}/drafts", headers=alice, json={"account_id": acc["id"], "subject": "E"}).json()
    r = client.patch(f"{B}/drafts/{d['id']}", headers=alice, json={"account_id": b["id"], "subject": "x"})
    assert r.status_code == 404


@pytest.mark.parametrize("target", [None, ""])
def test_verschieben_ohne_ziel_422_ohne_serverkontakt(client, alice, acc, monkeypatch, target):
    from backend import sync_job
    called = []
    monkeypatch.setattr(sync_job, "_open", lambda a: called.append(1))
    mid = _mid(client, alice, "Re: Unterlagen")
    body = {"ids": [mid], "action": "move"} | ({"target": target} if target is not None else {})
    assert client.post(f"{B}/messages/actions", headers=alice, json=body).status_code == 422
    assert called == []


def test_jede_besitzschicht_greift_einzeln(client, alice, acc, fake_net, bob_konto):
    """Drei unabhängige Schichten gegen fremde Mails: (1) Gruppierung nur eigene Konten, (2) Konto per get_own,
    (3) actions._targets nur Mails des Kontos. Jede einzeln prüfen – sonst deckt eine die andere zu."""
    from backend import action_routes, actions
    bob, bacc, _ = bob_konto
    mid = _mid(client, alice, "Re: Unterlagen")
    assert action_routes._by_account("bob", [mid]) == {}                                        # (1)
    assert action_routes._run_account("bob", acc["id"], [mid], "delete", None) == {"done": 0, "skipped": 1}  # (2)
    assert actions._targets(bacc["id"], [mid]) == []                                            # (3)
