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
GROUP_PORTS = {"nvidia": 4068, "amd": 4069}
# Nur auf den Karten der eigenen Gruppe schürfen (gemischte Rechner). rigel ist ohnehin nur NVIDIA.
# AMD-Gruppe zusätzlich ohne CUDA: SRBMiner 3.7.1 schürft trotz --disable-gpu-nvidia auf der
# NVIDIA-Karte weiter (auf wks197 gemessen). AMD läuft über OpenCL/ROCm, braucht kein CUDA.
GROUP_ENV = {"amd": {"CUDA_VISIBLE_DEVICES": ""}}
# AMD ohne ROCm: Mesa-OpenCL (rusticl, Paket mesa-opencl-icd) meldet Grafikkarten nur mit
# RUSTICL_ENABLE. Gilt auch für Rechner nur mit AMD. Stört ROCm/amdgpu-pro nicht.
AMD_ENV = {"RUSTICL_ENABLE": "radeonsi"}
DEVICE_FILTER = {
    "lolminer": {"nvidia": ["--devices", "NVIDIA"], "amd": ["--devices", "AMD"]},
    "srbminer": {"nvidia": ["--disable-gpu-amd", "--disable-gpu-intel"],
                 "amd": ["--disable-gpu-nvidia", "--disable-gpu-intel"]},
}


def api_port(group: str | None) -> int:
    return GROUP_PORTS.get(group or "", API_PORT)


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


def build(job: dict, vendor: str, *, mixed: bool = False, group: str | None = None) -> dict:
    """Auftrag prüfen und Startbeschreibung bauen. Wirft JobError bei allem Fremden.

    ``mixed``: Rechner hat Karten beider Hersteller → Miner nur auf Karten von ``vendor``,
    eigener API-Port und Worker-Name ``<rechner>-<hersteller>`` (Kryptex zählt getrennt).
    """
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
    port = api_port(group if mixed else None)
    if mixed:
        worker = f"{worker}-{vendor}"[:40]
    values = {"algo": algo, "pool": pool, "user": user, "worker": worker, "port": str(port)}
    args = [a.format(**values) for a in m["args"]]
    env: dict[str, str] = dict(AMD_ENV) if vendor == "amd" else {}
    if mixed:
        args += DEVICE_FILTER.get(name, {}).get(vendor, [])
        env.update(GROUP_ENV.get(vendor, {}))
    # Eigene Log-Datei für Miner, die ohne Terminal nichts ausgeben (SRBMiner); Pfad setzt der Runner.
    log_args = list(m.get("log_args") or [])
    log_file = (f"{name}.log" if not mixed else f"{name}-{vendor}.log") if log_args else None
    return {"coin": coin, "miner": name, "algo": algo, "pool": pool, "version": m["version"],
            "args": args, "api": m["api"], "api_port": port, "env": env, "log_args": log_args,
            "log_file": log_file}
