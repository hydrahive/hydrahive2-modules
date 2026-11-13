"""Startbildschirm aufspielen und zurück zum Original – Skripte und Auswertung (PLAN-E1.md Baustein 6).

Reihenfolge wie cleanyourtv launcher/build-and-install.sh (b953804), im Probelauf am Sony erprobt:
aufspielen → neuen Startbildschirm starten (erst dann am Original etwas ändern) → Original abschalten, Home setzen →
zurücklesen, wer Home ist → sonst sofort zurück zum Original. Pakete werden nur abgeschaltet, nie deinstalliert.
Alle Befehle sind feste Texte; Adresse und Paketnamen kommen nur geprüft hinein.
"""
from __future__ import annotations

import re
import shlex

from . import build, device

OUR = device.OUR_HOME
OUR_ACTIVITY = f"{OUR}/.MainActivity"
_PKG = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)+$")
_TMP = "/data/local/tmp/tvhome.apk"
_HOME_Q = "cmd package resolve-activity --brief -a android.intent.action.MAIN -c android.intent.category.HOME"
_SECURE = "android.permission.WRITE_SECURE_SETTINGS"
_MARK = "__TVW__"


class TvwInstallError(RuntimeError):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(code)
        self.code = code
        self.detail = detail


def stock(pkg: str) -> str:
    """Nur bekannte Original-Startbildschirme werden abgeschaltet oder zurückgeholt."""
    if pkg not in device.STOCK_HOMES or not _PKG.match(pkg):
        raise TvwInstallError("tvw_no_stock_home")
    return pkg


def _adb(serial: str, remote: str) -> str:
    return f"{device.ADB} -s {serial} shell {shlex.quote(remote)}"


def _connect(serial: str) -> str:
    """Verbinden und Zustand ausgeben – ohne Freigabe kein weiterer Befehl."""
    return (f"{device.ADB} start-server >/dev/null 2>&1; {device.ADB} connect {serial} >/dev/null 2>&1; "
            f'st=$({device.ADB} devices | awk -v s="{serial}" \'$1 == s {{print $2}}\' | head -n 1); '
            f'echo "{_MARK} state=${{st:-offline}}"; [ "$st" = device ] || exit 0; ')


def push_script(serial: str) -> str:
    return (_connect(serial) + f"{device.ADB} -s {serial} push {build.APK} {_TMP} >/dev/null && "
            + _adb(serial, f"pm install -r {_TMP}; rm -f {_TMP}"))


def start_script(serial: str) -> str:
    """Laufenden Startbildschirm stoppen (Tastenhelfer bleiben, wie sie waren), dann als Home starten."""
    keep = ('s=$(settings get secure enabled_accessibility_services); a=$(settings get secure accessibility_enabled); '
            f'am force-stop {OUR}; case "$s" in *{OUR}*) settings put secure enabled_accessibility_services ""; '
            'settings put secure enabled_accessibility_services "$s"; settings put secure accessibility_enabled "$a" ;; '
            'esac')
    return (_connect(serial) + _adb(serial, keep) + " >/dev/null; "
            + _adb(serial, f"am start -W -a android.intent.action.MAIN -c android.intent.category.HOME -n {OUR_ACTIVITY}"))


def switch_script(serial: str, stock_pkg: str) -> str:
    s = stock(stock_pkg)
    return (_connect(serial)
            + _adb(serial, f"pm grant {OUR} android.permission.ACCESS_FINE_LOCATION") + " >/dev/null 2>&1; "
            + _adb(serial, f"cmd package compile -m speed -f {OUR}") + " >/dev/null 2>&1; "
            + _adb(serial, f"pm disable-user --user 0 {s}") + "; "
            + _adb(serial, f"cmd package set-home-activity --user 0 {OUR_ACTIVITY}") + "; "
            + _adb(serial, f"pm revoke {OUR} {_SECURE}") + " >/dev/null 2>&1; "
            + home_line(serial))


def restore_script(serial: str, stock_pkg: str) -> str:
    """Original einschalten und als Home setzen (Android 9 braucht Paket/Aktivität → auf dem Gerät auflösen)."""
    s = stock(stock_pkg)
    return (_connect(serial) + _adb(serial, f"pm enable --user 0 {s}") + "; "
            + _adb(serial, f"cmd package set-home-activity --user 0 $({_HOME_Q} {s} | tail -n 1)") + "; "
            + home_line(serial))


def home_line(serial: str) -> str:
    return f'echo "{_MARK} home=$({_adb(serial, _HOME_Q)} | tail -n 1 | tr -d \'\\r\')"'


def state_of(out: str) -> str:
    st = device.parse(out).get("state", "")
    return {"device": "open", "unauthorized": "unauthorized"}.get(st, "closed")


def require_open(out: str) -> None:
    st = state_of(out)
    if st == "unauthorized":
        raise TvwInstallError("tvw_adb_unauthorized")
    if st != "open":
        raise TvwInstallError("tvw_adb_closed")


def check_installed(out: str) -> None:
    require_open(out)
    if "Success" not in out:
        m = re.search(r"INSTALL_FAILED_[A-Z_]+", out)
        raise TvwInstallError("tvw_install_failed", m.group(0) if m else build.clean_log(out)[-300:])


def check_started(out: str) -> None:
    require_open(out)
    if "Status: ok" not in out or any(ln.strip().startswith("Error") for ln in out.splitlines()):
        raise TvwInstallError("tvw_home_not_started", build.clean_log(out)[-300:])


def home_of(out: str) -> str:
    """Paket, dem Home gehört (aus `__TVW__ home=pkg/.Activity`), sonst leer."""
    pkg = device.parse(out).get("home", "").split("/", 1)[0]
    return pkg if _PKG.match(pkg) else ""
