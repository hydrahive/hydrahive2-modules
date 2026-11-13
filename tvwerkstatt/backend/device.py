"""Fernseher eintragen und prüfen (PLAN-E1.md Baustein 5).

adb läuft nur im Container (Google platform-tools aus der Einrichtung), nie auf dem Server. Geprüft wird nur lesend:
`getprop` und welche App Home ist. Gerätart und Original-Startbildschirm werden vom Gerät gelesen, nicht angenommen.
Adresse und Port stehen nur geprüft in den Skripten (IPv4 im Heimnetz, Port als Zahl), nie freier Text.
"""
from __future__ import annotations

import re

from . import incus, netrules

ADB = "/home/ubuntu/android-sdk/platform-tools/adb"
MIN_SDK = 26                                   # minSdk des Startbildschirms (com.gathin.tvhome)
MAX_NAME = 60
# Bekannte Original-Startbildschirme (Liste wie cleanyourtv launcher/build-and-install.sh, Stand b953804).
STOCK_HOMES = ("com.google.android.tvlauncher", "com.google.android.apps.tv.launcherx",
               "com.google.android.leanbacklauncher", "com.mitv.tvhome")
OUR_HOME = "com.gathin.tvhome"
_PKG = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)+$")
_PROPS = ("ro.product.model", "ro.product.manufacturer", "ro.build.version.release", "ro.build.version.sdk",
          "ro.build.display.id", "ro.build.characteristics")
_HOME_QUERY = "cmd package resolve-activity --brief -a android.intent.action.MAIN -c android.intent.category.HOME"
_MARK = "__TVW__"


class TvwDeviceError(RuntimeError):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(code)
        self.code = code
        self.detail = detail


def clean_name(name: str) -> str:
    raw = str(name or "")
    if any(ord(c) < 32 or ord(c) == 127 for c in raw):      # vor dem Zusammenziehen, sonst wird \n zu Leerzeichen
        raise TvwDeviceError("tvw_bad_name")
    n = " ".join(raw.split())
    if not n or len(n) > MAX_NAME:
        raise TvwDeviceError("tvw_bad_name")
    return n


def target(address: str, port: int, host_addresses: set[str]) -> str:
    """`a.b.c.d:port` – nur nach der gleichen Prüfung wie für die Sperrliste."""
    try:
        ip = netrules.check_tv(address, port, host_addresses)
    except netrules.TvwNetworkError:
        raise TvwDeviceError("tvw_bad_address") from None
    return f"{ip}:{port}"


def probe_script(serial: str) -> str:
    """Verbinden, Zustand und Eigenschaften lesen. Ausgabe in festen Zeilen `__TVW__ key=value`."""
    props = "; ".join(f'echo "{_MARK} {p}=$({ADB} -s {serial} shell getprop {p} | tr -d \'\\r\')"' for p in _PROPS)
    return (f"{ADB} start-server >/dev/null 2>&1; "
            f"{ADB} connect {serial} >/dev/null 2>&1; "
            f'st=$({ADB} devices | awk -v s="{serial}" \'$1 == s {{print $2}}\' | head -n 1); '
            f'echo "{_MARK} state=${{st:-offline}}"; '
            f'[ "$st" = device ] || exit 0; {props}; '
            f'echo "{_MARK} home=$({ADB} -s {serial} shell {_HOME_QUERY} | tail -n 1 | tr -d \'\\r\' | cut -d/ -f1)"; '
            f'echo "{_MARK} has_stock_tv=$({ADB} -s {serial} shell pm path com.google.android.tvlauncher | head -n 1 '
            f"| cut -c1-8)\"")


def parse(out: str) -> dict[str, str]:
    vals: dict[str, str] = {}
    for line in out.splitlines():
        if line.startswith(_MARK + " ") and "=" in line:
            k, v = line[len(_MARK) + 1:].split("=", 1)
            vals[k.strip()] = v.strip()[:200]
    return vals


def state_from_devices(out: str, serial: str) -> str:
    """Zustand dieser Adresse aus `adb devices` (Python-Gegenstück zum awk im Skript, für Tests und Prüfungen)."""
    for line in out.splitlines():
        cols = line.split()
        if len(cols) >= 2 and cols[0] == serial:
            return cols[1]
    return "offline"


def _state_of(raw: str) -> str:
    if raw == "device":
        return "open"
    if "unauthorized" in raw:
        return "unauthorized"
    return "closed"


def evaluate(vals: dict[str, str], *, stock_before: str = "") -> dict:
    """Aus den gelesenen Werten die Felder fürs Gerät. Kein `state` → Probe kaputt."""
    if "state" not in vals:
        raise TvwDeviceError("tvw_device_probe_failed")
    adb_state = _state_of(vals["state"])
    if adb_state != "open":
        return {"adb_state": adb_state}
    try:
        sdk = int(vals.get("ro.build.version.sdk", ""))
    except ValueError:
        raise TvwDeviceError("tvw_device_probe_failed") from None
    home = vals.get("home", "")
    home = home if _PKG.match(home) else ""
    if home in STOCK_HOMES:
        stock = home
    elif stock_before:
        stock = stock_before                    # unser Startbildschirm ist Home: das gemerkte Original bleibt
    elif home == OUR_HOME and vals.get("has_stock_tv") == "package:":
        stock = "com.google.android.tvlauncher"  # Sony im Probelauf umgestellt: Original noch installiert (abgeschaltet)
    else:
        stock = ""
    kind = "google_tv" if stock == "com.google.android.apps.tv.launcherx" else (
        "android_tv" if stock else "")
    model = vals.get("ro.product.model", "")
    maker = vals.get("ro.product.manufacturer", "")
    return {"adb_state": "open", "model": f"{maker} {model}".strip() if maker and maker not in model else model,
            "android": vals.get("ro.build.version.release", ""), "sdk": sdk,
            "build": vals.get("ro.build.display.id", ""), "stock_home": stock, "current_home": home, "kind": kind,
            "too_old": sdk < MIN_SDK}


async def probe(container: str, serial: str) -> dict[str, str]:
    rc, out, err = await incus.run("exec", container, "--user", "1000", "--group", "1000", "--env",
                                   "HOME=/home/ubuntu", "--", "bash", "-c", probe_script(serial), timeout=90)
    if rc != 0:
        raise TvwDeviceError("tvw_device_probe_failed", (err or out)[-300:])
    return parse(out)
