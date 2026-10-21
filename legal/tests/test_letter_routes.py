"""Routen Schriftverkehr + Briefe (Plan L3 Schritt 7). Gleicher Aufbau wie test_case_routes (Router direkt an der App)."""
# ruff: noqa: F811 - pytest-Fixtures aus test_case_routes werden als gleichnamige Parameter genutzt
from __future__ import annotations

import pytest
from test_case_routes import PREFIX, _caps, _create, _login, client, made  # noqa: F401 – pytest-Fixtures
from test_correspondence import LETTER


@pytest.fixture
def pid(client, made):
    return _create(client, made).json()["project_id"]


def test_templates_list(client):
    r = client.get(f"{PREFIX}/letters/templates", headers=_login(client, "bob"))
    assert r.status_code == 200 and r.json()["templates"][0]["key"] == "mangelanzeige"


def test_draft_from_template_needs_read_and_fills_from_case(client, pid):
    from backend import casefile
    a = _login(client, "alice")
    casefile.add_party(pid, {"role": "me", "name": "Alice Muster", "address": "Weg 1\n30159 Hannover"})
    opp = casefile.add_party(pid, {"role": "opponent", "name": "HV", "address": "Str. 2\n30159 Hannover"})
    r = client.post(f"{PREFIX}/cases/{pid}/letters/draft", json={"template": "mangelanzeige", "recipient_id": opp["id"]},
                    headers=a)
    assert r.status_code == 200 and r.json()["sender"].startswith("Alice Muster")
    assert client.post(f"{PREFIX}/cases/{pid}/letters/draft", json={"template": "mangelanzeige"},
                       headers=_login(client, "bob")).status_code == 404
    assert client.post(f"{PREFIX}/cases/{pid}/letters/draft", json={"template": "dsgvo"}, headers=a).status_code == 400


def test_check_route(client, pid):
    r = client.post(f"{PREFIX}/cases/{pid}/letters/check", json={**LETTER, "body": "binnen 14 Tagen"},
                    headers=_login(client, "alice"))
    assert r.status_code == 200
    assert {i["key"]: i["ok"] for i in r.json()["items"]}["deadline_date"] is False


def test_correspondence_crud_and_sent_lock(client, pid):
    a = _login(client, "alice")
    r = client.post(f"{PREFIX}/cases/{pid}/correspondence", json={"direction": "out", **LETTER}, headers=a)
    assert r.status_code == 201 and r.json()["status"] == "draft"
    eid = r.json()["id"]
    assert client.patch(f"{PREFIX}/cases/{pid}/correspondence/{eid}", json={"body": "Neu"}, headers=a).json()["body"] == "Neu"
    s = client.post(f"{PREFIX}/cases/{pid}/correspondence/{eid}/sent",
                    json={"date": "2026-10-21", "delivery": "einwurf_einschreiben", "proof": "RT 1"}, headers=a)
    assert s.status_code == 200 and s.json()["status"] == "sent"
    assert client.patch(f"{PREFIX}/cases/{pid}/correspondence/{eid}", json={"body": "x"}, headers=a).status_code == 409
    assert client.delete(f"{PREFIX}/cases/{pid}/correspondence/{eid}", headers=a).status_code == 409
    inc = client.post(f"{PREFIX}/cases/{pid}/correspondence",
                      json={"direction": "in", "date": "2026-10-22", "sender": "HV", "subject": "Antwort", "body": "kurz"},
                      headers=a)
    assert inc.status_code == 201 and inc.json()["status"] == "received"
    assert client.delete(f"{PREFIX}/cases/{pid}/correspondence/{inc.json()['id']}", headers=a).status_code == 204
    lst = client.get(f"{PREFIX}/cases/{pid}", headers=a).json()["correspondence"]
    assert [e["status"] for e in lst] == ["sent"]


def test_read_member_cannot_write_correspondence(client, pid):
    from hydrahive.projects import config as pc
    pc.update(pid, members=[{"username": "bob", "role": "read"}])
    b = _login(client, "bob")
    assert client.post(f"{PREFIX}/cases/{pid}/correspondence", json={"direction": "out", **LETTER},
                       headers=b).status_code == 403
    assert client.post(f"{PREFIX}/cases/{pid}/letters/check", json=LETTER, headers=b).status_code == 200


def test_invalid_input_400_with_code(client, pid):
    r = client.post(f"{PREFIX}/cases/{pid}/correspondence", json={**LETTER, "direction": "out", "delivery": "taube"},
                    headers=_login(client, "alice"))
    assert r.status_code == 400 and r.json()["detail"]["code"] == "legal_delivery_invalid"


def test_letter_proposal_accept_via_route(client, pid):
    from backend import casefile
    a = _login(client, "alice")
    pr = casefile.propose(pid, "letter", LETTER, author_name="Agent")
    assert client.post(f"{PREFIX}/cases/{pid}/proposals/{pr['id']}/accept", headers=a).status_code == 200
    lst = client.get(f"{PREFIX}/cases/{pid}", headers=a).json()["correspondence"]
    assert len(lst) == 1 and lst[0]["status"] == "draft" and lst[0]["created_by"] == "alice"
