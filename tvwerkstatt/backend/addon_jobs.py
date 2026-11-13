"""Aufträge der Zusätze: Katalog laden, bauen + installieren (ein Auftrag), entfernen. Container danach immer aus.

Katalog und Bilder liegen je Stand der Quelle unter data_dir/tvwerkstatt/addons/<commit>/. Bauen + Installieren nur mit
Rückfrage (Route): Quelle → Gradle-Prüfung → Bau → Auswertung (erwartetes Paket, minSdk gegen den Fernseher) →
pm install -r. Ohne Installationsskript des Zusatzes und ohne Sonderrechte.
"""
from __future__ import annotations

import base64
import io
import json
from pathlib import Path

from hydrahive.db.connection import db
from hydrahive.settings import settings

from . import (
    addon_build,
    addons,
    build,
    build_jobs,
    install,
    jobs,
    look_jobs,
    source,
    state,
)


def folder(commit: str = source.COMMIT) -> Path:
    return settings.data_dir / "tvwerkstatt" / "addons" / commit[:12]


def catalog() -> list[dict] | None:
    p = folder() / "catalog.json"
    return json.loads(p.read_text()) if p.is_file() else None


def image(addon_id: str) -> Path | None:
    if not addons._ID.match(addon_id or ""):
        return None
    p = folder() / f"{addon_id}.jpg"
    return p if p.is_file() else None


def _save(cat: list[dict], images: dict[str, bytes]) -> None:
    from PIL import Image, UnidentifiedImageError
    d = folder()
    d.mkdir(parents=True, exist_ok=True)
    for aid, data in images.items():
        try:
            with Image.open(io.BytesIO(data)) as im:
                im = im.convert("RGB")
                im.thumbnail((640, 360))
                im.save(d / f"{aid}.jpg", "JPEG", quality=82, optimize=True)
        except (UnidentifiedImageError, OSError, ValueError):
            next(c for c in cat if c["id"] == aid)["has_image"] = False
    tmp = d / "catalog.tmp"
    tmp.write_text(json.dumps(cat, ensure_ascii=False))
    tmp.replace(d / "catalog.json")


async def ensure_catalog(job_id: str) -> list[dict]:
    cat = catalog()
    if cat is not None:
        return cat
    jobs.update(job_id, step="catalog")
    await look_jobs._sh(source.FETCH_SCRIPT, 600)
    out = await look_jobs._sh(addons.SCRIPT, 120)
    line = next((ln.strip() for ln in out.splitlines() if len(ln.strip()) > 100), "")
    try:
        blob = base64.b64decode(line, validate=True)
    except ValueError:
        raise addons.TvwAddonError("tvw_addons_catalog_failed", "base64") from None
    cat, images = addons.parse(blob)
    _save(cat, images)
    return cat


async def run_catalog(job_id: str, device_id: str) -> None:
    err = None
    try:
        await look_jobs._ready(device_id)
        await ensure_catalog(job_id)
    except Exception as exc:                          # noqa: BLE001 - jeder Fehler endet im Auftrag
        err = exc
    await look_jobs._finish(job_id, err)


async def _step(job_id: str, step: str, script: str, timeout: float, code: str) -> str:
    jobs.update(job_id, step=step)
    rc, out, err = await build_jobs._run(script, "build" if step == "build" else "collect")
    if rc != 0:
        raise addons.TvwAddonError("tvw_source_mismatch" if rc == source.RC_MISMATCH else code,
                                   build.clean_log(f"{out}\n{err}"))
    return out


def runner_install(device_id: str, addon_id: str):
    item = next((c for c in catalog() or [] if c["id"] == addon_id), None)
    if item is None or not item.get("package"):
        raise addons.TvwAddonError("tvw_addon_unknown", str(addon_id)[:40])
    dev = next(d for d in state.devices() if d["device_id"] == device_id)
    if item["min_sdk"] and dev.get("sdk") and int(dev["sdk"]) < int(item["min_sdk"]):
        raise addons.TvwAddonError("tvw_sdk_too_old")

    async def runner(job_id: str, dev_id: str) -> None:
        err, build_id = None, ""
        try:
            serial = await look_jobs._ready(dev_id)
            jobs.update(job_id, step="fetch")
            await look_jobs._sh(source.FETCH_SCRIPT, 600)
            await _step(job_id, "verify", addon_build.verify_script(addon_id), 60, "tvw_source_mismatch")
            build_id = build_jobs._new_build(source.source_id())
            build_jobs._set_build(build_id, part=addon_id)
            log = build.clean_log(await _step(job_id, "build", addon_build.build_script(addon_id), 1800,
                                              "tvw_build_failed"))
            build_jobs._set_build(build_id, log_tail=log)
            info = addon_build.evaluate(build.parse(await _step(job_id, "collect", addon_build.collect_script(addon_id),
                                                                120, "tvw_build_unreadable")), item["package"])
            build_jobs._set_build(build_id, state="done", sha256=info["sha256"], size=info["size"],
                                  package=info["package"], version=info["version"],
                                  permissions=",".join(info["permissions"]))
            jobs.update(job_id, step="push")
            install.check_installed(await look_jobs._sh(addon_build.install_script(serial, addon_id), 300))
            with db() as conn:
                conn.execute("INSERT INTO module_tvwerkstatt_installed (device_id, package, build_id, sha256) "
                             "VALUES (?, ?, ?, ?) ON CONFLICT(device_id, package) DO UPDATE SET "
                             "build_id = excluded.build_id, sha256 = excluded.sha256, "
                             "installed_at = strftime('%Y-%m-%dT%H:%M:%SZ','now')",
                             (dev_id, info["package"], build_id, info["sha256"]))
                conn.commit()
        except Exception as exc:                      # noqa: BLE001
            err = exc
            if build_id:
                build_jobs._set_build(build_id, state="failed")
        await look_jobs._finish(job_id, err)
    return runner


def runner_remove(device_id: str, addon_id: str):
    item = next((c for c in catalog() or [] if c["id"] == addon_id), None)
    if item is None or not addon_build.debloat_pkg(item.get("package", "")):
        raise addons.TvwAddonError("tvw_addon_unknown", str(addon_id)[:40])
    pkg = item["package"]

    async def runner(job_id: str, dev_id: str) -> None:
        err = None
        try:
            serial = await look_jobs._ready(dev_id)
            jobs.update(job_id, step="remove")
            out = await look_jobs._sh(addon_build.remove_script(serial, pkg), 120)
            install.require_open(out)
            if "__TVW__ gone" not in out and "__TVW__ not_there" not in out:
                raise addons.TvwAddonError("tvw_addon_remove_failed", build.clean_log(out)[-200:])
            with db() as conn:
                conn.execute("DELETE FROM module_tvwerkstatt_installed WHERE device_id = ? AND package = ?",
                             (dev_id, pkg))
                conn.commit()
        except Exception as exc:                      # noqa: BLE001
            err = exc
        await look_jobs._finish(job_id, err)
    return runner


def view(device_id: str) -> dict:
    """Katalog mit Stand je Fernseher: installiert (von der Werkstatt) mit Version und Rechten der gebauten App."""
    cat = catalog()
    with db() as conn:
        rows = conn.execute("SELECT i.package, b.version, b.permissions, i.installed_at "
                            "FROM module_tvwerkstatt_installed i LEFT JOIN module_tvwerkstatt_builds b "
                            "ON b.build_id = i.build_id WHERE i.device_id = ?",
                            (device_id,)).fetchall()
    have = {r[0]: {"version": r[1] or "", "permissions": [p for p in (r[2] or "").split(",") if p],
                   "installed_at": r[3]} for r in rows}
    items = [{**c, "installed": have.get(c["package"])} for c in cat] if cat else None
    return {"items": items, "commit_id": source.COMMIT[:7]}
