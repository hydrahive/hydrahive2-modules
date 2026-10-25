"""Telefon-Assistent: Einstellungen speichern, Notizen ablegen/lesen, Dienste zusammenstecken (PLAN-AGENT-2B 6–7)."""
from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.usefixtures("clean_rows")
BASE = "/api/modules/telephony/connection"


@pytest.fixture(autouse=True)
def _lan(monkeypatch):
    from backend import connections, netguard

    monkeypatch.setattr(connections, "_resolve_target",
                        lambda host: netguard.check(host, resolve=lambda h: ["192.168.178.1"]))
    yield
    connections.MANAGER.stop_all()


def _setup(client, headers) -> str:
    from backend import connections

    r = client.put(BASE, json={"registrar": "fritz.box", "username": "hydra-telefon", "password": "Sehr-Geheim-42"},
                   headers=headers)
    assert r.status_code == 200, r.text
    return connections._row("user:user-owner")["id"]


def _save(client, headers, **over):
    body = {"answer_calls": True, "greeting": "", "mode": "assistant", "assistant_name": "Beispiel GmbH",
            "assistant_knowledge": "Öffnungszeiten: Mo–Fr 9–17 Uhr.", "assistant_model": ""}
    body.update(over)
    return client.put(f"{BASE}/calls", json=body, headers=headers)


def test_standard_ist_nur_ansage(client, auth_headers) -> None:
    _setup(client, auth_headers)
    d = client.get(BASE, headers=auth_headers).json()
    assert d["call_mode"] == "greeting" and d["assistant_name"] == "" and d["assistant_knowledge"] == ""


def test_assistent_einstellungen_speichern(client, auth_headers) -> None:
    _setup(client, auth_headers)
    assert _save(client, auth_headers).status_code == 200
    d = client.get(BASE, headers=auth_headers).json()
    assert d["call_mode"] == "assistant" and d["assistant_name"] == "Beispiel GmbH"
    assert d["assistant_knowledge"] == "Öffnungszeiten: Mo–Fr 9–17 Uhr." and d["assistant_model"] == ""


def test_alte_aufrufe_ohne_assistentfelder_gehen_weiter(client, auth_headers) -> None:
    """Oberfläche 0.7.x schickt nur answer_calls/greeting – der Modus bleibt dabei unverändert."""
    _setup(client, auth_headers)
    _save(client, auth_headers)
    r = client.put(f"{BASE}/calls", json={"answer_calls": False, "greeting": "x"}, headers=auth_headers)
    assert r.status_code == 200
    assert client.get(BASE, headers=auth_headers).json()["call_mode"] == "assistant"


@pytest.mark.parametrize("field,value", [
    ("mode", "chef"), ("assistant_name", "x" * 81), ("assistant_knowledge", "x" * 4001),
    ("assistant_knowledge", "a\x00b"), ("assistant_model", "x" * 201), ("assistant_name", "a\nb"),
])
def test_ungueltig(client, auth_headers, field: str, value: str) -> None:
    _setup(client, auth_headers)
    assert _save(client, auth_headers, **{field: value}).status_code == 422


def test_assistent_bundle_nur_wenn_modus_assistent(client, auth_headers, monkeypatch) -> None:
    from backend import assistant

    cid = _setup(client, auth_headers)
    assert assistant.bundle(cid) is None
    _save(client, auth_headers)
    b = assistant.bundle(cid)
    assert b["cfg"].owner_name == "Beispiel GmbH" and "9–17" in b["cfg"].knowledge
    assert callable(b["llm"]) and callable(b["stt"]) and callable(b["tts"])
    _save(client, auth_headers, mode="greeting")
    assert assistant.bundle(cid) is None


def test_modell_aus_einstellung_geht_an_den_aufruf(client, auth_headers, monkeypatch) -> None:
    from backend import assistant

    seen = {}

    async def fake_complete(messages, model=None, temperature=0.7, max_tokens=4096):
        seen.update(model=model, temperature=temperature, max_tokens=max_tokens, n=len(messages))
        return '{"say": "ok"}'
    monkeypatch.setattr(assistant, "_complete", fake_complete)
    cid = _setup(client, auth_headers)
    _save(client, auth_headers, assistant_model="ollama/llama3")
    out = assistant.bundle(cid)["llm"]([{"role": "system", "content": "x"}])
    assert out == '{"say": "ok"}' and seen["model"] == "ollama/llama3" and seen["temperature"] <= 0.4
    _save(client, auth_headers, assistant_model="")
    assistant.bundle(cid)["llm"]([{"role": "system", "content": "x"}])
    assert seen["model"] is None, "leer = Standardmodell"


def test_notiz_wird_gespeichert_und_als_neu_markiert(client, auth_headers) -> None:
    from backend import calls

    cid = _setup(client, auth_headers)
    calls.record(cid, {"number": "•••981", "result": "assistant_end", "codec": "PCMA", "rtp_out": 900, "rtp_in": 800,
                       "turns": 3, "notes": {"name": "Max Mustermann", "concern": "Rückruf wegen Angebot",
                                             "callback_number": "0123 456789", "callback_wanted": True,
                                             "summary": "Möchte ein Angebot."}})
    calls.record(cid, {"number": "•••981", "result": "rejected"})
    items = client.get(f"{BASE}/calls", headers=auth_headers).json()
    assert items["unread"] == 1
    note = items["calls"][1]
    assert note["turns"] == 3 and note["notes"]["name"] == "Max Mustermann" and note["notes_read"] is False
    assert items["calls"][0]["notes"] == {} and items["calls"][0]["notes_read"] is True
    r = client.post(f"{BASE}/calls/{note['id']}/read", headers=auth_headers)
    assert r.status_code == 200 and r.json()["notes_read"] is True
    assert client.get(f"{BASE}/calls", headers=auth_headers).json()["unread"] == 0


def test_leere_notiz_ist_nicht_neu(client, auth_headers) -> None:
    from backend import calls

    cid = _setup(client, auth_headers)
    calls.record(cid, {"number": "•••981", "result": "caller_hangup", "turns": 0, "notes": {}})
    assert client.get(f"{BASE}/calls", headers=auth_headers).json()["unread"] == 0


def test_notiz_nur_bekannte_felder_auch_beim_speichern(client, auth_headers) -> None:
    from hydrahive.db.connection import db

    from backend import calls

    cid = _setup(client, auth_headers)
    calls.record(cid, {"number": "x", "result": "assistant_end", "turns": 1,
                       "notes": {"name": "M", "geheim": "nein", "summary": "s" * 2000}})
    with db() as c:
        raw = c.execute("SELECT notes FROM module_telephony_calls").fetchone()[0]
    n = json.loads(raw)
    assert "geheim" not in n and len(n["summary"]) <= 600


def test_notiz_lesen_nur_eigene(client, auth_headers, other_headers) -> None:
    from backend import calls

    cid = _setup(client, auth_headers)
    calls.record(cid, {"number": "x", "result": "assistant_end", "turns": 1, "notes": {"name": "M"}})
    nid = client.get(f"{BASE}/calls", headers=auth_headers).json()["calls"][0]["id"]
    client.put(BASE, json={"registrar": "fritz.box", "username": "hydra-telefon2", "password": "Sehr-Geheim-42",
                           "local_sip_port": 5071}, headers=other_headers)
    assert client.post(f"{BASE}/calls/{nid}/read", headers=other_headers).status_code == 404


def test_agent_bekommt_assistent_quelle(client, auth_headers) -> None:
    from backend import connections

    _setup(client, auth_headers)
    cfg = connections._config(connections._row("user:user-owner"))
    assert callable(cfg["call_assistant"])
    from backend.conn_manager import fingerprint
    a = fingerprint(cfg)
    _save(client, auth_headers)
    assert fingerprint(connections._config(connections._row("user:user-owner"))) == a, "Modus ändern meldet nicht neu an"
