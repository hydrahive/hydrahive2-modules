"""Auftrag „Vom Fernseher lesen“ für Entrümpeln (Teil 1). Nur lesend: getprop, `pm list packages` (alle / aus).

Die Listen kommen aus der Quelle im Container (fester Stand, backend/source.py) als tar und werden auf dem Server nur
im Speicher gelesen (nur `*/debloat*.txt` und `*/tv.json`, Größen begrenzt), dann je Stand als JSON zwischengespeichert.
"""
from __future__ import annotations

import base64
import io
import json
import logging
import tarfile
from pathlib import Path

from hydrahive.db.connection import db
from hydrahive.settings import settings

from . import debloat, device, install, jobs, look_jobs, source

logger = logging.getLogger(__name__)
_MARK = "__TVW__"
IDENT = {"brand": "ro.product.brand", "product": "ro.product.name", "device": "ro.product.device",
         "model": "ro.product.model", "build_id": "ro.build.id", "incremental": "ro.build.version.incremental"}
MAX_TAR = 8_000_000
MAX_FILE = 200_000
LISTS_SCRIPT = (f"set -eu; cd {source.SRC}/examples; "
                "find . -mindepth 2 -maxdepth 2 -type f \\( -name 'debloat*.txt' -o -name tv.json \\) -print0 "
                "| sort -z | tar --null -T - -czf - | base64 -w0; echo")


def read_script(serial: str) -> str:
    a = f"{device.ADB} -s {serial} shell"
    props = "; ".join(f'echo "{_MARK} {k}=$({a} getprop {p} | tr -d \'\\r\')"' for k, p in IDENT.items())
    return (install._connect(serial) + props + "; "
            + f"{a} pm list packages | tr -d '\\r' | sed 's/^package:/{_MARK} all /'; "
            + f"{a} pm list packages -d | tr -d '\\r' | sed 's/^package:/{_MARK} off /'")


def parse_read(out: str) -> tuple[dict[str, str], dict[str, str]]:
    """(Kennung, {paket: on|off}) aus der Ausgabe von read_script."""
    install.require_open(out)
    vals = device.parse(out)
    ident = {k: vals.get(k, "")[:80] for k in IDENT}
    allp, off = set(), set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[0] == _MARK and parts[1] in ("all", "off") and debloat._PKG.fullmatch(parts[2]):
            (allp if parts[1] == "all" else off).add(parts[2])
    if not allp:
        raise install.TvwInstallError("tvw_debloat_read_failed", "keine Pakete gelesen")
    return ident, {p: ("off" if p in off else "on") for p in sorted(allp | off)}


def parse_lists(blob: bytes) -> dict[str, dict]:
    """{ordner/datei: {off, kept, head, brand}} aus dem tar der Quelle – nur im Speicher, nie entpackt."""
    if not blob or len(blob) > MAX_TAR:
        raise install.TvwInstallError("tvw_debloat_lists_failed", f"{len(blob)} Bytes")
    texts: dict[str, str] = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as t:
            for m in t.getmembers():
                parts = Path(m.name).parts[-2:]
                if not m.isfile() or m.size > MAX_FILE or len(parts) != 2:
                    continue
                if parts[1] == "tv.json" or (parts[1].startswith("debloat") and parts[1].endswith(".txt")):
                    texts["/".join(parts)] = t.extractfile(m).read().decode("utf-8-sig", "replace")
    except (tarfile.TarError, OSError, EOFError):
        raise install.TvwInstallError("tvw_debloat_lists_failed", "Archiv nicht lesbar") from None
    lists: dict[str, dict] = {}
    for name, text in texts.items():
        folder, file = name.split("/")
        if file == "tv.json":
            continue
        try:
            meta = json.loads(texts.get(f"{folder}/tv.json", "{}"))
        except ValueError:
            meta = {}
        off, kept, head = debloat.read_list(text)
        lists[name] = {"off": off, "kept": kept, "brand": str(meta.get("brand", ""))[:40],
                       "head": head + "\n" + json.dumps(meta, ensure_ascii=False)}
    if not lists:
        raise install.TvwInstallError("tvw_debloat_lists_failed", "keine Listen")
    return lists


def _cache(commit: str) -> Path:
    return settings.data_dir / "tvwerkstatt" / "debloat" / f"lists-{commit[:12]}.json"


def save_lists(commit: str, lists: dict[str, dict]) -> None:
    p = _cache(commit)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {k: {**v, "kept": sorted(v["kept"])} for k, v in lists.items()}
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False))
    tmp.replace(p)


def load_lists(commit: str = source.COMMIT) -> dict[str, dict] | None:
    p = _cache(commit)
    if not p.is_file():
        return None
    data = json.loads(p.read_text())
    return {k: {**v, "off": [tuple(x) for x in v["off"]], "kept": set(v["kept"])} for k, v in data.items()}


def _store(device_id: str, ident: dict, packages: dict) -> None:
    with db() as conn:
        conn.execute("INSERT INTO module_tvwerkstatt_debloat_reads (device_id, ident, packages, commit_id) "
                     "VALUES (?, ?, ?, ?) ON CONFLICT(device_id) DO UPDATE SET ident = excluded.ident, "
                     "packages = excluded.packages, commit_id = excluded.commit_id, "
                     "read_at = strftime('%Y-%m-%dT%H:%M:%SZ','now')",
                     (device_id, json.dumps(ident), json.dumps(packages), source.COMMIT))
        conn.commit()


async def run_read(job_id: str, device_id: str) -> None:
    err = None
    try:
        serial = await look_jobs._ready(device_id)
        if load_lists() is None:
            jobs.update(job_id, step="lists")
            await look_jobs._sh(source.FETCH_SCRIPT, 600)
            out = await look_jobs._sh(LISTS_SCRIPT, 120)
            line = next((ln.strip() for ln in out.splitlines() if len(ln.strip()) > 100), "")
            try:
                blob = base64.b64decode(line, validate=True)
            except ValueError:
                raise install.TvwInstallError("tvw_debloat_lists_failed", "base64") from None
            save_lists(source.COMMIT, parse_lists(blob))
        jobs.update(job_id, step="packages")
        ident, packages = parse_read(await look_jobs._sh(read_script(serial), 120))
        _store(device_id, ident, packages)
    except Exception as exc:                          # noqa: BLE001 - jeder Fehler endet im Auftrag
        err = exc
    await look_jobs._finish(job_id, err)


def view(device_id: str, stock: str) -> dict | None:
    """Für die Seite: letzter gelesener Stand gegen die Listen. None = noch nie gelesen."""
    with db() as conn:
        r = conn.execute("SELECT ident, packages, commit_id, read_at FROM module_tvwerkstatt_debloat_reads "
                         "WHERE device_id = ?", (device_id,)).fetchone()
    if r is None:
        return None
    lists = load_lists(r[2]) or {}
    out = debloat.evaluate(json.loads(r[1]), lists, json.loads(r[0]), stock)
    return {**out, "read_at": r[3], "commit_id": r[2][:7]}
