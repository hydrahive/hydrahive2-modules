"""USB drive detection via lsblk + mount (host-namespace-aware)."""
from __future__ import annotations

import json
import logging
import os
import re
import shlex
import subprocess
from dataclasses import dataclass

logger = logging.getLogger(__name__)

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


def _sudo_host(cmd: list[str]) -> list[str]:
    """Führt cmd im Host-Mount-Namespace aus.

    PrivateTmp=true im systemd-Unit erstellt einen privaten Namespace —
    ohne nsenter wären Mounts nur innerhalb des Service sichtbar.
    """
    return ["sudo", "/bin/bash", "-c",
            shlex.join(["nsenter", "-t", "1", "-m", "--"] + cmd)]


def list_drives() -> list[Drive]:
    # lsblk im Host-Namespace: zeigt korrekte Mountpoints
    try:
        out = subprocess.check_output(
            _sudo_host(["lsblk", "-J", "-o", "NAME,LABEL,SIZE,MOUNTPOINT,TRAN,RM,FSTYPE,PATH"]),
            text=True, timeout=10,
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
    """Mountet ein Device im Host-Mount-Namespace."""
    if not _DEVICE_RE.match(device):
        raise ValueError(f"Ungültiges Device: {device!r}")

    # Filesystem + Label im Host-Namespace ermitteln
    try:
        out = subprocess.check_output(
            _sudo_host(["lsblk", "-J", "-o", "FSTYPE,LABEL", device]),
            text=True, timeout=10,
        )
        info = json.loads(out).get("blockdevices", [{}])[0]
    except Exception:
        info = {}

    fstype = info.get("fstype") or ""
    label = info.get("label") or ""

    safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", label or os.path.basename(device))
    mountpoint = f"/media/hydrahive/{safe_name}"

    # Verzeichnis im Host-Namespace anlegen
    subprocess.run(
        _sudo_host(["mkdir", "-p", mountpoint]),
        capture_output=True, text=True, timeout=10,
    )

    # NTFS: Dirty-Bit löschen
    if fstype == "ntfs":
        logger.info("archiver: ntfsfix -d %s", device)
        subprocess.run(
            _sudo_host(["ntfsfix", "-d", device]),
            capture_output=True, text=True, timeout=30,
        )

    # Mount-Argumente
    mount_args = ["/usr/bin/mount"]
    if fstype == "ntfs":
        mount_args += ["-t", "ntfs3", "-o", "force,noatime,nls=utf8"]
    elif fstype in ("vfat", "exfat"):
        mount_args += ["-o", "utf8,umask=0022,noatime"]
    elif fstype:
        mount_args += ["-t", fstype, "-o", "noatime"]
    mount_args += [device, mountpoint]

    logger.info("archiver: mounting %s → %s (fstype=%s)", device, mountpoint, fstype or "auto")
    result = subprocess.run(
        _sudo_host(mount_args),
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        err = result.stderr.strip() or result.stdout.strip() or f"code {result.returncode}"
        logger.error("archiver: mount fehlgeschlagen: %s", err)
        raise RuntimeError(err)

    logger.info("archiver: mount erfolgreich %s → %s", device, mountpoint)
    return mountpoint


def unmount_drive(mountpoint: str) -> None:
    """Hängt einen Mountpoint im Host-Namespace aus."""
    if not mountpoint.startswith("/media/hydrahive/"):
        raise ValueError(f"Ungültiger Mountpoint: {mountpoint!r}")
    logger.info("archiver: unmounting %s", mountpoint)
    result = subprocess.run(
        _sudo_host(["/usr/bin/umount", mountpoint]),
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        err = result.stderr.strip() or result.stdout.strip() or f"code {result.returncode}"
        logger.error("archiver: umount fehlgeschlagen: %s", err)
        raise RuntimeError(err)
    logger.info("archiver: unmount erfolgreich %s", mountpoint)


def _walk(dev: dict, result: list[Drive], parent_tran: str) -> None:
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
