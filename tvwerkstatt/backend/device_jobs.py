"""Fernseher eintragen, prüfen, entfernen (PLAN-E1.md Baustein 5).

Prüfen ist ein Auftrag (kind=probe, target=device_id): Sperrliste nachziehen → Container an → per adb lesen. Beim ersten
Kontakt fragt der Fernseher „Debugging zulassen?“ – der Auftrag wartet bis WAIT_AUTH_S darauf und zeigt das als Schritt
„auf dem Fernseher bestätigen“. Danach wird der adb-Schlüssel des Containers im Datenordner gesichert und der Container
angehalten. Am Fernseher wird nichts geschaltet.
"""
from __future__ import annotations

import asyncio
import logging
import uuid

from hydrahive.db.connection import db

from . import container, device, incus, jobs, network, provision, state

logger = logging.getLogger(__name__)
WAIT_AUTH_S = 300                # Weg zum Fernseher und Fernbedienung brauchen Zeit
_STEP_S = 5.0
_FIELDS = ("adb_state", "model", "android", "sdk", "build", "stock_home", "current_home", "kind")


def _row(device_id: str) -> dict | None:
    with db() as conn:
        r = conn.execute("SELECT address, adb_port, stock_home FROM module_tvwerkstatt_devices WHERE device_id = ?",
                         (device_id,)).fetchone()
    return {"address": r[0], "adb_port": int(r[1]), "stock_home": r[2]} if r else None


def add(name: str, address: str, port: int, admin: str) -> str:
    n = device.clean_name(name)
    device.target(address, port, network._host_addresses())
    device_id = uuid.uuid4().hex[:12]
    with db() as conn:
        if conn.execute("SELECT 1 FROM module_tvwerkstatt_devices WHERE address = ?", (address,)).fetchone():
            raise device.TvwDeviceError("tvw_device_exists")
        conn.execute("INSERT INTO module_tvwerkstatt_devices (device_id, name, address, adb_port, created_by) "
                     "VALUES (?, ?, ?, ?, ?)", (device_id, n, address, port, admin))
        conn.commit()
    return device_id


async def remove(device_id: str) -> None:
    if _row(device_id) is None:
        raise device.TvwDeviceError("tvw_device_not_found")
    with db() as conn:
        conn.execute("DELETE FROM module_tvwerkstatt_devices WHERE device_id = ?", (device_id,))
        conn.commit()
    if await container.status() != "missing":
        await network.sync_rules(state.device_targets())      # Ausnahme für diesen Fernseher fällt weg


def _save(device_id: str, info: dict) -> None:
    fields = {k: info[k] for k in _FIELDS if k in info}
    sets = ", ".join(f"{k} = ?" for k in fields)
    with db() as conn:
        conn.execute(f"UPDATE module_tvwerkstatt_devices SET {sets}, checked_at = strftime('%Y-%m-%dT%H:%M:%SZ','now') "
                     "WHERE device_id = ?", (*fields.values(), device_id))
        conn.commit()


async def _backup_adbkey() -> None:
    """Den adb-Schlüssel des Containers sichern (SPEC Entscheidung 8), damit der Fernseher nach einem Abbau nicht
    erneut fragt. Gelingt das nicht, ist das kein Fehler des Prüfens."""
    dst = provision.adbkey_dir()
    dst.mkdir(parents=True, exist_ok=True, mode=0o700)
    for f in ("adbkey", "adbkey.pub"):
        rc, _, _ = await incus.run("file", "pull", f"{container.NAME}/home/ubuntu/.android/{f}", str(dst / f))
        if rc == 0:
            (dst / f).chmod(0o600)


async def _probe_until_allowed(job_id: str, serial: str) -> dict[str, str]:
    vals = await device.probe(container.NAME, serial)
    waited = 0.0
    while "unauthorized" in vals.get("state", "") and waited < WAIT_AUTH_S:
        jobs.update(job_id, step="authorize")
        await asyncio.sleep(_STEP_S)
        waited += _STEP_S
        vals = await device.probe(container.NAME, serial)
    return vals


async def run_check(job_id: str, device_id: str) -> None:
    step = "network"
    try:
        row = _row(device_id)
        if row is None:
            raise device.TvwDeviceError("tvw_device_not_found")
        serial = device.target(row["address"], row["adb_port"], network._host_addresses())
        if await container.status() == "missing":
            raise device.TvwDeviceError("tvw_not_set_up")
        await network.sync_rules(state.device_targets())
        step = "container"
        jobs.update(job_id, step=step)
        await container.ensure_running()
        await container.wait_for_address()
        step = "connect"
        jobs.update(job_id, step=step)
        info = device.evaluate(await _probe_until_allowed(job_id, serial), stock_before=row["stock_home"])
        _save(device_id, info)
        if info["adb_state"] == "unauthorized":
            raise device.TvwDeviceError("tvw_adb_unauthorized")
        if info["adb_state"] == "closed":
            raise device.TvwDeviceError("tvw_adb_closed")
        await _backup_adbkey()
        if info.get("too_old"):
            raise device.TvwDeviceError("tvw_sdk_too_old")
        jobs.finish(job_id)
    except (device.TvwDeviceError, network.TvwNetworkError, container.TvwContainerError) as exc:
        jobs.finish(job_id, error=exc.code, step=step, detail=getattr(exc, "detail", ""))
    except Exception:
        logger.exception("TV-Werkstatt: Prüfen des Fernsehers gescheitert")
        jobs.finish(job_id, error="tvw_device_probe_failed", step=step)
    finally:
        try:
            await container.stop()
        except container.TvwContainerError:
            logger.warning("TV-Werkstatt: Container nach dem Prüfen nicht angehalten")
