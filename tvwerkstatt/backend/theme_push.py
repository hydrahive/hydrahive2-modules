"""Aussehen auf den Fernseher schieben – wie cleanyourtv tools/theme.sh (b953804), ohne dessen Skript auszuführen.

Ordner im Container: config.json und wallpapers/*.jpg (vom Server geschrieben, nur geprüfte Namen). Je Datei:
per adb nach /data/local/tmp, dann über den ThemeProvider (content write) oder als Kopie in den Ordner der App,
Größe zurücklesen. Danach theme_revision schreiben und Home neu starten. Bilder, die vorher dort lagen, werden geleert,
damit nichts Altes stehen bleibt.
"""
from __future__ import annotations

import re
import shlex
import uuid

from . import device

PKG = "com.gathin.tvhome"
DIR = f"/sdcard/Android/data/{PKG}/files"
URI = f"content://{PKG}.theme"
STAGE = "/home/ubuntu/theme"
TMP = "/data/local/tmp/tvw-theme"
_NAME = re.compile(r"^(config\.json|wallpapers/[a-z0-9-]{1,40}\.jpg)$")
_MARK = "__TVW__"
NOT_WRITTEN = "tvw-not-written"


def _put(rel: str) -> str:
    """Shell-Zeile auf dem Fernseher: aus dem Zwischenstand schreiben und die Größe prüfen (wie theme.sh put())."""
    stage = f"{TMP}-{rel.replace('/', '-')}"
    return (f"rm -f {DIR}/{rel} 2>/dev/null; w=; "
            f"{{ o=$(content write --uri {URI}/{rel} < {stage} 2>&1) && case \"$o\" in *'Unsupported operation'*|"
            f"*'Error while accessing provider'*) false ;; esac && w=1; }} || "
            f"{{ mkdir -p $(dirname {DIR}/{rel}) 2>/dev/null; cp {stage} {DIR}/{rel} 2>/dev/null && w=1; }}; "
            f"s=$(wc -c < {stage}); rm -f {stage}; "
            f"[ -n \"$w\" ] && {{ {{ [ -e {DIR}/{rel} ] && [ \"$(wc -c < {DIR}/{rel})\" = \"$s\" ]; }} || "
            f"[ \"$(content read --uri {URI}/{rel} 2>/dev/null | wc -c)\" = \"$s\" ]; }} || echo {NOT_WRITTEN} {rel}")


def push_script(serial: str, files: list[str], revision: str | None = None) -> str:
    """Alle Dateien schieben, alte Bilder leeren, Revision setzen, Home neu starten, Home zurücklesen."""
    if not files or files[0] != "config.json" or not all(_NAME.match(f) for f in files):
        raise ValueError("ungültige Dateiliste")
    rev = revision or uuid.uuid4().hex
    a = f"{device.ADB} -s {serial}"
    sh = lambda cmd: f"{a} shell {shlex.quote(cmd)}"          # noqa: E731
    clear = (f"mkdir -p {DIR} 2>/dev/null; rm -f {DIR}/wallpaper.jpg {DIR}/wallpapers/*.jpg {DIR}/wallpapers/*.png "
             f"{DIR}/wallpapers/*.webp 2>/dev/null; content delete --uri {URI}/wallpaper.jpg 2>/dev/null; "
             f"content delete --uri {URI}/wallpapers 2>/dev/null; true")
    parts = [f"{device.ADB} connect {serial} >/dev/null 2>&1",
             f'st=$({device.ADB} devices | awk -v s="{serial}" \'$1 == s {{print $2}}\' | head -n 1)',
             f'echo "{_MARK} state=${{st:-offline}}"', '[ "$st" = device ] || exit 0', sh(clear) + " >/dev/null"]
    for rel in files:
        parts.append(f"{a} push {STAGE}/{rel} {TMP}-{rel.replace('/', '-')} >/dev/null")
        parts.append(sh(_put(rel)))
    parts.append(sh(f"printf '%s' '{rev}' > {TMP}-theme_revision; " + _put("theme_revision")))
    home_q = "cmd package resolve-activity --brief -a android.intent.action.MAIN -c android.intent.category.HOME"
    restart = (f"am force-stop {PKG}; h=$({home_q} | tail -n 1); case \"$h\" in {PKG}/*) "
               f"am start -a android.intent.action.MAIN -c android.intent.category.HOME ;; "
               f"*) am start -n {PKG}/.MainActivity ;; "
               f"esac >/dev/null 2>&1; echo {_MARK} restarted")
    parts.append(sh(restart))
    return "; ".join(parts)


def check(out: str) -> list[str]:
    """Fehlende Dateien (leer = alles geschrieben). Wirft nichts, die Aufrufer werten aus."""
    return [ln.split(" ", 1)[1].strip() for ln in out.splitlines() if ln.startswith(NOT_WRITTEN + " ")]


def reset_script(serial: str) -> str:
    """Theme vom Fernseher nehmen – Startbildschirm zeigt wieder sein eingebautes Aussehen."""
    a = f"{device.ADB} -s {serial}"
    rm = (f"rm -f {DIR}/config.json {DIR}/wallpaper.jpg {DIR}/wallpapers/* 2>/dev/null; "
          f"content delete --uri {URI}/config.json 2>/dev/null; content delete --uri {URI}/wallpapers 2>/dev/null; "
          f"am force-stop {PKG}; am start -a android.intent.action.MAIN -c android.intent.category.HOME >/dev/null 2>&1; "
          f"echo {_MARK} restarted")
    return (f"{device.ADB} connect {serial} >/dev/null 2>&1; "
            f'st=$({device.ADB} devices | awk -v s="{serial}" \'$1 == s {{print $2}}\' | head -n 1); '
            f'echo "{_MARK} state=${{st:-offline}}"; [ "$st" = device ] || exit 0; {a} shell {shlex.quote(rm)}')
