"""L3 (PLAN-L3.md Bausteine 1, 2, 4, 6): Probe-HydraHive im Labor bauen, starten, stoppen.

- Bauen: `npm run build` im Labor als `labor`; Daten/Schlüssel/Admin-Passwort der Probe unter /work/.probe (nur beim
  ersten Mal erzeugt, 0600). Der Auslieferer (probe/front.py) kommt als root nach /opt/hh-labor-probe (der Labor-Agent
  kann ihn nicht verändern).
- Starten: zwei Dienste per `systemd-run` im Container, beide als `labor`; eigene Daten, nichts vom Server (incus exec
  reicht keine Server-Umgebung weiter). Erst wenn die Probe antwortet: eingehende Regel (probe_net) und nginx :8443
  (probe_site) – beide im Zustand vermerkt, damit Stoppen/Entfernen nur Eigenes abräumt.
- Stoppen: Dienste aus, nginx-Block und Regel weg.
Skripte sind fest im Modul, keine Eingaben des Nutzers darin.
"""
from __future__ import annotations

import ipaddress
import re
from collections.abc import Callable
from pathlib import Path

from . import container, incus, probe_net, probe_site, state
from .container import LaborError

Report = Callable[[str], None]
UID = "1000"
DIR = "/work/.probe"
FRONT = "/opt/hh-labor-probe/front.py"
DIST = "/work/hydrahive2/frontend/dist"
_PW = re.compile(r"^[A-Za-z0-9_-]{8,100}$")
_LOCAL_FRONT = Path(__file__).resolve().parent.parent / "probe" / "front.py"
_ENV = ("HH_DATA_DIR=/work/.probe/data", "HH_CONFIG_DIR=/work/.probe/config", "HH_BASE_DIR=/work/hydrahive2",
        "HH_DISCORD_ENABLED=0", "HH_WA_ENABLED=0", "HH_MAIL_ENABLED=0", "HH_TEAMCHAT_ENABLED=0",
        "HH_UPDATE_CHECK_ENABLED=0", "HH_AGENTLINK_URL=", "HH_MODULE_HUB_GIT_URL=/work/hydrahive2-modules")
_PREPARE = (
    f"set -eu; umask 077; install -d -m 700 {DIR} {DIR}/data {DIR}/config; "
    f"if ! [ -f {DIR}/env ]; then "
    f"k=$(head -c 32 /dev/urandom | base64 | tr -d '\\n/+='); p=$(head -c 18 /dev/urandom | base64 | tr -d '\\n/+='); "
    f"printf 'HH_SECRET_KEY=%s\\nHH_INITIAL_ADMIN_PASSWORD=%s\\n' \"$k\" \"$p\" > {DIR}/env; "
    f"printf '%s\\n' \"$p\" > {DIR}/admin-password; fi; chmod 600 {DIR}/env {DIR}/admin-password")
_BUILD = "set -eu; cd /work/hydrahive2/frontend; npm run build >/dev/null 2>&1"
_RUN = "systemd-run -q --collect --unit {unit} --uid 1000 --gid 1000 -p WorkingDirectory=/work -E HOME=/home/labor "
_START = (
    f"set -u; [ -f {DIST}/index.html ] && [ -f {DIR}/env ] && [ -f {FRONT} ] || exit 3; "
    "systemctl stop hh-probe-front hh-probe-back 2>/dev/null; "
    + _RUN.format(unit="hh-probe-back") + f"-p EnvironmentFile={DIR}/env " + " ".join(f"-E {kv}" for kv in _ENV)
    + " /work/.venv/bin/uvicorn hydrahive.api.main:app --host 127.0.0.1 --port 8002 && "
    + _RUN.format(unit="hh-probe-front") + f"/work/.venv/bin/python {FRONT} {DIST} http://127.0.0.1:8002 8001 || exit 4; "
    "for i in $(seq 60); do curl -fsS -o /dev/null http://127.0.0.1:8001/api/health && exit 0; sleep 1; done; exit 4")
_STOP = "systemctl stop hh-probe-front hh-probe-back 2>/dev/null; exit 0"
_STATUS = (f": hh-probe-status; [ -f {DIST}/index.html ] && echo built=1 || echo built=0; "
           "echo back=$(systemctl is-active hh-probe-back); echo front=$(systemctl is-active hh-probe-front); "
           f"[ -f {DIR}/admin-password ] && echo pw=$(head -n1 {DIR}/admin-password); exit 0")


def _data_dir() -> Path:
    from hydrahive.settings import settings
    return settings.data_dir / "hydralabor" / "probe"


async def _exec(script: str, *, as_user: bool, timeout: float = 120.0) -> tuple[int, str]:
    who = ["--cwd", "/work", "--user", UID, "--group", UID, "--env", "HOME=/home/labor"] if as_user else []
    rc, out, _ = await incus.run("exec", container.NAME, *who, "--", "bash", "-c", script, timeout=timeout)
    return rc, out


async def build(report: Report) -> None:
    report("probe_build")
    rc, _ = await _exec(_PREPARE, as_user=True)
    if rc == 0:
        rc, _ = await _exec(_BUILD, as_user=True, timeout=900)
    if rc == 0:
        rc, _, _ = await incus.run("file", "push", str(_LOCAL_FRONT), f"{container.NAME}{FRONT}", "--create-dirs",
                                   "--uid", "0", "--gid", "0", "--mode", "0644")
    if rc != 0:
        raise LaborError("labor_probe_build_failed")


async def _address() -> str:
    rc, out, _ = await incus.run("list", container.NAME, "--format", "csv", "-c", "n4")
    for line in out.splitlines() if rc == 0 else []:
        name, _, rest = line.partition(",")
        if name == container.NAME:
            ip = rest.strip().strip('"').split(" ")[0]
            try:
                if ipaddress.IPv4Address(ip).is_private and rest.strip().strip('"').endswith("(eth0)"):
                    return ip
            except ValueError:
                break
    raise LaborError("labor_probe_no_address")


async def start(report: Report) -> None:
    report("probe_start")
    ip = await _address()
    rc, _ = await _exec(_START, as_user=False, timeout=180)
    if rc == 3:
        raise LaborError("labor_probe_not_built")
    if rc != 0:
        await _exec(_STOP, as_user=False)
        raise LaborError("labor_probe_start_failed")
    await probe_net.open_port()
    state.mark_made("probe_net")
    if not probe_site.apply(ip, root=probe_site.root, data_dir=_data_dir()):
        raise LaborError("labor_probe_nginx_failed")
    state.mark_made("probe_site")


async def cleanup() -> None:
    """nginx-Block und eingehende Regel weg – nur was laut Zustand von uns ist. Auch wenn der Container fehlt."""
    made = state.get()["made"]
    if "probe_site" in made:
        probe_site.remove(root=probe_site.root, data_dir=_data_dir())
        state.unmark("probe_site")
    if "probe_net" in made:
        await probe_net.close_port()
        state.unmark("probe_net")


async def stop(report: Report) -> None:
    report("probe_stop")
    await _exec(_STOP, as_user=False)
    await cleanup()


async def status() -> dict:
    out = {"built": False, "running": False, "user": "admin", "password": "", "port": probe_site.PORT,
           "open": "probe_site" in state.get()["made"]}
    if not await container.running():
        return out
    rc, text = await _exec(_STATUS, as_user=False, timeout=30)
    kv = dict(line.split("=", 1) for line in text.splitlines() if "=" in line) if rc == 0 else {}
    out["built"] = kv.get("built") == "1"
    out["running"] = kv.get("back") == "active" and kv.get("front") == "active"
    pw = kv.get("pw", "")
    out["password"] = pw if _PW.match(pw) else ""
    return out
