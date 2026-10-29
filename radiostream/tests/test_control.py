"""Sender steuern (PLAN-E2.md „Sendebetrieb“, Punkte 1, 4, 6): Konfiguration schreiben, starten, stoppen, überspringen.

systemctl/nginx laufen nie echt: `fake_system` ersetzt den einzigen Ausführungsweg (control._root) und merkt sich die
Befehle. Pfade zeigen in den Test-Ordner.
"""
from __future__ import annotations

import json
import stat

import pytest

from backend import control, feed_auth


@pytest.fixture
def fake_system(monkeypatch, tmp_path):
    calls: list[str] = []
    state = {"active": set(), "fail": set()}

    def root(script: str) -> tuple[int, str]:
        calls.append(script)
        for word in state["fail"]:
            if word in script:
                return 1, "kaputt"
        if "is-active" in script:
            unit = script.split()[-1]
            return (0, "active") if unit in state["active"] else (3, "inactive")
        if "systemctl enable --now" in script:
            state["active"].update(u for u in control.UNITS)
        if "systemctl disable --now" in script:
            state["active"].clear()
        return 0, ""

    data, cfg, web = tmp_path / "data", tmp_path / "cfg", tmp_path / "web"
    for d in (data, cfg, web):
        d.mkdir()
    (cfg / "secrets.env").write_text("RADIOSTREAM_SOURCE_PASSWORD=quelle\nRADIOSTREAM_ADMIN_PASSWORD=admin\n"
                                     "RADIOSTREAM_FEED_KEY=feed\n")
    monkeypatch.setattr(control, "_root", root)
    monkeypatch.setattr(control, "_units_installed", lambda: True)
    monkeypatch.setattr(control, "DATA_DIR", lambda: data)
    monkeypatch.setattr(control, "CONFIG_DIR", lambda: cfg)
    monkeypatch.setattr(control, "WEB_DIR", web)
    monkeypatch.setattr(feed_auth, "SECRETS_FILE", cfg / "secrets.env")
    return {"calls": calls, "state": state, "data": data, "cfg": cfg, "web": web}


def test_konfiguration_wird_geschrieben_nur_fuer_den_besitzer(fake_system, db_ready):
    control.write_config()
    liq = fake_system["data"] / "radio.liq"
    ice = fake_system["cfg"] / "icecast.xml"
    assert 'password="quelle"' in liq.read_text() and 'feed_key = "feed"' in liq.read_text()
    assert "<source-password>quelle</source-password>" in ice.read_text()
    for f in (liq, ice):
        assert stat.S_IMODE(f.stat().st_mode) == 0o600


def test_konfiguration_nimmt_sendernamen_und_hoererzahl(fake_system, db_ready):
    from backend import station
    station.save(user="boss", name="Molke FM", max_listeners=7)
    control.write_config()
    assert 'name="Molke FM"' in (fake_system["data"] / "radio.liq").read_text()
    assert "<max-listeners>7</max-listeners>" in (fake_system["cfg"] / "icecast.xml").read_text()


def test_ohne_passwoerter_kein_start(fake_system, db_ready):
    (fake_system["cfg"] / "secrets.env").write_text("")
    with pytest.raises(control.ControlError) as e:
        control.start()
    assert e.value.code == "radiostream_service_missing"
    assert not any("enable" in c for c in fake_system["calls"])


def test_ohne_dienste_kein_start(fake_system, db_ready, monkeypatch):
    monkeypatch.setattr(control, "_units_installed", lambda: False)
    with pytest.raises(control.ControlError) as e:
        control.start()
    assert e.value.code == "radiostream_service_missing"


def test_start_schreibt_konfiguration_startet_beide_und_merkt_sich_das(fake_system, db_ready):
    control.start()
    assert (fake_system["data"] / "radio.liq").exists()
    assert any(c.startswith("systemctl enable --now") and all(u in c for u in control.UNITS)
               for c in fake_system["calls"])
    assert (fake_system["data"] / "sender.on").exists()
    assert control.status()["running"] is True


def test_start_fehlgeschlagen_klare_meldung_und_kein_merker(fake_system, db_ready):
    fake_system["state"]["fail"].add("enable")
    with pytest.raises(control.ControlError) as e:
        control.start()
    assert e.value.code == "radiostream_service_failed"
    assert not (fake_system["data"] / "sender.on").exists()


def test_stop_haelt_beide_an_und_vergisst_den_merker(fake_system, db_ready):
    control.start()
    control.stop()
    assert any(c.startswith("systemctl disable --now") and all(u in c for u in control.UNITS)
               for c in fake_system["calls"])
    assert not (fake_system["data"] / "sender.on").exists()
    assert control.status()["running"] is False


def test_status_laeuft_nur_wenn_beide_laufen(fake_system, db_ready):
    fake_system["state"]["active"] = {control.UNITS[0]}
    assert control.status()["running"] is False
    fake_system["state"]["active"] = set(control.UNITS)
    assert control.status()["running"] is True


def test_jetzt_laeuft_aus_der_datei_nur_kuenstler_und_titel(fake_system, db_ready):
    (fake_system["web"] / "jetzt.json").write_text(json.dumps({"artist": "A", "title": "T", "x": "geheim"}))
    assert control.now_playing() == {"artist": "A", "title": "T"}


@pytest.mark.parametrize("inhalt", ["", "{kaputt", "[]", '{"artist": 5}'])
def test_jetzt_laeuft_kaputte_datei_ergibt_leer(fake_system, db_ready, inhalt):
    (fake_system["web"] / "jetzt.json").write_text(inhalt)
    assert control.now_playing() == {"artist": "", "title": ""}


def test_ueberspringen_schickt_genau_den_befehl(fake_system, db_ready, monkeypatch):
    sent = []
    monkeypatch.setattr(control, "_send", lambda cmd: sent.append(cmd) or "Done")
    fake_system["state"]["active"] = set(control.UNITS)
    control.skip()
    assert sent == ["sender.skip"]


def test_ueberspringen_wenn_aus_klare_meldung(fake_system, db_ready, monkeypatch):
    monkeypatch.setattr(control, "_send", lambda cmd: pytest.fail("nicht senden, wenn aus"))
    with pytest.raises(control.ControlError) as e:
        control.skip()
    assert e.value.code == "radiostream_not_running"


def test_hoererzahl_aus_icecast_ohne_adressen(fake_system, monkeypatch):
    body = {"icestats": {"source": {"listeners": 4, "listenurl": "http://localhost:8810/radio.mp3",
                                    "title": "x"}, "host": "localhost"}}
    monkeypatch.setattr(control, "_icecast_status", lambda: body)
    assert control.listeners() == 4


@pytest.mark.parametrize("body", [None, {}, {"icestats": {}}, {"icestats": {"source": [{"listeners": 2},
                                                                                       {"listeners": 3}]}}])
def test_hoererzahl_robust(fake_system, monkeypatch, body):
    monkeypatch.setattr(control, "_icecast_status", lambda: body)
    assert control.listeners() in (0, 5)


def test_root_befehle_ohne_fremde_eingaben(fake_system, db_ready):
    """Nichts aus der Datenbank (Sendername …) landet in einem root-Befehl."""
    from backend import station
    station.save(user="boss", name="X; rm -rf /")
    control.start()
    control.stop()
    assert all("rm -rf" not in c for c in fake_system["calls"])
