"""M1 Schritt 11: Routen über den echten Kern (Modul-Tor module.mailbox). Fremdes = 404, Passwort nie in Antworten."""
# ruff: noqa: F811 - pytest-Fixtures aus _routes_base werden als gleichnamige Parameter genutzt
from __future__ import annotations

import pytest
from conftest import eml  # noqa: F401
from _routes_base import B, NEW, _h, _mid, acc, alice, client, fake_net, rights  # noqa: F401 - Fixtures/Hilfen


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


