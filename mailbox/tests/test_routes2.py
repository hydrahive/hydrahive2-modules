"""M1 Schritt 11, Teil 2: Fremdzugriff mit eigenem Konto, Inline-Regeln, Token in der Adresse."""
# ruff: noqa: F811 - pytest-Fixtures aus _routes_base werden als gleichnamige Parameter genutzt
from __future__ import annotations

import pytest
from _fake_imap import FakeIMAP, FakeServer
from conftest import eml
from _routes_base import B, NEW, _h, _mid, acc, alice, client, fake_net, rights  # noqa: F401 - Fixtures/Hilfen


@pytest.fixture
def bob_mit_konto(client, fake_net, monkeypatch):
    """Bob hat ein EIGENES Konto (mit Mails) – der gefährliche Fall: fremde IDs raten, obwohl man Zugang hat."""
    from backend import sync_job
    bob = _h(client, "bob")
    srv_b = FakeServer(user="bob@example.net", password="pw-b")
    srv_b.boxes["INBOX"].add(eml("latin1"))
    servers = {"alice@example.net": fake_net, "bob@example.net": srv_b}
    monkeypatch.setattr(sync_job, "_open", lambda acc: FakeIMAP(servers[acc["address"]]))
    r = client.post(f"{B}/accounts", json={**NEW, "address": "bob@example.net", "username": "bob@example.net",
                                           "password": "pw-b"}, headers=bob)
    assert r.status_code == 201
    client.post(f"{B}/accounts/{r.json()['id']}/sync", headers=bob)
    return bob


def test_fremde_ids_trotz_eigenem_konto(client, alice, acc, bob_mit_konto):
    bob = bob_mit_konto
    assert [x["subject"] for x in client.get(f"{B}/messages", headers=bob).json()["items"]] == ["Grüße aus Köln 😃"]
    mid = _mid(client, alice, "Re: Unterlagen")
    for path in (f"messages/{mid}", f"messages/{mid}/html", f"messages/{mid}/eml", f"attachments/{mid}/0",
                 f"attachments/{mid}/1?inline=1", f"accounts/{acc['id']}"):
        assert client.get(f"{B}/{path}", headers=bob).status_code == 404, path
    alice_folders = client.get(f"{B}/folders", headers=alice).json()
    bob_folders = client.get(f"{B}/folders", headers=bob).json()
    assert {f["id"] for f in bob_folders}.isdisjoint({f["id"] for f in alice_folders})
    for f in alice_folders:
        r = client.get(f"{B}/messages", params={"folder_id": f["id"]}, headers=bob).json()
        assert r["items"] == [] and r["total"] == 0, f["name"]
    assert client.get(f"{B}/messages", params={"q": "konto:alice"}, headers=bob).json()["items"] == []


def test_patch_adresse_auch_mit_gueltigen_feldern_422(client, alice, acc):
    r = client.patch(f"{B}/accounts/{acc['id']}", json={"label": "x", "address": "alice@example.net"}, headers=alice)
    assert r.status_code == 422
    assert client.get(f"{B}/accounts/{acc['id']}", headers=alice).json()["label"] == "Privat", "nichts geändert"


def test_inline_nur_rasterbilder(client, alice, acc):
    mid = _mid(client, alice, "Re: Unterlagen")
    pdf = next(a for a in client.get(f"{B}/messages/{mid}", headers=alice).json()["attachments"] if not a["inline"])
    r = client.get(f"{B}/attachments/{mid}/{pdf['index']}", params={"inline": 1}, headers=alice)
    assert r.headers["content-type"] == "application/octet-stream" and r.headers["content-disposition"].startswith("attachment")


def test_negativer_anhang_index(client, alice, acc):
    mid = _mid(client, alice, "Re: Unterlagen")
    assert client.get(f"{B}/attachments/{mid}/-1", headers=alice).status_code == 404


def test_patch_schema_kennt_keine_adresse():
    """Dritte Schicht: das Schema selbst verbietet Felder außerhalb der Liste."""
    from backend.schemas import AccountPatch
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        AccountPatch.model_validate({"address": "x@y.de"})


def test_iframe_und_bilder_mit_token_in_der_adresse(client, alice, acc):
    """<iframe>/<img> schicken keinen Header → ?token= wie beim Mediaplayer. Ohne Token weiterhin 401."""
    token = alice["Authorization"].split(" ", 1)[1]
    mid = _mid(client, alice, "Re: Unterlagen")
    r = client.get(f"{B}/messages/{mid}/html", params={"token": token})
    assert r.status_code == 200 and "Anbei die Unterlagen" in r.text
    logo = next(a for a in client.get(f"{B}/messages/{mid}", headers=alice).json()["attachments"] if a["inline"])
    assert client.get(f"{B}/attachments/{mid}/{logo['index']}", params={"inline": 1, "token": token}).status_code == 200
    assert client.get(f"{B}/messages/{mid}/html").status_code == 401
    assert client.get(f"{B}/messages/{mid}/html", params={"token": "falsch"}).status_code == 401


def test_cid_links_tragen_den_token_nicht_selbst(client, alice, acc):
    """Der Token kommt vom Frontend an die iframe-Adresse – im HTML selbst steht er nie (Weiterleiten/Kopieren)."""
    token = alice["Authorization"].split(" ", 1)[1]
    mid = _mid(client, alice, "Re: Unterlagen")
    html = client.get(f"{B}/messages/{mid}/html", params={"token": token}).text
    assert token not in html


def test_alle_posteingaenge_route(client, alice, acc):
    r = client.get(f"{B}/messages", params={"inbox": "true"}, headers=alice).json()
    assert r["total"] == 2 and {x["folder"] for x in r["items"]} == {"INBOX"}
