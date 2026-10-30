"""Hydra-Labor L2 Baustein 1: GitHub verbinden (Device-Flow), Token verschlüsselt, nur public_repo."""
from __future__ import annotations

import asyncio
import logging

import pytest
from backend import github_auth
from fake_github import TOKEN


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def gh(fake_github, db_ready):
    github_auth.disconnect()
    yield fake_github
    github_auth.disconnect()


def test_client_id_aus_einstellung(monkeypatch):
    monkeypatch.setenv("HH_LABOR_GITHUB_CLIENT_ID", "Iv1.test123")
    assert github_auth.client_id() == "Iv1.test123"


def test_client_id_der_hydrahive_app(monkeypatch):
    monkeypatch.delenv("HH_LABOR_GITHUB_CLIENT_ID", raising=False)
    assert github_auth.client_id() == "Ov23lis4cKnscWQwA60e"


def test_leere_einstellung_nimmt_app(monkeypatch):
    monkeypatch.setenv("HH_LABOR_GITHUB_CLIENT_ID", "  ")
    assert github_auth.client_id() == "Ov23lis4cKnscWQwA60e"


def test_ohne_client_id_klare_meldung(gh, monkeypatch):
    monkeypatch.setattr(github_auth, "CLIENT_ID", "")
    monkeypatch.delenv("HH_LABOR_GITHUB_CLIENT_ID", raising=False)
    with pytest.raises(github_auth.GitHubError) as e:
        run(github_auth.start())
    assert e.value.code == "labor_github_not_configured"


@pytest.fixture
def cid(monkeypatch):
    monkeypatch.setenv("HH_LABOR_GITHUB_CLIENT_ID", "Iv1.test123")


def test_start_gibt_code_und_link_nie_device_code(gh, cid):
    out = run(github_auth.start())
    assert out == {"user_code": "ABCD-1234", "verification_uri": "https://github.com/login/device", "expires_in": 900}
    first = gh.calls[0]
    assert first["url"] == "https://github.com/login/device/code"
    assert first["data"] == {"client_id": "Iv1.test123", "scope": "public_repo"}


def test_warten_bis_freigabe_dann_gespeichert(gh, cid):
    gh.device_answers = [{"error": "authorization_pending"}, {"error": "authorization_pending"},
                         {"access_token": TOKEN, "scope": "public_repo"}]
    run(github_auth.start())
    assert run(github_auth.wait()) == {"connected": True, "login": "nutzer"}
    st = github_auth.status()
    assert st == {"connected": True, "login": "nutzer", "pending": False}
    polls = [c for c in gh.calls if c["url"].endswith("/access_token")]
    assert len(polls) == 3
    assert polls[0]["data"]["grant_type"] == "urn:ietf:params:oauth:grant-type:device_code"
    assert polls[0]["data"]["device_code"] == "DEV123"


def test_token_verschluesselt_und_nirgends_sichtbar(gh, cid, caplog):
    from hydrahive.db.connection import db
    with caplog.at_level(logging.DEBUG):
        run(github_auth.start())
        run(github_auth.wait())
    with db() as c:
        enc = c.execute("SELECT token_enc FROM module_hydralabor_github WHERE id = 1").fetchone()[0]
    assert enc.startswith("enc:v1:") and TOKEN not in enc
    assert github_auth.token() == TOKEN
    assert TOKEN not in caplog.text
    assert TOKEN not in str(github_auth.status())


def test_slow_down_verlaengert_abstand(gh, cid, monkeypatch):
    waits = []

    async def fake_sleep(s):
        waits.append(s)
    monkeypatch.setattr(github_auth.asyncio, "sleep", fake_sleep)
    gh.device_answers = [{"error": "slow_down", "interval": 10}, {"access_token": TOKEN, "scope": "public_repo"}]
    run(github_auth.start())
    run(github_auth.wait())
    assert waits[:2] == [5, 10]


@pytest.mark.parametrize(("err", "code"), [("expired_token", "labor_github_expired"),
                                           ("access_denied", "labor_github_denied"),
                                           ("incorrect_device_code", "labor_github_failed")])
def test_abbrueche(gh, cid, err, code):
    gh.device_answers = [{"error": err}]
    run(github_auth.start())
    with pytest.raises(github_auth.GitHubError) as e:
        run(github_auth.wait())
    assert e.value.code == code
    assert github_auth.status()["connected"] is False


def test_zu_viele_rechte_nicht_gespeichert(gh, cid):
    gh.scopes = "public_repo, repo, admin:org"
    run(github_auth.start())
    with pytest.raises(github_auth.GitHubError) as e:
        run(github_auth.wait())
    assert e.value.code == "labor_github_scope"
    assert github_auth.status()["connected"] is False and github_auth.token() == ""


def test_zeit_abgelaufen_ohne_antwort(gh, cid, monkeypatch):
    gh.device_answers = [{"error": "authorization_pending"}]
    monkeypatch.setattr(github_auth, "_now", iter([0, 0, 1000, 1000, 1000]).__next__)
    run(github_auth.start())
    with pytest.raises(github_auth.GitHubError) as e:
        run(github_auth.wait())
    assert e.value.code == "labor_github_expired"


def test_warten_ohne_start(gh, cid):
    with pytest.raises(github_auth.GitHubError) as e:
        run(github_auth.wait())
    assert e.value.code == "labor_github_not_started"


def test_trennen(gh, cid):
    run(github_auth.start())
    run(github_auth.wait())
    github_auth.disconnect()
    assert github_auth.status() == {"connected": False, "login": "", "pending": False}
    assert github_auth.token() == ""


def test_start_waehrend_warten_ist_pending(gh, cid):
    run(github_auth.start())
    assert github_auth.status()["pending"] is True


@pytest.mark.parametrize("key", ["POST https://github.com/login/device/code"])
def test_start_github_lehnt_ab(gh, cid, key):
    gh.fail[key] = (422, {"error": "device_flow_disabled"})
    with pytest.raises(github_auth.GitHubError) as e:
        run(github_auth.start())
    assert e.value.code == "labor_github_failed"
    assert github_auth.status()["pending"] is False


def test_nutzer_abfrage_scheitert_nichts_gespeichert(gh, cid):
    gh.fail["GET https://api.github.com/user"] = (401, {"message": "Bad credentials"})
    run(github_auth.start())
    with pytest.raises(github_auth.GitHubError) as e:
        run(github_auth.wait())
    assert e.value.code == "labor_github_failed" and github_auth.token() == ""
