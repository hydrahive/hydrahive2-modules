"""USB drive detection via lsblk + udisksctl mount."""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass

_EXCLUDED_MOUNTS = frozenset(["/", "/boot", "/home", "/tmp", "/var", "/usr", "/opt"])
_EXCLUDED_FS = frozenset(["squashfs", "tmpfs", "devtmpfs", "sysfs", "proc", "cifs", "nfs"])


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
    _walk(data.get("blockdevices", []), drives)
    return drives


def mount_drive(device: str) -> str:
    """Mountet ein Device via udisksctl. Gibt den Mountpoint zurück."""
    # Sicherheit: nur /dev/sd*, /dev/nvme*, /dev/mmcblk* erlaubt
    import re
    if not re.match(r"^/dev/(sd[a-z]\d+|nvme\d+n\d+p\d+|mmcblk\d+p\d+)$", device):
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


def _walk(devices: list[dict], result: list[Drive]) -> None:
    for dev in devices:
        _collect(dev, result)
        for child in dev.get("children") or []:
            _collect(child, result)


def _collect(dev: dict, result: list[Drive]) -> None:
    fstype = dev.get("fstype") or ""
    tran = dev.get("tran") or ""
    removable = str(dev.get("rm", "0")) in ("1", "true")
    mountpoint = dev.get("mountpoint") or ""
    device = dev.get("path") or f"/dev/{dev.get('name', '')}"

    # Partitionen ohne Dateisystem überspringen (raw device, extended partition etc.)
    if not fstype:
        return
    if fstype in _EXCLUDED_FS:
        return
    if not (removable or tran == "usb"):
        return
    if mountpoint and any(mountpoint == m or mountpoint.startswith(m + "/") for m in _EXCLUDED_MOUNTS):
        return

    result.append(Drive(
        name=dev.get("name", ""),
        label=dev.get("label") or dev.get("name", ""),
        size=dev.get("size", "?"),
        mountpoint=mountpoint,
        transport=tran,
        device=device,
    ))
