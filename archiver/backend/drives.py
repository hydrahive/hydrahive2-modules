"""USB drive detection via lsblk."""
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
    mountpoint: str
    transport: str


def list_drives() -> list[Drive]:
    try:
        out = subprocess.check_output(
            ["lsblk", "-J", "-o", "NAME,LABEL,SIZE,MOUNTPOINT,TRAN,RM,FSTYPE"],
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


def _walk(devices: list[dict], result: list[Drive]) -> None:
    for dev in devices:
        _collect(dev, result)
        for child in dev.get("children") or []:
            _collect(child, result)


def _collect(dev: dict, result: list[Drive]) -> None:
    mountpoint = dev.get("mountpoint") or ""
    fstype = dev.get("fstype") or ""
    tran = dev.get("tran") or ""
    removable = str(dev.get("rm", "0")) in ("1", "true")

    if not mountpoint:
        return
    if fstype in _EXCLUDED_FS:
        return
    if any(mountpoint == m or mountpoint.startswith(m + "/") for m in _EXCLUDED_MOUNTS):
        return
    if not (removable or tran == "usb"):
        return

    result.append(Drive(
        name=dev.get("name", ""),
        label=dev.get("label") or dev.get("name", ""),
        size=dev.get("size", "?"),
        mountpoint=mountpoint,
        transport=tran,
    ))
