"""Referenz-Hashraten je Grafikkarte (Kryptex-Angaben) für die Ertragstabelle.

Nur Startwerte, bis ein Rig selbst gemessen hat (E3). Quelle und Datum stehen
in reference_hashrates.json.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_FILE = Path(__file__).with_name("reference_hashrates.json")


@lru_cache(maxsize=1)
def _data() -> dict:
    return json.loads(_FILE.read_text(encoding="utf-8"))


def gpus() -> list[dict]:
    """[{id, name, vendor, watts}] sortiert nach Name."""
    return sorted(
        ({"id": k, "name": v["name"], "vendor": v["vendor"], "watts": v["watts"]}
         for k, v in _data()["gpus"].items()),
        key=lambda g: g["name"],
    )


def hashrates(gpu_id: str) -> dict[str, float] | None:
    g = _data()["gpus"].get(gpu_id)
    return dict(g["hashrates"]) if g else None


def meta() -> dict:
    d = _data()
    return {"source": d["source"], "fetched": d["fetched"], "note": d["note"]}
