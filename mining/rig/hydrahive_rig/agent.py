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


def report_once(cfg: RigConfig, runner: Runner | None = None) -> dict:
    card = gpu.detect()
    state = {"miner": "idle", "gpu_count": card.get("gpu_count", 0), **{k: card.get(k) for k in _LIVE}}
    if runner is not None:
        state.update(runner.tick(card.get("power_w")))
    return Server(cfg.server, cfg.pin).post(
        "/report", {"info": system_info(card), "state": state},
        {"Authorization": f"Bearer {cfg.token}"},
    )


def next_delay(failures: int) -> int:
    return INTERVAL if failures == 0 else min(MAX_BACKOFF, INTERVAL * 2 ** min(failures, 4))


def run_forever(cfg: RigConfig, *, state_dir: Path | None = None, sleep=time.sleep, clock=time.monotonic,
                runner: Runner | None = None, once: bool = False) -> None:
    if runner is None and state_dir is not None:
        runner = Runner(state_dir, gpu.detect().get("gpu_vendor") or "none")
    failures, last_action, last_ok, stop_offline = 0, None, clock(), False
    while True:
        try:
            resp = report_once(cfg, runner)
            failures, last_ok = 0, clock()
            desired = resp.get("desired") or {}
            stop_offline = bool(desired.get("stop_when_offline"))
            if runner is not None:
                runner.apply(desired)
            summary = (desired.get("action"), (desired.get("job") or {}).get("coin"))
            if summary != last_action:
                logger.info("Soll-Zustand: %s %s (%s)", summary[0], summary[1] or "", desired.get("reason"))
                last_action = summary
        except ClientError as exc:
            failures += 1
            if exc.status == 401:
                logger.error("Server lehnt diesen Rig ab (gesperrt?). Neu koppeln nötig.")
                failures = 4
                if runner is not None:
                    runner.apply({"action": "stop"})
            else:
                logger.warning("Melden fehlgeschlagen: %s", exc)
        except OSError as exc:
            failures += 1
            logger.warning("Server nicht erreichbar: %s", exc)
        if runner is not None and stop_offline and clock() - last_ok > OFFLINE_STOP_SECONDS:
            if runner.proc is not None:
                logger.warning("Server seit %d min weg und Energie-Steuerung aktiv → Miner aus.",
                               OFFLINE_STOP_SECONDS // 60)
            runner.apply({"action": "stop"})
        if once:
            return
        sleep(next_delay(failures))
