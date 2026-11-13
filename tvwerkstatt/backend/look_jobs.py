"""Aufträge „Apps lesen“ und „Aussehen schieben“ (PLAN-E2.md Baustein B/C). Nur nach Klick, Container danach aus."""
from __future__ import annotations

import hashlib
import io
import logging
import tarfile

from hydrahive.containers.incus_client import IncusError
from hydrahive.db.connection import db

from . import (
    apps,
    container,
    device,
    incus,
    install,
    jobs,
    look,
    network,
    state,
    theme_push,
    wallpapers,
)

logger = logging.getLogger(__name__)
_U = ("--cwd", "/home/ubuntu", "--user", "1000", "--group", "1000", "--env", "HOME=/home/ubuntu")


async def _sh(script: str, timeout: float = 180.0, stdin: bytes | None = None) -> str:
    try:
        rc, out, err = await incus.run("exec", container.NAME, *_U, "--", "bash", "-c", script,
                                              timeout=timeout, input_bytes=stdin)
    except IncusError as exc:
        raise install.TvwInstallError("tvw_adb_closed", str(exc)[-200:]) from None
    if rc != 0:
        raise install.TvwInstallError("tvw_look_push_failed", f"{out}\n{err}"[-300:])
    return f"{out}\n{err}"


async def _ready(device_id: str) -> str:
    with db() as conn:
        r = conn.execute("SELECT address, adb_port FROM module_tvwerkstatt_devices WHERE device_id = ?",
                         (device_id,)).fetchone()
    if r is None:
        raise install.TvwInstallError("tvw_device_not_found")
    serial = device.target(r[0], int(r[1]), network._host_addresses())
    if await container.status() == "missing":
        raise install.TvwInstallError("tvw_not_set_up")
    await network.sync_rules(state.device_targets())
    await container.ensure_running()
    await container.wait_for_address()
    return serial


def known_apps(device_id: str) -> list[dict]:
    cols = ("package", "label", "version", "has_banner", "color")
    with db() as conn:
        rows = conn.execute(f"SELECT {', '.join(cols)} FROM module_tvwerkstatt_apps WHERE device_id = ? "
                            "ORDER BY label COLLATE NOCASE, package", (device_id,)).fetchall()
    return [dict(zip(cols, r, strict=True)) for r in rows if r[0] != install.OUR]


async def _read_apps(job_id: str, device_id: str, serial: str) -> None:
    jobs.update(job_id, step="apps")
    out = await _sh(apps.list_script(serial), 60)
    install.require_open(out)
    found = apps.parse_list(out)
    have = {a["package"]: a["version"] for a in known_apps(device_id)}
    todo = sorted(p for p, v in found.items() if have.get(p) != v and p != install.OUR)
    info, blob = apps.parse_read(await _sh(apps.read_script(serial, todo), 900)) if todo else ({}, b"")
    colors = apps.store_images(device_id, blob)
    with db() as conn:
        for (gone,) in conn.execute("SELECT package FROM module_tvwerkstatt_apps WHERE device_id = ?",
                                    (device_id,)).fetchall():
            if gone not in found:                             # deinstalliert → aus der Liste
                conn.execute("DELETE FROM module_tvwerkstatt_apps WHERE device_id = ? AND package = ?",
                             (device_id, gone))
        for p in todo:
            i = info.get(p, {})
            conn.execute("INSERT INTO module_tvwerkstatt_apps (device_id, package, label, version, has_banner, color) "
                         "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(device_id, package) DO UPDATE SET label = excluded.label, "
                         "version = excluded.version, has_banner = excluded.has_banner, color = excluded.color, "
                         "read_at = strftime('%Y-%m-%dT%H:%M:%SZ','now')",
                         (device_id, p, i.get("label") or p, found[p], 1 if i.get("kind") == "banner" else 0,
                          colors.get(p, "")))
        conn.commit()


def bundle(device_id: str) -> tuple[bytes, list[str], str]:
    """tar mit config.json + Bildern, Dateiliste (config.json zuerst) und Prüfsumme des Ganzen."""
    walls = wallpapers.by_mood(device_id)
    cfg = look.theme_json(look.load(device_id), walls)
    files = [("config.json", cfg)] + [(f"wallpapers/{n}", (wallpapers.folder(device_id) / n).read_bytes())
                                      for m in look.MOODS for n in walls.get(m, [])]
    buf, h = io.BytesIO(), hashlib.sha256()
    with tarfile.open(fileobj=buf, mode="w") as t:
        for name, data in files:
            ti = tarfile.TarInfo(name)
            ti.size, ti.mode = len(data), 0o644
            t.addfile(ti, io.BytesIO(data))
            h.update(name.encode() + b"\0" + data)
    return buf.getvalue(), [n for n, _ in files], h.hexdigest()


async def _finish(job_id: str, err: Exception | None) -> None:
    if err is None:
        jobs.finish(job_id)
    else:
        if not hasattr(err, "code"):
            logger.error("TV-Werkstatt: Auftrag Aussehen gescheitert: %r", err)
        jobs.finish(job_id, error=getattr(err, "code", "tvw_look_push_failed"), detail=getattr(err, "detail", ""))
    try:
        await container.stop()
    except container.TvwContainerError:
        logger.warning("TV-Werkstatt: Container nicht angehalten")


async def run_read_apps(job_id: str, device_id: str) -> None:
    err = None
    try:
        await _read_apps(job_id, device_id, await _ready(device_id))
    except Exception as exc:                         # noqa: BLE001 - jeder Fehler endet im Auftrag
        err = exc
    await _finish(job_id, err)


async def run_push_look(job_id: str, device_id: str) -> None:
    err = None
    try:
        serial = await _ready(device_id)
        jobs.update(job_id, step="push")
        blob, files, digest = bundle(device_id)
        await _sh(f"rm -rf {theme_push.STAGE}; mkdir -p {theme_push.STAGE}; tar -x -C {theme_push.STAGE} -f -",
                  60, stdin=blob)
        out = await _sh(theme_push.push_script(serial, files), 600)
        install.require_open(out)
        missing = theme_push.check(out)
        if missing:
            raise install.TvwInstallError("tvw_look_push_failed", ", ".join(missing))
        look.save(device_id, look.load(device_id))            # Zeile anlegen, falls noch nie gespeichert
        with db() as conn:
            conn.execute("UPDATE module_tvwerkstatt_looks SET pushed_at = strftime('%Y-%m-%dT%H:%M:%SZ','now'), "
                         "pushed_hash = ? WHERE device_id = ?", (digest, device_id))
            conn.commit()
    except Exception as exc:                         # noqa: BLE001
        err = exc
    await _finish(job_id, err)
