"""Einrichtung im Labor-Container, Sicherungspunkt „frisch“, Zurücksetzen (PLAN-L1.md Baustein 3).

Gemessen hydratest 30.10. (Ubuntu 24.04, 2 CPU): Einrichtung ~1,5 min, Platz ~1,3 GB, Kern-Tests im Container
5235 grün; `qemu-utils` und `lsof` braucht die Kern-Testreihe (sonst 5 rot). Skripte sind fest im Modul, keine
Eingaben des Nutzers darin. Klon über öffentliches https, ohne Zugangsdaten.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from . import container, incus, network

SNAPSHOT = "frisch"
UID = "1000"


@dataclass(frozen=True)
class Step:
    key: str
    script: str
    as_user: bool = False
    timeout: float = 900.0


class SetupError(RuntimeError):
    def __init__(self, code: str, step: str = ""):
        super().__init__(code)
        self.code = code
        self.step = step


_APT = "export DEBIAN_FRONTEND=noninteractive; "
STEPS: tuple[Step, ...] = (
    Step("user", "set -eu; "
         "if id ubuntu >/dev/null 2>&1; then usermod -l labor -d /home/labor -m ubuntu; groupmod -n labor ubuntu; fi; "
         "id labor >/dev/null 2>&1 || useradd -m -u 1000 -s /bin/bash labor; "
         "gpasswd -d labor sudo 2>/dev/null || true; rm -f /etc/sudoers.d/90-incus /etc/sudoers.d/90-cloud-init-users; "
         "install -d -o labor -g labor /work"),
    Step("packages", "set -eu; " + _APT + "apt-get update -qq; apt-get install -y -qq --no-install-recommends "
         "git python3-venv python3-pip build-essential ripgrep curl ca-certificates qemu-utils lsof"),
    Step("node", "set -eu; " + _APT + "curl -fsSL https://deb.nodesource.com/setup_20.x | bash -; "
         "apt-get install -y -qq nodejs"),
    Step("code", "set -eu; cd /work; "
         "git clone -q --depth 50 https://github.com/hydrahive/hydrahive2.0.git hydrahive2; "
         "git clone -q --depth 50 https://github.com/hydrahive/hydrahive2-modules.git hydrahive2-modules",
         as_user=True),
    Step("python", "set -eu; python3 -m venv /work/.venv; /work/.venv/bin/pip install -q --upgrade pip; "
         "/work/.venv/bin/pip install -q -e /work/hydrahive2/core pytest pytest-asyncio pytest-xdist ruff",
         as_user=True),
    Step("frontend", "set -eu; cd /work/hydrahive2/frontend; npm ci --no-audit --no-fund --loglevel=error",
         as_user=True),
    # Das venv als Standard: die Kern-Tests rufen `python` über PATH (Befund test_mac_update im Container).
    # python/python3 als Startskript – über eine Verknüpfung erkennt Python das venv nicht (Befund hydratest 30.10.).
    Step("links", "set -eu; " + "; ".join(
        [f"printf '#!/bin/sh\\nexec /work/.venv/bin/{t} \"$@\"\\n' > /usr/local/bin/{t}; chmod 755 /usr/local/bin/{t}"
         for t in ("python", "python3")]
        + [f"ln -sf /work/.venv/bin/{t} /usr/local/bin/{t}" for t in ("pip", "pytest", "ruff")])),
)


def _exec_args(step: Step) -> list[str]:
    if step.as_user:
        return ["exec", container.NAME, "--cwd", "/work", "--user", UID, "--group", UID,
                "--env", "HOME=/home/labor", "--", "bash", "-c", step.script]
    return ["exec", container.NAME, "--", "bash", "-c", step.script]


async def setup(report: Callable[[str], None]) -> None:
    """Alle Schritte nacheinander. `report(key)` vor jedem Schritt (Fortschritt im Assistenten)."""
    for step in STEPS:
        report(step.key)
        rc, _, _ = await incus.run(*_exec_args(step), timeout=step.timeout)
        if rc != 0:
            raise SetupError("labor_setup_failed", step.key)


async def has_snapshot() -> bool:
    rc, out, _ = await incus.run("snapshot", "list", container.NAME, "--format", "csv")
    return rc == 0 and SNAPSHOT in incus.first_column(out)


async def snapshot() -> None:
    """Sicherungspunkt im gestoppten Zustand (konsistent), danach wieder starten."""
    if await has_snapshot():
        return
    await incus.run("stop", container.NAME, timeout=120)
    rc, _, _ = await incus.run("snapshot", "create", container.NAME, SNAPSHOT, timeout=600)
    await incus.run("start", container.NAME, timeout=120)
    if rc != 0:
        raise container.LaborError("labor_snapshot_failed")


async def reset() -> dict:
    """Zurück auf „frisch“, dann Sperre erneut prüfen."""
    if not await has_snapshot():
        raise container.LaborError("labor_no_snapshot")
    rc, _, _ = await incus.run("snapshot", "restore", container.NAME, SNAPSHOT, timeout=600)
    if rc != 0:
        raise container.LaborError("labor_reset_failed")
    await incus.run("start", container.NAME, timeout=120)       # läuft er schon: Fehler egal
    await container.wait_for_address()
    return await network.probe(container.NAME, await network.gateway())
