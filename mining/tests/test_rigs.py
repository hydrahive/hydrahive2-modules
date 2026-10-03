"""E2: Rigs koppeln, freigeben, sperren, melden."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from backend import pairing, rigs, tls_pin

P = "/api/modules/mining"
D = "/api/module-device/mining"
INFO = {"hostname": "wks", "os": "Ubuntu 26.04", "client_version": "0.1.0",
        "gpu_vendor": "nvidia", "gpu_model": "RTX 5060 Ti", "gpu_mem_mb": 16311, "driver": "595.91"}


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    try:
        from hydrahive.api.middleware import inbound_ratelimit
        inbound_ratelimit.reset()
    except ImportError:
        pass
    yield


def _pair(client, admin_headers, name="rig-01") -> dict:
    r = client.post(f"{P}/rigs/pairing", headers=admin_headers, json={"name": name})
    assert r.status_code == 200, r.text
    return r.json()


def _enroll(client, code, info=INFO):
    return client.post(f"{D}/enroll", headers={"X-Pairing-Code": code}, json={"info": info})


def _report(client, token, state=None):
    return client.post(f"{D}/report", headers={"Authorization": f"Bearer {token}"},
                       json={"state": state or {"miner": "idle"}, "info": INFO})


# ---- Kopplungs-Code ----
def test_pairing_needs_control(client, user_headers):
    assert client.post(f"{P}/rigs/pairing", headers=user_headers, json={"name": "x"}).status_code == 403


@pytest.mark.parametrize("name", ["", "Rig 1", "-a", "a" * 33, "../x", "RIG"])
def test_pairing_rejects_bad_names(client, admin_headers, name):
    assert client.post(f"{P}/rigs/pairing", headers=admin_headers, json={"name": name}).status_code == 400


def test_pairing_returns_code_and_command(client, admin_headers):
    p = _pair(client, admin_headers)
    assert len(pairing.normalize(p["code"])) == pairing.CODE_LEN
    assert set(pairing.normalize(p["code"])) <= set(pairing.ALPHABET)
    assert "--code" in p["command"] and p["code"] in p["command"]
    with __import__("hydrahive.db.connection", fromlist=["db"]).db() as c:
        stored = [r[0] for r in c.execute("SELECT code_hash FROM module_mining_pairing")]
    assert pairing.normalize(p["code"]) not in stored          # nur Hash gespeichert
    assert pairing.code_hash(p["code"]) in stored


# ---- Enroll ----
def test_enroll_happy_path_creates_pending_rig(client, admin_headers):
    p = _pair(client, admin_headers)
    r = _enroll(client, p["code"].lower())                       # Groß/klein + Bindestriche egal
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "rig-01" and body["status"] == "pending"
    assert body["token"].startswith(rigs.TOKEN_PREFIX)
    listed = client.get(f"{P}/rigs", headers=admin_headers).json()
    assert listed[0]["gpu_model"] == "RTX 5060 Ti" and "token_hash" not in listed[0]


def test_enroll_code_single_use(client, admin_headers):
    p = _pair(client, admin_headers)
    assert _enroll(client, p["code"]).status_code == 201
    assert _enroll(client, p["code"]).status_code == 401


def test_enroll_expired_code(client, admin_headers, monkeypatch):
    p = _pair(client, admin_headers)
    later = datetime.now(timezone.utc) + timedelta(minutes=pairing.TTL_MINUTES + 1)
    monkeypatch.setattr(pairing, "_now", lambda: later)
    assert _enroll(client, p["code"]).status_code == 401


def test_enroll_wrong_or_missing_code(client):
    assert _enroll(client, "AAAA-BBBB-CCCC").status_code == 401
    assert client.post(f"{D}/enroll", json={"info": INFO}).status_code == 401


def test_enroll_with_token_instead_of_code_rejected(client, admin_headers):
    tok = _enroll(client, _pair(client, admin_headers)["code"]).json()["token"]
    r = client.post(f"{D}/enroll", headers={"Authorization": f"Bearer {tok}"}, json={})
    assert r.status_code == 401


def test_enroll_layer_rejects_used_code_without_route_guard(client, admin_headers):
    """Zweite Schutzschicht: rigs.enroll selbst verbraucht nur gültige Codes.

    Die Route prüft vorher schon mit peek(); hier wird die innere Schicht
    direkt angesprochen (Schutz gegen gleichzeitige Anfragen, die beide
    peek() passieren).
    """
    p = _pair(client, admin_headers, "race")
    assert rigs.enroll(p["code"], INFO, "1.2.3.4")["name"] == "race"
    with pytest.raises(rigs.RigError, match="pairing_code_invalid"):
        rigs.enroll(p["code"], INFO, "1.2.3.4")


def test_enroll_layer_rejects_expired_code(client, admin_headers, monkeypatch):
    p = _pair(client, admin_headers, "late")
    later = datetime.now(timezone.utc) + timedelta(minutes=pairing.TTL_MINUTES + 1)
    monkeypatch.setattr(pairing, "_now", lambda: later)
    with pytest.raises(rigs.RigError, match="pairing_code_invalid"):
        rigs.enroll(p["code"], INFO, "1.2.3.4")


def test_enroll_route_ignores_token_header_when_code_also_sent(client, admin_headers):
    """Token + Code zusammen: Token gewinnt → kein Enroll (kein zweiter Rig per Token)."""
    tok = _enroll(client, _pair(client, admin_headers, "a1")["code"]).json()["token"]
    p2 = _pair(client, admin_headers, "a2")
    r = client.post(f"{D}/enroll", headers={"Authorization": f"Bearer {tok}", "X-Pairing-Code": p2["code"]},
                    json={})
    assert r.status_code == 401
    assert pairing.peek(p2["code"]) is not None


def test_invalid_bearer_is_rejected_even_with_valid_code(client, admin_headers):
    """Ein kaputtes Token wird abgewiesen, nicht stillschweigend auf den Code umgelenkt."""
    p = _pair(client, admin_headers, "strict")
    r = client.post(f"{D}/enroll", headers={"Authorization": "Bearer hhrig_kaputt", "X-Pairing-Code": p["code"]},
                    json={})
    assert r.status_code == 401
    assert pairing.peek(p["code"]) is not None


def test_enroll_name_taken_keeps_code_unused(client, admin_headers):
    _enroll(client, _pair(client, admin_headers, "dup")["code"])
    p2 = _pair(client, admin_headers, "dup")
    assert _enroll(client, p2["code"]).status_code == 409
    assert pairing.peek(p2["code"]) is not None                   # Rollback: Code noch gültig


def test_enroll_sanitizes_info(client, admin_headers):
    p = _pair(client, admin_headers)
    _enroll(client, p["code"], {"gpu_vendor": "evil", "gpu_mem_mb": True, "gpu_model": "x" * 500})
    rig = client.get(f"{P}/rigs", headers=admin_headers).json()[0]
    assert rig["gpu_vendor"] == "unknown" and rig["gpu_mem_mb"] is None and len(rig["gpu_model"]) == 120


# ---- Melden + Soll-Zustand ----
def test_report_pending_then_approved(client, admin_headers):
    e = _enroll(client, _pair(client, admin_headers)["code"]).json()
    r = _report(client, e["token"])
    assert r.status_code == 200 and r.json()["desired"] == {"action": "stop", "reason": "awaiting_approval"}
    assert client.post(f"{P}/rigs/{e['rig_id']}/approve", headers=admin_headers).status_code == 200
    assert _report(client, e["token"]).json()["desired"]["reason"] == "no_miner_yet"
    rig = client.get(f"{P}/rigs", headers=admin_headers).json()[0]
    assert rig["status"] == "active" and rig["last_report"] == {"miner": "idle"}


def test_report_disabled(client, admin_headers):
    e = _enroll(client, _pair(client, admin_headers)["code"]).json()
    client.post(f"{P}/rigs/{e['rig_id']}/approve", headers=admin_headers)
    client.post(f"{P}/rigs/{e['rig_id']}/enabled", headers=admin_headers, json={"enabled": False})
    assert _report(client, e["token"]).json()["desired"]["reason"] == "disabled"
    assert client.post(f"{P}/rigs/{e['rig_id']}/enabled", headers=admin_headers,
                       json={"enabled": "nein"}).status_code == 400


def test_report_wrong_token(client):
    assert _report(client, "hhrig_falsch").status_code == 401
    assert _report(client, "kein-prefix").status_code == 401


def test_report_with_pairing_code_rejected(client, admin_headers):
    p = _pair(client, admin_headers)
    r = client.post(f"{D}/report", headers={"X-Pairing-Code": p["code"]}, json={})
    assert r.status_code == 401


def test_report_too_large(client, admin_headers):
    e = _enroll(client, _pair(client, admin_headers)["code"]).json()
    assert _report(client, e["token"], {"x": "a" * (rigs.MAX_REPORT_BYTES + 10)}).status_code == 413


# ---- Sperren / Löschen ----
def test_revoke_takes_effect_immediately(client, admin_headers):
    e = _enroll(client, _pair(client, admin_headers)["code"]).json()
    assert _report(client, e["token"]).status_code == 200
    assert client.post(f"{P}/rigs/{e['rig_id']}/revoke", headers=admin_headers).status_code == 200
    assert _report(client, e["token"]).status_code == 401
    assert client.post(f"{P}/rigs/{e['rig_id']}/approve", headers=admin_headers).status_code == 404


def test_revoke_removes_token_hash(client, admin_headers):
    """Schicht 1: das Token ist nach dem Sperren physisch weg (nicht nur der Status)."""
    e = _enroll(client, _pair(client, admin_headers)["code"]).json()
    client.post(f"{P}/rigs/{e['rig_id']}/revoke", headers=admin_headers)
    from hydrahive.db.connection import db
    with db() as c:
        assert c.execute("SELECT token_hash FROM module_mining_rigs WHERE id = ?",
                         (e["rig_id"],)).fetchone()[0] is None


def test_by_token_ignores_revoked_status(client, admin_headers):
    """Schicht 2: auch wenn ein Hash stehen bliebe, gilt ein gesperrter Rig nicht."""
    e = _enroll(client, _pair(client, admin_headers)["code"]).json()
    from hydrahive.db.connection import db
    with db() as c:
        c.execute("UPDATE module_mining_rigs SET status = 'revoked' WHERE id = ?", (e["rig_id"],))
    assert rigs.by_token(e["token"]) is None


def test_delete_only_revoked(client, admin_headers):
    e = _enroll(client, _pair(client, admin_headers)["code"]).json()
    assert client.delete(f"{P}/rigs/{e['rig_id']}", headers=admin_headers).status_code == 404
    client.post(f"{P}/rigs/{e['rig_id']}/revoke", headers=admin_headers)
    assert client.delete(f"{P}/rigs/{e['rig_id']}", headers=admin_headers).status_code == 200
    assert client.get(f"{P}/rigs", headers=admin_headers).json() == []


def test_admin_routes_need_control(client, user_headers):
    for method, path in (("get", "/rigs"), ("post", "/rigs/x/approve"), ("post", "/rigs/x/revoke"),
                         ("delete", "/rigs/x")):
        assert getattr(client, method)(f"{P}{path}", headers=user_headers).status_code == 403, path


# ---- Zertifikats-Pin ----
def test_spki_pin_matches_openssl_format():
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, "t")])
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(1).not_valid_before(now).not_valid_after(now + timedelta(days=1))
            .sign(key, hashes.SHA256()))
    pin = tls_pin.spki_pin_from_pem(cert.public_bytes(serialization.Encoding.PEM))
    import base64
    import hashlib
    spki = key.public_key().public_bytes(serialization.Encoding.DER,
                                         serialization.PublicFormat.SubjectPublicKeyInfo)
    assert pin == "sha256//" + base64.b64encode(hashlib.sha256(spki).digest()).decode()
    assert tls_pin.spki_pin_from_pem(b"kein zertifikat") is None


# ---- Pin nur bei lokalen Adressen (Fehler beim Kollegen 03.10.: Cloudflare-Domain) ----
@pytest.mark.parametrize("host,local", [
    ("192.168.178.75", True), ("192.168.178.217:443", True), ("[fd00::1]:8443", True), ("fd00::1", True),
    ("hydrahive", True), ("hydra.local", True), ("server.lan", True), ("nas.home.arpa", True),
    ("hydra.myemployeeai.com", False), ("hydra.myemployeeai.com:443", False), ("example.org", False),
    ("", False),
])
def test_is_local_host(host, local):
    assert tls_pin.is_local_host(host) is local


def _fake_cert(tmp_path, monkeypatch):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, "hydrahive2")])
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(1).not_valid_before(now).not_valid_after(now + timedelta(days=1)).sign(key, hashes.SHA256()))
    p = tmp_path / "hydrahive.crt"
    p.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    monkeypatch.setattr(tls_pin, "_cert_path", lambda: p)


def test_pairing_command_without_pin_for_public_domain(client, admin_headers, tmp_path, monkeypatch):
    _fake_cert(tmp_path, monkeypatch)
    r = client.post(f"{P}/rigs/pairing", headers={**admin_headers, "Host": "hydra.myemployeeai.com"},
                    json={"name": "kollege"})
    body = r.json()
    assert body["pin"] is None and "--pin" not in body["command"]
    assert "--server https://hydra.myemployeeai.com" in body["command"]


def test_pairing_command_with_pin_for_lan_ip(client, admin_headers, tmp_path, monkeypatch):
    _fake_cert(tmp_path, monkeypatch)
    r = client.post(f"{P}/rigs/pairing", headers={**admin_headers, "Host": "192.168.178.75"}, json={"name": "heim"})
    body = r.json()
    assert body["pin"] and body["pin"].startswith("sha256//") and f"--pin {body['pin']}" in body["command"]
