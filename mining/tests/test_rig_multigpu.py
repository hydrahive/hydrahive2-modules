"""Mehrere Grafikkarten pro Rechner (Kugelfang, 03.10.2026: mehrere AMD-Karten, nur eine sichtbar,
ohne Temperatur und Watt). Client meldet alle Karten; Summen/Maxima für Anzeige und Energie."""
from __future__ import annotations

import errno
import sys
from pathlib import Path

import pytest

RIG_DIR = Path(__file__).resolve().parents[1] / "rig"
if str(RIG_DIR) not in sys.path:
    sys.path.insert(0, str(RIG_DIR))

from hydrahive_rig import gpu, minerapi


def _amd(root: Path, card: str, *, temp="64000", power=("power1_average", "231000000"), busy="97",
         name="Radeon RX 6800 XT", pci="0000:03:00.0", runtime="active", hwmon=True) -> Path:
    dev = root / card / "device"
    dev.mkdir(parents=True)
    (dev / "vendor").write_text("0x1002\n")
    (dev / "device").write_text("0x73bf\n")
    (dev / "product_name").write_text(name + "\n")
    (dev / "mem_info_vram_total").write_text(str(16 * 1024 ** 3))
    (dev / "uevent").write_text(f"DRIVER=amdgpu\nPCI_SLOT_NAME={pci}\n")
    (dev / "power").mkdir()
    (dev / "power" / "runtime_status").write_text(runtime + "\n")
    if busy is not None:
        (dev / "gpu_busy_percent").write_text(busy + "\n")
    if hwmon:
        hw = dev / "hwmon" / "hwmon3"
        hw.mkdir(parents=True)
        if temp is not None:
            (hw / "temp1_input").write_text(temp + "\n")
        if power is not None:
            (hw / power[0]).write_text(power[1] + "\n")
    return dev


def test_read_amd_reports_every_card(tmp_path):
    _amd(tmp_path, "card0", pci="0000:03:00.0")
    _amd(tmp_path, "card1", pci="0000:06:00.0", temp="58000", power=("power1_average", "180000000"))
    _amd(tmp_path, "card2", pci="0000:09:00.0", temp="71000", power=("power1_average", "205500000"))
    gpus = gpu.read_amd(tmp_path)
    assert [g["pci"] for g in gpus] == ["0000:03:00.0", "0000:06:00.0", "0000:09:00.0"]
    assert [g["temp_c"] for g in gpus] == [64.0, 58.0, 71.0]
    assert [g["power_w"] for g in gpus] == [231.0, 180.0, 205.5]


def test_card_order_is_numeric_not_alphabetic(tmp_path):
    for i in (0, 1, 2, 10):
        _amd(tmp_path, f"card{i}", pci=f"0000:{i:02x}:00.0")
    assert [g["pci"] for g in gpus_of(tmp_path)] == ["0000:00:00.0", "0000:01:00.0", "0000:02:00.0", "0000:0a:00.0"]


def gpus_of(root):
    return gpu.read_amd(root)


def test_rdna3_has_only_power1_input(tmp_path):
    """RDNA3 (RX 7000) bietet kein power1_average, nur power1_input (amdgpu_pm.c, „not all products
    support both average and instantaneous“)."""
    _amd(tmp_path, "card0", power=("power1_input", "150000000"))
    (g,) = gpu.read_amd(tmp_path)
    assert g["power_w"] == 150.0


def test_unreadable_average_falls_back_to_input(tmp_path):
    dev = _amd(tmp_path, "card0", power=("power1_input", "142000000"))
    (dev / "hwmon" / "hwmon3" / "power1_average").mkdir()   # existiert, Lesen schlägt fehl
    (g,) = gpu.read_amd(tmp_path)
    assert g["power_w"] == 142.0


def test_temp_falls_back_to_other_sensor(tmp_path):
    dev = _amd(tmp_path, "card0", temp=None)
    (dev / "hwmon" / "hwmon3" / "temp2_input").write_text("77000\n")     # nur Hotspot vorhanden
    (g,) = gpu.read_amd(tmp_path)
    assert g["temp_c"] == 77.0


def test_sleeping_card_is_marked_not_silently_empty(tmp_path, monkeypatch):
    """Ab Linux 6.15 liefert amdgpu Temp/Watt/Last im Laufzeit-Ruhezustand nur -EPERM
    (amdgpu_pm_get_access_if_active). Dann ehrlich „schläft“ melden statt nur leere Felder."""
    _amd(tmp_path, "card0", runtime="suspended")
    real = Path.read_text

    def eperm(self, *a, **kw):
        if self.name in ("temp1_input", "power1_average", "gpu_busy_percent"):
            raise PermissionError(errno.EPERM, "Operation not permitted")
        return real(self, *a, **kw)

    monkeypatch.setattr(Path, "read_text", eperm)
    (g,) = gpu.read_amd(tmp_path)
    assert g["temp_c"] is None and g["power_w"] is None
    assert g["sensors"] == "asleep"


def test_eperm_alone_means_asleep(tmp_path, monkeypatch):
    """EPERM ist der eigentliche Beweis — runtime_status fehlt bei manchen Kerneln/Containern."""
    dev = _amd(tmp_path, "card0")
    (dev / "power" / "runtime_status").unlink()
    real = Path.read_text

    def eperm(self, *a, **kw):
        if self.name in ("temp1_input", "power1_average"):
            raise PermissionError(errno.EPERM, "Operation not permitted")
        return real(self, *a, **kw)

    monkeypatch.setattr(Path, "read_text", eperm)
    (g,) = gpu.read_amd(tmp_path)
    assert g["sensors"] == "asleep"


def test_missing_hwmon_is_reported(tmp_path):
    _amd(tmp_path, "card0", hwmon=False)
    (g,) = gpu.read_amd(tmp_path)
    assert g["sensors"] == "no_hwmon"


def test_readable_card_has_sensors_ok(tmp_path):
    _amd(tmp_path, "card0")
    (g,) = gpu.read_amd(tmp_path)
    assert g["sensors"] == "ok"


def test_summary_sums_power_and_takes_hottest(monkeypatch):
    cards = [{"gpu_vendor": "amd", "gpu_model": "RX 6800 XT", "gpu_mem_mb": 16384, "driver": "amdgpu",
              "temp_c": 64.0, "power_w": 231.0, "util_pct": 97.0, "fan_pct": None, "pci": "a", "sensors": "ok"},
             {"gpu_vendor": "amd", "gpu_model": "RX 6800 XT", "gpu_mem_mb": 16384, "driver": "amdgpu",
              "temp_c": 71.0, "power_w": None, "util_pct": 80.0, "fan_pct": None, "pci": "b", "sensors": "asleep"},
             {"gpu_vendor": "amd", "gpu_model": "RX 6700", "gpu_mem_mb": 10240, "driver": "amdgpu",
              "temp_c": None, "power_w": 180.0, "util_pct": None, "fan_pct": None, "pci": "c", "sensors": "ok"}]
    monkeypatch.setattr(gpu, "_nvidia", list)
    monkeypatch.setattr(gpu, "read_amd", lambda: cards)
    d = gpu.detect()
    assert d["gpu_count"] == 3 and len(d["gpus"]) == 3
    assert d["power_w"] == 411.0            # Summe der bekannten Werte
    assert d["temp_c"] == 71.0              # heißeste Karte
    assert d["util_pct"] == pytest.approx(88.5)
    assert d["gpu_mem_mb"] == 10240         # kleinste Karte entscheidet, welche Coins gehen
    assert d["gpu_model"] == "3× AMD (2× RX 6800 XT, 1× RX 6700)"


def test_summary_single_card_keeps_plain_model(monkeypatch):
    card = {"gpu_vendor": "nvidia", "gpu_model": "NVIDIA GeForce RTX 5060 Ti", "gpu_mem_mb": 16311,
            "driver": "595.91.07", "temp_c": 55.0, "power_w": 28.0, "util_pct": 0.0, "fan_pct": 0.0}
    monkeypatch.setattr(gpu, "_nvidia", lambda: [card])
    d = gpu.detect()
    assert d["gpu_model"] == "NVIDIA GeForce RTX 5060 Ti" and d["gpu_count"] == 1 and d["power_w"] == 28.0


def test_summary_all_power_unknown_stays_none(monkeypatch):
    cards = [{"gpu_vendor": "amd", "gpu_model": "RX 580", "power_w": None, "temp_c": None}] * 2
    monkeypatch.setattr(gpu, "_nvidia", list)
    monkeypatch.setattr(gpu, "read_amd", lambda: cards)
    assert gpu.detect()["power_w"] is None


# ---- Miner-APIs: Watt aller Karten summieren, nicht nur Karte 0 ----
def test_lolminer_sums_power_of_all_workers():
    d = {"Algorithms": [{"Total_Performance": 90, "Performance_Factor": 1e6, "Total_Accepted": 3,
                         "Total_Rejected": 0}], "Workers": [{"Power": 120.5}, {"Power": 130.0}, {"Power": 0}]}
    assert minerapi.parse("lolminer", d)["watts"] == 250.5


def test_rigel_sums_power_of_all_devices():
    d = {"hashrate": {"kawpow": 42e6}, "solution_stat": {},
         "devices": [{"power_usage": 150.0}, {"power_usage": 160.25}]}
    assert minerapi.parse("rigel", d)["watts"] == 310.25


# ---- Server: Mehrkarten-Rig ----
def _three_amd_state():
    card = {"gpu_vendor": "amd", "gpu_model": "Radeon RX 6800 XT", "gpu_mem_mb": 16384, "temp_c": 64.0,
            "power_w": 231.0, "util_pct": 97.0, "fan_pct": None, "pci": "0000:03:00.0", "sensors": "ok"}
    return {"miner": "idle", "gpu_count": 3, "temp_c": 71.0, "power_w": 642.0, "util_pct": 95.0,
            "gpus": [card, {**card, "pci": "0000:06:00.0"}, {**card, "pci": "0000:09:00.0", "temp_c": 71.0}]}


def test_server_keeps_all_cards_in_rig_list(client, admin_headers):
    from tests.test_rigs import D, P, _enroll, _pair
    e = _enroll(client, _pair(client, admin_headers)["code"]).json()
    r = client.post(f"{D}/report", headers={"Authorization": f"Bearer {e['token']}"},
                    json={"info": {"gpu_vendor": "amd", "gpu_model": "3× AMD (3× Radeon RX 6800 XT)"},
                          "state": _three_amd_state()})
    assert r.status_code == 200, r.text
    (row,) = client.get(f"{P}/rigs", headers=admin_headers).json()
    rep = row["last_report"]
    assert rep["gpu_count"] == 3 and len(rep["gpus"]) == 3 and rep["power_w"] == 642.0
    assert row["gpu_model"] == "3× AMD (3× Radeon RX 6800 XT)"


def test_report_with_twenty_cards_fits():
    """Bis 20 Karten pro Rechner dürfen nicht an der Report-Grenze scheitern."""
    import json

    from backend import rigs
    card = _three_amd_state()["gpus"][0]
    state = {**_three_amd_state(), "gpu_count": 20, "gpus": [card] * 20,
             "job": {"coin": "quai-kawpow", "miner": "srbminer"}, "error": "x" * 200}
    assert len(json.dumps(state, separators=(",", ":"))) < rigs.MAX_REPORT_BYTES


def test_power_default_counts_per_card():
    from backend import power
    rig = {"last_report_obj": {"gpu_count": 4}}
    assert power.rig_watts(rig) == 4 * power.DEFAULT_RIG_WATTS
    assert power.rig_watts({"last_report_obj": {"gpu_count": 4, "power_w": 20}}) == 4 * power.DEFAULT_RIG_WATTS
    assert power.rig_watts({"last_report_obj": {"gpu_count": 4, "power_w": 700}}) == 700.0


@pytest.fixture
def quotes():
    from backend import catalog, store
    from backend.profit import CoinQuote
    store.replace_quotes([CoinQuote(coin=c, name=c, algo="A", fee=0.01, fee_type="PPS+",
                                    profit_per_hs_day=1e-6, price_usd=1.0) for c in catalog.coins()])


def test_benchmark_watts_of_big_rig_are_kept(client, admin_headers, quotes):
    from backend import store
    from tests.test_planner import P, _report, _rig
    store.update_config({"kryptex_user": "krxTEST"})
    e = _rig(client, admin_headers)
    j = _report(client, e)["job"]
    _report(client, e, {"benchmark_result": {"coin": j["coin"], "miner": j["miner"], "hashrate": 9e7, "watts": 2600}})
    (b,) = client.get(f"{P}/rigs/{e['rig_id']}/benchmarks", headers=admin_headers).json()
    assert b["watts"] == 2600
