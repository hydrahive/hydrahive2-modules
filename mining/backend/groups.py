"""Vendor groups of a rig (mixed AMD + NVIDIA rigs).

Each group has its own measurements and its own assignment. Storage uses the key
``<rig_id>#<vendor>``; a rig with only one vendor keeps its plain ``rig_id``,
so existing measurements and history stay valid (no data migration needed).
"""
from __future__ import annotations

VENDORS = ("nvidia", "amd")
SEP = "#"


def vendors_of(rig: dict, state: dict | None = None) -> list[str]:
    """Vendors present in this rig, from the report (``state.groups``) or the stored vendor."""
    groups = (state or {}).get("groups") if isinstance(state, dict) else None
    if not isinstance(groups, dict) or not groups:
        last = rig.get("last_report_obj") or rig.get("last_report")
        groups = last.get("groups") if isinstance(last, dict) else None   # aus der DB ggf. noch JSON-Text
    found = [v for v in VENDORS if isinstance(groups, dict) and v in groups]
    if found:
        return found
    v = rig.get("gpu_vendor") or ""
    return [v] if v in VENDORS else []


def is_mixed(rig: dict, state: dict | None = None) -> bool:
    return len(vendors_of(rig, state)) > 1


def key(rig_id: str, vendor: str, mixed: bool) -> str:
    """Storage key of the group: plain ID for single-vendor rigs (compatible with before)."""
    return f"{rig_id}{SEP}{vendor}" if mixed else rig_id


def keys(rig: dict, state: dict | None = None) -> dict[str, str]:
    """{vendor: storage key} for every group in the rig."""
    vs = vendors_of(rig, state)
    mixed = len(vs) > 1
    return {v: key(rig["id"], v, mixed) for v in vs}


def group_state(state: dict, vendor: str, mixed: bool) -> dict:
    """Group's report data; old/single-vendor clients report flat (whole state)."""
    groups = state.get("groups") if isinstance(state, dict) else None
    if isinstance(groups, dict) and isinstance(groups.get(vendor), dict):
        return groups[vendor]
    return state if not mixed else {}


def mem_mb(rig: dict, state: dict, vendor: str, mixed: bool) -> int | None:
    g = group_state(state, vendor, mixed)
    v = g.get("gpu_mem_mb") if mixed else (g.get("gpu_mem_mb") or rig.get("gpu_mem_mb"))
    return int(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0 else rig.get("gpu_mem_mb")


def overview(rig: dict) -> list[dict]:
    """Je Gruppe: Zuteilung + Messfortschritt (für Rechner-Liste und Buddy)."""
    from . import compat, runtime_store
    from .rigs import bench_total
    state = rig.get("last_report") if isinstance(rig.get("last_report"), dict) else {}
    ks = keys(rig, state)
    mixed = len(ks) > 1
    known = compat.known_coins(rig.get("client_version"))
    out = []
    for vendor, k in ks.items():
        a, since, _ = runtime_store.get_assignment(k)
        bench, failed = runtime_store.bench_for(k)
        bench = {p: v for p, v in bench.items() if p[0] in known}          # nur was der Client kennt
        failed = {p for p in failed if p[0] in known}
        g = group_state(state or {}, vendor, mixed)
        out.append({"vendor": vendor, "key": k, "gpu_count": g.get("gpu_count"), "gpu_model": g.get("gpu_model"),
                    "hashrate": g.get("hashrate"), "power_w": g.get("power_w"),
                    "assignment": ({"mode": a.mode, "coin": a.coin, "miner": a.miner, "reason": a.reason,
                                    "since": since.isoformat() if since else None} if a else None),
                    "bench_done": len(bench), "bench_failed": len(failed),
                    "bench_total": bench_total(vendor, mem_mb(rig, state or {}, vendor, mixed), known)})
    return out
