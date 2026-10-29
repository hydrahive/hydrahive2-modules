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
    monkeypatch.setattr(control, "_port_taken_by_other", lambda port: False)
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


def test_konfiguration_ist_nie_fuer_andere_lesbar_auch_nicht_kurz(fake_system, db_ready, monkeypatch):
    """Die Temp-Datei wird schon mit 0600 angelegt (nicht erst danach umgestellt) – auch bei umask 000."""
    import os as _os
    seen = []
    real_replace = _os.replace

    def spy(a, b):
        seen.append(stat.S_IMODE(_os.stat(a).st_mode))
        return real_replace(a, b)

    monkeypatch.setattr(control.os, "replace", spy)
    monkeypatch.setattr(control.os, "chmod", lambda *a, **k: None)
    old = _os.umask(0)
    try:
        control.write_config()
    finally:
        _os.umask(old)
    assert seen and all(m == 0o600 for m in seen)


def test_konfiguration_wird_bei_jedem_schreiben_wieder_0600(fake_system, db_ready):
    control.write_config()
    liq = fake_system["data"] / "radio.liq"
    liq.chmod(0o644)
    neu = liq.with_suffix(".liq.neu")
    neu.write_text("alt")
    neu.chmod(0o644)
    control.write_config()
    assert stat.S_IMODE(liq.stat().st_mode) == 0o600


def test_liquidsoap_fragt_den_geraete_weg_ohne_anmeldung(fake_system, db_ready):
    """Die Zuspielung hängt unter /api/module-device (ohne HydraHive-Anmeldung). Unter /api/modules bekäme Liquidsoap
    401 (hydratest 29.10.)."""
    from hydrahive.settings import settings
    control.write_config()
    liq = (fake_system["data"] / "radio.liq").read_text()
    assert f'feed_base = "http://127.0.0.1:{settings.port}/api/module-device/radiostream"' in liq
    assert "/api/modules/" not in liq


def test_konfiguration_nimmt_sendernamen_und_hoererzahl(fake_system, db_ready):
    from backend import station
    station.save(user="boss", name="Molke FM", max_listeners=7)
    control.write_config()
    assert 'name="Molke FM"' in (fake_system["data"] / "radio.liq").read_text()
    assert "<max-listeners>7</max-listeners>" in (fake_system["cfg"] / "icecast.xml").read_text()


@pytest.mark.parametrize("fehlt", ["RADIOSTREAM_SOURCE_PASSWORD", "RADIOSTREAM_ADMIN_PASSWORD",
                                   "RADIOSTREAM_FEED_KEY", "alle"])
def test_ohne_passwoerter_kein_start(fake_system, db_ready, fehlt):
    alle = {"RADIOSTREAM_SOURCE_PASSWORD": "q", "RADIOSTREAM_ADMIN_PASSWORD": "a", "RADIOSTREAM_FEED_KEY": "f"}
    rest = {} if fehlt == "alle" else {k: v for k, v in alle.items() if k != fehlt}
    (fake_system["cfg"] / "secrets.env").write_text("".join(f"{k}={v}\n" for k, v in rest.items()))
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
    starts = [c for c in fake_system["calls"] if c.startswith("systemctl enable --now")]
    assert len(starts) == 1
    first = starts[0].split("&&")[0].split()
    assert all(u in first for u in control.UNITS)
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
    stops = [c for c in fake_system["calls"] if c.startswith("systemctl disable --now")]
    assert stops and all(u in stops[-1].split() for u in control.UNITS)
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


def test_hoererzahl_zaehlt_alle_mounts(fake_system, monkeypatch):
    body = {"icestats": {"source": [{"listeners": 2}, {"listeners": 3}]}}
    monkeypatch.setattr(control, "_icecast_status", lambda: body)
    assert control.listeners() == 5


def test_root_befehle_ohne_fremde_eingaben(fake_system, db_ready):
    """Nichts aus der Datenbank (Sendername …) landet in einem root-Befehl."""
    from backend import station
    station.save(user="boss", name="X; rm -rf /")
    control.start()
    control.stop()
    assert all("rm -rf" not in c for c in fake_system["calls"])


# --- Hörer-Seite anwenden (PLAN-E2.md Punkt 5) ---------------------------------------------------------------------

def test_hoerer_seite_schreibt_dateien_und_laedt_nginx(fake_system, db_ready):
    control.apply_listener_site()
    web = fake_system["web"]
    assert {p.name for p in web.iterdir()} >= {"index.html", "radio.css", "radio.js"}
    assert (fake_system["data"] / "nginx.conf").read_text().startswith("# Erzeugt von HydraHive Radiostream")
    script = [c for c in fake_system["calls"] if "nginx -t" in c][-1]
    assert script.index("nginx -t") < script.index("systemctl reload nginx")
    assert "/etc/nginx/sites-enabled/hydrahive-radiostream" in script


def test_hoerer_seite_abgelehnt_alte_bleibt(fake_system, db_ready):
    fake_system["state"]["fail"].add("nginx -t")
    with pytest.raises(control.ControlError) as e:
        control.apply_listener_site()
    assert e.value.code == "radiostream_nginx_failed"
    script = [c for c in fake_system["calls"] if "nginx -t" in c][-1]
    # vor dem Test gesichert, bei Fehler zurückgelegt – nie reload mit kaputter Fassung
    assert "cp -a" in script and ".alt" in script
    assert script.index("nginx -t") < script.index("systemctl reload nginx")


def test_hoerer_seite_aus_entfernt_den_block(fake_system, db_ready):
    from backend import station
    control.apply_listener_site()
    assert (fake_system["data"] / "nginx.conf").exists()
    station.save(user="boss", reach="off")
    control.apply_listener_site()
    script = [c for c in fake_system["calls"] if "hydrahive-radiostream" in c][-1]
    assert "rm -f /etc/nginx/sites-enabled/hydrahive-radiostream /etc/nginx/sites-available/hydrahive-radiostream" \
        in script
    assert not (fake_system["data"] / "nginx.conf").exists()


def test_hoerer_seite_root_befehl_ohne_einstellungen(fake_system, db_ready):
    from backend import station
    station.save(user="boss", name="X'; rm -rf / #", subtitle="$(reboot)")
    control.apply_listener_site()
    for c in fake_system["calls"]:
        assert "rm -rf /" not in c and "reboot" not in c


def test_port_belegt_von_fremdem_dienst(fake_system, db_ready, monkeypatch):
    monkeypatch.setattr(control, "_port_taken_by_other", lambda port: True)
    with pytest.raises(control.ControlError) as e:
        control.apply_listener_site()
    assert e.value.code == "radiostream_port_in_use"
    assert not any("nginx -t" in c for c in fake_system["calls"])


def test_start_wendet_auch_die_hoerer_seite_an(fake_system, db_ready):
    control.start()
    assert any("nginx -t" in c for c in fake_system["calls"])


def test_stop_nimmt_die_hoerer_seite_weg(fake_system, db_ready):
    control.start()
    assert (fake_system["data"] / "nginx.conf").exists()
    n = len(fake_system["calls"])
    control.stop()
    after = fake_system["calls"][n:]
    assert any("rm -f /etc/nginx/sites-enabled/hydrahive-radiostream" in c for c in after)
    assert not (fake_system["data"] / "nginx.conf").exists()


def test_hoerer_seite_fuer_nginx_lesbar(fake_system, db_ready):
    control.apply_listener_site()
    for name in ("index.html", "radio.css", "radio.js"):
        assert stat.S_IMODE((fake_system["web"] / name).stat().st_mode) == 0o644


@pytest.mark.parametrize("ausgabe, belegt", [
    ("", False),
    ('LISTEN 0 511 0.0.0.0:8800 0.0.0.0:* users:(("nginx",pid=5,fd=59))', False),
    ('LISTEN 0 4096 0.0.0.0:8800 0.0.0.0:* users:(("python3",pid=7,fd=3))', True),
    (('LISTEN 0 511 0.0.0.0:8800 0.0.0.0:* users:(("nginx",pid=5,fd=59))\n'
      'LISTEN 0 4096 [::]:8800 [::]:* users:(("gitea",pid=9,fd=3))'), True),
])
def test_port_pruefung_ueber_root_und_nginx_ist_unserer(ausgabe, belegt):
    from backend import listener_apply
    calls = []

    def root(script):
        calls.append(script)
        return 0, ausgabe

    assert listener_apply.port_taken_by_other(8800, root) is belegt
    assert calls == ["ss -Hltnp 'sport = :8800'"]


def test_port_pruefung_fehlgeschlagen_gilt_als_frei():
    from backend import listener_apply
    assert listener_apply.port_taken_by_other(8800, lambda s: (1, 'users:(("x",pid=1))')) is False


# --- Nach Neustart/Update: Konfiguration aus der aktuellen Modulfassung (PLAN-E2.md Punkt 1) ---------------------

def test_nach_neustart_wird_alles_neu_geschrieben_wenn_der_sender_an_ist(fake_system, db_ready):
    (fake_system["data"] / "sender.on").touch()
    (fake_system["web"] / "index.html").write_text("alte Fassung")
    assert control.refresh_after_restart() is True
    assert "alte Fassung" not in (fake_system["web"] / "index.html").read_text()
    assert any(c.startswith("systemctl enable --now") for c in fake_system["calls"])


def test_nach_neustart_nichts_wenn_der_sender_aus_ist(fake_system, db_ready):
    assert control.refresh_after_restart() is False
    assert fake_system["calls"] == []


def test_nach_neustart_fehler_bricht_nichts_ab(fake_system, db_ready):
    (fake_system["data"] / "sender.on").touch()
    fake_system["state"]["fail"].add("enable")
    assert control.refresh_after_restart() is False


def test_nach_neustart_ohne_aenderung_kein_neustart_des_senders(fake_system, db_ready):
    """Gleiche Konfiguration + Sender läuft → nur die Hörer-Seite auffrischen, Hörer fliegen nicht raus."""
    control.start()
    fake_system["calls"].clear()
    assert control.refresh_after_restart() is True
    assert not any("systemctl restart" in c or "enable --now" in c for c in fake_system["calls"])
    assert any("nginx -t" in c for c in fake_system["calls"])


def test_nach_neustart_mit_aenderung_neustart(fake_system, db_ready):
    from backend import station
    control.start()
    station.save(user="boss", name="Neuer Name")
    fake_system["calls"].clear()
    assert control.refresh_after_restart() is True
    assert any("systemctl restart" in c for c in fake_system["calls"])


def test_nach_neustart_sender_steht_wird_gestartet(fake_system, db_ready):
    control.start()
    fake_system["state"]["active"].clear()
    fake_system["calls"].clear()
    assert control.refresh_after_restart() is True
    assert any("enable --now" in c for c in fake_system["calls"])
