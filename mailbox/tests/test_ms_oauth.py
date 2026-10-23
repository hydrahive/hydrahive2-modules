"""M1b: Transport zu Microsoft (Geräte-Code, Token, Erneuern) und die globale Microsoft-App des Admins."""
# ruff: noqa: F811 - pytest-Fixtures aus _ms_base
from __future__ import annotations

import pytest
from _ms_base import CID, DEVICE, _ms_state, err, ms  # noqa: F401

SCOPES = {"https://outlook.office.com/IMAP.AccessAsUser.All", "https://outlook.office.com/SMTP.Send", "offline_access"}


def test_geraete_code_richtige_adresse_und_bereiche(ms):
    from backend import oauth_ms
    r = oauth_ms.device_code(CID, "common")
    assert r == {"device_code": "DEV-geheim", "user_code": "ABCD-EFGH", "verification_uri": "https://microsoft.com/devicelogin",
                 "expires_in": 900, "interval": 5}
    path, form = ms.calls[0]
    assert path == "login.microsoftonline.com/common/oauth2/v2.0/devicecode"
    assert form["client_id"] == CID and set(form["scope"].split()) == SCOPES


def test_fremder_link_wird_ersetzt(ms):
    """Der Link landet als Knopf in der Oberfläche – nur Microsoft-Adressen, sonst der bekannte Standard."""
    from backend import oauth_ms
    ms.device.append((200, {**DEVICE, "verification_uri": "https://boese.example/devicelogin"}))
    assert oauth_ms.device_code(CID, "common")["verification_uri"] == "https://microsoft.com/devicelogin"
    ms.device.append((200, {**DEVICE, "verification_uri": "https://login.microsoft.com/device"}))
    assert oauth_ms.device_code(CID, "common")["verification_uri"] == "https://login.microsoft.com/device"


def test_fehler_von_microsoft_nur_erste_zeile(ms):
    from backend import oauth_ms
    ms.device.append(err("invalid_client", "AADSTS7000218: public client flows not allowed"))
    with pytest.raises(oauth_ms.OAuthError) as e:
        oauth_ms.device_code(CID, "common")
    assert e.value.code == "invalid_client" and "AADSTS7000218" in e.value.description
    assert "Trace ID" not in str(e.value)


def test_trace_id_auf_derselben_zeile_wird_abgeschnitten(ms):
    """So antwortet Microsoft wirklich (gemessen 23.10.2026 gegen login.microsoftonline.com)."""
    from backend import oauth_ms
    ms.device.append((400, {"error": "unauthorized_client", "error_description": "AADSTS700016: Application with "
                            "identifier 'x' was not found. Trace ID: e43 Correlation ID: 1 Timestamp: 2026"}))
    with pytest.raises(oauth_ms.OAuthError) as e:
        oauth_ms.device_code(CID, "consumers")
    assert e.value.description == "AADSTS700016: Application with identifier 'x' was not found."


def test_kein_netz(ms):
    from backend import oauth_ms
    ms.fail_network = True
    with pytest.raises(oauth_ms.OAuthError) as e:
        oauth_ms.device_code(CID, "common")
    assert e.value.code == "network"


@pytest.mark.parametrize("answer,state", [(err("authorization_pending"), "pending"), (err("slow_down"), "slow_down")])
def test_abfragen_wartend(ms, answer, state):
    from backend import oauth_ms
    ms.token.append(answer)
    assert oauth_ms.poll(CID, "common", "DEV-geheim") == {"state": state}
    path, form = ms.calls[0]
    assert path.endswith("/common/oauth2/v2.0/token")
    assert form == {"client_id": CID, "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    "device_code": "DEV-geheim"}


def test_abfragen_fertig(ms):
    from backend import oauth_ms
    r = oauth_ms.poll(CID, "common", "DEV-geheim")
    assert r == {"state": "done", "tokens": {"access_token": "AT-1", "refresh_token": "RT-1", "expires_in": 3600}}


def test_ohne_refresh_token_kein_erfolg(ms):
    from backend import oauth_ms
    ms.token.append((200, {"access_token": "AT-1", "expires_in": 3600}))
    with pytest.raises(oauth_ms.OAuthError) as e:
        oauth_ms.poll(CID, "common", "DEV-geheim")
    assert e.value.code == "no_refresh_token"


@pytest.mark.parametrize("code", ["expired_token", "access_denied", "authorization_declined", "bad_verification_code"])
def test_abfragen_endgueltig(ms, code):
    from backend import oauth_ms
    ms.token.append(err(code))
    with pytest.raises(oauth_ms.OAuthError) as e:
        oauth_ms.poll(CID, "common", "DEV-geheim")
    assert e.value.code == code


def test_erneuern(ms):
    from backend import oauth_ms
    ms.token.append((200, {"access_token": "AT-2", "refresh_token": "RT-2", "expires_in": 3599}))
    want = {"access_token": "AT-2", "refresh_token": "RT-2", "expires_in": 3599}
    assert oauth_ms.refresh(CID, "consumers", "RT-1") == want
    path, form = ms.calls[0]
    assert path.endswith("/consumers/oauth2/v2.0/token")
    assert form["grant_type"] == "refresh_token" and form["refresh_token"] == "RT-1"
    assert set(form["scope"].split()) == SCOPES
    ms.token.append(err("invalid_grant", "AADSTS70000: revoked"))
    with pytest.raises(oauth_ms.OAuthError) as e:
        oauth_ms.refresh(CID, "consumers", "RT-2")
    assert e.value.code == "invalid_grant" and "RT-2" not in str(e.value)


# ---- Microsoft-App (einmal global, Admin) ----

@pytest.mark.parametrize("tenant,want", [("", "common"), ("Consumers", "consumers"),
                                         ("organizations", "organizations"),
                                         ("firma.onmicrosoft.com", "firma.onmicrosoft.com"),
                                         ("AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE",
                                          "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")])
def test_app_gueltig(tenant, want):
    from backend import ms_app
    assert ms_app.normalize(" " + CID.upper() + " ", tenant) == (CID, want)


@pytest.mark.parametrize("cid,tenant", [("123", "common"), (CID, "../x"), (CID, "a b"), (CID, "common/../evil"),
                                        ("", "common"), (CID, "x" * 300)])
def test_app_ungueltig(cid, tenant):
    from backend import ms_app
    with pytest.raises(ValueError):
        ms_app.normalize(cid, tenant)


def test_app_speichern_lesen_leeren():
    from backend import ms_app
    assert ms_app.get() == {"client_id": "", "tenant": "common"} and not ms_app.configured()
    ms_app.save(CID, "consumers")
    assert ms_app.get() == {"client_id": CID, "tenant": "consumers"} and ms_app.configured()
    ms_app.save("", "")
    assert not ms_app.configured()
