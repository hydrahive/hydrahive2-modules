"""Bau des Startbildschirms im Container: Skripte und Auswertung (PLAN-E1.md Baustein 4).

Gradle führt Bau-Skripte des Repos als Code aus – darum nur im Container, als Nutzer ohne sudo, im abgeschotteten Netz.
Nach dem Bau wird die App gelesen: Prüfsumme, Größe, Paket und Version (aapt2), Signatur (apksigner) gegen den
Signierschlüssel des Containers. Passt die Signatur nicht, ließe sie sich auf dem Fernseher nicht als Update einspielen.
"""
from __future__ import annotations

import re

from . import source

SDK = f"{source.HOME}/android-sdk"
BT = f"{SDK}/build-tools/34.0.0"
APK = f"{source.SRC}/launcher/app/build/outputs/apk/release/app-release.apk"
LOG = f"{source.HOME}/build-logs/launcher.log"
LOG_LINES = 60
MAX_LOG = 6000
_MARK = "__TVW__"
_CTRL = re.compile(r"\x1b\[[0-9;]*[A-Za-z]|[\x00-\x08\x0b-\x1f\x7f]")
_BADGING = re.compile(r"name='(?P<pkg>[^']+)' versionCode='(?P<code>\d+)' versionName='(?P<name>[^']*)'")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")

BUILD_SCRIPT = (
    f"set -u; cd {source.SRC}/launcher; mkdir -p {source.HOME}/build-logs; "
    f"export ANDROID_HOME={SDK} ANDROID_SDK_ROOT={SDK} GRADLE_USER_HOME={source.HOME}/.gradle; "
    f"sh ./gradlew --no-daemon --console=plain assembleRelease > {LOG} 2>&1; rc=$?; "
    f"tail -n {LOG_LINES} {LOG}; exit $rc"
)

COLLECT_SCRIPT = (
    f"set -eu; A={APK}; test -f \"$A\"; "
    f'echo "{_MARK} sha256=$(sha256sum "$A" | cut -d" " -f1)"; '
    f'echo "{_MARK} size=$(stat -c %s "$A")"; '
    f'echo "{_MARK} badging=$({BT}/aapt2 dump badging "$A" | head -n 1)"; '
    f'echo "{_MARK} signer=$({BT}/apksigner verify --print-certs "$A" | grep -m1 "certificate SHA-256 digest" '
    f"| awk '{{print $NF}}')\"; "
    f'echo "{_MARK} keystore=$(keytool -list -v -keystore {source.HOME}/.android/debug.keystore -storepass android '
    f"2>/dev/null | grep -m1 'SHA256:' | awk '{{print $NF}}' | tr -d : | tr A-F a-f)\""
)


class TvwBuildError(RuntimeError):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(code)
        self.code = code
        self.detail = detail


def clean_log(text: str) -> str:
    """Protokoll ohne Farbfolgen und Steuerzeichen, ohne Containernamen, höchstens MAX_LOG Zeichen (das Ende zählt)."""
    t = _CTRL.sub("", text or "").replace("hh-tvwerkstatt", "")
    lines = [ln.rstrip() for ln in t.splitlines()]
    out = "\n".join(lines[-LOG_LINES:]).strip()
    return out if len(out) <= MAX_LOG else "…" + out[-(MAX_LOG - 1):]


def parse(out: str) -> dict[str, str]:
    vals: dict[str, str] = {}
    for line in out.splitlines():
        if line.startswith(_MARK + " ") and "=" in line:
            k, v = line[len(_MARK) + 1:].split("=", 1)
            vals[k.strip()] = v.strip()[:400]
    return vals


def evaluate(vals: dict[str, str]) -> dict:
    """Werte der gebauten App prüfen. Falsches Paket oder fremde Signatur → Fehlercode."""
    sha, signer, key = vals.get("sha256", ""), vals.get("signer", "").lower(), vals.get("keystore", "").lower()
    m = _BADGING.search(vals.get("badging", ""))
    if not _HEX64.match(sha) or not m or not vals.get("size", "").isdigit():
        raise TvwBuildError("tvw_build_unreadable")
    if m["pkg"] != source.PACKAGE:
        raise TvwBuildError("tvw_build_unexpected", m["pkg"])
    if not _HEX64.match(signer) or signer != key:
        raise TvwBuildError("tvw_signer_mismatch")
    return {"sha256": sha, "size": int(vals["size"]), "package": m["pkg"],
            "version": f"{m['name']} ({m['code']})", "signer": signer}
