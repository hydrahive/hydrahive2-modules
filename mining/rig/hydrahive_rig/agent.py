"""Koppeln und Melde-Schleife.

E2: Der Rig meldet alle 30 s Karte + Messwerte und bekommt den Soll-Zustand
zurück. Miner starten/stoppen folgt in E3 — bis dahin wird ``desired`` nur
protokolliert. Bei Fehlern wartet der Rig länger, statt den Server zu fluten.
"""
from __future__ import annotations

import logging
import platform
import socket
import time

from . import __version__, gpu
from .client import ClientError, Server
from .config import RigConfig

logger = logging.getLogger("hydrahive_rig")

INTERVAL = 30
MAX_BACKOFF = 300
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


def report_once(cfg: RigConfig) -> dict:
    card = gpu.detect()
    state = {"miner": "idle", "gpu_count": card.get("gpu_count", 0), **{k: card.get(k) for k in _LIVE}}
    return Server(cfg.server, cfg.pin).post(
        "/report", {"info": system_info(card), "state": state},
        {"Authorization": f"Bearer {cfg.token}"},
    )


def next_delay(failures: int) -> int:
    return INTERVAL if failures == 0 else min(MAX_BACKOFF, INTERVAL * 2 ** min(failures, 4))


def run_forever(cfg: RigConfig, *, sleep=time.sleep, once: bool = False) -> None:
    failures, last_action = 0, None
    while True:
        try:
            resp = report_once(cfg)
            failures = 0
            desired = resp.get("desired") or {}
            if desired != last_action:
                logger.info("Soll-Zustand: %s (%s)", desired.get("action"), desired.get("reason"))
                last_action = desired
        except ClientError as exc:
            failures += 1
            if exc.status == 401:
                logger.error("Server lehnt diesen Rig ab (gesperrt?). Neu koppeln nötig.")
                failures = 4  # langsam weiterversuchen: Freigabe könnte zurückkommen
            else:
                logger.warning("Melden fehlgeschlagen: %s", exc)
        except OSError as exc:
            failures += 1
            logger.warning("Server nicht erreichbar: %s", exc)
        if once:
            return
        sleep(next_delay(failures))
