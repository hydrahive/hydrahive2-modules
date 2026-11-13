"""Aufträge „Abschalten“ und „Einschalten / Alles zurück“ für Entrümpeln (Teil 2). Nur mit Rückfrage (Routen).

Abschalten: Schutzprüfung am Gerät (nichts geändert, wenn ein gewähltes Paket nicht weg darf) → Sicherung des Stands
vor der ersten Änderung → in Schüben zu 4: erst vermerken, dann abschalten, zurücklesen. Ist ein Paket danach nicht aus
oder Home ein anderes als vorher, wird alles aus diesem Auftrag sofort wieder eingeschaltet. Einschalten nimmt Vermerke
erst weg, wenn das Paket zurückgelesen wieder an ist. Container danach immer aus.
"""
from __future__ import annotations

import json

from hydrahive.db.connection import db

from . import debloat_jobs, debloat_switch, jobs, look_jobs, state

SW = debloat_switch


def _stock(device_id: str) -> str:
    return next((d.get("stock_home") or "" for d in state.devices() if d["device_id"] == device_id), "")


def ours(device_id: str) -> list[str]:
    with db() as conn:
        rows = conn.execute("SELECT package FROM module_tvwerkstatt_debloat_changes WHERE device_id = ? "
                            "ORDER BY changed_at, package", (device_id,)).fetchall()
    return [r[0] for r in rows]


def _mark(device_id: str, pkgs: list[str], *, add: bool) -> None:
    with db() as conn:
        for p in pkgs:
            if add:
                conn.execute("INSERT OR IGNORE INTO module_tvwerkstatt_debloat_changes (device_id, package) "
                             "VALUES (?, ?)", (device_id, p))
            else:
                conn.execute("DELETE FROM module_tvwerkstatt_debloat_changes WHERE device_id = ? AND package = ?",
                             (device_id, p))
        conn.commit()


def backup_of(device_id: str) -> dict | None:
    with db() as conn:
        r = conn.execute("SELECT packages, taken_at FROM module_tvwerkstatt_debloat_backup WHERE device_id = ?",
                         (device_id,)).fetchone()
    return {"packages": json.loads(r[0]), "taken_at": r[1]} if r else None


async def _fresh(device_id: str, serial: str) -> dict[str, str]:
    """Aktuellen Stand lesen, als gelesenen Stand speichern; erste Sicherung anlegen, falls noch keine da ist."""
    ident, packages = debloat_jobs.parse_read(await look_jobs._sh(debloat_jobs.read_script(serial), 120))
    debloat_jobs._store(device_id, ident, packages)
    with db() as conn:
        conn.execute("INSERT OR IGNORE INTO module_tvwerkstatt_debloat_backup (device_id, packages) VALUES (?, ?)",
                     (device_id, json.dumps(packages)))
        conn.commit()
    return packages


async def _switch(serial: str, pkgs: list[str], *, on: bool) -> tuple[set[str], str]:
    return SW.read_back(await look_jobs._sh(SW.switch_script(serial, pkgs, on=on), 180))


async def _turn_off(job_id: str, device_id: str, serial: str, pkgs: list[str]) -> None:
    jobs.update(job_id, step="guard")
    out = await look_jobs._sh(SW.guard_script(serial, pkgs), 180)
    why = SW.blocked(out, pkgs)
    if why:
        raise SW.TvwDebloatError("tvw_debloat_blocked", ", ".join(f"{p}: {w}" for p, w in why.items())[:500])
    home = debloat_jobs.install.home_of(out)
    jobs.update(job_id, step="backup")
    await _fresh(device_id, serial)
    done: list[str] = []
    for i, part in enumerate(SW.batches(pkgs), 1):
        jobs.update(job_id, step=f"batch {i}")
        _mark(device_id, part, add=True)                          # erst vermerken, dann abschalten
        off, now_home = await _switch(serial, part, on=False)
        done += part
        missing = [p for p in part if p not in off]
        if missing or now_home != home:
            jobs.update(job_id, step="restore")
            back_off, back_home = await _switch(serial, done, on=True)
            _mark(device_id, [p for p in done if p not in back_off], add=False)
            code = "tvw_debloat_home_changed" if now_home != home else "tvw_debloat_not_off"
            if back_home != home or any(p in back_off for p in done):
                code = "tvw_debloat_restore_incomplete"
            raise SW.TvwDebloatError(code, f"Home {home} → {now_home or '-'}; nicht aus: {', '.join(missing)}"[:500])


async def _turn_on(job_id: str, device_id: str, serial: str, pkgs: list[str]) -> None:
    for i, part in enumerate(SW.batches(pkgs), 1):
        jobs.update(job_id, step=f"batch {i}")
        off, _ = await _switch(serial, part, on=True)
        _mark(device_id, [p for p in part if p not in off], add=False)
        still = [p for p in part if p in off]
        if still:
            raise SW.TvwDebloatError("tvw_debloat_not_on", ", ".join(still)[:500])


async def run_switch(job_id: str, device_id: str, pkgs: list[str], on: bool) -> None:
    err = None
    try:
        serial = await look_jobs._ready(device_id)
        await (_turn_on if on else _turn_off)(job_id, device_id, serial, pkgs)
        jobs.update(job_id, step="read")
        await _fresh(device_id, serial)
    except Exception as exc:                          # noqa: BLE001 - jeder Fehler endet im Auftrag
        err = exc
    await look_jobs._finish(job_id, err)


def prepare(device_id: str, pkgs: list[str] | None, *, on: bool) -> list[str]:
    """Pakete für einen Auftrag prüfen. `None` beim Einschalten = alles, was die Werkstatt abgeschaltet hat."""
    if on and pkgs is None:
        pkgs = ours(device_id)
        if not pkgs:
            raise SW.TvwDebloatError("tvw_debloat_nothing")
    return SW.clean(list(pkgs or []), _stock(device_id))
