"""M3a Schritt 1: Freigabe je Projekt / Buddy – wer sieht welches Konto in einem Werkzeuglauf."""
from __future__ import annotations

import pytest


def _acc(user: str, address: str) -> str:
    from backend import accounts
    from hydrahive.db._utils import now_iso
    from hydrahive.db.connection import db
    aid = "acc-" + address.split("@")[0]
    with db() as c:
        c.execute("INSERT INTO module_mailbox_accounts(id, owner, label, address, imap_host, username, secret, "
                  "status, created_at, updated_at) VALUES (?,?,?,?,?,?,?, 'ok', ?, ?)",
                  (aid, f"user:{user}", address, address, "imap.example.net", address, "x", now_iso(), now_iso()))
    assert accounts.get_own(user, aid)
    return aid


@pytest.fixture
def project():
    from hydrahive.projects import config as pc
    p = pc.create("Mail-Projekt", llm_model="m", created_by="alice", members=[{"username": "bob", "role": "read"}])
    yield p["id"]
    pc.delete(p["id"])


@pytest.fixture
def other_project():
    from hydrahive.projects import config as pc
    p = pc.create("Anderes", llm_model="m", created_by="alice")
    yield p["id"]
    pc.delete(p["id"])


def test_freigabe_nur_fuer_eigenes_konto(project):
    from backend import shares
    aid = _acc("alice", "alice@example.net")
    shares.put("alice", aid, f"project:{project}", "read")
    assert shares.list_for("alice", aid) == [{"target": f"project:{project}", "level": "read",
                                              "created_by": "alice", "created_at": shares.list_for("alice", aid)[0]["created_at"]}]
    with pytest.raises(shares.NotFound):
        shares.put("bob", aid, f"project:{project}", "read")
    with pytest.raises(shares.NotFound):
        shares.list_for("bob", aid)


def test_ziel_und_stufe_werden_geprueft(project):
    from backend import shares
    aid = _acc("alice", "alice@example.net")
    for bad in ("project:gibtsnicht", "project:../x", "irgendwas", "", "buddy:bob"):
        with pytest.raises(ValueError):
            shares.put("alice", aid, bad, "read")
    with pytest.raises(ValueError):
        shares.put("alice", aid, f"project:{project}", "send")   # Senden kommt erst mit M4


def test_nur_mitglieder_duerfen_ein_projekt_freigeben(other_project):
    """bob ist nicht Mitglied von other_project → er darf sein Konto dort nicht hineinreichen."""
    from backend import shares
    aid = _acc("bob", "bob@example.net")
    with pytest.raises(ValueError):
        shares.put("bob", aid, f"project:{other_project}", "read")


def test_werkzeug_sieht_nur_freigaben_des_aktiven_projekts(project, other_project):
    from backend import shares
    aid = _acc("alice", "alice@example.net")
    shares.put("alice", aid, f"project:{project}", "read")
    assert set(shares.visible("alice", project)) == {aid}
    assert shares.visible("alice", other_project) == {}
    assert shares.visible("alice", None) == {}                    # ohne Projekt: nur Buddy-Freigaben


def test_mitglied_sieht_freigabe_nichtmitglied_nicht(project):
    from backend import shares
    aid = _acc("alice", "alice@example.net")
    shares.put("alice", aid, f"project:{project}", "read")
    assert set(shares.visible("bob", project)) == {aid}           # bob ist Mitglied (read)
    assert shares.visible("carol", project) == {}                 # carol nicht


def test_buddy_freigabe_nur_fuer_besitzer_ohne_projekt(project):
    from backend import shares
    aid = _acc("alice", "alice@example.net")
    shares.put("alice", aid, "buddy", "read")
    assert set(shares.visible("alice", None)) == {aid}
    assert shares.visible("bob", None) == {}
    assert shares.visible("alice", project) == {}                 # im Projekt zählt nur die Projekt-Freigabe


def test_entfernen_und_konto_loeschen_raeumt_auf(project):
    from backend import accounts, shares
    aid = _acc("alice", "alice@example.net")
    shares.put("alice", aid, f"project:{project}", "read")
    shares.put("alice", aid, f"project:{project}", "read")        # zweimal = einmal
    assert len(shares.list_for("alice", aid)) == 1
    assert shares.remove("alice", aid, f"project:{project}") is True
    assert shares.remove("alice", aid, f"project:{project}") is False
    shares.put("alice", aid, "buddy", "read")
    accounts.remove("alice", aid)
    assert shares.visible("alice", None) == {}
