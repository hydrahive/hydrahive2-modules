"""„Film machen“ im geführten Weg (Spec „Bauplan G5“): ein Auftrag, der die vorhandenen Bausteine nacheinander nutzt –
Erzählstimme → Zeitleiste aus dem Drehbuch → Musik → Untertitel → Ausgabe. Teilfehler brechen nicht ab.
"""
from __future__ import annotations

import logging

from . import _film_steps as steps
from . import jobs, plan, render, render_preset, render_queue, timeline
from ._store import read_json, root, write_json

logger = logging.getLogger("hhmod_studio.film")
STEPS = ("voice", "timeline", "music", "subtitles", "render")
_FLAGS = ("music", "voice", "subtitles")


def _options(data) -> tuple[dict, bool | None]:
    data = data if isinstance(data, dict) else {}
    opts = {}
    for k in _FLAGS:
        v = data.get(k, False)
        if not isinstance(v, bool):
            raise plan.PlanError("studio_film_invalid")
        opts[k] = v
    rebuild = data.get("rebuild")
    if rebuild is not None and not isinstance(rebuild, bool):
        raise plan.PlanError("studio_film_invalid")
    return opts, rebuild


def _remembered(pid: str) -> int | None:
    v = read_json(root(pid) / "film.json", {})
    return v.get("revision") if isinstance(v, dict) and isinstance(v.get("revision"), int) else None


def edited(pid: str) -> bool:
    """Wurde die Zeitleiste seit dem letzten „Film machen“ (oder überhaupt, ohne Film) von Hand geändert?"""
    tl = timeline.load(pid)
    if not timeline.clips_of(tl):
        return False
    return _remembered(pid) != tl["revision"]


def _render_step(pid: str, subtitles: bool, progress: jobs.Progress) -> dict:
    head = plan.get_head(pid)
    preset = render_preset.resolve(None, None, head["aspect_ratio"])
    tl = timeline.load(pid)
    clips = timeline.clips_of(tl)
    ticket, _ = render_queue.enter(pid)
    try:
        with render_queue.turn(ticket, progress):          # gibt den Platz am Ende selbst frei
            return render._render(pid, tl, clips, head, preset, subtitles, steps.Quiet(progress))
    finally:
        render_queue.leave(ticket)                         # falls `turn` gar nicht erst begann (doppelt schadet nicht)


def start(pid: str, data) -> dict:
    opts, rebuild = _options(data)
    if not any(sc.get("shots") for sc in plan.list_scenes(pid)):
        raise plan.PlanError("studio_timeline_no_shots")
    if rebuild is None and edited(pid):
        raise plan.PlanError("studio_film_edited", 409)
    build = rebuild is not False

    def work(progress: jobs.Progress) -> dict:
        notes: list[str] = []
        voice_failed = 0

        def at(name: str) -> None:
            if progress.cancelled():
                raise jobs.Cancelled()
            progress.set(current=name, done=STEPS.index(name))

        at("voice")
        if opts["voice"]:
            voice_failed = steps.add_voice(pid, progress)
        at("timeline")
        if build:
            timeline.from_plan(pid, replace=True)
        tl = timeline.load(pid)
        write_json(root(pid, create=True) / "film.json", {"revision": tl["revision"]})
        at("music")
        music = steps.has_music(tl)
        if opts["music"] and not music:
            music = steps.add_music(pid, notes)
            if music:
                write_json(root(pid) / "film.json", {"revision": timeline.load(pid)["revision"]})
        at("subtitles")
        subs = steps.add_subtitles(pid, notes) if opts["subtitles"] else False
        at("render")
        out = _render_step(pid, subs, progress)
        progress.set(done=len(STEPS), current="")
        return {**out, "music": bool(music), "subtitles": subs, "voice_failed": voice_failed, "notes": notes}

    return jobs.start(pid, "film", f"film:{pid}", "", work, busy_code="studio_film_running",
                      progress={"total": len(STEPS), "done": 0, "failed": 0, "current": ""})
