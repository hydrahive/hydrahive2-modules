"""Entrümpeln Teil 2: Pakete ab- und wieder einschalten – Skripte, Schutzprüfung am Gerät, Auswertung.

Nur `pm disable-user --user 0` und `pm enable --user 0`, nie deinstallieren. Vor jedem Abschalten liest der Fernseher
selbst, was nicht weg darf (wie cleanyourtv tools/disable.sh, b953804):
- Pakete mit android.permission.TV_INPUT_HARDWARE: die Schicht unter HDMI/AV/Tuner. Ohne sie bleiben die Eingänge
  schwarz, und nur eine volle Wiederherstellung plus Kaltstart hilft (#321). Nicht lesbar → gilt als geschützt.
- Apps, mit denen der Fernseher seine Eingänge oder die Einstellungen öffnet (Rückweg zu den Entwickleroptionen).
- Android selbst, Startbildschirm, Original und Einrichtungs-Helfer (backend/debloat.py).
Abgeschaltet wird in Schüben; nach jedem Schub muss Home noch derselbe sein, sonst sofort zurück.
"""
from __future__ import annotations

from . import debloat, device, install

_MARK = "__TVW__"
BATCH = 4
MAX_PER_JOB = 40
_Q = "cmd package query-activities --brief"


class TvwDebloatError(install.TvwInstallError):
    pass


def clean(pkgs: list[str], stock: str) -> list[str]:
    """Gültige, nicht gesperrte Namen, ohne Doppelte, in Reihenfolge. Zu viele → Fehler."""
    out: list[str] = []
    for p in pkgs:
        if not isinstance(p, str):
            raise TvwDebloatError("tvw_debloat_bad_package", str(p)[:80])
        if debloat.protected(p, stock):                # zuerst: auch „android“ (ohne Punkt) heißt gesperrt
            raise TvwDebloatError("tvw_debloat_locked", p)
        if not debloat._PKG.fullmatch(p):
            raise TvwDebloatError("tvw_debloat_bad_package", p[:80])
        if p not in out:
            out.append(p)
    if not out or len(out) > MAX_PER_JOB:
        raise TvwDebloatError("tvw_debloat_bad_package", f"{len(out)} Pakete")
    return out


def guard_script(serial: str, pkgs: list[str]) -> str:
    """Nur lesen: je Paket ob es TV_INPUT_HARDWARE anfragt (hw/ok/nochk/hung), Handler für Eingänge/Einstellungen."""
    a = f"{device.ADB} -s {serial} shell"
    names = " ".join(pkgs)                              # geprüft durch clean(), kein freier Text
    loop = ("for p in " + names + "; do d=$(dumpsys package $p 2>/dev/null); case \"$d\" in "
            "*'hung system process'*) echo \"" + _MARK + " hw $p hung\";; "
            "*'requested permissions:'*) if printf '%s\\n' \"$d\" | sed -n -E '/requested permissions:/,"
            "/(install|runtime) permissions:|User [0-9]+:/p' | grep -q TV_INPUT_HARDWARE; "
            "then echo \"" + _MARK + " hw $p hw\"; else echo \"" + _MARK + " hw $p ok\"; fi;; "
            "*\"Package [$p]\"*) echo \"" + _MARK + " hw $p ok\";; "
            "*) echo \"" + _MARK + " hw $p nochk\";; esac; done")
    return (install._connect(serial)
            + f"{a} {_shq(loop)} | tr -d '\\r'; "
            + f"{a} {_shq(_Q + ' -a android.intent.action.VIEW -t vnd.android.cursor.item/channel')} | tr -d '\\r' "
            + f"| sed -n -E 's#^[[:space:]]*([A-Za-z0-9_.]+)/.*#{_MARK} handler \\1#p'; "
            + f"{a} {_shq(_Q + ' -a android.settings.SETTINGS')} | tr -d '\\r' "
            + f"| sed -n -E 's#^[[:space:]]*([A-Za-z0-9_.]+)/.*#{_MARK} handler \\1#p'; "
            + install.home_line(serial))


def _shq(s: str) -> str:
    import shlex
    return shlex.quote(s)


def blocked(out: str, pkgs: list[str]) -> dict[str, str]:
    """{paket: grund} für alles, was am Gerät nicht abgeschaltet werden darf. Fehlende Antwort zählt als geschützt."""
    install.require_open(out)
    hw: dict[str, str] = {}
    handlers: set[str] = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 4 and parts[:2] == [_MARK, "hw"]:
            hw[parts[2]] = parts[3]
        elif len(parts) == 3 and parts[:2] == [_MARK, "handler"]:
            handlers.add(parts[2])
    why: dict[str, str] = {}
    for p in pkgs:
        state = hw.get(p, "nochk")
        if state != "ok":
            why[p] = "inputs" if state == "hw" else "unchecked"
        elif p in handlers:
            why[p] = "handler"
    return why


def switch_script(serial: str, pkgs: list[str], *, on: bool) -> str:
    """Ein Schub: Pakete ab- (oder ein-)schalten, dann Stand dieser Pakete und Home zurücklesen."""
    a = f"{device.ADB} -s {serial} shell"
    verb = "pm enable --user 0" if on else "pm disable-user --user 0"
    cmds = "".join(f"{a} {verb} {p} >/dev/null 2>&1; " for p in pkgs if debloat._PKG.fullmatch(p))
    return (install._connect(serial) + cmds
            + f"{a} pm list packages -d | tr -d '\\r' | sed 's/^package:/{_MARK} off /'; "
            + install.home_line(serial))


def read_back(out: str) -> tuple[set[str], str]:
    """(abgeschaltete Pakete, Home-Paket) aus einem Schub."""
    install.require_open(out)
    off = {ln.split()[2] for ln in out.splitlines()
           if len(ln.split()) == 3 and ln.split()[:2] == [_MARK, "off"] and debloat._PKG.fullmatch(ln.split()[2])}
    return off, install.home_of(out)


def batches(pkgs: list[str]) -> list[list[str]]:
    return [pkgs[i:i + BATCH] for i in range(0, len(pkgs), BATCH)]
