"""alchemy_key — Vorab-Test VOR dem Speichern, maskierter Status, Löschen. Key nie im Klartext."""
from __future__ import annotations

import pytest
from hydrahive.credentials.store import delete_credential

from backend import alchemy_client as ac
from backend import alchemy_key as ak

PREFIX = "/api/modules/cryptoboard"
USER = "testuser"


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    delete_credential(USER, ak.CREDENTIAL_NAME)


# ---------------------------------------------------------------- Unit: set_key/test_key


@pytest.mark.asyncio
async def test_erfolgreicher_key_wird_gespeichert(monkeypatch):
    async def fake_call(chain, key, method, params):
        return "0x10"
    monkeypatch.setattr(ac, "call", fake_call)
    ok, code = await ak.set_key(USER, "gueltiger-key-123")
    assert ok is True
    assert code == ""
    assert ak.status(USER)["set"] is True


@pytest.mark.asyncio
async def test_ungueltiger_key_401_wird_nicht_gespeichert(monkeypatch):
    async def fake_call(chain, key, method, params):
        raise ac.AlchemyHttpError(401, "Unauthorized")
    monkeypatch.setattr(ac, "call", fake_call)
    ok, code = await ak.set_key(USER, "falscher-key")
    assert ok is False
    assert code == "alchemy_key_invalid"
    assert ak.status(USER)["set"] is False


@pytest.mark.asyncio
async def test_base_nicht_im_plan_403_mit_hinweis_wird_nicht_gespeichert(monkeypatch):
    async def fake_call(chain, key, method, params):
        raise ac.AlchemyHttpError(403, "This network is not enabled for your plan")
    monkeypatch.setattr(ac, "call", fake_call)
    ok, code = await ak.set_key(USER, "key-ohne-base")
    assert ok is False
    assert code == "alchemy_base_not_enabled"
    assert ak.status(USER)["set"] is False


@pytest.mark.asyncio
async def test_netzfehler_wird_nicht_gespeichert(monkeypatch):
    async def fake_call(chain, key, method, params):
        raise ac.AlchemyNetworkError()
    monkeypatch.setattr(ac, "call", fake_call)
    ok, code = await ak.set_key(USER, "irgendein-key")
    assert ok is False
    assert code == "alchemy_network_error"
    assert ak.status(USER)["set"] is False


@pytest.mark.asyncio
async def test_leerer_key_wird_abgelehnt(monkeypatch):
    async def boom(*a, **kw):
        raise AssertionError("darf nicht getestet werden")
    monkeypatch.setattr(ac, "call", boom)
    ok, code = await ak.set_key(USER, "   ")
    assert ok is False
    assert code == "alchemy_key_empty"


def test_status_ohne_key():
    s = ak.status("ganz-neuer-user-ohne-key")
    assert s == {"set": False, "masked": None}


@pytest.mark.asyncio
async def test_maskierung_zeigt_nie_den_klartext(monkeypatch):
    async def fake_call(chain, key, method, params):
        return "0x1"
    monkeypatch.setattr(ac, "call", fake_call)
    secret = "sk-alchemy-ganzgeheim-0001"
    await ak.set_key(USER, secret)
    s = ak.status(USER)
    assert s["set"] is True
    assert secret not in s["masked"]
    assert s["masked"].startswith(secret[:4])
    assert s["masked"].endswith(secret[-4:])


@pytest.mark.asyncio
async def test_delete_entfernt_key(monkeypatch):
    async def fake_call(chain, key, method, params):
        return "0x1"
    monkeypatch.setattr(ac, "call", fake_call)
    await ak.set_key(USER, "key-zum-loeschen")
    assert ak.status(USER)["set"] is True
    assert ak.delete_key(USER) is True
    assert ak.status(USER)["set"] is False


# ---------------------------------------------------------------- Routen (End-to-End gegen TestClient)


@pytest.mark.asyncio
async def test_route_put_speichert_bei_erfolg(client, auth_headers, monkeypatch):
    async def fake_call(chain, key, method, params):
        return "0x10"
    monkeypatch.setattr(ac, "call", fake_call)
    r = client.put(f"{PREFIX}/alchemy-key", json={"key": "guter-key-123"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["set"] is True
    assert "guter-key-123" not in r.text


@pytest.mark.asyncio
async def test_route_put_speichert_nichts_bei_fehler(client, auth_headers, monkeypatch):
    async def fake_call(chain, key, method, params):
        raise ac.AlchemyHttpError(401, "nope")
    monkeypatch.setattr(ac, "call", fake_call)
    r = client.put(f"{PREFIX}/alchemy-key", json={"key": "schlechter-key"}, headers=auth_headers)
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "alchemy_key_invalid"
    assert "schlechter-key" not in r.text
    status_r = client.get(f"{PREFIX}/alchemy-key", headers=auth_headers)
    assert status_r.json()["set"] is False


def test_route_get_ohne_auth_401(client):
    assert client.get(f"{PREFIX}/alchemy-key").status_code == 401


@pytest.mark.asyncio
async def test_route_delete(client, auth_headers, monkeypatch):
    async def fake_call(chain, key, method, params):
        return "0x1"
    monkeypatch.setattr(ac, "call", fake_call)
    client.put(f"{PREFIX}/alchemy-key", json={"key": "zu-loeschen-123"}, headers=auth_headers)
    r = client.delete(f"{PREFIX}/alchemy-key", headers=auth_headers)
    assert r.status_code == 200
    assert client.get(f"{PREFIX}/alchemy-key", headers=auth_headers).json()["set"] is False


@pytest.mark.asyncio
async def test_url_pattern_erlaubt_automatischen_einsatz():
    """has_concrete_host muss das Muster akzeptieren, sonst würde ein echter fetch_url-Aufruf
    den Key nie automatisch einsetzen (Security-Konvention ef27f79b)."""
    from hydrahive.credentials.models import has_concrete_host
    assert has_concrete_host(ak._URL_PATTERN) is True
