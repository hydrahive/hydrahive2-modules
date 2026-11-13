"""Aufträge „Auf den Fernseher schieben“ und „Zurück zum Original“ (PLAN-E1.md Baustein 6).

Aufspielen nur mit Rückfrage-Kennzeichen, nur mit dem zuletzt gelungenen Bau, nur wenn dessen Prüfsumme im Container
noch stimmt und das Original bekannt ist. Vor dem Aufspielen liest die Vorprüfung (backend/guard.py), ob ein
Einrichtungs-Helfer Home beansprucht (Google TV), und schaltet ihn ab, solange das Original noch Home ist – vermerkt in
`extra_disabled`. Danach wird vom Gerät zurückgelesen, wer Home ist. Springt Home nicht um oder scheitert ein Schritt
nach der Vorprüfung, geht der Auftrag von selbst zurück zum Original und schaltet den Helfer wieder ein.
Container danach immer angehalten.
"""
from __future__ import annotations

import logging

from hydrahive.containers.incus_client import IncusError
from hydrahive.db.connection import db

from . import build, container, device, guard, incus, install, jobs, network, state

logger = logging.getLogger(__name__)
_FIELDS = "address, adb_port, stock_home, sdk, extra_disabled"


class _Ctx:
    def __init__(self, job_id: str, device_id: str):
        self.job_id, self.device_id, self.step = job_id, device_id, "container"

    def at(self, step: str) -> None:
        self.step = step
        jobs.update(self.job_id, step=step)


def _device(device_id: str) -> dict:
    with db() as conn:
        r = conn.execute(f"SELECT {_FIELDS} FROM module_tvwerkstatt_devices WHERE device_id = ?",
                         (device_id,)).fetchone()
    if r is None:
        raise install.TvwInstallError("tvw_device_not_found")
    return {"address": r[0], "port": int(r[1]), "stock": r[2], "sdk": int(r[3] or 0),
            "extras": guard.extras(r[4] or "")}


def good_build() -> dict | None:
    return next((b for b in state.builds() if b["state"] == "done" and b["part"] == "launcher"), None)


async def _sh(script: str, timeout: float = 180.0) -> str:
    """Als Bau-Nutzer im Container; adb-Fehler stehen in der Ausgabe, nicht im Exit-Code."""
    try:
        rc, out, err = await incus.run(
            "exec", container.NAME, "--cwd", "/home/ubuntu", "--user", "1000", "--group", "1000", "--env",
            "HOME=/home/ubuntu", "--", "bash", "-c", script, timeout=timeout)
    except IncusError as exc:
        raise install.TvwInstallError("tvw_adb_closed", str(exc)[-200:]) from None
    return f"{out}\n{err}"


def _set_extras(device_id: str, pkgs: list[str]) -> None:
    with db() as conn:
        conn.execute("UPDATE module_tvwerkstatt_devices SET extra_disabled = ? WHERE device_id = ?",
                     (",".join(pkgs), device_id))
        conn.commit()


def _save(device_id: str, home: str, build_row: dict | None) -> None:
    with db() as conn:
        conn.execute("UPDATE module_tvwerkstatt_devices SET current_home = ?, "
                     "checked_at = strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE device_id = ?", (home, device_id))
        if build_row is not None:
            conn.execute("INSERT INTO module_tvwerkstatt_installed (device_id, package, build_id, sha256) "
                         "VALUES (?, ?, ?, ?) ON CONFLICT(device_id, package) DO UPDATE SET build_id = excluded.build_id, "
                         "sha256 = excluded.sha256, installed_at = strftime('%Y-%m-%dT%H:%M:%SZ','now')",
                         (device_id, install.OUR, build_row["build_id"], build_row["sha256"]))
        conn.commit()


async def _prepare(ctx: _Ctx) -> tuple[dict, str]:
    dev = _device(ctx.device_id)
    serial = device.target(dev["address"], dev["port"], network._host_addresses())
    if await container.status() == "missing":
        raise install.TvwInstallError("tvw_not_set_up")
    await network.sync_rules(state.device_targets())
    await container.ensure_running()
    await container.wait_for_address()
    return dev, serial


async def _restore(ctx: _Ctx, serial: str, stock_pkg: str, extras: list[str]) -> str:
    """Original (und was die Vorprüfung abgeschaltet hat) zurück; der Vermerk fällt nur, wenn Home wieder stimmt."""
    ctx.at("restore")
    out = await _sh(install.restore_script(serial, stock_pkg, tuple(extras)))
    install.require_open(out)
    home = install.home_of(out)
    _save(ctx.device_id, home, None)
    if home == stock_pkg:
        _set_extras(ctx.device_id, [])
    return home


async def _guard(ctx: _Ctx, serial: str, stock_pkg: str, pkgs: list[str]) -> None:
    """Vorgemerkte Abschaltungen ausführen, solange das Original Home ist, und zurücklesen."""
    if not pkgs:
        return
    home = install.home_of(await _sh(guard.disable_script(serial, pkgs)))
    if home != stock_pkg:
        raise install.TvwInstallError("tvw_guard_failed", f"Home: {home or '-'}")


async def _finish(ctx: _Ctx, error: Exception | None = None) -> None:
    if isinstance(error, (install.TvwInstallError, device.TvwDeviceError, network.TvwNetworkError,
                          container.TvwContainerError)):
        jobs.finish(ctx.job_id, error=error.code, step=ctx.step, detail=getattr(error, "detail", ""))
    elif error is not None:
        logger.error("TV-Werkstatt: Auftrag am Fernseher gescheitert: %r", error)
        jobs.finish(ctx.job_id, error="tvw_install_failed", step=ctx.step)
    else:
        jobs.finish(ctx.job_id)
    try:
        await container.stop()
    except container.TvwContainerError:
        logger.warning("TV-Werkstatt: Container nicht angehalten")


async def run_install(job_id: str, device_id: str) -> None:
    ctx, err = _Ctx(job_id, device_id), None
    try:
        b = good_build()
        if b is None:
            raise install.TvwInstallError("tvw_no_build")
        dev, serial = await _prepare(ctx)
        stock_pkg = install.stock(dev["stock"])
        if dev["sdk"] and dev["sdk"] < device.MIN_SDK:
            raise device.TvwDeviceError("tvw_sdk_too_old")
        ctx.at("verify")
        if f"__TVW__ sha256={b['sha256']}" not in await _sh(build.COLLECT_SCRIPT, 120):
            raise install.TvwInstallError("tvw_build_changed")
        ctx.at("guard")
        pkgs = guard.plan(await _sh(guard.read_script(serial)), stock_pkg)   # nur lesen; Fehler → nichts geändert
        extras = sorted(set(dev["extras"]) | set(pkgs))
        _set_extras(device_id, extras)                                       # erst vermerken, dann abschalten
        try:
            await _guard(ctx, serial, stock_pkg, pkgs)
            await _hand_over(ctx, serial, stock_pkg, extras, b)
        except Exception as exc:                      # noqa: BLE001 - nach der Vorprüfung immer zurück
            raise await _roll_back(ctx, serial, stock_pkg, extras, exc) from None
    except Exception as exc:                          # noqa: BLE001 - jeder Fehler endet im Auftrag, nie still
        err = exc
    await _finish(ctx, err)


async def _roll_back(ctx: _Ctx, serial: str, stock_pkg: str, extras: list[str], exc: Exception) -> Exception:
    """Hat die Vorprüfung etwas abgeschaltet, kommt es wieder an. Scheitert auch das, sagt der Fehler es."""
    code = getattr(exc, "code", "")
    if not extras or code in ("tvw_home_not_switched", "tvw_restore_incomplete"):
        return exc                                    # nichts abgeschaltet, oder der Rückweg lief schon
    try:
        back = await _restore(ctx, serial, stock_pkg, extras)
    except Exception:                                 # noqa: BLE001
        back = ""
    detail = f"{getattr(exc, 'detail', '') or code or type(exc).__name__} | zurück: {back or '-'}"
    return install.TvwInstallError((code or "tvw_install_failed") if back == stock_pkg else "tvw_restore_incomplete",
                                   detail.strip(" |")[:300])


async def _hand_over(ctx: _Ctx, serial: str, stock_pkg: str, extras: list[str], b: dict) -> None:
    ctx.at("push")
    install.check_installed(await _sh(install.push_script(serial), 300))
    ctx.at("start")
    install.check_started(await _sh(install.start_script(serial)))
    ctx.at("switch")
    home = install.home_of(await _sh(install.switch_script(serial, stock_pkg)))
    if home != install.OUR:
        back = await _restore(ctx, serial, stock_pkg, extras)
        raise install.TvwInstallError("tvw_home_not_switched" if back == stock_pkg else "tvw_restore_incomplete",
                                      f"Home: {home or '-'} → {back or '-'}")
    _save(ctx.device_id, home, b)


async def run_restore(job_id: str, device_id: str) -> None:
    ctx, err = _Ctx(job_id, device_id), None
    try:
        dev, serial = await _prepare(ctx)
        stock_pkg = install.stock(dev["stock"])
        if await _restore(ctx, serial, stock_pkg, dev["extras"]) != stock_pkg:
            raise install.TvwInstallError("tvw_restore_incomplete")
    except Exception as exc:                          # noqa: BLE001
        err = exc
    await _finish(ctx, err)
