"""Apps eines Fernsehers lesen: Paket, Name, Banner/Symbol (PLAN-E2.md Baustein B). Nur lesend.

Im Container: startbare TV-Apps (LEANBACK_LAUNCHER), je App Version; nur für neue oder geänderte Versionen wird das APK
gezogen und mit aapt2 gelesen (Name deutsch vor englisch, Banner sonst Symbol, größte Dichte). Das Bild landet in
einem Ordner im Container und wird als tar abgeholt. Auf dem Server werden die Bilder mit Pillow geprüft und
verkleinert. Gemessen am Sony (13.11.): 20 Apps, Abzug ~0,7 s je App.
"""
from __future__ import annotations

import io
import re
import tarfile
from pathlib import Path

from hydrahive.settings import settings

from . import device

OUT = "/home/ubuntu/appimg"
_MARK = "__TVW__"
_PKG = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)+$")
MAX_IMG = 2_000_000
IMG_W, IMG_H = 320, 180

BT = "/home/ubuntu/android-sdk/build-tools/34.0.0"
_PY = r'''
import re, subprocess, sys, zipfile
apk, out, pkg = sys.argv[1], sys.argv[2], sys.argv[3]
b = subprocess.run([sys.argv[4], "dump", "badging", apk], capture_output=True, text=True).stdout
lab = re.search(r"^application-label-de:'(.*)'$", b, re.M) or re.search(r"^application-label:'(.*)'$", b, re.M)
app = re.search(r"^application: .*", b, re.M)
line = app.group(0) if app else ""
ban = re.search(r"banner='([^']+)'", line)
ico = re.search(r"icon='([^']+)'", line)
kind, path = ("banner", ban.group(1)) if ban else ("icon", ico.group(1) if ico else "")
best = ""
if path:
    z = zipfile.ZipFile(apk)
    stem = path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    names = set(z.namelist())
    cands = [n for n in names if n.rsplit("/", 1)[-1].rsplit(".", 1)[0] == stem and n.endswith((".png", ".webp"))
             and ("/mipmap" in n or "/drawable" in n)]
    cands.sort(key=lambda n: z.getinfo(n).file_size, reverse=True)
    if not cands and path in names and path.endswith((".png", ".webp")):
        cands = [path]                      # verschleierte Pfade (res/dN.png): genau diese Datei
    if cands:
        best = cands[0]
        open(f"{out}/{pkg}.img", "wb").write(z.read(best)[:2000000])
print("__TVW__ app", pkg, kind if best else "none", (lab.group(1) if lab else "")[:60].replace("\t", " "), sep="\t")
'''


def list_script(serial: str) -> str:
    """Startbare TV-Apps mit versionCode, in Zeilen `__TVW__ pkg <paket> <version>`."""
    a = f"{device.ADB} -s {serial}"
    return (f"{device.ADB} connect {serial} >/dev/null 2>&1; "
            f'st=$({device.ADB} devices | awk -v s="{serial}" \'$1 == s {{print $2}}\' | head -n 1); '
            f'echo "{_MARK} state=${{st:-offline}}"; [ "$st" = device ] || exit 0; '
            f"vers=$({a} shell pm list packages --show-versioncode | tr -d '\\r'); "
            f"for p in $({a} shell cmd package query-activities --brief -a android.intent.action.MAIN "
            f"-c android.intent.category.LEANBACK_LAUNCHER | grep / | cut -d/ -f1 | tr -d ' \\r' | sort -u); do "
            f'v=$(printf "%s\\n" "$vers" | grep -m1 "^package:$p versionCode:" | sed "s/.*versionCode://"); '
            f'echo "{_MARK} pkg $p ${{v:-0}}"; done')


def read_script(serial: str, packages: list[str]) -> str:
    """APK ziehen und lesen – nur für die genannten Pakete (geprüfte Namen)."""
    pkgs = [p for p in packages if _PKG.match(p)]
    a = f"{device.ADB} -s {serial}"
    py = _PY.replace("'", "'\"'\"'")
    return (f"set -u; rm -rf {OUT}; mkdir -p {OUT}; cd /tmp; "
            f"for p in {' '.join(pkgs)}; do "
            f"path=$({a} shell pm path $p | head -n 1 | sed 's/^package://' | tr -d '\\r'); "
            f'[ -n "$path" ] || continue; {a} pull "$path" /tmp/tvw-app.apk >/dev/null 2>&1 || continue; '
            f"python3 -c '{py}' /tmp/tvw-app.apk {OUT} $p {BT}/aapt2; rm -f /tmp/tvw-app.apk; done; "
            f"tar -C {OUT} -cf - . | base64 -w0; echo")


def parse_list(out: str) -> dict[str, str]:
    found = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 4 and parts[:2] == [_MARK, "pkg"] and _PKG.match(parts[2]) and parts[3].isdigit():
            found[parts[2]] = parts[3]
    return found


def parse_read(out: str) -> tuple[dict[str, dict], bytes]:
    """Zeilen `__TVW__ app <pkg> <kind> <label>` und am Ende das tar (base64)."""
    import base64
    info: dict[str, dict] = {}
    blob = b""
    for line in out.splitlines():
        if line.startswith(f"{_MARK} app\t"):
            parts = line.split("\t")
            if len(parts) == 4 and _PKG.match(parts[1]) and parts[2] in ("banner", "icon", "none"):
                info[parts[1]] = {"kind": parts[2], "label": parts[3].strip()[:60]}
        elif line and not line.startswith(_MARK) and re.fullmatch(r"[A-Za-z0-9+/=]+", line.strip()):
            try:
                blob = base64.b64decode(line.strip(), validate=True)
            except ValueError:
                blob = b""
    return info, blob


def image_dir(device_id: str) -> Path:
    return settings.data_dir / "tvwerkstatt" / "apps" / device_id


def store_images(device_id: str, blob: bytes) -> dict[str, str]:
    """Bilder aus dem tar prüfen (Pillow), auf 320×180 einpassen, als PNG ablegen. Gibt Paket → Grundfarbe."""
    from PIL import Image, UnidentifiedImageError
    target = image_dir(device_id)
    target.mkdir(parents=True, exist_ok=True)
    colors: dict[str, str] = {}
    if not blob:
        return colors
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:") as t:
        for m in t.getmembers():
            name = m.name.removeprefix("./")
            pkg = name.removesuffix(".img")
            if not m.isfile() or not name.endswith(".img") or not _PKG.match(pkg) or m.size > MAX_IMG:
                continue
            try:
                with Image.open(io.BytesIO(t.extractfile(m).read())) as im:
                    im = im.convert("RGBA")
                    im.thumbnail((IMG_W, IMG_H))
                    canvas = Image.new("RGBA", (IMG_W, IMG_H), (0, 0, 0, 0))
                    canvas.paste(im, ((IMG_W - im.width) // 2, (IMG_H - im.height) // 2), im)
                    canvas.save(target / f"{pkg}.png", "PNG", optimize=True)
                    r, g, b, _ = im.resize((1, 1)).getpixel((0, 0))
                    colors[pkg] = f"#{r:02x}{g:02x}{b:02x}"
            except (UnidentifiedImageError, OSError, ValueError):
                continue
    return colors
