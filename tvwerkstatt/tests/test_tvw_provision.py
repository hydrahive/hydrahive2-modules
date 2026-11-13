"""Baustein 3: Einrichtung im Container (Werkzeuge mit Prüfsumme, Lizenz nur nach Bestätigung, Schlüssel)."""
from __future__ import annotations

import asyncio

import pytest
from backend import provision


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def box(fake_incus, monkeypatch, tmp_path):
    monkeypatch.setattr(provision, "_PAUSES", (0.0, 0.0))
    monkeypatch.setattr(provision, "keystore_path", lambda: tmp_path / "signing" / "debug.keystore")
    fake_incus.containers["hh-tvwerkstatt"] = {"running": True, "network": "hhtvw0"}
    return fake_incus


def _setup(**kw) -> list[str]:
    seen: list[str] = []
    run(provision.setup(seen.append, **kw))
    return seen


def test_ohne_lizenz_laeuft_nichts(box):
    with pytest.raises(provision.SetupError) as e:
        _setup(license_accepted=False)
    assert e.value.code == "tvw_license_required"
    assert box.exec_log == []


def test_alle_schritte_in_reihenfolge(box):
    assert _setup(license_accepted=True) == ["user", "packages", "tools", "sdk", "keystore"]


def test_werkzeuge_nur_mit_passender_pruefsumme_und_groesse():
    tools = next(s for s in provision.STEPS if s.key == "tools").script
    assert provision.CLT_SHA1 in tools and str(provision.CLT_SIZE) in tools
    assert tools.index("sha1sum -c") < tools.index("unzip")              # erst prüfen, dann entpacken
    assert tools.index("stat -c %s") < tools.index("unzip")
    assert "https://dl.google.com/android/repository/" + provision.CLT_FILE in tools


def test_lizenz_nur_im_sdk_schritt():
    for s in provision.STEPS:
        assert ("--licenses" in s.script) == (s.key == provision.LICENSE_STEP), s.key


def test_kein_sudo_fuer_den_bau_nutzer():
    user = next(s for s in provision.STEPS if s.key == "user").script
    assert "gpasswd -d ubuntu sudo" in user and "90-cloud-init-users" in user


def test_pruefsumme_falsch_bricht_sofort_ab(box):
    box.exec_answers["sha1sum -c"] = (provision.RC_CHECKSUM, "Prüfsumme passt nicht")
    with pytest.raises(provision.SetupError) as e:
        _setup(license_accepted=True)
    assert (e.value.code, e.value.step) == ("tvw_checksum_mismatch", "tools")
    assert sum("sha1sum -c" in b for b in box.exec_log) == 1              # kein zweiter Versuch
    assert not any("--licenses" in b for b in box.exec_log)


def test_netzschritt_wird_wiederholt(box):
    box.exec_answers["apt-get update"] = (1, "Temporary failure resolving")
    with pytest.raises(provision.SetupError) as e:
        _setup(license_accepted=True)
    assert (e.value.code, e.value.step) == ("tvw_setup_failed", "packages")
    assert sum("apt-get update" in b for b in box.exec_log) == provision.NET_ATTEMPTS
    assert "Temporary failure resolving" in e.value.detail


def test_lokaler_schritt_nur_einmal(box):
    box.exec_answers["id ubuntu"] = (1, "kein Nutzer")
    with pytest.raises(provision.SetupError):
        _setup(license_accepted=True)
    assert sum("id ubuntu" in b for b in box.exec_log) == 1


def test_weiter_ab_schritt(box):
    assert _setup(license_accepted=True, start_at="sdk") == ["sdk", "keystore"]


def test_unbekannter_startschritt(box):
    with pytest.raises(provision.SetupError):
        _setup(license_accepted=True, start_at="rm -rf")


def test_detail_ohne_steuerzeichen_und_ohne_containernamen():
    d = provision._detail("\x1b[31mrot\x1b[0m hh-tvwerkstatt sagt\n" + "x" * 2000, "")
    assert "\x1b" not in d and "hh-tvwerkstatt" not in d and len(d) <= provision.MAX_DETAIL


def test_gesicherter_schluessel_wird_hineingelegt(box, tmp_path):
    key = tmp_path / "signing" / "debug.keystore"
    key.parent.mkdir(parents=True)
    key.write_bytes(b"erfundener-schluessel")
    _setup(license_accepted=True)
    push = box.pushed[-1]
    assert push[push.index("--mode") + 1] == "0600" and push[-1] == "hh-tvwerkstatt/home/ubuntu/.android/debug.keystore"


def test_ohne_gesicherten_schluessel_kein_push(box):
    _setup(license_accepted=True)
    assert box.pushed == []
