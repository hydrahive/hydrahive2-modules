"""Rig-Client (mining/rig): GPU-Erkennung, Pin, Konfiguration, Melde-Schleife."""
from __future__ import annotations

import base64
import hashlib
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

RIG_DIR = Path(__file__).resolve().parents[1] / "rig"
if str(RIG_DIR) not in sys.path:
    sys.path.insert(0, str(RIG_DIR))

from hydrahive_rig import agent, client, gpu
from hydrahive_rig.config import RigConfig

# Echte Ausgabe von tills-master-wks (03.10.2026)
NVSMI = "NVIDIA GeForce RTX 5060 Ti, 16311, 595.91.07, 55, 28.01, 0, 0\n"


def test_parse_nvidia_smi_real_output():
    (g,) = gpu.parse_nvidia_smi(NVSMI)
    assert g == {"gpu_vendor": "nvidia", "gpu_model": "NVIDIA GeForce RTX 5060 Ti", "gpu_mem_mb": 16311,
                 "driver": "595.91.07", "temp_c": 55.0, "power_w": 28.01, "fan_pct": 0.0, "util_pct": 0.0}


def test_parse_nvidia_smi_not_supported_fields():
    (g,) = gpu.parse_nvidia_smi("Tesla T4, 15360, 535.1, 40, [N/A], [Not Supported], 3\n")
    assert g["power_w"] is None and g["fan_pct"] is None and g["util_pct"] == 3.0
    assert gpu.parse_nvidia_smi("") == [] and gpu.parse_nvidia_smi("kaputt\n") == []


def test_read_amd_sysfs(tmp_path):
    dev = tmp_path / "card0" / "device"
    hw = dev / "hwmon" / "hwmon3"
    hw.mkdir(parents=True)
    (dev / "vendor").write_text("0x1002\n")
    (dev / "device").write_text("0x73bf\n")
    (dev / "product_name").write_text("Radeon RX 6800 XT\n")
    (dev / "mem_info_vram_total").write_text(str(16 * 1024 ** 3))
    (dev / "gpu_busy_percent").write_text("97\n")
    (hw / "temp1_input").write_text("64000\n")
    (hw / "power1_average").write_text("231000000\n")
    # Anschluss (card0-DP-1): device zeigt im echten sysfs auf die Karte selbst
    # (readlink auf wks197 geprüft) → ohne Filter würde die Karte doppelt gezählt.
    (tmp_path / "card0-DP-1").mkdir()
    (tmp_path / "card0-DP-1" / "device").symlink_to(dev, target_is_directory=True)
    nv = tmp_path / "card1" / "device"
    nv.mkdir(parents=True)
    (nv / "vendor").write_text("0x10de\n")                        # NVIDIA → hier ignoriert
    (g,) = gpu.read_amd(tmp_path)
    assert g["gpu_vendor"] == "amd" and g["gpu_model"] == "Radeon RX 6800 XT"
    assert g["gpu_mem_mb"] == 16384 and g["temp_c"] == 64.0 and g["power_w"] == 231.0 and g["util_pct"] == 97.0


def test_detect_none(monkeypatch):
    monkeypatch.setattr(gpu, "_nvidia", list)
    monkeypatch.setattr(gpu, "read_amd", list)
    assert gpu.detect() == {"gpu_vendor": "none", "gpu_count": 0}


def _cert(key_type="ec"):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec, rsa
    key = ec.generate_private_key(ec.SECP256R1()) if key_type == "ec" else \
        rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, "hydrahive2")])
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(4711).not_valid_before(now).not_valid_after(now + timedelta(days=1))
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .sign(key, hashes.SHA256()))
    spki = key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    return cert.public_bytes(serialization.Encoding.DER), cert.public_bytes(serialization.Encoding.PEM), spki


@pytest.mark.parametrize("key_type", ["ec", "rsa"])
def test_client_pin_equals_server_pin(key_type):
    """Rig (ohne cryptography) und Server (mit) müssen denselben Pin errechnen."""
    from backend import tls_pin
    der, pem, spki = _cert(key_type)
    assert client.extract_spki(der) == spki
    assert client._spki_pin(der) == tls_pin.spki_pin_from_pem(pem)
    assert client._spki_pin(der) == "sha256//" + base64.b64encode(hashlib.sha256(spki).digest()).decode()


def test_server_requires_https():
    with pytest.raises(ValueError):
        client.Server("http://1.2.3.4")


def test_config_roundtrip_and_permissions(tmp_path):
    p = tmp_path / "c" / "config.json"
    RigConfig(server="https://x", token="hhrig_t", name="r", rig_id="id", pin="sha256//p").save(p)
    assert (p.stat().st_mode & 0o777) == 0o600
    assert RigConfig.load(p).token == "hhrig_t"
    p.chmod(0o644)
    with pytest.raises(PermissionError):
        RigConfig.load(p)


def test_backoff():
    assert agent.next_delay(0) == agent.INTERVAL
    assert agent.next_delay(1) == 60 and agent.next_delay(2) == 120
    assert agent.next_delay(10) == agent.MAX_BACKOFF


class _Stop(Exception):
    pass


def test_run_loop_handles_401_and_network_errors(monkeypatch):
    """Echte Schleife: 401 → lange Pause, Netzfehler → Backoff, Erfolg → normaler Takt."""
    seq = [client.ClientError(401, "x"), OSError("down"), {"desired": {"action": "stop", "reason": "r"}}]
    sleeps: list[int] = []

    def fake_report(cfg):
        v = seq.pop(0)
        if isinstance(v, Exception):
            raise v
        return v

    def fake_sleep(s):
        sleeps.append(s)
        if not seq:
            raise _Stop

    monkeypatch.setattr(agent, "report_once", fake_report)
    with pytest.raises(_Stop):
        agent.run_forever(RigConfig(server="https://x", token="t", name="n", rig_id="i"), sleep=fake_sleep)
    assert sleeps == [agent.next_delay(4), agent.next_delay(5), agent.INTERVAL]
