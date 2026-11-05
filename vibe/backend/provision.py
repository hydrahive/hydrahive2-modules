"""Einrichtung im Vibe-Container (PLAN-V1.md Baustein 3; Muster hydralabor/backend/provision.py).

Gemessen hydratest 4.11. (Ubuntu 24.04, 2 CPU): Node aus apt ist v18 und für Vite zu alt → gepinnter Node-LTS-Tarball
(3,6 s), `npm ci` der Vorlage ~6 s, Dev-Server nach 1,6 s. Skripte sind feste Texte im Modul, keine Eingaben des
Nutzers darin; der Container-Name steht nur in der incus-Argumentliste. Der Nutzer im Container heißt `labor`, weil
der Kern-Launcher `HOME=/home/labor` und UID 1000 fest setzt (tools/_launcher_container.py).
"""
from __future__ import annotations

import asyncio
import io
import logging
import tarfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from hydrahive.containers.incus_client import IncusError

from . import container, incus
from .version_text import _CTRL

logger = logging.getLogger(__name__)
UID = "1000"
TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "template"
NODE_VERSION = "v26.13.0"           # LTS „Lithium“, nodejs.org/dist, 28.10.2026
NODE_SHA256 = "d28a96af6c38596f6d9d97c0ee531c13d238d757742387d1928de822d959e997"   # SHASUMS256.txt, linux-x64.tar.xz
_SKIP = ("node_modules", "dist")


@dataclass(frozen=True)
class Step:
    key: str
    script: str
    as_user: bool = False
    timeout: float = 900.0
    net: bool = False                      # braucht das Netz → bei Aussetzern bis zu NET_ATTEMPTS-mal versuchen


# Netz-Schritte werden bei Aussetzern wiederholt (hydratest 5.11.: `npm ci` scheiterte einmal, direkt danach lief derselbe
# Befehl in 2 s). Lokale Schritte genau einmal: ein Fehler dort ist kein Aussetzer.
NET_ATTEMPTS = 3
_PAUSES = (2.0, 5.0)
MAX_DETAIL = 600
_TAIL_LINES = 8


class SetupError(RuntimeError):
    def __init__(self, code: str, step: str = "", detail: str = ""):
        super().__init__(code)
        self.code = code
        self.step = step
        self.detail = detail               # letzte Zeilen der Ausgabe des gescheiterten Schritts (gekürzt, bereinigt)


def _detail(out: str, err: str) -> str:
    """Die letzten Zeilen der Ausgabe, ohne Steuerzeichen und ohne den Container-Namen, höchstens MAX_DETAIL Zeichen."""
    text = _CTRL.sub("", f"{out or ''}\n{err or ''}").replace("hh-vibe-", "")      # Fehlermeldung (stderr) ans Ende
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
    tail = "\n".join(lines[-_TAIL_LINES:])
    return tail if len(tail) <= MAX_DETAIL else "…" + tail[-(MAX_DETAIL - 1):]


_APT = "export DEBIAN_FRONTEND=noninteractive; "
_NODE = f"node-{NODE_VERSION}-linux-x64.tar.xz"
STEPS: tuple[Step, ...] = (
    Step("user", "set -eu; "
         "if id ubuntu >/dev/null 2>&1; then usermod -l labor -d /home/labor -m ubuntu; groupmod -n labor ubuntu; fi; "
         "id labor >/dev/null 2>&1 || useradd -m -u 1000 -s /bin/bash labor; "
         "gpasswd -d labor sudo 2>/dev/null || true; rm -f /etc/sudoers.d/90-incus /etc/sudoers.d/90-cloud-init-users; "
         "install -d -o labor -g labor /work"),
    Step("packages", "set -eu; " + _APT + "apt-get update -qq; "
         "apt-get install -y -qq --no-install-recommends git curl ca-certificates xz-utils ripgrep libatomic1", net=True),
    Step("node", "set -eu; cd /tmp; "
         f"curl -fsSL --retry 3 --retry-delay 2 --connect-timeout 15 --max-time 180 -o {_NODE} https://nodejs.org/dist/{NODE_VERSION}/{_NODE}; "
         f'echo "{NODE_SHA256}  {_NODE}" | sha256sum -c -; '
         f"tar -xJ -C /usr/local --strip-components=1 --no-same-owner -f {_NODE}; rm -f {_NODE}; "
         f"node -v | grep -qx {NODE_VERSION}", net=True),
    Step("template", "set -eu; cd /work; tar -x -C /work --no-same-owner -f -", as_user=True),
    Step("git", "set -eu; cd /work; git init -q -b main; git config user.name Vibe; "
         "git config user.email vibe@localhost; git config core.hooksPath /dev/null; "
         "git add -A; git commit -q -m Start", as_user=True),
    Step("deps", "set -eu; cd /work; npm ci --no-audit --no-fund --loglevel=error", as_user=True, net=True),
    Step("devserver", "set -eu; cat > /etc/systemd/system/vibe-dev.service <<'EOF'\n"
         "[Unit]\nDescription=Vibe Dev-Server\nAfter=network.target\n\n"
         "[Service]\nUser=labor\nWorkingDirectory=/work\nEnvironment=HOME=/home/labor\n"
         "ExecStart=/usr/local/bin/node /work/node_modules/vite/bin/vite.js\nRestart=always\nRestartSec=2\n\n"
         "[Install]\nWantedBy=multi-user.target\nEOF\n"
         "systemctl daemon-reload; systemctl enable --now vibe-dev.service; "
         "for i in $(seq 1 40); do curl -s -o /dev/null -m 1 http://127.0.0.1:5173/ && exit 0; sleep 0.5; done; exit 1",
         timeout=120.0, net=True),
)


def template_file(rel: str) -> str:
    """Eine Datei der Vorlage als Text (für Tests und Prüfungen)."""
    return (TEMPLATE_DIR / rel).read_text(encoding="utf-8")


def _neutral(info: tarfile.TarInfo) -> tarfile.TarInfo:
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    info.mode = 0o755 if info.isdir() else 0o644
    info.mtime = 0
    return info


def template_tar() -> bytes:
    """Die Vorlage als tar: neutrale Besitzer, keine Sonderrechte, keine Links, ohne node_modules/dist."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as t:
        for path in sorted(TEMPLATE_DIR.rglob("*")):
            rel = path.relative_to(TEMPLATE_DIR)
            if rel.parts[0] in _SKIP or path.is_symlink() or not (path.is_file() or path.is_dir()):
                continue
            t.add(path, arcname=rel.as_posix(), recursive=False, filter=_neutral)
    return buf.getvalue()


def _exec_args(name: str, step: Step) -> list[str]:
    if step.as_user:
        return ["exec", name, "--cwd", "/work", "--user", UID, "--group", UID, "--env", "HOME=/home/labor",
                "--", "bash", "-c", step.script]
    return ["exec", name, "--", "bash", "-c", step.script]


async def setup(project_id: str, report: Callable[[str], None], *, start_at: str = "") -> None:
    """Alle Schritte nacheinander. `report(key)` vor jedem Schritt. Ein Fehler beendet die Einrichtung sofort.
    `start_at`: ab diesem Schritt beginnen („Nochmal versuchen“ nach einem Fehler); unbekannter Name → Fehler."""
    name = container.name_for(project_id)
    keys = [s.key for s in STEPS]
    if start_at and start_at not in keys:
        raise SetupError("vibe_setup_failed", "")
    for step in STEPS[keys.index(start_at) if start_at else 0:]:
        report(step.key)
        stdin = template_tar() if step.key == "template" else None
        attempts = NET_ATTEMPTS if step.net else 1
        detail = ""
        for attempt in range(attempts):
            try:
                rc, out, err = await incus.run(*_exec_args(name, step), timeout=step.timeout, input_bytes=stdin)
            except IncusError as exc:                      # Zeitlimit oder incus nicht erreichbar: wie ein Fehlschlag
                rc, out, err = 1, "", str(exc)
            if rc == 0:
                break
            detail = _detail(out, err)
            if attempt < attempts - 1:
                logger.warning("Vibe: Schritt %s (Versuch %d/%d) fehlgeschlagen, neuer Versuch: %s", step.key,
                               attempt + 1, attempts, detail.splitlines()[-1] if detail else "")
                await asyncio.sleep(_PAUSES[min(attempt, len(_PAUSES) - 1)])
        else:
            raise SetupError("vibe_setup_failed", step.key, detail)
