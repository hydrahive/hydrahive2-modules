"""Vorprüfung vor dem Umstellen von Home – Google TV und andere Geräte mit Einrichtungs-Helfer.

Auf Google TV beansprucht neben dem Original auch der Einrichtungs-Helfer (setupwraith, `.RecoveryActivity`) Home.
Wird das Original abgeschaltet, kann Home dort landen und das System in eine Schleife bringen (cleanyourtv
launcher/build-and-install.sh, b953804). Deshalb wie dort: den Helfer abschalten, solange das Original noch Home ist,
und zurücklesen. Gehört ihm das gespeicherte WLAN, würde Android es beim Abschalten löschen (tools/disable.sh) –
dann wird nichts umgestellt. Entschieden wird nach dem, was das Gerät meldet, nicht nach Hersteller oder Modell.
"""
from __future__ import annotations

from . import device
from .install import TvwInstallError, _adb, _connect, home_line, stock

SETUP = "com.google.android.tungsten.setupwraith"
_CLAIMS_Q = "cmd package query-activities --brief -a android.intent.action.MAIN -c android.intent.category.HOME"
_MARK = "__TVW__"


def read_script(serial: str) -> str:
    """Nur lesen: wer Home beansprucht, wem gespeicherte WLANs gehören, ob überhaupt eines gespeichert ist."""
    return (_connect(serial)
            + f'echo "{_MARK} claims=$({_adb(serial, _CLAIMS_Q)} | tr -d \'\\r\' | grep -oE \'^ *[A-Za-z0-9_.]+/\' '
            + "| tr -d ' /' | sort -u | tr '\\n' ',')\"; "
            + f'echo "{_MARK} wifi_owners=$({_adb(serial, "dumpsys wifi")} | grep -oE \'cname=[A-Za-z0-9_.]+\' '
            + "| cut -d= -f2 | sort -u | tr '\\n' ',')\"; "
            + f'echo "{_MARK} wifi_none=$({_adb(serial, "cmd wifi list-networks")} 2>&1 | grep -c \'No networks\')"; '
            + home_line(serial))


def _list(raw: str) -> set[str]:
    return {p for p in raw.split(",") if p}


def plan(out: str, stock_pkg: str) -> list[str]:
    """Welche Pakete vor dem Umstellen abgeschaltet werden müssen ([] = nichts). Fehler → nichts wird umgestellt."""
    vals = device.parse(out)
    if vals.get("state") != "device":
        raise TvwInstallError("tvw_adb_unauthorized" if vals.get("state") == "unauthorized" else "tvw_adb_closed")
    if SETUP not in _list(vals.get("claims", "")):
        return []
    if vals.get("home", "").split("/", 1)[0] != stock(stock_pkg):
        raise TvwInstallError("tvw_guard_failed", f"Home: {vals.get('home') or '-'}")
    owners = _list(vals.get("wifi_owners", ""))
    if SETUP in owners:
        raise TvwInstallError("tvw_wifi_owned_by_setup")
    if not owners and vals.get("wifi_none") != "1":
        raise TvwInstallError("tvw_wifi_unreadable")
    return [SETUP]


def disable_script(serial: str, pkgs: list[str]) -> str:
    """Helfer abschalten, solange das Original Home ist; danach zurücklesen, wer Home ist."""
    cmds = "".join(_adb(serial, f"pm disable-user --user 0 {_known(p)}") + "; " for p in pkgs)
    return _connect(serial) + cmds + home_line(serial)


def _known(pkg: str) -> str:
    if pkg != SETUP:                                   # nur, was diese Vorprüfung selbst vorgeschlagen hat
        raise TvwInstallError("tvw_guard_failed", pkg[:80])
    return pkg


def extras(raw: str) -> list[str]:
    """Gemerkte Zusatz-Abschaltungen aus der Datenbank – nur bekannte Pakete, sonst gar keine."""
    return [p for p in raw.split(",") if p == SETUP]
