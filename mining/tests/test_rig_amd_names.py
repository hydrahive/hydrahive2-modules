"""AMD: Modellname und Lüfter (Kugelfang, 04.10.2026: „AMD 0x67df“ statt RX 470, Lüfter immer leer).

amdgpu hat kein product_name für Consumer-Karten. Den Namen liefert libdrm in
amdgpu.ids (Gerät + Revision), die Datei liegt bei Ubuntu/Debian mit Mesa bei.
Lüfter: hwmon pwm1 (0…pwm1_max) → Prozent.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

RIG_DIR = Path(__file__).resolve().parents[1] / "rig"
if str(RIG_DIR) not in sys.path:
    sys.path.insert(0, str(RIG_DIR))

from hydrahive_rig import amdinfo, catalog, gpu

IDS = """# List of AMDGPU IDs
#
# Syntax:
# device_id,\trevision_id,\tproduct_name        <-- single tab after comma

1.0.0
66AF,\tC1,\tAMD Radeon VII
67DF,\tC4,\tAMD Radeon RX 480 Graphics
67DF,\tC5,\tAMD Radeon RX 470 Graphics
67DF,\tE7,\tAMD Radeon RX 580 Series
699F,\tC7,\tAMD Radeon RX 550 / 550 Series
"""


def _card(root: Path, name: str, device: str, revision: str | None, *, product: str | None = None,
          pwm: str | None = None, pwm_max: str | None = None) -> None:
    dev = root / name / "device"
    (dev / "hwmon" / "hwmon0").mkdir(parents=True)
    (dev / "vendor").write_text("0x1002\n")
    (dev / "device").write_text(device + "\n")
    if revision is not None:
        (dev / "revision").write_text(revision + "\n")
    if product is not None:
        (dev / "product_name").write_text(product + "\n")
    if pwm is not None:
        (dev / "hwmon" / "hwmon0" / "pwm1").write_text(pwm + "\n")
    if pwm_max is not None:
        (dev / "hwmon" / "hwmon0" / "pwm1_max").write_text(pwm_max + "\n")


@pytest.fixture
def ids(tmp_path, monkeypatch):
    p = tmp_path / "amdgpu.ids"
    p.write_text(IDS)
    monkeypatch.setattr(amdinfo, "AMDGPU_IDS", [tmp_path / "fehlt.ids", p])
    amdinfo.ids_table.cache_clear()
    yield p
    amdinfo.ids_table.cache_clear()


def test_kugelfangs_cards_get_real_names(tmp_path, ids):
    drm = tmp_path / "drm"
    _card(drm, "card1", "0x67df", "0xc5")
    _card(drm, "card2", "0x66af", "0xc1")
    _card(drm, "card3", "0x67df", "0xc5")
    assert [g["gpu_model"] for g in gpu.read_amd(drm)] == [
        "AMD Radeon RX 470 Graphics", "AMD Radeon VII", "AMD Radeon RX 470 Graphics"]


def test_rx550(tmp_path, ids):
    _card(tmp_path / "drm", "card0", "0x699f", "0xc7")
    assert gpu.read_amd(tmp_path / "drm")[0]["gpu_model"] == "AMD Radeon RX 550 / 550 Series"


def test_same_device_other_revision_is_other_card(tmp_path, ids):
    _card(tmp_path / "drm", "card0", "0x67df", "0xe7")
    assert gpu.read_amd(tmp_path / "drm")[0]["gpu_model"] == "AMD Radeon RX 580 Series"


def test_unknown_revision_falls_back_to_device_family(tmp_path, ids):
    """Revision fehlt in der Liste → erster Name des Geräts, mit Hinweis (nicht falsch-genau)."""
    _card(tmp_path / "drm", "card0", "0x67df", "0x99")
    assert gpu.read_amd(tmp_path / "drm")[0]["gpu_model"] == "AMD Radeon RX 480 Graphics (?)"


def test_unknown_device_keeps_hex(tmp_path, ids):
    _card(tmp_path / "drm", "card0", "0x7480", "0xc0")
    assert gpu.read_amd(tmp_path / "drm")[0]["gpu_model"] == "AMD 0x7480"


def test_product_name_wins_if_present(tmp_path, ids):
    _card(tmp_path / "drm", "card0", "0x66af", "0xc1", product="Radeon Pro VII")
    assert gpu.read_amd(tmp_path / "drm")[0]["gpu_model"] == "Radeon Pro VII"


def test_no_ids_file_keeps_hex(tmp_path, monkeypatch):
    monkeypatch.setattr(amdinfo, "AMDGPU_IDS", [tmp_path / "fehlt.ids"])
    amdinfo.ids_table.cache_clear()
    _card(tmp_path / "drm", "card0", "0x67df", "0xc5")
    assert gpu.read_amd(tmp_path / "drm")[0]["gpu_model"] == "AMD 0x67df"
    amdinfo.ids_table.cache_clear()


def test_broken_ids_lines_are_skipped(tmp_path, monkeypatch):
    p = tmp_path / "amdgpu.ids"
    p.write_bytes(b"kaputt\n67DF,\tC5\n\xff\xfe,\t,\t\n#67DF,\tC5,\tKommentar\n67DF,\t,\tLeer\n67DF,\tC5,\t\n"
                  b"67DF,\tC5,\tAMD Radeon RX 470 Graphics\n")
    monkeypatch.setattr(amdinfo, "AMDGPU_IDS", [p])
    amdinfo.ids_table.cache_clear()
    _card(tmp_path / "drm", "card0", "0x67df", "0xc5")
    assert gpu.read_amd(tmp_path / "drm")[0]["gpu_model"] == "AMD Radeon RX 470 Graphics"
    amdinfo.ids_table.cache_clear()


@pytest.mark.parametrize("pwm, pwm_max, expected", [
    ("128", "255", 50.2), ("255", "255", 100.0), ("0", "255", 0.0), ("77", None, 30.2),
    (None, None, None), ("kaputt", "255", None), ("300", "255", 100.0), ("50", "0", None),
])
def test_fan_percent_from_pwm(tmp_path, ids, pwm, pwm_max, expected):
    _card(tmp_path / "drm", "card0", "0x67df", "0xc5", pwm=pwm, pwm_max=pwm_max)
    assert gpu.read_amd(tmp_path / "drm")[0]["fan_pct"] == expected


def test_summary_shows_fan(tmp_path, ids):
    _card(tmp_path / "drm", "card0", "0x67df", "0xc5", pwm="100")
    _card(tmp_path / "drm", "card1", "0x66af", "0xc1", pwm="200")
    s = gpu.summarize(gpu.read_amd(tmp_path / "drm"))
    assert s["fan_pct"] is not None


# ---- OpenCL ohne ROCm: Mesa (rusticl) gibt AMD-Karten nur mit RUSTICL_ENABLE frei ----
JOB = {"coin": "erg", "miner": "lolminer", "algo": "AUTOLYKOS2", "user": "krxXJK8JJW", "worker": "rig-01",
       "region": "eu"}


@pytest.mark.parametrize("miner, algo", [("lolminer", "AUTOLYKOS2"), ("srbminer", "autolykos2")])
def test_amd_miner_enables_rusticl_gpus(miner, algo):
    for mixed in (False, True):
        spec = catalog.build({**JOB, "miner": miner, "algo": algo}, "amd", mixed=mixed, group="amd")
        assert spec["env"]["RUSTICL_ENABLE"] == "radeonsi"


def test_nvidia_miner_gets_no_rusticl():
    for mixed in (False, True):
        spec = catalog.build({**JOB, "miner": "rigel", "algo": "autolykos2"}, "nvidia", mixed=mixed, group="nvidia")
        assert "RUSTICL_ENABLE" not in spec["env"]
