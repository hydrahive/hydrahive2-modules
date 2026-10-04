"""AMD-Zusatzinfos: Kartenname aus libdrm und ob ein OpenCL-Treiber für AMD da ist.

Name: amdgpu liefert ``product_name`` nur für Profi-Karten. Für alle anderen steht
er in ``amdgpu.ids`` (kommt mit libdrm/Mesa, bei Ubuntu/Debian Standard).
Zeilenformat: ``67DF,<TAB>C5,<TAB>AMD Radeon RX 470 Graphics``.

OpenCL: Die Miner rechnen auf AMD nur über OpenCL. Ubuntu/Debian bringen dafür
keinen Treiber mit; ohne ICD-Datei in /etc/OpenCL/vendors finden sie keine Karte.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

AMDGPU_IDS = [Path("/usr/share/libdrm/amdgpu.ids"), Path("/usr/local/share/libdrm/amdgpu.ids")]
OPENCL_DIRS = [Path("/etc/OpenCL/vendors"), Path("/usr/local/etc/OpenCL/vendors")]
# Bibliotheken, die AMD-Grafikkarten bedienen: Mesa rusticl/clover, ROCm/amdgpu-pro.
_AMD_ICD = ("rusticl", "mesaopencl", "amdocl")


@lru_cache(maxsize=1)
def ids_table() -> dict[tuple[str, str], str]:
    for p in AMDGPU_IDS:
        try:
            text = p.read_bytes().decode("utf-8", "replace")
        except OSError:
            continue
        out: dict[tuple[str, str], str] = {}
        for line in text.splitlines():
            parts = [x.strip() for x in line.split(",", 2)]
            if len(parts) == 3 and all(parts) and not line.startswith("#"):
                out.setdefault((parts[0].upper(), parts[1].upper()), parts[2][:80])
        return out
    return {}


def _hex(v: str | None) -> str:
    return (v or "").strip().lower().removeprefix("0x").upper()


def name(device: str | None, revision: str | None) -> str | None:
    """Name zu Gerät/Revision; Revision unbekannt → erster Name des Geräts mit „(?)“; sonst None."""
    table, dev, rev = ids_table(), _hex(device), _hex(revision)
    if not dev:
        return None
    if (dev, rev) in table:
        return table[(dev, rev)]
    family = next((n for (d, _), n in table.items() if d == dev), None)
    return f"{family} (?)" if family else None


def opencl(dirs: list[Path] | None = None) -> str:
    """„ok“, wenn ein OpenCL-Treiber für AMD-Karten eingetragen ist, sonst „missing“."""
    for d in OPENCL_DIRS if dirs is None else dirs:
        try:
            icds = list(d.glob("*.icd"))
        except OSError:
            continue
        for icd in icds:
            try:
                lib = icd.read_text(errors="replace").strip().lower()
            except OSError:
                continue
            if any(k in lib for k in _AMD_ICD):
                return "ok"
    return "missing"
