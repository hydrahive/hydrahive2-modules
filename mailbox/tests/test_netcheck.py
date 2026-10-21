"""M1 Schritt 3: Anbieter-Vorschläge und Prüfung der Server-Adresse (kein Zugriff aufs interne Netz, feste Ports)."""
from __future__ import annotations

import pytest


def test_gmail_vorschlag_mit_app_passwort_hinweis():
    from backend import providers
    p = providers.suggest("Till.Mustermann@GMAIL.com")
    assert p["imap_host"] == "imap.gmail.com" and p["imap_port"] == 993 and p["imap_tls"] == "ssl"
    assert p["smtp_host"] == "smtp.gmail.com" and p["smtp_port"] == 465
    assert "App-Passwort" in p["hint"]


@pytest.mark.parametrize("addr, host", [("a@gmx.de", "imap.gmx.net"), ("a@web.de", "imap.web.de"),
                                        ("a@posteo.de", "posteo.de"), ("a@googlemail.com", "imap.gmail.com")])
def test_bekannte_anbieter(addr, host):
    from backend import providers
    assert providers.suggest(addr)["imap_host"] == host


def test_unbekannt_raet_imap_domain():
    from backend import providers
    p = providers.suggest("info@beispiel-firma.de")
    assert p["imap_host"] == "imap.beispiel-firma.de" and p["known"] is False


@pytest.mark.parametrize("bad", ["", "kein-at", "a@", "@b.de", "a b@c.de", "a@b", "a@-b.de", "a@b..de", "x" * 250 + "@b.de"])
def test_kaputte_adresse(bad):
    from backend import providers
    with pytest.raises(ValueError):
        providers.suggest(bad)


def _res(mapping):
    return lambda host: mapping.get(host, ["93.184.216.34"])


@pytest.mark.parametrize("host, ips", [
    ("localhost", ["127.0.0.1"]), ("127.0.0.1", ["127.0.0.1"]), ("192.168.178.3", ["192.168.178.3"]),
    ("10.0.0.5", ["10.0.0.5"]), ("::1", ["::1"]), ("169.254.169.254", ["169.254.169.254"]),
    ("intern.example", ["192.168.1.10"]), ("gemischt.example", ["93.184.216.34", "10.1.2.3"]),
    ("mapped.example", ["::ffff:127.0.0.1"]), ("0.0.0.0", ["0.0.0.0"]),
])
def test_interne_ziele_blockiert(host, ips):
    from backend import netcheck
    with pytest.raises(netcheck.HostBlocked):
        netcheck.check(host, 993, resolve=_res({host: ips}))


def test_oeffentlich_ok_und_liefert_feste_ip():
    """Die geprüfte IP wird zurückgegeben: verbunden wird genau mit ihr (kein DNS-Rebinding zwischen Prüfen und Verbinden)."""
    from backend import netcheck
    assert netcheck.check("imap.gmail.com", 993, resolve=_res({"imap.gmail.com": ["142.250.1.108"]})) == "142.250.1.108"


@pytest.mark.parametrize("port", [22, 80, 443, 8080, 0, 70000])
def test_nur_mailports(port):
    from backend import netcheck
    with pytest.raises(netcheck.HostBlocked):
        netcheck.check("imap.gmail.com", port, resolve=_res({}))


@pytest.mark.parametrize("port", [993, 143, 465, 587, 25])
def test_mailports_erlaubt(port):
    from backend import netcheck
    assert netcheck.check("mail.example.org", port, resolve=_res({}))


def test_dns_fehler_blockiert():
    from backend import netcheck

    def boom(host):
        raise OSError("NXDOMAIN")
    with pytest.raises(netcheck.HostBlocked):
        netcheck.check("gibts-nicht.example", 993, resolve=boom)


def test_admin_freigabe_fuer_lan_server():
    """Eigener Mailserver im Heimnetz: nur wenn der Admin den Host ausdrücklich freigibt."""
    from backend import netcheck
    r = _res({"mail.lan": ["192.168.178.50"]})
    with pytest.raises(netcheck.HostBlocked):
        netcheck.check("mail.lan", 993, resolve=r)
    assert netcheck.check("mail.lan", 993, resolve=r, allow_internal={"mail.lan"}) == "192.168.178.50"
    with pytest.raises(netcheck.HostBlocked):
        netcheck.check("anderer.lan", 993, resolve=_res({"anderer.lan": ["192.168.178.51"]}), allow_internal={"mail.lan"})


@pytest.mark.parametrize("host", ["localhost", "LOCALHOST.", "metadata.google.internal"])
def test_gesperrte_namen_ohne_dns(host):
    """Diese Namen sind gesperrt, egal was ein (manipuliertes) DNS liefert."""
    from backend import netcheck
    with pytest.raises(netcheck.HostBlocked):
        netcheck.check(host, 993, resolve=lambda h: ["93.184.216.34"])
