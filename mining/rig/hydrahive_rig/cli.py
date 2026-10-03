"""Kommandozeile: ``hydrahive-rig enroll|run|status``."""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from . import agent, gpu
from .client import ClientError
from .config import DEFAULT_PATH, RigConfig


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="hydrahive-rig")
    p.add_argument("--config", type=Path, default=DEFAULT_PATH)
    p.add_argument("--state", type=Path, default=Path("/var/lib/hydrahive-rig"), help="Miner + Logs")
    sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("enroll", help="mit Kopplungs-Code beim Server anmelden")
    e.add_argument("--server", required=True)
    e.add_argument("--code", required=True)
    e.add_argument("--pin", default=None, help="sha256//… des Server-Schlüssels")
    sub.add_parser("run", help="Melde-Schleife (für systemd)")
    sub.add_parser("status", help="Karte + einmal melden")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s", stream=sys.stdout)
    log = logging.getLogger("hydrahive_rig")

    if args.cmd == "enroll":
        try:
            cfg = agent.enroll(args.server, args.code, args.pin)
        except (ClientError, OSError, ValueError) as exc:
            log.error("Koppeln fehlgeschlagen: %s", exc)
            return 2
        cfg.save(args.config)
        log.info("Gekoppelt als '%s'. Jetzt in HydraHive unter Mining → Rechner freigeben.", cfg.name)
        return 0

    try:
        cfg = RigConfig.load(args.config)
    except (OSError, ValueError, TypeError) as exc:
        log.error("Konfiguration nicht lesbar (%s). Erst 'hydrahive-rig enroll' ausführen.", exc)
        return 2
    if args.cmd == "status":
        log.info("Karte: %s", json.dumps(gpu.detect(), ensure_ascii=False))
        try:
            log.info("Server: %s", json.dumps(agent.report_once(cfg), ensure_ascii=False))
        except (ClientError, OSError) as exc:
            log.error("Melden fehlgeschlagen: %s", exc)
            return 1
        return 0
    args.state.mkdir(parents=True, exist_ok=True)
    agent.run_forever(cfg, state_dir=args.state)
    return 0
