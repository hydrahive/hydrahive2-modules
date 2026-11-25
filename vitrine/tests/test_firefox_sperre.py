"""MS12: Website-Sperre nur für den Kiosk-Firefox, nie systemweit (live 25.11.2026: am zweiten Arbeitsplatz „keine
Berechtigung“, weil /etc/firefox/policies/policies.json für alle Benutzer galt).

- Installation schreibt keine systemweite Firefox-Richtlinie mehr; die Sperre steht im user.js des Kiosk-Profils.
- Migration: eine vorhandene policies.json wird nur entfernt, wenn sie exakt eine unserer früheren Fassungen ist
  (Fixtures aus der Git-Historie von kiosk-install.sh); fremde bleibt.
Ob Firefox die Proxy-Sperre wirklich anwendet, prüft kein Test hier (kein Firefox in der Testumgebung) – das ist der
Live-Test; belegt ist das Verhalten aus dem Firefox-Quelltext (siehe Kommentar in kiosk-install.sh).
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest
from _installer_env import _ETC, EXT, Installer

FIX = Path(__file__).resolve().parent / "fixtures" / "firefox-policies"
OURS = sorted(FIX.glob("vitrine-*.json"))
POLICY = "etc/firefox/policies/policies.json"
USERJS = "home/hydrahive-kiosk/firefox/user.js"
FOREIGN = '{"policies": {"DisableAppUpdate": true, "Homepage": {"URL": "https://example.org"}}}\n'


def _prefs(text: str) -> dict[str, object]:
    out: dict[str, object] = {}
    for m in re.finditer(r'^user_pref\("([^"]+)",\s*(.+?)\);$', text, re.M):
        v = m.group(2)
        out[m.group(1)] = v.strip('"') if v.startswith('"') else {"true": True, "false": False}.get(v, v if not v.isdigit() else int(v))
    return out


def test_bekannte_fassungen_aus_der_git_historie():
    """Die Prüfsummen im Skript sind genau die der beiden Fixture-Fassungen (0.7.0 und 0.7.3–0.18.1)."""
    sums = {hashlib.sha256(f.read_bytes()).hexdigest() for f in OURS}
    assert len(OURS) == 2 and len(sums) == 2
    for script in ("kiosk-install.sh", "kiosk-uninstall.sh"):
        line = next(ln for ln in (EXT / script).read_text().splitlines() if ln.startswith("FF_OURS="))
        assert set(line.split('"')[1].split()) == sums, script


def test_installation_schreibt_keine_systemweite_richtlinie(tmp_path):
    inst = Installer(tmp_path)
    assert inst.run().returncode == 0
    assert not inst.etc("firefox/policies/policies.json").exists()
    code = [ln for ln in (EXT / "kiosk-install.sh").read_text().splitlines() if not ln.lstrip().startswith("#")]
    assert not any("policies.json" in ln and ("cat >" in ln or "tee" in ln or "> " in ln) for ln in code)


def test_kiosk_profil_sperre(tmp_path):
    inst = Installer(tmp_path)
    inst.run()
    p = _prefs((inst.root / USERJS).read_text())
    assert p["network.proxy.type"] == 1                                   # fester Proxy (kein PAC: fail-open)
    assert (p["network.proxy.http"], p["network.proxy.http_port"]) == ("127.0.0.1", 65535)
    assert (p["network.proxy.ssl"], p["network.proxy.ssl_port"]) == ("127.0.0.1", 65535)
    assert p["network.proxy.share_proxy_settings"] is True and p["network.proxy.socks"] == ""
    assert p["network.proxy.allow_hijacking_localhost"] is False          # Loopback nie über den Proxy
    assert p["network.proxy.failover_direct"] is False                    # kein direkter Rückfall
    assert p["media.peerconnection.enabled"] is False and p["network.trr.mode"] == 5
    for k in ("devtools.policy.disabled",):                               # aus den früheren Richtlinien übernommen
        assert p[k] is True
    assert p["app.update.enabled"] is False and p["datareporting.policy.dataSubmissionEnabled"] is False


@pytest.mark.parametrize("fixture", OURS, ids=lambda f: f.stem)
def test_migration_entfernt_eigene_fassung(tmp_path, fixture):
    inst = Installer(tmp_path)
    pol = inst.etc("firefox/policies/policies.json")
    pol.parent.mkdir(parents=True, exist_ok=True)
    pol.write_bytes(fixture.read_bytes())
    r = inst.run()
    assert r.returncode == 0 and not pol.exists() and not pol.parent.exists()
    assert "alte systemweite Firefox-Sperre entfernt" in inst.out(r)


@pytest.mark.parametrize("text", [FOREIGN, OURS[-1].read_text() + " ", OURS[-1].read_text().replace("true", "false", 1)],
                         ids=["fremd", "eigene-mit-leerzeichen", "eigene-veraendert"])
def test_migration_laesst_fremde_richtlinie(tmp_path, text):
    inst = Installer(tmp_path)
    pol = inst.etc("firefox/policies/policies.json")
    pol.parent.mkdir(parents=True, exist_ok=True)
    pol.write_text(text)
    assert inst.run().returncode == 0
    assert pol.read_text() == text


@pytest.mark.parametrize("fixture, keep", [(OURS[0], False), (OURS[1], False), (None, True)],
                         ids=["0.7.0", "0.7.3-0.18.1", "fremd"])
def test_uninstall_entfernt_nur_eigene(tmp_path, fixture, keep):
    inst = Installer(tmp_path)
    (inst.root / _ETC.lstrip("/")).mkdir(parents=True)
    pol = inst.etc("firefox/policies/policies.json")
    pol.parent.mkdir(parents=True, exist_ok=True)
    text = fixture.read_text() if fixture else FOREIGN
    pol.write_text(text)
    assert inst.run("kiosk-uninstall.sh").returncode == 0
    assert pol.exists() is keep and (not keep or pol.read_text() == text)
