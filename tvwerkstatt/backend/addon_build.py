"""Zusätze bauen und installieren – Skripte und Auswertung. Fremder Code läuft nur im Container (SPEC Entscheidung 1).

Bau: `./gradlew assembleRelease` im Ordner des Zusatzes. Vorher wird geprüft, dass der Gradle-Wrapper (eigener oder der
des Startbildschirms, 8 Zusätze rufen `../../launcher/gradlew`) zu den Prüfsummen von gradle.org passt und die
Distribution festgenagelt ist. Installationsskripte der Zusätze laufen nicht (SPEC Entscheidung 4): die Werkstatt
installiert die gebaute App selbst (`pm install -r`) und gibt keine Sonderrechte. Was ein Zusatz danach braucht
(Bildschirmschoner wählen, Rechte per ADB), zeigt der Katalog als Hinweis aus der README.
"""
from __future__ import annotations

import re

from . import addons, build, device, install, source

# Gradle laut gradle.org (gelesen 13.11.2026): Wrapper-Jar und Distribution je Version.
GRADLE = {
    "8.9": ("498495120a03b9a6ab5d155f5de3c8f0d986a449153702fb80fc80e134484f17",
            "d725d707bfabd4dfdc958c624003b3c80accc03f7037b5122c4b1d0ef15cecab"),
    "8.11.1": ("2db75c40782f5e8ba1fc278a5574bab070adccb2d21ca5a6e5ed840888448046",
               "f397b287023acdba1e9f6fc5ea72d22dd63669d59ed4a289a29b1a76eee151c6"),
}
_MARK = "__TVW__"
_TMP = "/data/local/tmp/tvw-addon.apk"


def folder(addon_id: str) -> str:
    if not addons._ID.match(addon_id or ""):
        raise addons.TvwAddonError("tvw_addon_unknown", str(addon_id)[:40])
    return f"{source.SRC}/addons/{addon_id}"


def apk(addon_id: str) -> str:
    return f"{folder(addon_id)}/app/build/outputs/apk/release/app-release.apk"


def verify_script(addon_id: str) -> str:
    """Wrapper finden (eigener oder ../../launcher), Version lesen, Jar und Distribution gegen GRADLE prüfen."""
    d = folder(addon_id)
    cases = " ".join(f'{v}) want_dist={dist};;' for v, (_, dist) in GRADLE.items())
    jars = "|".join(j for j, _ in GRADLE.values())            # Wrapper-Jar ist versionsunabhängig (tv-hub: 8.9-Jar)
    return (f"set -eu; cd {d}; w=gradle/wrapper; "
            f'if [ ! -f $w/gradle-wrapper.properties ]; then grep -q "../../launcher/gradlew" gradlew '
            f"|| {{ echo 'kein Gradle-Wrapper' >&2; exit {source.RC_MISMATCH}; }}; w=../../launcher/gradle/wrapper; fi; "
            "v=$(sed -n -E 's#^distributionUrl=.*/gradle-([0-9.]+)-bin\\.zip$#\\1#p' $w/gradle-wrapper.properties); "
            f'case "$v" in {cases} *) echo "Gradle $v nicht freigegeben" >&2; exit {source.RC_MISMATCH};; esac; '
            f'case "$(sha256sum $w/gradle-wrapper.jar | cut -d" " -f1)" in {jars}) ;; '
            f"*) echo 'Gradle-Wrapper passt nicht zur Prüfsumme von gradle.org' >&2; exit {source.RC_MISMATCH};; esac; "
            f'grep -qxF "distributionSha256Sum=$want_dist" $w/gradle-wrapper.properties '
            f"|| {{ echo 'Gradle-Distribution nicht festgenagelt' >&2; exit {source.RC_MISMATCH}; }}; "
            f'echo "{_MARK} gradle=$v"')


def build_script(addon_id: str) -> str:
    d = folder(addon_id)
    log = f"{source.HOME}/build-logs/addon-{addon_id}.log"
    return (f"set -u; cd {d}; mkdir -p {source.HOME}/build-logs; rm -f {apk(addon_id)}; "
            f"export ANDROID_HOME={build.SDK} ANDROID_SDK_ROOT={build.SDK} GRADLE_USER_HOME={source.HOME}/.gradle; "
            f"sh ./gradlew --no-daemon --console=plain assembleRelease > {log} 2>&1; rc=$?; "
            f"tail -n {build.LOG_LINES} {log}; exit $rc")


def collect_script(addon_id: str) -> str:
    a = apk(addon_id)
    return (f"set -eu; A={a}; test -f \"$A\"; "
            f'echo "{_MARK} sha256=$(sha256sum "$A" | cut -d" " -f1)"; '
            f'echo "{_MARK} size=$(stat -c %s "$A")"; '
            f'echo "{_MARK} badging=$({build.BT}/aapt2 dump badging "$A" | head -n 1)"; '
            f'echo "{_MARK} sdk=$({build.BT}/aapt2 dump badging "$A" | sed -n "s/^sdkVersion:.\\([0-9]*\\).*/\\1/p")"; '
            f'echo "{_MARK} perms=$({build.BT}/aapt2 dump permissions "$A" '
            f'| sed -n "s/^uses-permission: name=.\\([A-Za-z0-9_.]*\\).*/\\1/p" | tr \'\\n\' \',\')"')


def evaluate(vals: dict[str, str], expected_pkg: str) -> dict:
    """Gebaute App prüfen: lesbar, erwartetes Paket. Rechte aus der fertigen App (inkl. Bibliotheken)."""
    sha = vals.get("sha256", "")
    m = build._BADGING.search(vals.get("badging", ""))
    if not build._HEX64.match(sha) or not m or not vals.get("size", "").isdigit():
        raise addons.TvwAddonError("tvw_build_unreadable")
    if not expected_pkg or m["pkg"] != expected_pkg:
        raise addons.TvwAddonError("tvw_build_unexpected", m["pkg"])
    perms = sorted({p.removeprefix("android.permission.") for p in vals.get("perms", "").split(",")
                    if re.fullmatch(r"[A-Za-z0-9_.]{3,120}", p)})
    return {"sha256": sha, "size": int(vals["size"]), "package": m["pkg"], "version": f"{m['name']} ({m['code']})",
            "min_sdk": int(vals["sdk"]) if vals.get("sdk", "").isdigit() else 0, "permissions": perms}


def install_script(serial: str, addon_id: str) -> str:
    """Gebaute App übertragen und installieren – keine Sonderrechte, kein Skript des Zusatzes."""
    return (install._connect(serial) + f"{device.ADB} -s {serial} push {apk(addon_id)} {_TMP} >/dev/null && "
            + install._adb(serial, f"pm install -r {_TMP}; rm -f {_TMP}"))


def remove_script(serial: str, pkg: str) -> str:
    """Nur nachinstallierte Pakete (Prüfung auf dem Gerät), danach zurücklesen."""
    if not debloat_pkg(pkg):
        raise addons.TvwAddonError("tvw_addon_unknown", str(pkg)[:80])
    remote = (f'pm list packages -3 | grep -qx "package:{pkg}" || {{ echo "{_MARK} not_there"; exit 0; }}; '
              f'pm uninstall {pkg}; pm list packages | grep -qx "package:{pkg}" && echo "{_MARK} still" '
              f'|| echo "{_MARK} gone"')
    return install._connect(serial) + install._adb(serial, remote)


def debloat_pkg(pkg: str) -> bool:
    return isinstance(pkg, str) and bool(addons.debloat._PKG.fullmatch(pkg)) and pkg != install.OUR
