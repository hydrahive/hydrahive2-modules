"""USB drive detection via lsblk + udisksctl mount."""
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass

_EXCLUDED_MOUNTS = frozenset(["/", "/boot", "/home", "/tmp", "/var", "/usr", "/opt"])
_EXCLUDED_FS = frozenset(["squashfs", "tmpfs", "devtmpfs", "sysfs", "proc", "cifs", "nfs"])
_DEVICE_RE = re.compile(r"^/dev/(sd[a-z]\d*|nvme\d+n\d+(?:p\d+)?|mmcblk\d+(?:p\d+)?)$")


@dataclass
class Drive:
    name: str
    label: str
    size: str
    mountpoint: str   # leer = nicht gemountet
    transport: str
    device: str       # z.B. /dev/sdb1


def list_drives() -> list[Drive]:
    try:
        out = subprocess.check_output(
            ["lsblk", "-J", "-o", "NAME,LABEL,SIZE,MOUNTPOINT,TRAN,RM,FSTYPE,PATH"],
            text=True, timeout=5,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return []

    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return []

    drives: list[Drive] = []
    for dev in data.get("blockdevices", []):
        _walk(dev, drives, parent_tran=dev.get("tran") or "")
    return drives


def mount_drive(device: str) -> str:
    """Mountet ein Device via udisksctl. Gibt den Mountpoint zurück."""
    if not _DEVICE_RE.match(device):
        raise ValueError(f"Ungültiges Device: {device!r}")

    result = subprocess.run(
        ["udisksctl", "mount", "-b", device, "--no-user-interaction"],
        capture_output=True, text=True, timeout=15,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"udisksctl fehlgeschlagen (code {result.returncode})")

    # Ausgabe: "Mounted /dev/sdb1 at /media/hydrahive/LABEL."
    for part in result.stdout.split():
        if part.startswith("/media/") or part.startswith("/run/media/"):
            return part.rstrip(".")
    raise RuntimeError(f"Mountpoint nicht erkannt in: {result.stdout!r}")


def _walk(dev: dict, result: list[Drive], parent_tran: str) -> None:
    """Rekursiv — gibt parent_tran an Partitionen weiter (lsblk setzt tran nur am Parent)."""
    tran = dev.get("tran") or parent_tran
    _collect(dev, result, effective_tran=tran)
    for child in dev.get("children") or []:
        _walk(child, result, parent_tran=tran)


def _collect(dev: dict, result: list[Drive], effective_tran: str) -> None:
    fstype = dev.get("fstype") or ""
    removable = str(dev.get("rm", "0")) in ("1", "true")
    mountpoint = dev.get("mountpoint") or ""
    device = dev.get("path") or f"/dev/{dev.get('name', '')}"

    if not fstype or fstype in _EXCLUDED_FS:
        return
    # USB-Kriterium: entweder removable ODER USB-Transport irgendwo im Baum
    if not (removable or effective_tran == "usb"):
        return
    if mountpoint and any(mountpoint == m or mountpoint.startswith(m + "/") for m in _EXCLUDED_MOUNTS):
        return

    result.append(Drive(
        name=dev.get("name", ""),
        label=dev.get("label") or dev.get("name", ""),
        size=dev.get("size", "?"),
        mountpoint=mountpoint,
        transport=effective_tran,
        device=device,
    ))
