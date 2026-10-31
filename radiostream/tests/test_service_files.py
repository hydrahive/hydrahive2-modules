"""Konfiguration für Icecast und Liquidsoap (PLAN-E2.md „Sendebetrieb“).

Geprüft wird nur der erzeugte Text. Ob Liquidsoap ihn annimmt, prüft die Probe auf hydratest (`liquidsoap --check`).
"""
from __future__ import annotations

import re
from xml.etree import ElementTree as ET

from backend import service_files as sf

_ICE = {"source_password": "q<u&e>lle", "admin_password": "ad\"min", "max_listeners": 20, "name": "Molke <FM> & Co",
        "log_dir": "/var/log/hydrahive2/radiostream"}
_LIQ = {"feed_base": "http://127.0.0.1:8001/api/modules/radiostream", "feed_key": "FEEDKEY-123",
        "source_password": "QUELLE-456", "name": "Molke FM", "subtitle": "rund um die Uhr",
        "fallback_file": "/x/stille.mp3", "control_socket": "/run/x/radio.sock", "now_file": "/var/x/jetzt.json"}


def test_icecast_ist_gueltiges_xml_und_nur_lokal():
    root = ET.fromstring(sf.icecast_xml(**_ICE))
    sock = root.find("listen-socket")
    assert sock.findtext("bind-address") == "127.0.0.1"
    assert sock.findtext("port") == str(sf.ICECAST_PORT)
    assert len(root.findall("listen-socket")) == 1


def test_icecast_passwoerter_und_name_sauber_maskiert():
    root = ET.fromstring(sf.icecast_xml(**_ICE))
    auth = root.find("authentication")
    assert auth.findtext("source-password") == "q<u&e>lle"
    assert auth.findtext("admin-password") == 'ad"min'
    assert root.find("mount").findtext("stream-name") == "Molke <FM> & Co"


def test_icecast_hoererzahl_am_mount_und_genug_plaetze_insgesamt():
    root = ET.fromstring(sf.icecast_xml(**_ICE))
    mount = root.find("mount")
    assert mount.findtext("mount-name") == sf.MOUNT
    assert mount.findtext("max-listeners") == "20"
    assert int(root.find("limits").findtext("clients")) > 20
    assert mount.findtext("public") == "0"
    assert root.find("security").findtext("chroot") == "0"


def _strings(script: str) -> list[str]:
    """Alle Liquidsoap-Zeichenketten (mit \\" und \\\\ maskiert)."""
    return re.findall(r'"((?:[^"\\]|\\.)*)"', script)


def test_liquidsoap_sendet_nur_an_lokales_icecast_mit_passwort():
    s = sf.liquidsoap_script(**_LIQ)
    out = s[s.index("output.icecast("):]
    assert 'host="127.0.0.1"' in out and f"port={sf.ICECAST_PORT}" in out
    assert 'password="QUELLE-456"' in out and f'mount="{sf.MOUNT}"' in out
    assert "%mp3(bitrate=192)" in out and "public=false" in out


def test_liquidsoap_steuerung_nur_ueber_eigene_datei():
    """Kein Netz-Port für die Steuerung: nur eine Unix-Steuerdatei, die nur der Besitzer öffnen darf (0600 = 384)."""
    s = sf.liquidsoap_script(**_LIQ)
    assert "settings.server.socket.set(true)" in s
    assert 'settings.server.socket.path.set("/run/x/radio.sock")' in s
    assert "settings.server.socket.permissions.set(384)" in s
    assert "telnet" not in s


def test_jetzt_laeuft_nur_kuenstler_und_titel_an_den_metadaten():
    s = sf.liquidsoap_script(**_LIQ)
    assert 'jetzt = {artist=m["artist"], title=m["title"]}' in s
    assert "json.stringify({artist=jetzt.artist, title=jetzt.title, recent=zuletzt()})" in s
    assert "zuletzt := list.prefix(10, list.add(jetzt, zuletzt()))" in s
    assert "file.write(perms=420," in s
    assert '"/var/x/jetzt.json"' in s
    assert "source.on_metadata(radio, write_now)" in s
    assert 'if m["title"] != "" or m["artist"] != "" then' in s


def test_liquidsoap_schickt_feed_schluessel_bei_beiden_abrufen():
    s = sf.liquidsoap_script(**_LIQ)
    assert 'feed_key = "FEEDKEY-123"' in s
    assert s.count('("X-Radiostream-Feed", feed_key)') == 2
    assert '"#{feed_base}/feed/next"' in s and '"#{feed_base}/feed/file/' in s
    assert 'protocol.add("radiostream", fetch_track, temporary=true' in s


def test_liquidsoap_programm_mit_ueberblendung_lautheit_und_notschleife():
    s = sf.liquidsoap_script(**_LIQ)
    assert "request.dynamic(" in s and "crossfade(" in s
    # Lautheit je Titel fest (Wert aus /feed/next), nicht laufend nachgeregelt – normalize() zog das Ausklingen am
    # Titelende hoch (Befund Till 31.10., gemessen: −45 dB → −29 dB).
    assert "normalize(" not in s
    assert 'amplify(1.0, override="liq_amplify", auto)' in s
    assert s.index("amplify(") < s.index("crossfade(")              # erst je Titel angleichen, dann überblenden
    assert 'single(id="notschleife", "/x/stille.mp3")' in s
    assert "fallback(" in s and "mksafe(radio)" in s


def test_name_mit_anfuehrungszeichen_bricht_das_skript_nicht():
    boese = {**_LIQ, "name": 'X" ; output.dummy(blank()) ; "', "subtitle": "a\\\nb", "feed_key": 'k"ey'}
    s = sf.liquidsoap_script(**boese)
    assert "output.dummy" not in s.replace('X\\" ; output.dummy(blank()) ; \\"', "")
    assert 'name="X\\" ; output.dummy(blank()) ; \\""' in s
    assert 'description="a\\\\ b"' in s
    assert 'feed_key = "k\\"ey"' in s
    for line in s.splitlines():
        assert line.count('"') - line.count('\\"') in (0, 2, 4, 6, 8, 10, 12), line


def test_ohne_pausenzeichen_stille_statt_absturz():
    s = sf.liquidsoap_script(**{**_LIQ, "fallback_file": ""})
    assert 'notschleife = blank(id="notschleife")' in s and "single(" not in s


# --- Liquidsoap 2.2 (Ubuntu 24.04) UND 2.4 (26.04, Hauptserver) – Befund 30.10.2026 -----------------------------
# 2.4 lehnt das 2.2-Skript ab: protocol.add erwartet string? statt [string], null() ist veraltet, on_metadata ist eine
# Methode der Quelle. Das Skript wählt den passenden Teil mit %ifversion zur Ladezeit von Liquidsoap.

def _blocks(s: str) -> tuple[str, str]:
    """(Teil für >= 2.3, Teil für ältere) aller %ifversion-Blöcke zusammen."""
    new, old = [], []
    for part in s.split("%ifversion >= 2.3.0\n")[1:]:
        a, rest = part.split("%else\n", 1)
        b = rest.split("%endif", 1)[0]
        new.append(a)
        old.append(b)
    return "".join(new), "".join(old)


def test_skript_hat_teile_fuer_alt_und_neu():
    s = sf.liquidsoap_script(**_LIQ)
    assert s.count("%ifversion >= 2.3.0\n") == 3 and s.count("%endif") == 3
    new, old = _blocks(s)
    assert "if ok then tmp else null end" in new and "if ok then [tmp] else [] end" in old
    assert "def no_request() = null end" in new and "def no_request() = null() end" in old
    assert "radio.on_metadata(synchronous=false, write_now)" in new
    assert "radio = source.on_metadata(radio, write_now)" in old


def test_ausserhalb_der_bloecke_keine_versionsabhaengigen_aufrufe():
    s = sf.liquidsoap_script(**_LIQ)
    outside = s
    for part in s.split("%ifversion >= 2.3.0\n")[1:]:
        outside = outside.replace(part.split("%endif", 1)[0], "")
    assert "null()" not in outside and "source.on_metadata" not in outside and "[tmp]" not in outside
    assert outside.count("no_request()") == 2


def test_temp_datei_bei_fehler_geloescht_in_beiden_fassungen():
    s = sf.liquidsoap_script(**_LIQ)
    assert "if not ok() then file.remove(tmp) end" in s
    assert "(ok(), tmp)" in s


# --- Programm: vorgeladenen Titel verwerfen (PLAN-PROGRAMM.md „Als Nächstes“) ------------------------------------------

def test_nur_ein_titel_vorgeladen():
    s = sf.liquidsoap_script(**_LIQ)
    assert "prefetch=1," in s and "prefetch=3" not in s


def test_steuerkommando_verwirft_vorgeladenen_titel_und_nennt_ihn():
    s = sf.liquidsoap_script(**_LIQ)
    assert 'server.register(namespace="autodj"' in s and '"flush", flush)' in s
    flush = s[s.index("def flush("):s.index('server.register(namespace="autodj"')]
    assert "auto.set_queue([])" in flush and "q = auto.queue()" in flush
    assert flush.index("q = auto.queue()") < flush.index("auto.set_queue([])")
    assert 'm["rs_play"]' in flush and 'string.concat(separator=",", ' in flush


def test_flush_vor_lautheit_und_ueberblendung():
    """auto muss noch die Liquidsoap-Warteschlange sein (request.dynamic), nicht schon amplify/crossfade."""
    s = sf.liquidsoap_script(**_LIQ)
    assert s.index("server.register(namespace=\"autodj\"") < s.index("auto = amplify(")
