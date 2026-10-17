"""Entwurf übernehmen (Spec „Bauplan B2“): leeres Drehbuch → neu, sonst Szenen anhängen.

Bestehende Szenen, Shots, Bausteine und gefüllte Kopf-Felder bleiben unverändert. Bausteine gleicher Art und gleichen
Namens werden wiederverwendet. Erst wird der ganze Entwurf geprüft, dann geschrieben.
"""
from __future__ import annotations

from . import _draft, plan, shots


def _elements(pid: str, draft: dict) -> tuple[dict[str, str], int, int]:
    existing = {(e["kind"], e["name"].casefold()): e["id"] for e in plan.list_elements(pid)}
    ids: dict[str, str] = {}
    new = reused = 0
    for e in draft["elements"]:
        found = existing.get((e["kind"], e["name"].casefold()))
        if found:
            reused += 1
        else:
            found = plan.save_element(pid, {"kind": e["kind"], "name": e["name"], "description": e["description"]})["id"]
            existing[(e["kind"], e["name"].casefold())] = found
            new += 1
        ids[e["key"]] = found
    return ids, new, reused


def _head(pid: str, head: dict) -> None:
    cur = plan.get_head(pid)
    patch: dict = {k: head[k] for k in ("title", "logline", "description") if head[k] and not cur[k]}
    if head["style"] and not cur["look"]["style"]:
        patch["look"] = {**cur["look"], "style": head["style"]}
    if patch:
        plan.save_head(pid, patch)


def apply(pid: str, data) -> dict:
    try:
        draft = _draft.clean(data, strict=True)
    except _draft.DraftInvalid as e:
        raise plan.PlanError("studio_draft_invalid") from e
    mode = "append" if plan.list_scenes(pid) else "new"
    ids, new, reused = _elements(pid, draft)
    _head(pid, draft["head"])
    total = 0

    def mapped(keys: list[str]) -> list[str]:
        return [ids[k] for k in keys if k in ids]

    for sc in draft["scenes"]:
        own = mapped(sc["element_keys"])
        # Shots dürfen nur Bausteine ihrer Szene nutzen → was ein Shot zeigt, gehört auch zur Szene
        extra = [i for s in sc["shots"] for i in mapped(s["element_keys"]) if i not in own]
        saved = plan.save_scene(pid, {"title": sc["title"], "description": sc["description"], "location": sc["location"],
                                      "time_of_day": sc["time_of_day"], "element_ids": list(dict.fromkeys(own + extra))})
        if sc["shots"]:
            fresh = [{"shot": s["shot"], "prompt": s["prompt"], "element_ids": mapped(s["element_keys"]),
                      "duration": s["duration"], "status": "planned"} for s in sc["shots"]]
            total += len(shots.save_shots(pid, shots.load_scene(pid, saved["id"]), fresh))
    return {"mode": mode, "scenes": len(draft["scenes"]), "shots": total, "elements_new": new, "elements_reused": reused}
