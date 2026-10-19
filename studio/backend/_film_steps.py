"""Schritte von „Film machen“ (G5): Erzählstimme, Musik, Untertitel – jeweils mit den vorhandenen Bausteinen."""
from __future__ import annotations

import logging

from . import (
    jobs,
    music,
    music_provider,
    plan,
    shots,
    speech,
    subtitle_speech,
    timeline,
)

logger = logging.getLogger("hhmod_studio.film")
FADE = 2.0


class Quiet:
    """Fortschritt der Ausgabe nicht in den Film-Auftrag schreiben (der zählt Schritte), Abbrechen aber durchreichen."""

    def __init__(self, progress: jobs.Progress) -> None:
        self.job, self._p = progress.job, progress

    def set(self, **_fields) -> None:
        pass

    def cancelled(self) -> bool:
        return self._p.cancelled()


def card_text(scene: dict, shot: dict) -> str:
    """Text der Karte im geführten Weg: Szenentext, bei mehreren Shots die Bildbeschreibung."""
    return (shot.get("prompt") if len(scene.get("shots") or []) > 1 else scene.get("description") or scene.get("title")) or ""


def add_voice(pid: str, progress: jobs.Progress) -> int:
    """Shots ohne Sprechtext bekommen den Kartentext; fehlende Sprache wird erzeugt. Gibt die Zahl der Fehlschläge zurück."""
    failed = 0
    for sc in plan.list_scenes(pid):
        for s in sc.get("shots") or []:
            if progress.cancelled():
                raise jobs.Cancelled()
            if not (s.get("speech") or "").strip():
                text = card_text(sc, s)[:1000]
                if not text:
                    continue
                shots.update(pid, sc["id"], s["id"], {"speech": text})
            if s.get("voice_rel"):
                continue
            try:
                speech.work(pid, sc["id"], s["id"])
            except (jobs.JobFailed, plan.PlanError) as e:
                logger.info("Film: Stimme für Shot %s fehlgeschlagen (%s)", s["id"], e)
                failed += 1
    return failed


def has_music(tl: dict) -> bool:
    return bool(timeline.clips_of(tl, "A2"))


def add_music(pid: str, notes: list[str]) -> bool:
    """Musik zum ganzen Film auf A2 ab 0; zu lang → gekürzt mit Ausblende. Fehler → Hinweis, kein Abbruch."""
    head = plan.get_head(pid)
    tl = timeline.load(pid)
    length = max((c["start"] + c["out"] - c["in"] for c in timeline.clips_of(tl)), default=0.0)
    seconds = max(music.MIN_SECONDS, min(music.MAX_SECONDS, round(length)))
    description = ". ".join(t for t in (head["title"], head["logline"], "Background music for a short film") if t)
    model = head["models"]["music"] or music_provider.server_default_model()
    try:
        r = music._work(pid, description, seconds, "", model)
    except jobs.JobFailed as e:
        logger.info("Film: Musik fehlgeschlagen (%s)", e)
        notes.append("music_failed")
        return False
    out = min(float(r["duration"]), float(seconds))
    clip = {"kind": "audio", "start": 0, "in": 0, "out": out, "media_rel": r["rel"], "label": "Musik"}
    if r["duration"] > seconds:
        clip["fade_out"] = min(FADE, out / 2)
    cur = timeline.load(pid)
    tracks = [t for t in cur["tracks"] if t["id"] != "A2"] + [{"id": "A2", "kind": "audio", "clips": [clip]}]
    timeline.save(pid, {"revision": cur["revision"], "fps": cur["fps"], "tracks": tracks})
    return True


def add_subtitles(pid: str, notes: list[str]) -> bool:
    lang = plan.get_head(pid)["language"]
    try:
        subtitle_speech.from_speech(pid, lang, replace=True)
        return True
    except plan.PlanError as e:
        if e.code != "studio_subtitles_no_speech":
            raise
        notes.append("no_speech")
        return False
