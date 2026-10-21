"""M1 Schritt 10: Konten – nur eigene, Passwort nie im Klartext/in Antworten, Verbindungstest, Status."""
from __future__ import annotations

import pytest

BASE = {"label": "Privat", "address": "till@example.net", "imap_host": "imap.example.net", "imap_port": 993,
        "imap_tls": "ssl", "smtp_host": "smtp.example.net", "smtp_port": 465, "smtp_tls": "ssl",
        "username": "till@example.net", "password": "geheim-123"}


@pytest.fixture(autouse=True)
def no_net(monkeypatch):
    """Kein echtes Netz: Verbindungstest über einen Schalter."""
    from backend import accounts
    calls = []

    def fake_test(acc, password):
        calls.append((acc["imap_host"], password))
        if password == "falsch":
            raise accounts.ConnectError("auth", "Anmeldung fehlgeschlagen")
        return {"folders": 3}
    monkeypatch.setattr(accounts, "_test_login", fake_test)
    return calls


def test_anlegen_und_lesen_ohne_passwort(no_net):
    from backend import accounts
    a = accounts.create("alice", dict(BASE))
    assert a["address"] == "till@example.net" and a["status"] == "ok" and "password" not in a and "secret" not in a
    assert no_net == [("imap.example.net", "geheim-123")], "vor dem Speichern getestet"
    assert [x["id"] for x in accounts.list_for("alice")] == [a["id"]]


def test_passwort_nicht_im_klartext_in_db():
    from backend import accounts
    from hydrahive.db.connection import db
    a = accounts.create("alice", dict(BASE))
    with db() as c:
        row = c.execute("SELECT * FROM module_mailbox_accounts WHERE id=?", (a["id"],)).fetchone()
    assert "geheim-123" not in " ".join(str(v) for v in tuple(row)) and row["secret"].startswith("mbx:v1:")
    assert accounts.password_of(a["id"]) == "geheim-123"


def test_falsches_passwort_wird_nicht_gespeichert(no_net):
    from backend import accounts
    with pytest.raises(accounts.ConnectError) as e:
        accounts.create("alice", {**BASE, "password": "falsch"})
    assert e.value.code == "auth" and accounts.list_for("alice") == []


def test_nur_eigene_konten():
    from backend import accounts
    a = accounts.create("alice", dict(BASE))
    assert accounts.list_for("bob") == []
    assert accounts.get_own("bob", a["id"]) is None and accounts.get_own("alice", a["id"])["id"] == a["id"]
    with pytest.raises(accounts.NotFound):
        accounts.update("bob", a["id"], {"label": "fremd"})
    with pytest.raises(accounts.NotFound):
        accounts.remove("bob", a["id"])


@pytest.mark.parametrize("bad", [{"address": "kaputt"}, {"imap_port": 8080}, {"imap_tls": "none"}, {"imap_host": ""},
                                 {"password": ""}, {"label": "x" * 300}, {"username": ""}, {"smtp_port": 22},
                                 {"imap_host": "a" * 300}])
def test_ungueltige_eingaben(bad):
    from backend import accounts
    with pytest.raises(ValueError):
        accounts.create("alice", {**BASE, **bad})


def test_aendern_ohne_passwort_behaelt_es(no_net):
    from backend import accounts
    a = accounts.create("alice", dict(BASE))
    no_net.clear()
    b = accounts.update("alice", a["id"], {"label": "Privat neu", "signature": "Gruß Till"})
    assert b["label"] == "Privat neu" and accounts.password_of(a["id"]) == "geheim-123" and no_net == []


def test_aendern_mit_neuem_passwort_testet(no_net):
    from backend import accounts
    a = accounts.create("alice", dict(BASE))
    with pytest.raises(accounts.ConnectError):
        accounts.update("alice", a["id"], {"password": "falsch"})
    assert accounts.password_of(a["id"]) == "geheim-123", "altes Passwort bleibt bei Fehlschlag"
    accounts.update("alice", a["id"], {"password": "neu-456"})
    assert accounts.password_of(a["id"]) == "neu-456"


def test_adresse_nicht_aenderbar():
    """Die Adresse ist der Archivordner – ändern würde das Archiv zerreißen."""
    from backend import accounts
    a = accounts.create("alice", dict(BASE))
    with pytest.raises(ValueError):
        accounts.update("alice", a["id"], {"address": "anders@example.net"})


def test_doppelt_gleiche_adresse_abgelehnt():
    from backend import accounts
    accounts.create("alice", dict(BASE))
    with pytest.raises(accounts.Conflict):
        accounts.create("alice", dict(BASE))


def test_entfernen_behaelt_archiv(archive):
    """Konto entfernen: Zugang weg, Archivdateien bleiben (Spec: nie löschen)."""
    from backend import accounts
    a = accounts.create("alice", dict(BASE))
    f = archive / "till@example.net" / "INBOX" / "2026" / "x.eml"
    f.parent.mkdir(parents=True)
    f.write_bytes(b"mail")
    accounts.remove("alice", a["id"])
    assert accounts.list_for("alice") == [] and f.read_bytes() == b"mail"


def test_status_setzen_und_fehlertext_gekuerzt():
    from backend import accounts
    a = accounts.create("alice", dict(BASE))
    accounts.set_status(a["id"], "auth_failed", "x" * 1000)
    b = accounts.get_own("alice", a["id"])
    assert b["status"] == "auth_failed" and len(b["status_detail"]) <= 300


def test_lan_server_nur_mit_freigabe(monkeypatch):
    """Die Prüfung des Hosts (netcheck) passiert beim Verbinden; ohne Admin-Freigabe kein LAN-Server."""
    from backend import accounts
    assert accounts.allowed_internal_hosts() == set()


def test_update_lehnt_adresse_selbst_ab():
    """Zweite Schicht unabhängig von der Route: accounts.update weist „address“ ab, auch mit gültigen Feldern."""
    from backend import accounts
    a = accounts.create("alice", dict(BASE))
    with pytest.raises(ValueError):
        accounts.update("alice", a["id"], {"label": "x", "address": "till@example.net"})
    assert accounts.get_own("alice", a["id"])["label"] == "Privat"
