"""Freie Bilder ohne Shot (Spec „Bauplan B3“): Beschreibung, Modell, Format, Anzahl 1–4, optional Referenzbilder.

Ein Auftrag je Projekt, die Bilder entstehen nacheinander. Ein fehlgeschlagenes Bild bricht die übrigen nicht ab.
Ablage: studio/media/free/<id>.<ext> mit Begleitdatei. Bild-Aufruf wie in generate.py (gleicher Anbieter).
"""
from __future__ import annotations

import base64
import logging
from datetime import datetime, timezone

from . import image_provider, jobs, plan
from ._store import new_id, project_root, root, safe_rel, write_json
from .generate import _MIME, MAX_REFERENCES

logger = logging.getLogger("hhmod_studio.free_images")

FREE_DIR = "studio/media/free"
MAX_COUNT = 4
MAX_PROMPT = 2000
ASPECTS = ("16:9", "9:16", "1:1", "4:3", "21:9")        # wie im Drehbuch (frontend/planApi.ts ASPECTS)


def _check(data: dict) -> tuple[str, int, str, str, list[str]]:
    prompt, count = data.get("prompt"), data.get("count")
    model, aspect, refs = data.get("model") or "", data.get("aspect_ratio") or "", data.get("references") or []
    ok = (isinstance(prompt, str) and prompt.strip() and len(prompt) <= MAX_PROMPT
          and isinstance(count, int) and not isinstance(count, bool) and 1 <= count <= MAX_COUNT
          and isinstance(model, str) and len(model) <= 200 and (aspect == "" or aspect in ASPECTS) and isinstance(refs, list))
    if not ok:
        raise plan.PlanError("studio_free_invalid")
    return prompt.strip(), count, model.strip(), aspect, [r for r in refs if isinstance(r, str)]


def _references(pid: str, refs: list[str]) -> list[str]:
    """Nur echte Bilder im Projekt, höchstens 3, als data:-URLs."""
    urls: list[str] = []
    for rel in refs:
        if safe_rel(pid, rel, plan.IMAGE_EXT) and len(urls) < MAX_REFERENCES:
            ext = rel.rsplit(".", 1)[-1].lower()
            data = base64.b64encode((project_root(pid) / rel).read_bytes()).decode("ascii")
            urls.append(f"data:{_MIME.get(ext, 'image/png')};base64,{data}")
    return urls


def _one(pid: str, prompt: str, model: str, aspect: str, refs: list[str]) -> str:
    try:
        raw = image_provider.request_image(model=model, prompt=prompt, references=refs, aspect_ratio=aspect)
    except image_provider.ProviderError as e:
        raise jobs.JobFailed(str(e)) from e
    ext = image_provider.image_kind(raw)
    if ext is None:
        raise jobs.JobFailed("bad_image")
    name = f"{new_id()}.{ext}"
    target = root(pid, create=True) / "media" / "free" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    write_json(target.with_name(name + ".json"), {"prompt": prompt, "model": model, "aspect_ratio": aspect, "created_at": created})
    return f"{FREE_DIR}/{name}"


def start(pid: str, data: dict) -> dict:
    prompt, count, model, aspect, ref_rels = _check(data)
    head = plan.get_head(pid)
    model = model or head["models"]["image"] or image_provider.server_default_model()
    aspect = aspect or head["aspect_ratio"]
    refs = _references(pid, ref_rels)

    def work(progress: jobs.Progress) -> dict:
        images: list[str] = []
        errors: list[str] = []
        for _ in range(count):
            if progress.cancelled():
                raise jobs.Cancelled()
            try:
                images.append(_one(pid, prompt, model, aspect, refs))
            except jobs.JobFailed as e:
                logger.info("Studio-Freies-Bild: ein Bild fehlgeschlagen (%s)", e)
                errors.append(str(e))
            progress.set(done=len(images), failed=len(errors))
        if not images:
            raise jobs.JobFailed(errors[0] if errors else "internal")
        return {"images": images, "errors": errors, "model": model}

    return jobs.start(pid, "free_images", f"free:{pid}", "", work, busy_code="studio_free_running",
                      progress={"total": count, "done": 0, "failed": 0, "current": ""})
