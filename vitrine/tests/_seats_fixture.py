"""Nachgestellte Systemdaten für Multiseat M1 – echte Struktur (sysfs-Verweise, /proc/bus/input/devices).

Vorlage: Server mit AMD-Grafik ohne Bildschirm, USB-Display (EVDI) am Gehäuse, NVIDIA mit Fernseher an HDMI, Logitech
K400 (USB-Empfänger hinter einem Hub, Zweig 1-2) und Rapoo (Zweig 1-5). Nur hier stehen Adressen und Namen eines
echten Rechners, nie im Modulcode.
"""
from __future__ import annotations

from pathlib import Path

AMD = "0000:0d:00.0"
NV = "0000:01:00.0"
USB = "/devices/pci0000:00/0000:00:02.1/0000:02:00.0/0000:03:0c.0/0000:0a:00.0/usb1"


def _gpu(root: Path, card: str, dev: str, driver: str, *, vendor: str | None, boot_vga: str | None,
         outputs: dict[str, str]) -> None:
    d = root / "sys" / dev.lstrip("/")
    (d / "drm" / card).mkdir(parents=True, exist_ok=True)
    drv = root / "sys/bus/drivers" / driver
    drv.mkdir(parents=True, exist_ok=True)
    (d / "driver").symlink_to(drv)
    if vendor:
        (d / "vendor").write_text(vendor + "\n")
    if boot_vga is not None:
        (d / "boot_vga").write_text(boot_vga + "\n")
    cls = root / "sys/class/drm"
    cls.mkdir(parents=True, exist_ok=True)
    (cls / card).symlink_to(d / "drm" / card)
    (d / "drm" / card / "device").symlink_to(d)
    for name, status in outputs.items():
        o = d / "drm" / card / f"{card}-{name}"
        o.mkdir()
        (o / "status").write_text(status + "\n")
        (cls / f"{card}-{name}").symlink_to(o)


def _sound(root: Path, card: str, dev: str, sid: str) -> None:
    d = root / "sys" / dev.lstrip("/")
    (d / "sound" / card).mkdir(parents=True, exist_ok=True)
    (d / "sound" / card / "id").write_text(sid + "\n")
    (d / "sound" / card / "device").symlink_to(d)
    cls = root / "sys/class/sound"
    cls.mkdir(parents=True, exist_ok=True)
    (cls / card).symlink_to(d / "sound" / card)


def _input(name: str, sysfs: str, handlers: str, uniq: str = "") -> str:
    return f'I: Bus=0003\nN: Name="{name}"\nP: Phys=x\nS: Sysfs={sysfs}\nU: Uniq={uniq}\nH: Handlers={handlers} \n\n'


K400 = _input("Logitech K400 Plus", f"{USB}/1-2/1-2.1/1-2.1:1.2/0003:046D:C52B.0005/0003:046D:404D.0006/input/input13",
              "sysrq kbd mouse0 event3 leds")
RAPOO = (_input("RAPOO Rapoo 2.4G Wireless Device", f"{USB}/1-5/1-5:1.0/0003:24AE:1008.000B/input/input31", "mouse1 event16")
         + _input("RAPOO Rapoo 2.4G Wireless Device", f"{USB}/1-5/1-5:1.1/0003:24AE:1008.000C/input/input32",
                  "sysrq kbd event17 leds"))
BT_KB = _input("MX Keys", "/devices/pci0000:00/0000:00:14.0/usb3/3-9/3-9:1.0/bluetooth/hci0/hci0:256/0005:046D:B35B.0001/input/input40",
               "sysrq kbd event20 leds", uniq="aa:bb:cc:dd:ee:ff")
OTHER = (_input("Power Button", "/devices/platform/PNP0C0C:00/input/input0", "kbd event0")
         + _input("HDA NVidia HDMI/DP,pcm=3", f"/devices/pci0000:00/0000:00:01.1/{NV[:-1]}1/sound/card0/input18", "event7"))


def build(root: Path, *, nvidia: bool = True, evdi: bool = True, tv: bool = True, amd_monitor: bool = False,
          inputs: str | None = None) -> Path:
    """Nachgebauter Rechner unter root. Standard = Vorlage oben."""
    _gpu(root, "card0", f"/devices/pci0000:00/0000:00:08.1/{AMD}", "amdgpu", vendor="0x1002", boot_vga="0",
         outputs={"DP-4": "disconnected", "HDMI-A-2": "connected" if amd_monitor else "disconnected",
                  "Writeback-1": "unknown"})
    if evdi:
        _gpu(root, "card1", "/devices/platform/evdi.0", "evdi", vendor=None, boot_vga=None, outputs={"DVI-I-1": "connected"})
    if nvidia:
        _gpu(root, "card2", f"/devices/pci0000:00/0000:00:01.1/{NV}", "nvidia", vendor="0x10de", boot_vga="1",
             outputs={"DP-1": "disconnected", "HDMI-A-1": "connected" if tv else "disconnected"})
        _sound(root, "card0", f"/devices/pci0000:00/0000:00:01.1/{NV[:-1]}1", "NVidia")
    _sound(root, "card1", f"/devices/pci0000:00/0000:00:08.1/{AMD[:-1]}1", "Generic")
    _sound(root, "card2", f"/devices/pci0000:00/0000:00:08.1/{AMD[:-1]}6", "Generic_1")
    proc = root / "proc/bus/input"
    proc.mkdir(parents=True, exist_ok=True)
    (proc / "devices").write_text(OTHER + (K400 + RAPOO if inputs is None else inputs))
    return root
