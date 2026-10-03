"""Eigener Katalog des Rigs: Aus einem Auftrag (nur Namen) wird ein Startbefehl.

Alles Ausführbare kommt aus miners.json, die mit dem Client ausgeliefert wird:
Download-URL, SHA-256, Datei im Archiv, Argumente. Pools nur *.kryptex.network.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

_FILE = Path(__file__).with_name("miners.json")
POOL_DOMAIN = "kryptex.network"
REGION_SUFFIX = {"global": "", "eu": "-eu", "us": "-us", "br": "-br", "sg": "-sg",
                 "hk": "-hk", "ru": "-ru", "ae": "-ae"}
_WORKER_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,31}$")
_USER_RE = re.compile(r"^[A-Za-z0-9._@+\-]{1,128}$")
API_PORT = 4068


class JobError(ValueError):
    pass


@lru_cache(maxsize=1)
def data() -> dict:
    return json.loads(_FILE.read_text(encoding="utf-8"))


def miner(name: str) -> dict:
    m = data()["miners"].get(name)
    if not m:
        raise JobError("unknown_miner")
    return m


def build(job: dict, vendor: str) -> dict:
    """Auftrag prüfen und Startbeschreibung bauen. Wirft JobError bei allem Fremden."""
    coin, name, algo = job.get("coin"), job.get("miner"), job.get("algo")
    user, worker, region = job.get("user") or "", job.get("worker") or "", job.get("region") or ""
    entry = data()["coins"].get(coin)
    if not entry:
        raise JobError("unknown_coin")
    if [name, algo] not in (entry.get("options") or {}).get(vendor, []):
        raise JobError("combination_not_allowed")
    if not _USER_RE.match(user) or not _WORKER_RE.match(worker):
        raise JobError("bad_user_or_worker")
    if region not in REGION_SUFFIX:
        raise JobError("bad_region")
    m = miner(name)
    pool = f"{coin}{REGION_SUFFIX[region]}.{POOL_DOMAIN}:{entry['port']}"
    values = {"algo": algo, "pool": pool, "user": user, "worker": worker, "port": str(API_PORT)}
    return {"coin": coin, "miner": name, "algo": algo, "pool": pool, "version": m["version"],
            "args": [a.format(**values) for a in m["args"]], "api": m["api"]}
