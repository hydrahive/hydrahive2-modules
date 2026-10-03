"""Miner-Katalog — dieselbe Datei wie beim Rig (rig/hydrahive_rig/miners.json).

Sicherheitsmodell: Der Server schickt dem Rig nur ``coin``, ``miner``,
``algo``, Pool-Region, Benutzer und Worker. Download-URL, SHA-256 und die
Startargumente nimmt der Rig ausschließlich aus seinem eigenen Katalog. Ein
manipulierter Server kann den Rig damit nicht zu fremden Programmen oder
Pools bringen. Der Server nutzt den Katalog nur, um zu planen.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

_FILE = Path(__file__).resolve().parents[1] / "rig" / "hydrahive_rig" / "miners.json"
_WORKER_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,31}$")
_USER_RE = re.compile(r"^[A-Za-z0-9._@+\-]{1,128}$")
REGIONS = ("global", "eu", "us", "br", "sg", "hk", "ru", "ae")


@lru_cache(maxsize=1)
def data() -> dict:
    return json.loads(_FILE.read_text(encoding="utf-8"))


def miners() -> dict[str, dict]:
    return data()["miners"]


def coins() -> list[str]:
    return sorted(data()["coins"])


def family(coin: str) -> str:
    return data()["coins"][coin]["family"]


def min_mem_mb(coin: str) -> int | None:
    """Mindest-Grafikspeicher für den Coin (z. B. Cuckaroo29 ≥ 6 GB), sonst None."""
    v = (data()["coins"].get(coin) or {}).get("min_mem_mb")
    return int(v) if isinstance(v, int) and v > 0 else None


def options(coin: str, vendor: str) -> list[tuple[str, str]]:
    """[(miner, algo), …] in Vorzugsreihenfolge für Coin + Hersteller."""
    entry = data()["coins"].get(coin) or {}
    return [(m, a) for m, a in (entry.get("options") or {}).get(vendor, [])]


def job(coin: str, miner: str, algo: str, *, user: str, worker: str, region: str) -> dict:
    """Auftrag an den Rig — nur Namen, keine Befehle. Geprüft gegen den Katalog."""
    if not _USER_RE.match(user or ""):
        raise ValueError("kryptex_user_invalid")
    if not _WORKER_RE.match(worker or ""):
        raise ValueError("worker_invalid")
    if region not in REGIONS:
        raise ValueError("region_invalid")
    if (miner, algo) not in {(m, a) for v in ("nvidia", "amd") for m, a in options(coin, v)}:
        raise ValueError("combination_not_in_catalog")
    return {"coin": coin, "miner": miner, "algo": algo, "user": user, "worker": worker, "region": region,
            "version": miners()[miner]["version"]}
