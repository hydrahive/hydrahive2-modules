"""Multiseat M1 (MS9): Vorschlag aus nachgestellten Systemdaten; Hinweis nur bei echtem Monitor an Nicht-EVDI-Karte."""
from __future__ import annotations

import pytest
from _seats_fixture import AMD, BT_KB, K400, NV, RAPOO, build

from backend import seats, seats_snapshot


def _snap(tmp_path, vitrine_bt=None, **kw):
    return seats_snapshot.read(build(tmp_path, **kw), vitrine_bt=vitrine_bt)


def test_snapshot_liest_karten_ton_und_eingabe(tmp_path):
    s = _snap(tmp_path)
    g = {x["id"]: x for x in s["gpus"]}
    assert set(g) == {f"gpu:pci:{AMD}", "gpu:evdi:evdi.0", f"gpu:pci:{NV}"}
    assert g[f"gpu:pci:{NV}"]["vendor"] == "NVIDIA" and g["gpu:evdi:evdi.0"]["evdi"]
    assert [o["name"] for o in g[f"gpu:pci:{NV}"]["outputs"] if o["connected"]] == ["HDMI-A-1"]
    assert {x["id"] for x in s["sound"]} == {f"sound:pci:{NV[:-1]}1", f"sound:pci:{AMD[:-1]}1", f"sound:pci:{AMD[:-1]}6"}
    ins = {x["id"]: x for x in s["inputs"]}
    assert set(ins) == {"input:usb:1-2.1", "input:usb:1-5"}                 # Rapoo = ein Gerät, Power-Button/Ton nicht
    assert ins["input:usb:1-5"]["kinds"] == ["keyboard", "mouse"] and ins["input:usb:1-2.1"]["branch"] == "1-2"


def test_vorschlag_vorlage_grafik_und_ton(tmp_path):
    r = seats.suggest(_snap(tmp_path))
    a = r["assignment"]
    assert r["feasible"] and r["reasons"] == []
    assert a["gpu:evdi:evdi.0"] == "seat0" and a[f"gpu:pci:{AMD}"] == "seat0"          # Vitrine: EVDI + Karte ohne Bildschirm
    assert a[f"gpu:pci:{NV}"] == "seat1" and a[f"sound:pci:{NV[:-1]}1"] == "seat1"     # Fernseher-Karte + ihr HDMI-Ton
    assert a[f"sound:pci:{AMD[:-1]}6"] == "seat0"


def test_eingabe_unklar_feld_leer(tmp_path):
    """Die Vitrine kennt keine ihrer Eingaben → nicht raten, beide Felder leer, Oberfläche fragt."""
    r = seats.suggest(_snap(tmp_path))
    assert r["inputs_unclear"] is True
    assert r["assignment"]["input:usb:1-2.1"] is None and r["assignment"]["input:usb:1-5"] is None


def test_bekannte_vitrine_eingabe_bestimmt_den_zweig(tmp_path):
    """Über das Vitrine-Bluetooth gekoppelte Tastatur → seat0; anderer USB-Zweig → seat1; gleicher Zweig → seat0."""
    inputs = BT_KB + K400 + RAPOO
    r = seats.suggest(_snap(tmp_path, vitrine_bt=["AA:BB:CC:DD:EE:FF"], inputs=inputs))
    a = r["assignment"]
    assert a["input:bt:aa:bb:cc:dd:ee:ff"] == "seat0"
    assert a["input:usb:1-2.1"] == "seat1" and a["input:usb:1-5"] == "seat1"
    assert r["inputs_unclear"] is False


def test_nur_eine_grafikkarte_nicht_machbar(tmp_path):
    r = seats.suggest(_snap(tmp_path, nvidia=False, amd_monitor=True))
    assert not r["feasible"] and "one_gpu" in r["reasons"] and r["assignment"] == {}
    assert r["monitor_detected"] is True                                     # Hinweis trotzdem ehrlich


def test_kein_bildschirm_kein_hinweis_nicht_machbar(tmp_path):
    r = seats.suggest(_snap(tmp_path, tv=False))
    assert r["monitor_detected"] is False
    assert not r["feasible"] and "no_monitor" in r["reasons"]


def test_evdi_fehlt_nicht_machbar(tmp_path):
    r = seats.suggest(_snap(tmp_path, evdi=False))
    assert not r["feasible"] and r["reasons"] == ["no_evdi"] and r["monitor_detected"] is True


def test_nur_evdi_bildschirm_ist_kein_hinweis(tmp_path):
    """Das Gehäuse-Display allein (EVDI connected) löst keinen Hinweis aus."""
    s = _snap(tmp_path, tv=False)
    assert any(o["connected"] for g in s["gpus"] if g["evdi"] for o in g["outputs"])
    assert seats.monitor_detected(s) is False


def test_zwei_karten_mit_bildschirm_unklar(tmp_path):
    r = seats.suggest(_snap(tmp_path, amd_monitor=True))
    assert not r["feasible"] and "gpu_unclear" in r["reasons"]


# --- Prüfung der vom Admin bestätigten Zuordnung (PUT) ----------------------------------------------------------

def _ok(s):
    a = {d: "seat0" for d in seats.device_ids(s)}
    a.update({f"gpu:pci:{NV}": "seat1", f"sound:pci:{NV[:-1]}1": "seat1", "input:usb:1-5": "seat1"})
    return a


def test_validate_nimmt_gueltige_zuordnung(tmp_path):
    s = _snap(tmp_path)
    assert seats.validate(s, _ok(s))[f"gpu:pci:{NV}"] == "seat1"


@pytest.mark.parametrize("change,code", [
    ({"/dev/input/event3": "seat1"}, "vitrine_seat_unknown_device"),
    ({"gpu:pci:0000:99:00.0": "seat1"}, "vitrine_seat_unknown_device"),
    ({"input:usb:1-5": "seat2"}, "vitrine_seat_bad_seat"),
    ({"gpu:evdi:evdi.0": "seat1"}, "vitrine_seat_evdi_not_seat0"),
    ({f"gpu:pci:{NV}": "seat0"}, "vitrine_seat_gpu_per_seat"),
])
def test_validate_lehnt_ab(tmp_path, change, code):
    s = _snap(tmp_path)
    with pytest.raises(seats.SeatError) as e:
        seats.validate(s, {**_ok(s), **change})
    assert e.value.code == code


def test_kein_festes_geraet_im_modulcode():
    from pathlib import Path
    src = "".join((Path(seats.__file__).parent / f).read_text() for f in ("seats.py", "seats_snapshot.py", "seat_routes.py"))
    for fixed in ("0d:00", "01:00", "K400", "Rapoo", "RAPOO", "evdi.0", "card2", "HDMI-A-1", "1-5"):
        assert fixed not in src, fixed
