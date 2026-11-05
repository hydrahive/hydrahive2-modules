"""Platzgrenze (PLAN-V1.md Entscheidung 5, Baustein 7).

`size=` greift auf dem `dir`-Pool nicht; das Modul misst darum selbst mit einem fest eingetragenen Befehl im Container.
Über der Grenze wird kein Agentenlauf mehr gestartet. KEIN lückenloser Schutz: ein einzelner Lauf kann innerhalb einer
Runde füllen. Echter Schutz wäre ein Pool-Typ mit Quota (btrfs/zfs/lvm), siehe Task „Server-Hardware“.
Unlesbare oder fehlgeschlagene Messung gilt als „nicht ok“ – lieber einmal zu streng als einen vollen Container
weiterbearbeiten.
"""
from __future__ import annotations

import re

from . import container, incus
from .version_text import _CTRL

GB = 1024 ** 3
MAX_BYTES = 5 * GB
_MAX_PLAUSIBLE_KIB = 2 ** 40                       # 1 PiB: darüber ist die Ausgabe Unsinn
_DU = ["exec", "{name}", "--", "bash", "-c", "du -sk -- /work 2>/dev/null | head -1"]
_TOP = ["exec", "{name}", "--", "bash", "-c",
        "cd /work && du -sk -- * .[!.]* 2>/dev/null | sort -rn | head -5"]
_LINE = re.compile(r"^(\d{1,15})\t(.+)$")


def _args(template: list[str], name: str) -> list[str]:
    return [name if a == "{name}" else a for a in template]


def _kib(out: str) -> int | None:
    m = _LINE.match((out or "").strip().splitlines()[0]) if (out or "").strip() else None
    if not m:
        return None
    kib = int(m.group(1))
    return kib if kib <= _MAX_PLAUSIBLE_KIB else None            # Regex lässt nur Ziffern zu: negativ ist unmöglich


def _top(out: str) -> list[dict]:
    rows: list[dict] = []
    for line in (out or "").splitlines():
        m = _LINE.match(line.strip("\r"))
        if not m:
            continue
        name = _CTRL.sub("", m.group(2)).strip()
        name = name if len(name) <= 80 else name[:79] + "…"
        if name:
            rows.append({"name": name, "bytes": int(m.group(1)) * 1024})
    return rows[:5]


async def check(project_id: str, *, detail: bool = False) -> dict:
    """{"ok", "bytes", "limit"[, "top"]}. Wirft VibeError nur bei ungültiger Projekt-ID (name_for)."""
    name = container.name_for(project_id)
    rc, out, _ = await incus.run(*_args(_DU, name), timeout=60)
    kib = _kib(out) if rc == 0 else None
    result: dict = {"ok": kib is not None and kib * 1024 <= MAX_BYTES,
                    "bytes": None if kib is None else kib * 1024, "limit": MAX_BYTES}
    if detail and not result["ok"] and kib is not None:
        rc2, out2, _ = await incus.run(*_args(_TOP, name), timeout=60)
        result["top"] = _top(out2) if rc2 == 0 else []
    return result


def message(result: dict) -> str:
    """Text für den Chat: Größe und Grenze, keine Pfade, keine Projekt-ID."""
    if result.get("bytes") is None:
        return "Ich konnte nicht prüfen, wie viel Platz das Projekt belegt, und mache deshalb nicht weiter."
    have, limit = result["bytes"] / GB, result["limit"] / GB
    text = f"Das Projekt ist mit {have:.1f} GB größer als erlaubt ({limit:.0f} GB). Ich mache erst weiter, wenn Platz frei ist."
    top = result.get("top") or []
    if top:
        text += " Am meisten belegen: " + ", ".join(f"{t['name']} ({t['bytes'] / GB:.1f} GB)" for t in top[:3]) + "."
    return text
