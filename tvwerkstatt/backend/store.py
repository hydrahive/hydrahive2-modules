"""App-Verwaltung: selbst installierte Apps lesen, Play Store am Fernseher öffnen oder suchen, deinstallieren.

Lesen: `pm list packages -3` und je App Version, Herkunft (installerPackageName) und Zustand – nur lesend.
Play Store: ein VIEW-Aufruf `market://details?id=…` bzw. `market://search?q=…`, fest an com.android.vending. Installiert
wird am Fernseher, nicht hier (Google lässt stilles Installieren aus dem Store nicht zu).
Deinstallieren: nur eine App, die der Fernseher selbst als nachinstalliert meldet (Prüfung im Skript auf dem Gerät),
nie den Startbildschirm der Werkstatt und nie das gemerkte Original. Vorinstalliertes gehört zu „Entrümpeln“.
"""
from __future__ import annotations

import re
import shlex
from urllib.parse import quote

from . import debloat, device, install

STORE = "com.android.vending"
_MARK = "__TVW__"
_QUERY = re.compile(r"^[\w .,&'+\-]{1,60}$", re.UNICODE)
_FIELD = re.compile(r"^[A-Za-z0-9._+\- ]{0,80}$")


class TvwStoreError(install.TvwInstallError):
    pass


def package(p: str) -> str:
    if not isinstance(p, str) or not debloat._PKG.fullmatch(p) or len(p) > 150:
        raise TvwStoreError("tvw_store_bad_package", str(p)[:80])
    return p


def query(q: str) -> str:
    """Suchtext: Buchstaben, Ziffern, Leerzeichen und . , & ' + -, höchstens 60 Zeichen. Zurück kommt er kodiert."""
    raw = str(q or "")
    if any(ord(c) < 32 or ord(c) == 127 for c in raw):        # vor dem Zusammenziehen, sonst wird \n zu Leerzeichen
        raise TvwStoreError("tvw_store_bad_query")
    q = " ".join(raw.split())
    if not _QUERY.fullmatch(q):
        raise TvwStoreError("tvw_store_bad_query")
    return quote(q, safe="")


def _sh(serial: str, remote: str) -> str:
    return f"{device.ADB} -s {serial} shell {shlex.quote(remote)}"


def list_script(serial: str) -> str:
    loop = ('for p in $(pm list packages -3 | sed "s/^package://"); do d=$(dumpsys package $p); '
            'vn=$(printf "%s\\n" "$d" | grep -m1 "versionName=" | sed "s/.*versionName=//"); '
            'vc=$(printf "%s\\n" "$d" | grep -m1 -o "versionCode=[0-9]*" | cut -d= -f2); '
            'ins=$(printf "%s\\n" "$d" | grep -m1 -o "installerPackageName=[A-Za-z0-9_.]*" | cut -d= -f2); '
            'en=$(printf "%s\\n" "$d" | grep -m1 -o " enabled=[0-9]" | cut -d= -f2); '
            f'echo "{_MARK} app|$p|$vc|$vn|$ins|$en"; done')
    return install._connect(serial) + _sh(serial, loop) + " | tr -d '\\r'"


def parse_list(out: str) -> list[dict]:
    install.require_open(out)
    apps = []
    for line in out.splitlines():
        if not line.startswith(f"{_MARK} app|"):
            continue
        parts = line[len(_MARK) + 5:].split("|")
        if len(parts) != 5 or not debloat._PKG.fullmatch(parts[0]):
            continue
        p, vc, vn, ins, en = parts
        apps.append({"package": p, "version_code": vc if vc.isdigit() else "",
                     "version_name": vn[:40] if _FIELD.fullmatch(vn) else "",
                     "installer": ins if debloat._PKG.fullmatch(ins) else "",
                     "enabled": en not in ("2", "3", "4")})
    return sorted(apps, key=lambda a: a["package"])


def open_script(serial: str, pkg: str) -> str:
    url = f"market://details?id={package(pkg)}"
    return install._connect(serial) + _sh(serial, f"am start -a android.intent.action.VIEW -d '{url}' -p {STORE}")


def search_script(serial: str, q: str) -> str:
    url = f"market://search?q={query(q)}"
    return install._connect(serial) + _sh(serial, f"am start -a android.intent.action.VIEW -d '{url}' -p {STORE}")


def started(out: str) -> None:
    """„Starting: Intent“ ohne „Error“. Die Warnung „delivered to currently running top-most instance“ ist ok:
    der Store war schon vorn und hat den Aufruf trotzdem bekommen (Sony, 13.11.)."""
    install.require_open(out)
    if "Starting: Intent" not in out or any(ln.strip().startswith("Error") for ln in out.splitlines()):
        raise TvwStoreError("tvw_store_failed", install.build.clean_log(out)[-200:])


def protected(pkg: str, stock: str) -> bool:
    return pkg in (install.OUR, stock, STORE) or debloat.is_core(pkg)


def uninstall_script(serial: str, pkg: str) -> str:
    """Nur wenn der Fernseher die App als nachinstalliert führt; danach zurücklesen, ob sie weg ist."""
    p = package(pkg)
    remote = (f'pm list packages -3 | grep -qx "package:{p}" || {{ echo "{_MARK} not_user"; exit 0; }}; '
              f'pm uninstall {p}; pm list packages | grep -qx "package:{p}" && echo "{_MARK} still" '
              f'|| echo "{_MARK} gone"')
    return install._connect(serial) + _sh(serial, remote)


def uninstalled(out: str) -> None:
    install.require_open(out)
    if f"{_MARK} not_user" in out:
        raise TvwStoreError("tvw_store_not_user_app")
    if f"{_MARK} gone" not in out:
        raise TvwStoreError("tvw_store_failed", install.build.clean_log(out)[-200:])
