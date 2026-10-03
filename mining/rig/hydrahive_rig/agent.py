"""Koppeln und Melde-Schleife.

Alle ``INTERVAL`` Sekunden: Karte lesen → Miner-Zustand (runner.tick) →
melden → Soll-Zustand anwenden (runner.apply). Bei Fehlern wartet der Rig
länger, statt den Server zu fluten. Ist der Server länger als
``OFFLINE_STOP_SECONDS`` weg und war das zuletzt verlangt (Energie-Steuerung
aktiv), stoppt der Rig den Miner — sonst schürft er weiter.
"""
from __future__ import annotations

import logging
import platform
import socket
import time
from pathlib import Path

from . import __version__, gpu
from .client import ClientError, Server
from .config import RigConfig
from .runner import Runner

logger = logging.getLogger("hydrahive_rig")

INTERVAL = 30
MAX_BACKOFF = 300
OFFLINE_STOP_SECONDS = 900
_STATIC = ("gpu_vendor", "gpu_model", "gpu_mem_mb", "driver")
_LIVE = ("temp_c", "power_w", "fan_pct", "util_pct")


def _os_name() -> str:
    try:
        rel = platform.freedesktop_os_release()
        return rel.get("PRETTY_NAME") or rel.get("NAME") or platform.system()
    except (OSError, AttributeError):
        return platform.system()


def system_info(card: dict) -> dict:
    return {"hostname": socket.gethostname(), "os": _os_name(), "client_version": __version__,
            **{k: card.get(k) for k in _STATIC}}


def enroll(server: str, code: str, pin: str | None) -> RigConfig:
    card = gpu.detect()
    resp = Server(server, pin).post("/enroll", {"info": system_info(card)}, {"X-Pairing-Code": code})
    return RigConfig(server=server, token=resp["token"], name=resp["name"], rig_id=resp["rig_id"], pin=pin)


def group_states(card: dict, runners: dict[str, Runner]) -> dict[str, dict]:
    """Zustand je Hersteller-Gruppe: Karten-Zusammenfassung + Miner-Zustand."""
    out = {}
    for vendor, grp in (card.get("groups") or {}).items():
        st = {"gpu_count": grp.get("gpu_count", 0), "gpu_model": grp.get("gpu_model"),
              "gpu_mem_mb": grp.get("gpu_mem_mb"), **{k: grp.get(k) for k in _LIVE}}
        r = runners.get(vendor)
        if r is not None:
            st.update(r.tick(grp.get("power_w")))
        out[vendor] = st
    return out


def apply_desired(runners: dict[str, Runner], desired: dict) -> None:
    """Soll vom Server an die Gruppen verteilen.

    Neuer Server: ``desired["groups"][vendor]``; fehlt eine Gruppe → stoppen.
    Alter Server (ohne ``groups``): flaches Soll gilt für die einzige Gruppe.
    """
    groups = desired.get("groups")
    for vendor, r in runners.items():
        if isinstance(groups, dict):
            r.apply(groups.get(vendor) or {"action": "stop"})
        elif len(runners) == 1:
            r.apply(desired)
        else:
            r.apply({"action": "stop"})       # gemischter Rechner an altem Server: nicht raten


def _summary(desired: dict) -> str:
    def one(d: dict) -> str:
        return f"{d.get('action')} {(d.get('job') or {}).get('coin') or ''} ({d.get('reason')})".replace("  ", " ")
    groups = desired.get("groups")
    if isinstance(groups, dict) and groups:
        return " · ".join(f"{v}: {one(g)}" for v, g in sorted(groups.items()))
    return one(desired)


def make_runners(state_dir: Path, card: dict) -> dict[str, Runner]:
    groups = list(card.get("groups") or {})
    mixed = len(groups) > 1
    return {v: Runner(state_dir, v, group=v, mixed=mixed) for v in groups}


def report_once(cfg: RigConfig, runners: dict[str, Runner] | Runner | None = None) -> dict:
    card = gpu.detect()
    if isinstance(runners, Runner):                     # Aufrufer mit einem Runner (Tests, alte Pfade)
        runners = {runners.vendor: runners}
    runners = runners or {}
    state = {"miner": "idle", "gpu_count": card.get("gpu_count", 0), "gpus": card.get("gpus") or [],
             **{k: card.get(k) for k in _LIVE}}
    groups = group_states(card, runners)
    state["groups"] = groups
    if len(groups) == 1:                                # flach wie bisher → alte Server verstehen es
        only = next(iter(groups.values()))
        state.update({k: v for k, v in only.items() if k not in ("gpu_count", "gpu_model", "gpu_mem_mb")})
    return Server(cfg.server, cfg.pin).post(
        "/report", {"info": system_info(card), "state": state},
        {"Authorization": f"Bearer {cfg.token}"},
    )


def next_delay(failures: int) -> int:
    return INTERVAL if failures == 0 else min(MAX_BACKOFF, INTERVAL * 2 ** min(failures, 4))


def run_forever(cfg: RigConfig, *, state_dir: Path | None = None, sleep=time.sleep, clock=time.monotonic,
                runner: Runner | dict[str, Runner] | None = None, once: bool = False) -> None:
    runners: dict[str, Runner] = {}
    if isinstance(runner, Runner):
        runners = {runner.vendor: runner}
    elif isinstance(runner, dict):
        runners = runner
    elif state_dir is not None:
        runners = make_runners(state_dir, gpu.detect())
    failures, last_action, last_ok, stop_offline = 0, None, clock(), False
    while True:
        try:
            resp = report_once(cfg, runners)
            failures, last_ok = 0, clock()
            desired = resp.get("desired") or {}
            stop_offline = bool(desired.get("stop_when_offline"))
            apply_desired(runners, desired)
            summary = _summary(desired)
            if summary != last_action:
                logger.info("Soll-Zustand: %s", summary)
                last_action = summary
        except ClientError as exc:
            failures += 1
            if exc.status == 401:
                logger.error("Server lehnt diesen Rig ab (gesperrt?). Neu koppeln nötig.")
                failures = 4
                apply_desired(runners, {"action": "stop", "groups": {}})
            else:
                logger.warning("Melden fehlgeschlagen: %s", exc)
        except OSError as exc:
            failures += 1
            logger.warning("Server nicht erreichbar: %s", exc)
        if runners and stop_offline and clock() - last_ok > OFFLINE_STOP_SECONDS:
            if any(r.proc is not None for r in runners.values()):
                logger.warning("Server seit %d min weg und Energie-Steuerung aktiv → Miner aus.",
                               OFFLINE_STOP_SECONDS // 60)
            apply_desired(runners, {"action": "stop", "groups": {}})
        if once:
            return
        sleep(next_delay(failures))
