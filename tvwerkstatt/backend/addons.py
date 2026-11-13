"""Zusätze, Teil 1: Katalog aus cleanyourtv `addons/` am festen Stand lesen (backend/source.py). Nur lesend.

Im Container werden nur `addons/README.md`, je Zusatz `app/build.gradle*`, `app/src/main/AndroidManifest.xml` und
`screenshot.jpg` als tar geholt. Hier wird nur im Speicher gelesen (Größen begrenzt): Name, Beschreibung, Autor, getestet
auf, Paket, minSdk, Rechte laut Manifest, ob es ein Bildschirmschoner ist. Grundlage ist jeder Ordner mit build.gradle;
die README-Tabelle ergänzt nur Texte. Rechte aus Bibliotheken stehen nicht im Manifest – nach dem Bau zählt die App.
"""
from __future__ import annotations

import io
import re
import tarfile
from pathlib import PurePosixPath

from . import debloat, install, source

MAX_TAR = 15_000_000
MAX_TEXT = 200_000
MAX_IMG = 2_000_000
_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")
_PERM = re.compile(r'<uses-permission(?:-sdk-23)?\b[^>]*android:name="([A-Za-z0-9_.]+)"')
_APP_ID = re.compile(r"applicationId\s*=?\s*['\"]([^'\"]+)['\"]")
_MIN_SDK = re.compile(r"minSdk(?:Version)?\s*=?\s*(\d+)")
RED = {"WRITE_SECURE_SETTINGS", "REQUEST_INSTALL_PACKAGES", "UPDATE_PACKAGES_WITHOUT_USER_ACTION", "DUMP"}
YELLOW = {"SYSTEM_ALERT_WINDOW", "RECEIVE_BOOT_COMPLETED", "FOREGROUND_SERVICE", "FOREGROUND_SERVICE_SPECIAL_USE",
          "FOREGROUND_SERVICE_DATA_SYNC", "PACKAGE_USAGE_STATS", "ACCESS_COARSE_LOCATION", "ACCESS_FINE_LOCATION",
          "SCHEDULE_EXACT_ALARM", "BIND_ACCESSIBILITY_SERVICE"}

SCRIPT = (
    f"set -eu; cd {source.SRC}/addons; "
    "{ find . -maxdepth 1 -name README.md -type f -print0; "
    "find . -mindepth 3 -maxdepth 3 -path './*/app/build.gradle*' -type f -print0; "
    "find . -mindepth 5 -maxdepth 5 -path './*/app/src/main/AndroidManifest.xml' -type f -print0; "
    "find . -mindepth 2 -maxdepth 2 -name screenshot.jpg -type f -print0; } "
    "| sort -z | tar --null -T - -czf - | base64 -w0; echo"
)


class TvwAddonError(install.TvwInstallError):
    pass


def plain(cell: str) -> str:
    """Markdown/HTML einer Tabellenzelle → schlichter Text."""
    t = re.sub(r"<[^>]+>", "", cell)
    t = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"[`*_]{1,2}([^`*_]+)[`*_]{1,2}", r"\1", t)
    return " ".join(t.split())[:400]


def readme_rows(text: str) -> dict[str, dict]:
    """{ordner: {name, what, author, tested, permissions_text}} aus der Tabelle „| Add-on |“."""
    out: dict[str, dict] = {}
    for line in text.splitlines():
        m = re.match(r"^\|\s*\[([^\]]+)\]\(([a-z0-9-]+)/\)\s*\|", line.strip())
        if not m:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 5:
            continue
        out[m.group(2)] = {"name": plain(m.group(1))[:60], "what": plain(cells[1]), "author": plain(cells[2])[:80],
                           "tested": plain(cells[3])[:160], "permissions_text": plain(cells[4])[:200]}
    return out


def level(perm: str) -> str:
    return "red" if perm in RED else "yellow" if perm in YELLOW else ""


def _short(name: str) -> str:
    return name.removeprefix("android.permission.")


def parse(blob: bytes) -> tuple[list[dict], dict[str, bytes]]:
    """(Katalog, {ordner: Bildbytes}) aus dem tar. Unbekannte, zu große oder seltsame Dateien werden übergangen."""
    if not blob or len(blob) > MAX_TAR:
        raise TvwAddonError("tvw_addons_catalog_failed", f"{len(blob)} Bytes")
    texts: dict[str, str] = {}
    images: dict[str, bytes] = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as t:
            for m in t.getmembers():
                p = PurePosixPath(m.name.removeprefix("./"))
                if not m.isfile() or ".." in p.parts:
                    continue
                if p.name == "screenshot.jpg" and len(p.parts) == 2 and m.size <= MAX_IMG:
                    images[p.parts[0]] = t.extractfile(m).read()
                elif m.size <= MAX_TEXT:
                    texts[str(p)] = t.extractfile(m).read().decode("utf-8-sig", "replace")
    except (tarfile.TarError, OSError, EOFError):
        raise TvwAddonError("tvw_addons_catalog_failed", "Archiv nicht lesbar") from None
    rows = readme_rows(texts.get("README.md", ""))
    catalog = []
    for key, text in sorted(texts.items()):
        parts = PurePosixPath(key).parts
        if len(parts) != 3 or parts[1] != "app" or not parts[2].startswith("build.gradle") or not _ID.match(parts[0]):
            continue
        folder = parts[0]
        app = _APP_ID.search(text)
        pkg = app.group(1) if app and debloat._PKG.fullmatch(app.group(1)) else ""
        sdk = _MIN_SDK.search(text)
        manifest = texts.get(f"{folder}/app/src/main/AndroidManifest.xml", "")
        perms = sorted({_short(p) for p in _PERM.findall(manifest)})
        info = rows.get(folder, {})
        catalog.append({"id": folder, "name": info.get("name") or folder, "what": info.get("what", ""),
                        "author": info.get("author", ""), "tested": info.get("tested", ""),
                        "permissions_text": info.get("permissions_text", ""), "package": pkg,
                        "min_sdk": int(sdk.group(1)) if sdk else 0, "dream": "android.service.dreams.DreamService"
                        in manifest, "permissions": [{"name": p, "level": level(p)} for p in perms],
                        "has_image": folder in images})
    if not catalog:
        raise TvwAddonError("tvw_addons_catalog_failed", "keine Zusätze")
    return catalog, {k: v for k, v in images.items() if any(c["id"] == k for c in catalog)}
