"""Aufträge der App-Verwaltung: Apps lesen, Store öffnen/suchen (am Fernseher), deinstallieren. Container danach aus."""
from __future__ import annotations

import json

from hydrahive.db.connection import db

from . import jobs, look_jobs, state, store


def _stock(device_id: str) -> str:
    return next((d.get("stock_home") or "" for d in state.devices() if d["device_id"] == device_id), "")


def view(device_id: str) -> dict | None:
    with db() as conn:
        r = conn.execute("SELECT apps, read_at FROM module_tvwerkstatt_store_reads WHERE device_id = ?",
                         (device_id,)).fetchone()
    if r is None:
        return None
    stock = _stock(device_id)
    apps = [{**a, "store": a["installer"] == store.STORE, "locked": store.protected(a["package"], stock)}
            for a in json.loads(r[0])]
    return {"apps": apps, "read_at": r[1]}


async def _read(device_id: str, serial: str) -> None:
    apps = store.parse_list(await look_jobs._sh(store.list_script(serial), 120))
    with db() as conn:
        conn.execute("INSERT INTO module_tvwerkstatt_store_reads (device_id, apps) VALUES (?, ?) "
                     "ON CONFLICT(device_id) DO UPDATE SET apps = excluded.apps, "
                     "read_at = strftime('%Y-%m-%dT%H:%M:%SZ','now')",
                     (device_id, json.dumps(apps)))
        conn.commit()


async def _run(job_id: str, device_id: str, work) -> None:
    err = None
    try:
        serial = await look_jobs._ready(device_id)
        await work(serial)
    except Exception as exc:                          # noqa: BLE001 - jeder Fehler endet im Auftrag
        err = exc
    await look_jobs._finish(job_id, err)


async def run_read(job_id: str, device_id: str) -> None:
    async def work(serial: str) -> None:
        jobs.update(job_id, step="read")
        await _read(device_id, serial)
    await _run(job_id, device_id, work)


def runner_open(pkg: str | None, q: str | None):
    """Store am Fernseher öffnen: bei einer App (pkg) oder mit einer Suche (q). Prüft vorher, wirft TvwStoreError."""
    script_for = (lambda s: store.open_script(s, pkg)) if pkg else (lambda s: store.search_script(s, q or ""))
    script_for("0.0.0.0:0")                                    # Eingabe jetzt prüfen, nicht erst im Auftrag

    async def runner(job_id: str, device_id: str) -> None:
        async def work(serial: str) -> None:
            jobs.update(job_id, step="open")
            store.started(await look_jobs._sh(script_for(serial), 60))
        await _run(job_id, device_id, work)
    return runner


def runner_uninstall(device_id: str, pkg: str):
    p = store.package(pkg)
    if store.protected(p, _stock(device_id)):
        raise store.TvwStoreError("tvw_store_locked")

    async def runner(job_id: str, dev_id: str) -> None:
        async def work(serial: str) -> None:
            jobs.update(job_id, step="uninstall")
            store.uninstalled(await look_jobs._sh(store.uninstall_script(serial, p), 180))
            jobs.update(job_id, step="read")
            await _read(dev_id, serial)
        await _run(job_id, dev_id, work)
    return runner
