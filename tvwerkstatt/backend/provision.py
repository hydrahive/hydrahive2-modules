"""Einrichtung im Container `hh-tvwerkstatt` (PLAN-E1.md Baustein 3; Muster vibe/backend/provision.py).

Gemessen im Probelauf 13.11. (Ubuntu 24.04): openjdk 17, Android cmdline-tools 11076708, platform-tools,
platforms;android-34, build-tools;34.0.0 – zusammen ca. 445 MB im Heimordner. Skripte sind feste Texte im Modul, keine
Eingaben des Nutzers darin. Die cmdline-tools werden nur entpackt, wenn Größe und Prüfsumme zu Googles Verzeichnis
(repository2-3.xml) passen. Die Lizenz der Android-Werkzeuge wird nur angenommen, wenn der Admin sie im Auftrag bestätigt.
"""
from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass

from hydrahive.containers.incus_client import IncusError
from hydrahive.settings import settings

from . import container, incus

logger = logging.getLogger(__name__)
UID = "1000"
HOME = "/home/ubuntu"
SDK = f"{HOME}/android-sdk"
CLT_FILE = "commandlinetools-linux-11076708_latest.zip"
CLT_SIZE = 153607504                                         # repository2-3.xml, gelesen 13.11.2026
CLT_SHA1 = "d313adb7aedccf6cf0cfca51ec180f0059f5f8f8"
SDK_PACKAGES = ("platform-tools", "platforms;android-34", "build-tools;34.0.0")
RC_CHECKSUM = 3                                              # eigener Exit-Code: Download passt nicht zum Verzeichnis
NET_ATTEMPTS = 3
_PAUSES = (2.0, 5.0)
MAX_DETAIL = 600
_TAIL_LINES = 8
_CTRL = re.compile(r"\x1b\[[0-9;]*[A-Za-z]|[\x00-\x08\x0b-\x1f\x7f]")


@dataclass(frozen=True)
class Step:
    key: str
    script: str
    as_user: bool = False
    timeout: float = 900.0
    net: bool = False


class SetupError(RuntimeError):
    def __init__(self, code: str, step: str = "", detail: str = ""):
        super().__init__(code)
        self.code = code
        self.step = step
        self.detail = detail


_APT = "export DEBIAN_FRONTEND=noninteractive; "
_SDKM = f"{SDK}/cmdline-tools/latest/bin/sdkmanager --sdk_root={SDK}"
STEPS: tuple[Step, ...] = (
    Step("user", "set -eu; id ubuntu >/dev/null; gpasswd -d ubuntu sudo 2>/dev/null || true; "
         "rm -f /etc/sudoers.d/90-incus /etc/sudoers.d/90-cloud-init-users; "
         f"install -d -o ubuntu -g ubuntu -m 0700 {HOME}/.android {HOME}/src"),
    Step("packages", "set -eu; " + _APT + "apt-get update -qq; apt-get install -y -qq --no-install-recommends "
         "openjdk-17-jdk-headless unzip curl ca-certificates git", net=True, timeout=1200.0),
    Step("tools", f"set -eu; if [ ! -x {SDK}/cmdline-tools/latest/bin/sdkmanager ]; then cd /tmp; "
         f"curl -fsSL --retry 3 --retry-delay 2 --connect-timeout 15 --max-time 900 -o clt.zip "
         f"https://dl.google.com/android/repository/{CLT_FILE}; "
         f'[ "$(stat -c %s clt.zip)" = "{CLT_SIZE}" ] || '
         f'{{ echo "Größe passt nicht" >&2; rm -f clt.zip; exit {RC_CHECKSUM}; }}; '
         f'echo "{CLT_SHA1}  clt.zip" | sha1sum -c - >/dev/null || {{ echo "Prüfsumme passt nicht" >&2; rm -f clt.zip; '
         f"exit {RC_CHECKSUM}; }}; rm -rf {SDK}/cmdline-tools; mkdir -p {SDK}/cmdline-tools; "
         f"unzip -q clt.zip -d {SDK}/cmdline-tools; mv {SDK}/cmdline-tools/cmdline-tools {SDK}/cmdline-tools/latest; "
         "rm -f clt.zip; fi", as_user=True, net=True, timeout=1200.0),
    Step("sdk", f"set -eu; yes | {_SDKM} --licenses >/dev/null; "
         f"{_SDKM} " + " ".join(f"'{p}'" for p in SDK_PACKAGES) + " >/dev/null; "
         f"test -x {SDK}/platform-tools/adb; test -d {SDK}/build-tools/34.0.0", as_user=True, net=True, timeout=1800.0),
)
LICENSE_STEP = "sdk"


def keystore_path():
    """Gesicherter Signierschlüssel des Moduls (SPEC Entscheidung 7). Fehlt er, erzeugt der erste Bau einen neuen."""
    return settings.data_dir / "tvwerkstatt" / "signing" / "debug.keystore"


def _detail(out: str, err: str) -> str:
    text = _CTRL.sub("", f"{out or ''}\n{err or ''}").replace(container.NAME, "")
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
    tail = "\n".join(lines[-_TAIL_LINES:])
    return tail if len(tail) <= MAX_DETAIL else "…" + tail[-(MAX_DETAIL - 1):]


def _exec_args(step: Step) -> list[str]:
    if step.as_user:
        return ["exec", container.NAME, "--cwd", HOME, "--user", UID, "--group", UID, "--env", f"HOME={HOME}",
                "--", "bash", "-c", step.script]
    return ["exec", container.NAME, "--", "bash", "-c", step.script]


async def _once(step: Step) -> tuple[int, str]:
    try:
        rc, out, err = await incus.run(*_exec_args(step), timeout=step.timeout)
    except IncusError as exc:
        return 1, _detail("", str(exc))
    return rc, ("" if rc == 0 else _detail(out, err))


async def _step(step: Step) -> None:
    detail = ""
    for attempt in range(NET_ATTEMPTS if step.net else 1):
        rc, detail = await _once(step)
        if rc == 0:
            return
        if rc == RC_CHECKSUM and step.key == "tools":
            raise SetupError("tvw_checksum_mismatch", step.key, detail)
        if attempt < (NET_ATTEMPTS if step.net else 1) - 1:
            logger.warning("TV-Werkstatt: Schritt %s, Versuch %d fehlgeschlagen", step.key, attempt + 1)
            await asyncio.sleep(_PAUSES[min(attempt, len(_PAUSES) - 1)])
    raise SetupError("tvw_setup_failed", step.key, detail)


async def push_keystore() -> bool:
    """Gesicherten Schlüssel in den Container legen (nur lesbar für ubuntu). False, wenn keiner gesichert ist."""
    src = keystore_path()
    if not src.is_file():
        return False
    rc, _, _ = await incus.run("file", "push", "--uid", UID, "--gid", UID, "--mode", "0600", str(src),
                               f"{container.NAME}{HOME}/.android/debug.keystore")
    if rc != 0:
        raise SetupError("tvw_setup_failed", "keystore")
    return True


async def setup(report: Callable[[str], None], *, license_accepted: bool, start_at: str = "") -> None:
    """Alle Schritte nacheinander, `report(key)` vor jedem. Ohne bestätigte Lizenz läuft kein Schritt."""
    if not license_accepted:
        raise SetupError("tvw_license_required")
    keys = [s.key for s in STEPS]
    if start_at and start_at not in keys:
        raise SetupError("tvw_setup_failed")
    for step in STEPS[keys.index(start_at) if start_at else 0:]:
        report(step.key)
        await _step(step)
    report("keystore")
    await push_keystore()
