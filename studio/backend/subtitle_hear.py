"""Untertitel aus dem Ton heraushören (Spec „Bauplan 6b“): Hördatei mischen → Anbieter (Abschnitte mit Zeit) →
Untertitel. Als Auftrag im Hintergrund, höchstens einer je Projekt und Sprache."""
from __future__ import annotations

import math
import re
import tempfile
from pathlib import Path

from . import (
    hear_args,
    hear_provider,
    jobs,
    plan,
    render,
    render_args,
    subtitle_speech,
    subtitles,
    timeline,
)
from ._store import project_lock, project_root

MAX_SECONDS = 3600
NO_SPEECH = 0.6
# Nur ein Geräusch-Hinweis der Erkennung („*Geschrei*“, „[Musik]“, „(lacht)“, „♪“) – kein gesprochener Text (Probe 18.10.)
_NOISE = re.compile(r"^\s*(\*[^*]*\*|\[[^\]]*\]|\([^)]*\)|[♪♫\s]+)\s*$")


def _num(v) -> float | None:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) else None


def cues_from(segments: list, *, film_end: float) -> list[dict]:
    """Abschnitte → Untertitel: ohne Sprache weg, lange geteilt (wie 6a), mind. 0,5 s, keine Überlappung, ≤ Filmende."""
    cues: list[dict] = []
    for s in segments:
        if not isinstance(s, dict):
            continue
        a, b = _num(s.get("start")), _num(s.get("end"))
        text = " ".join(str(s.get("text") or "").split())
        p = _num(s.get("no_speech_prob")) or 0.0
        if a is None or b is None or p > NO_SPEECH or _NOISE.match(text):   # leerer Text ergibt bei spread() keinen
            continue
        a = max(a, cues[-1]["end"] if cues else 0.0, 0.0)
        b = min(max(b, a + subtitles.MIN_SECONDS), max(film_end, a + subtitles.MIN_SECONDS))
        if a >= film_end:
            break
        cues += subtitle_speech.spread(text, a, b - a)
    return subtitles.clean_cues(cues)


def _parts(pid: str) -> tuple[list[dict], list[dict], float]:
    tl = timeline.load(pid)
    segs = render._segments(pid, timeline.clips_of(tl))
    voice = [c for c in render._audio(pid, tl) if c.get("track") == "A1"]
    segs = render_args.pad_to(segs, render_args.audio_end(voice))
    return segs, voice, render_args.total_seconds(segs)


def info(pid: str, lang: str) -> dict:
    """Werte für den Dialog: Filmlänge, Modell, ob es ein Cloud-Modell ist, vorhandene Untertitel (prüft die Sprache)."""
    existing = len(subtitles.load(pid, lang)["cues"])
    tl = timeline.load(pid)
    end = max((c["start"] + c["out"] - c["in"] for c in timeline.all_clips(tl)), default=0.0)
    model = hear_provider.model_for_subtitles()
    return {"seconds": round(end, 3), "model": model, "cloud": not hear_provider.is_local(model),
            "existing": existing, "max_seconds": MAX_SECONDS}


def start(pid: str, lang: str, *, replace: bool) -> dict:
    subtitles.language(lang)
    current = subtitles.load(pid, lang)
    if current["cues"] and not replace:
        raise plan.PlanError("studio_subtitles_not_empty", 409)
    segs, voice, seconds = _parts(pid)
    if not voice and not any(s["kind"] == "video" and s.get("has_audio") for s in segs):
        raise plan.PlanError("studio_subtitles_no_audio")
    if seconds > MAX_SECONDS:
        raise plan.PlanError("studio_subtitles_too_long")
    model = hear_provider.model_for_subtitles()
    if hear_provider.is_local(model):
        raise plan.PlanError("studio_subtitles_cloud_model")
    revision = current["revision"]

    def work() -> dict:
        with tempfile.TemporaryDirectory(prefix="studio-hear-") as td:
            out = Path(td) / "ton.m4a"
            try:
                render._run_ffmpeg(hear_args.command(segs, voice, project_root(pid), out), seconds, lambda f: None)
            except render.RenderFailed as e:
                raise jobs.JobFailed("render_failed") from e
            try:
                segments = hear_provider.transcribe(out, lang, model)
            except hear_provider.ProviderError as e:
                raise jobs.JobFailed(str(e)) from e
        cues = cues_from(segments, film_end=seconds)
        if not cues:
            raise jobs.JobFailed("no_speech_found")
        with project_lock(pid):
            try:
                subtitles.write(pid, lang, cues, revision, "audio")       # inzwischen geändert → nicht überschreiben
            except plan.PlanError as e:
                raise jobs.JobFailed("changed") from e
        return {"count": len(cues), "seconds": seconds, "model": model}

    return jobs.start(pid, "transcribe", f"subtitles:{pid}:{lang}", "", work, busy_code="studio_subtitles_running")
