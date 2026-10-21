"""M1 Schritt 11: Routen über den echten Kern (Modul-Tor module.mailbox). Fremdes = 404, Passwort nie in Antworten."""
from __future__ import annotations

import pytest
from _fake_imap import FakeIMAP, FakeServer
from fastapi.testclient import TestClient

from conftest import MODULE_DIR, eml

B = "/api/modules/mailbox"
NEW = {"label": "Privat", "address": "alice@example.net", "imap_host": "imap.example.net", "imap_port": 993,
       "imap_tls": "ssl", "smtp_host": "smtp.example.net", "smtp_port": 465, "smtp_tls": "ssl",
       "username": "alice@example.net", "password": "geheim-123"}


@pytest.fixture(scope="module")
def client(setup_test_env):
    from contextlib import asynccontextmanager

    import backend
    from hydrahive.access.capabilities import catalog
    from hydrahive.api import main
    from hydrahive.modules.context import ModuleContext
    from hydrahive.modules.manifest import ModuleManifest
    from hydrahive.modules.registry import REGISTRY, LoadedModule
    manifest = ModuleManifest.load(MODULE_DIR / "manifest.json")
    catalog().register_module(manifest)
    ctx = ModuleContext("mailbox")
    backend.register(ctx)
    saved = dict(REGISTRY)
    REGISTRY.clear()
    REGISTRY["mailbox"] = LoadedModule(name="mailbox", manifest=manifest, path=MODULE_DIR, ctx=ctx, loaded=True)
    try:
        main.mount_module_routers(main.app)
    finally:
        REGISTRY.clear()
        REGISTRY.update(saved)

    @asynccontextmanager
    async def life(app):
        from hydrahive.settings import settings
        settings.ensure_dirs()
        yield
    orig = main.app.router.lifespan_context
    main.app.router.lifespan_context = life
    with TestClient(main.app) as c:
        yield c
    main.app.router.lifespan_context = orig
    catalog().unregister_module("mailbox")


@pytest.fixture(autouse=True)
def rights(monkeypatch):
    """alice + bob dürfen das Modul nutzen, carol nicht."""
    from hydrahive.access import check
    ok = {check.user_id_for("alice"), check.user_id_for("bob")}
    monkeypatch.setattr(check, "_levels", lambda uid: {"module.mailbox": "use"} if uid in ok else {})


@pytest.fixture(autouse=True)
def fake_net(monkeypatch, archive):
    from backend import accounts, sync_job
    srv = FakeServer(user="alice@example.net", password="geheim-123")
    srv.box("Gesendet", special="\\Sent")
    srv.boxes["INBOX"].add(eml("attachments"))
    srv.boxes["INBOX"].add(eml("html_tracking"))
    srv.boxes["Gesendet"].add(eml("plain"))
    monkeypatch.setattr(accounts, "_test_login", lambda acc, pw: {"folders": 2})
    monkeypatch.setattr(sync_job, "_open", lambda acc: FakeIMAP(srv))
    return srv


def _h(client, user):
    r = client.post("/api/auth/login", json={"username": user, "password": "testpass123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def alice(client):
    return _h(client, "alice")


@pytest.fixture
def acc(client, alice):
    r = client.post(f"{B}/accounts", json=NEW, headers=alice)
    assert r.status_code == 201, r.text
    a = r.json()
    assert client.post(f"{B}/accounts/{a['id']}/sync", headers=alice).status_code == 202
    return a


def test_ohne_login_401_ohne_recht_403(client):
    assert client.get(f"{B}/accounts").status_code == 401
    assert client.get(f"{B}/accounts", headers=_h(client, "carol")).status_code in (401, 403)


def test_konto_anlegen_ohne_passwort_in_antwort(client, alice, acc):
    for r in (client.get(f"{B}/accounts", headers=alice), client.get(f"{B}/accounts/{acc['id']}", headers=alice)):
        assert r.status_code == 200 and "geheim-123" not in r.text and "secret" not in r.text and "mbx:v1" not in r.text


def test_vorschlag(client, alice):
    r = client.get(f"{B}/suggest", params={"address": "x@gmail.com"}, headers=alice)
    assert r.json()["imap_host"] == "imap.gmail.com" and "App-Passwort" in r.json()["hint"]
    assert client.get(f"{B}/suggest", params={"address": "kaputt"}, headers=alice).status_code == 422


@pytest.mark.parametrize("bad", [{"imap_port": 8080}, {"address": "x"}, {"extra": 1}, {"imap_tls": "plain"}])
def test_anlegen_ungueltig_422(client, alice, bad):
    assert client.post(f"{B}/accounts", json={**NEW, **bad}, headers=alice).status_code == 422


def test_falsches_passwort_400_mit_code(client, alice, monkeypatch):
    from backend import accounts

    def nope(acc, pw):
        raise accounts.ConnectError("auth", "Anmeldung fehlgeschlagen")
    monkeypatch.setattr(accounts, "_test_login", nope)
    r = client.post(f"{B}/accounts", json=NEW, headers=alice)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "auth"


def test_ordner_und_liste(client, alice, acc):
    f = client.get(f"{B}/folders", headers=alice).json()
    names = {x["name"]: x for x in f}
    assert names["INBOX"]["total"] == 2 and names["Gesendet"]["role"] == "sent"
    m = client.get(f"{B}/messages", params={"folder_id": names["INBOX"]["id"]}, headers=alice).json()
    assert m["total"] == 2 and {x["subject"] for x in m["items"]} == {"Re: Unterlagen", "Angebot"}


def test_suche(client, alice, acc):
    r = client.get(f"{B}/messages", params={"q": "hat:anhang"}, headers=alice).json()
    assert [x["subject"] for x in r["items"]] == ["Re: Unterlagen"]


def _mid(client, alice, subject):
    return next(x["id"] for x in client.get(f"{B}/messages", params={"q": f'betreff:"{subject}"'}, headers=alice)
                .json()["items"])


def test_mail_ansehen(client, alice, acc):
    r = client.get(f"{B}/messages/{_mid(client, alice, 'Re: Unterlagen')}", headers=alice).json()
    assert r["subject"] == "Re: Unterlagen" and r["has_html"] is True and "Anbei die Unterlagen" in r["text"]
    assert [a["name"] for a in r["attachments"] if not a["inline"]] == ["Vertrag ä.pdf"]


def test_html_bereinigt_mit_csp_und_bilder_gesperrt(client, alice, acc):
    mid = _mid(client, alice, "Angebot")
    r = client.get(f"{B}/messages/{mid}/html", headers=alice)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    assert "default-src 'none'" in r.headers["content-security-policy"]
    assert r.headers["x-content-type-options"] == "nosniff"
    assert "<script" not in r.text.lower() and "track.example" not in r.text and "javascript:" not in r.text
    r2 = client.get(f"{B}/messages/{mid}/html", params={"images": 1}, headers=alice)
    assert "track.example" in r2.text and "https:" in r2.headers["content-security-policy"]


def test_anhang_download_sicher(client, alice, acc):
    mid = _mid(client, alice, "Re: Unterlagen")
    att = client.get(f"{B}/messages/{mid}", headers=alice).json()["attachments"]
    pdf = next(a for a in att if a["name"] == "Vertrag ä.pdf")
    r = client.get(f"{B}/attachments/{mid}/{pdf['index']}", headers=alice)
    assert r.status_code == 200 and r.content == b"%PDF-1.4 fake pdf"
    assert r.headers["content-disposition"].startswith("attachment;") and r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["content-type"] == "application/octet-stream", "nie im Browser ausführen"
    assert client.get(f"{B}/attachments/{mid}/99", headers=alice).status_code == 404


def test_inline_bild_im_html_erreichbar(client, alice, acc):
    mid = _mid(client, alice, "Re: Unterlagen")
    html = client.get(f"{B}/messages/{mid}/html", headers=alice).text
    assert f"{B}/attachments/{mid}/" in html
    logo = next(a for a in client.get(f"{B}/messages/{mid}", headers=alice).json()["attachments"] if a["inline"])
    r = client.get(f"{B}/attachments/{mid}/{logo['index']}", params={"inline": 1}, headers=alice)
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"


def test_eml_herunterladen(client, alice, acc):
    mid = _mid(client, alice, "Angebot")
    r = client.get(f"{B}/messages/{mid}/eml", headers=alice)
    assert r.status_code == 200 and r.content == eml("html_tracking") and r.headers["content-type"] == "message/rfc822"


def test_fremdes_ist_404(client, alice, acc):
    bob = _h(client, "bob")
    mid = _mid(client, alice, "Angebot")
    assert client.get(f"{B}/accounts", headers=bob).json() == []
    assert client.get(f"{B}/folders", headers=bob).json() == []
    assert client.get(f"{B}/messages", headers=bob).json()["items"] == []
    for path in (f"accounts/{acc['id']}", f"messages/{mid}", f"messages/{mid}/html", f"messages/{mid}/eml",
                 f"attachments/{mid}/0"):
        assert client.get(f"{B}/{path}", headers=bob).status_code == 404, path
    assert client.patch(f"{B}/accounts/{acc['id']}", json={"label": "x"}, headers=bob).status_code == 404
    assert client.delete(f"{B}/accounts/{acc['id']}", headers=bob).status_code == 404
    assert client.post(f"{B}/accounts/{acc['id']}/sync", headers=bob).status_code == 404
    folders = client.get(f"{B}/folders", headers=alice).json()
    assert client.get(f"{B}/messages", params={"folder_id": folders[0]["id"]}, headers=bob).json()["items"] == []


def test_konto_aendern_und_entfernen(client, alice, acc):
    r = client.patch(f"{B}/accounts/{acc['id']}", json={"label": "Neu"}, headers=alice)
    assert r.status_code == 200 and r.json()["label"] == "Neu"
    assert client.patch(f"{B}/accounts/{acc['id']}", json={"address": "x@y.de"}, headers=alice).status_code == 422
    assert client.delete(f"{B}/accounts/{acc['id']}", headers=alice).status_code == 204
    assert client.get(f"{B}/accounts", headers=alice).json() == []


def test_status_und_fortschritt(client, alice, acc):
    r = client.get(f"{B}/accounts/{acc['id']}", headers=alice).json()
    assert r["status"] == "ok" and r["sync"]["messages_done"] == 3 and r["sync"]["running"] == 0


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
