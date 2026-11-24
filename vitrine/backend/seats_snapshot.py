"""Multiseat M1: Grafikkarten, Ausgänge, Ton und Eingabegeräte aus dem System lesen (ziele/vitrine-multiseat.md §2).

Nur lesen, ohne root: /sys/class/drm, /sys/class/sound, /proc/bus/input/devices, `loginctl list-seats`. Keine festen
Geräte-Pfade oder Kartennummern – alles wird hier ermittelt. Jedes Gerät bekommt eine feste ID (Art + PCI-Adresse bzw.
USB-Port bzw. Bluetooth-Adresse); nur diese IDs nimmt die Zuordnung später an, nie freie Pfade.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

_PCI = re.compile(r"^[0-9a-f]{4}:[0-9a-f]{2}:[0-9a-f]{2}\.[0-7]$")
_USB_DEV = re.compile(r"^\d+-[\d.]+$")              # USB-Gerät (Bus-Port[.Port]), keine Schnittstelle (…:1.0)
_BT = re.compile(r"^[0-9a-f]{2}(:[0-9a-f]{2}){5}$")
VENDORS = {"0x10de": "NVIDIA", "0x1002": "AMD", "0x8086": "Intel"}


def _read(p: Path) -> str | None:
    try:
        return p.read_text().strip()
    except OSError:
        return None


def _sysfs(p: Path, sys_root: Path) -> str | None:
    """Echter sysfs-Pfad (/sys/devices/…) relativ zur Systemwurzel – für `loginctl attach` (Multiseat M2)."""
    try:
        return "/" + str(p.resolve().relative_to(sys_root.resolve()))
    except (OSError, ValueError):
        return None


def _pci_of(device: Path) -> str | None:
    name = device.resolve().name
    return name if _PCI.match(name) else None


def gpus(sys_root: Path) -> list[dict]:
    out = []
    for card in sorted((sys_root / "sys/class/drm").glob("card[0-9]*")):
        if "-" in card.name:
            continue
        dev = card / "device"
        driver = (dev / "driver").resolve().name if (dev / "driver").exists() else ""
        pci = _pci_of(dev)
        evdi = driver == "evdi" or dev.resolve().name.startswith("evdi.")
        if not pci and not evdi:
            continue
        outputs = [{"name": o.name.split("-", 1)[1], "connected": _read(o / "status") == "connected"}
                   for o in sorted(card.parent.glob(f"{card.name}-*")) if (o / "status").exists()]
        gid = f"gpu:evdi:{dev.resolve().name}" if evdi else f"gpu:pci:{pci}"
        vendor = _read(dev / "vendor") or ""
        out.append({"id": gid, "card": card.name, "pci": pci, "driver": driver, "evdi": evdi,
                    "vendor": VENDORS.get(vendor, driver or "?"), "boot_vga": _read(dev / "boot_vga") == "1",
                    "outputs": outputs, "sysfs": _sysfs(dev, sys_root)})
    return out


def sound(sys_root: Path) -> list[dict]:
    out = []
    for card in sorted((sys_root / "sys/class/sound").glob("card[0-9]*")):
        pci = _pci_of(card / "device")
        if pci:
            out.append({"id": f"sound:pci:{pci}", "card": card.name, "pci": pci, "name": _read(card / "id") or card.name,
                        "sysfs": _sysfs(card, sys_root)})
    return out


def _blocks(text: str) -> list[dict]:
    blocks, cur = [], {}
    for line in text.splitlines() + [""]:
        if not line.strip():
            if cur:
                blocks.append(cur)
            cur = {}
        elif line[1:3] == ": " and "=" in line:
            key, _, val = line[3:].partition("=")
            cur[key] = val.strip().strip('"')
    return blocks


def _usb_parts(sysfs: str) -> list[str]:
    return [p for p in sysfs.split("/") if _USB_DEV.match(p)]


def _usb_device(sysfs: str) -> str | None:
    """sysfs-Pfad des USB-GERÄTS (…/usbX/X-Y), nicht des input-Kinds – so wurde in M0 per `loginctl attach` zugeordnet."""
    parts = sysfs.split("/")
    idx = [i for i, p in enumerate(parts) if _USB_DEV.match(p)]
    return "/sys" + "/".join(parts[: idx[-1] + 1]) if idx and sysfs.startswith("/devices/") else None


def inputs(proc_text: str) -> list[dict]:
    """Tastaturen und Mäuse an USB oder Bluetooth, je physischem Gerät eine Zeile (Funk-Empfänger melden Tastatur und Maus als mehrere Knoten)."""
    groups: dict[str, dict] = {}
    for b in _blocks(proc_text):
        sysfs, handlers = b.get("Sysfs", ""), b.get("Handlers", "").split()
        kinds = {k for k, h in (("keyboard", "kbd"), ("mouse", "mouse")) if any(x.startswith(h) for x in handlers)}
        uniq = b.get("Uniq", "").lower()
        usb = _usb_parts(sysfs)
        if not kinds or ("/usb" not in sysfs and "/bluetooth/" not in sysfs):
            continue
        if "/bluetooth/" in sysfs and _BT.match(uniq):
            gid, port = f"input:bt:{uniq}", None
        elif usb:
            gid, port = f"input:usb:{usb[-1]}", usb[-1]
        else:
            continue
        g = groups.setdefault(gid, {"id": gid, "names": [], "kinds": set(), "usb": port,
                                     "branch": usb[0] if usb else None, "bt": uniq if gid.startswith("input:bt:") else None,
                                     "usb_sysfs": None if gid.startswith("input:bt:") else _usb_device(sysfs)})
        g["names"].append(b.get("Name", "?"))
        g["kinds"] |= kinds
    return [{**{k: v for k, v in g.items() if k != "names"}, "name": min(g["names"], key=len), "kinds": sorted(g["kinds"])}
            for g in sorted(groups.values(), key=lambda g: g["id"])]


def seats() -> list[str]:
    loginctl = shutil.which("loginctl")
    if not loginctl:
        return []
    try:
        r = subprocess.run([loginctl, "list-seats", "--no-legend"], capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.SubprocessError):
        return []
    return [line.split()[0] for line in r.stdout.splitlines() if line.strip()]


def read(sys_root: Path = Path("/"), *, vitrine_bt: list[str] | None = None) -> dict:
    proc = _read(sys_root / "proc/bus/input/devices") or ""
    return {"gpus": gpus(sys_root), "sound": sound(sys_root), "inputs": inputs(proc),
            "seats": seats() if sys_root == Path("/") else [], "vitrine_bt": [a.lower() for a in vitrine_bt or []]}
