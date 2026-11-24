"""Multiseat M2: Aus Snapshot (M1) und geprüfter Zuordnung (seats.validate) den Plan für multiseat-apply.sh bauen.

Rein und testbar. Der Plan enthält nur Werte aus dem Snapshot (nie freie Nutzereingaben):
- `seat0_busid`: Haupt-GPU der Vitrine im Xorg-Format, DEZIMAL (sysfs 0000:0d:00.0 → PCI:13:0:0; M0, Probe D/E)
- `evdi_kmsdev`: EVDI-Gerät über den stabilen by-path-Namen (Kartennummern wechseln nach Neustart)
- `attach`: sysfs-Pfade für `loginctl attach seat1` – PCI-Funktion der GPU, Tonkarte, USB-GERÄT der Eingabe (M0)
`render_lightdm` / `render_xorg` erzeugen die Dateien; das Skript prüft alle Werte zusätzlich selbst.
"""
from __future__ import annotations

import json
import re

from .seats import SeatError

KIOSK_USER = "hydrahive-kiosk"
KIOSK_SESSION = "hydrahive-vitrine-kiosk"
GREETER = "lightdm-gtk-greeter"
_PCI = re.compile(r"^([0-9a-f]{4}):([0-9a-f]{2}):([0-9a-f]{2})\.([0-7])$")
_SAFE = re.compile(r"^/sys/devices/[A-Za-z0-9:._/-]+$")
_EVDI = re.compile(r"^evdi\.[0-9]+$")
# Kernel-Treiber → Xorg-Treiber; alles andere über modesetting (M0: amdgpu belegt)
XORG_DRIVERS = {"amdgpu": "amdgpu", "radeon": "radeon", "nvidia": "nvidia"}


def xorg_busid(pci: str) -> str:
    """sysfs-PCI-Adresse → Xorg-BusID (dezimal). Domäne 0 wird weggelassen, sonst bus@domain wie Xorg es erwartet."""
    m = _PCI.match(pci or "")
    if not m:
        raise SeatError("vitrine_seat_plan_pci")
    dom, bus, dev, fn = (int(x, 16) for x in m.groups())
    return f"PCI:{bus}@{dom}:{dev}:{fn}" if dom else f"PCI:{bus}:{dev}:{fn}"


def _safe(path: str | None) -> str:
    if not path or not _SAFE.match(path) or "/../" in path or path.endswith("/.."):
        raise SeatError("vitrine_seat_plan_path")
    return path


def build_plan(snapshot: dict, assignment: dict[str, str]) -> dict:
    gpus = snapshot.get("gpus", [])
    real0 = [g for g in gpus if not g["evdi"] and assignment.get(g["id"]) == "seat0"]
    evdi = [g for g in gpus if g["evdi"]]
    if len(real0) != 1 or len(evdi) != 1:
        raise SeatError("vitrine_seat_gpu_per_seat")
    evdi_name = (evdi[0]["id"].split(":", 2) + [""])[2]
    if not _EVDI.match(evdi_name):
        raise SeatError("vitrine_seat_plan_evdi")

    attach: list[str] = []
    for g in gpus:
        if assignment.get(g["id"]) == "seat1":
            attach.append(_safe(g.get("sysfs")))
    for s in snapshot.get("sound", []):
        if assignment.get(s["id"]) == "seat1":
            attach.append(_safe(s.get("sysfs")))
    seat0_usb: list[str] = []
    for i in snapshot.get("inputs", []):
        where = assignment.get(i["id"])
        if where == "seat1":
            if not i.get("usb_sysfs"):
                raise SeatError("vitrine_seat_plan_bt_seat1")   # Bluetooth hängt am Funkchip, nicht einzeln zuordenbar
            attach.append(_safe(i["usb_sysfs"]))
        elif where == "seat0" and i.get("usb_sysfs"):
            seat0_usb.append(i["usb_sysfs"])
    if any(u == a or u.startswith(a + "/") for u in seat0_usb for a in attach):
        raise SeatError("vitrine_seat_plan_usb_shared")         # Vitrine-Gerät hängt unter einem seat1-USB-Gerät
    if not attach:
        raise SeatError("vitrine_seat_empty")
    return {"version": 1, "seat0_busid": xorg_busid(real0[0]["pci"]), "seat0_driver": XORG_DRIVERS.get(real0[0].get("driver") or "", "modesetting"),
            "evdi_kmsdev": f"/dev/dri/by-path/platform-{evdi_name}-card", "attach": sorted(dict.fromkeys(attach)),
            "kiosk_user": KIOSK_USER, "kiosk_session": KIOSK_SESSION}


def render_lightdm(plan: dict) -> str:
    return (
        "# Von HydraHive Vitrine geschrieben (Zweiter Arbeitsplatz). Rückbau: multiseat-revert.sh\n"
        "[Seat:seat0]\n"
        f"autologin-user={plan['kiosk_user']}\n"
        f"autologin-session={plan['kiosk_session']}\n"
        "autologin-user-timeout=0\n"
        "\n"
        "[Seat:seat1]\n"
        f"greeter-session={GREETER}\n"
    )


def render_xorg(plan: dict) -> str:
    """Nach M0 Probe E (multiseat-m0/xorg-seat0-m0e.conf): Haupt-GPU per BusID + EVDI als GPUDevice, nur seat0."""
    drv = plan.get("seat0_driver") if plan.get("seat0_driver") in XORG_DRIVERS.values() else "modesetting"
    return f'''# Von HydraHive Vitrine geschrieben (Zweiter Arbeitsplatz): Vitrine-Arbeitsplatz seat0 = Haupt-GPU + USB-Display.
# Rückbau: multiseat-revert.sh
Section "ServerLayout"
    Identifier "hh-vitrine-seat0"
    MatchSeat  "seat0"
    Screen     "hh-vitrine-main"
EndSection
Section "Device"
    Identifier "hh-vitrine-main"
    Driver     "{drv}"
    BusID      "{plan['seat0_busid']}"
    MatchSeat  "seat0"
EndSection
Section "Device"
    Identifier "hh-vitrine-evdi"
    Driver     "modesetting"
    Option     "kmsdev" "{plan['evdi_kmsdev']}"
    MatchSeat  "seat0"
EndSection
Section "Screen"
    Identifier "hh-vitrine-main"
    Device     "hh-vitrine-main"
    GPUDevice  "hh-vitrine-evdi"
    MatchSeat  "seat0"
EndSection
'''


def plan_json(plan: dict) -> str:
    return json.dumps(plan, indent=2, sort_keys=True) + "\n"
