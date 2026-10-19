"""Untertitel übersetzen (Spec „Bauplan 6c“): Eintrag für Eintrag, die Zeiten bleiben genau gleich.

Die Text-KI bekommt eine nummerierte Liste mit dem Film als Kontext (Titel, Kurzbeschreibung) und antwortet mit einer
JSON-Liste in derselben Reihenfolge. Je Aufruf höchstens BLOCK Einträge. Passt eine Antwort nicht, wird der Block einmal
neu angefragt, sonst bricht der Auftrag ab – lieber nichts als falsch zugeordnete Zeilen.
"""
from __future__ import annotations

import asyncio
import json
import logging

from hydrahive.llm import client as llm_client

from . import jobs, plan, subtitle_speech, subtitles
from ._store import project_lock

logger = logging.getLogger("hhmod_studio.translate")

BLOCK = 80
TRIES = 2
NAMES = {"de": "German", "en": "English", "fr": "French", "es": "Spanish", "it": "Italian", "nl": "Dutch", "pl": "Polish",
         "pt": "Portuguese", "tr": "Turkish", "uk": "Ukrainian", "ru": "Russian", "sv": "Swedish", "da": "Danish",
         "no": "Norwegian", "fi": "Finnish", "cs": "Czech", "ja": "Japanese", "zh": "Chinese"}

SYSTEM = ("You translate film subtitles. Keep names, tone and meaning; keep it short enough to read while watching. "
          "Translate each numbered line on its own (a ' / ' inside a line is a line break and may be dropped). "
          "Reply ONLY with a JSON array of strings, one per numbered line, same order and same count, no prose.")


class BadAnswer(RuntimeError):
    pass


def parse(raw: str, n: int) -> list[str]:
    t = (raw or "").strip()
    a, b = t.find("["), t.rfind("]")
    try:
        data = json.loads(t[a:b + 1]) if a != -1 and b > a else None
    except json.JSONDecodeError:
        data = None
    if not isinstance(data, list) or len(data) != n or not all(isinstance(x, str) and x.strip() for x in data):
        raise BadAnswer()
    return data


def fit(text: str) -> str:
    """Höchstens 2 Zeilen: passt es in 2 × 42 Zeichen, wie 6a; sonst zwei ausgewogene Zeilen (die Zeiten bleiben, also wird
    kein Wort weggelassen – erst ab MAX_TEXT wird gekürzt). Zeilenumbrüche aus der Vorlage zählen nicht."""
    flat = " ".join(text.split())[:subtitles.MAX_TEXT - 1].rstrip()
    lines = subtitle_speech.wrap(flat)
    if len(lines) > 2:
        words, best = flat.split(" "), 1
        for k in range(1, len(words)):
            a, b = " ".join(words[:k]), " ".join(words[k:])
            if max(len(a), len(b)) < max(len(" ".join(words[:best])), len(" ".join(words[best:]))):
                best = k
        lines = [" ".join(words[:best]), " ".join(words[best:])]
    return subtitles.clean_text("\n".join(lines))


def _prompt(head: dict, src: str, dst: str, texts: list[str]) -> list[dict]:
    film = "\n".join(x for x in (f"Film: {head.get('title')}" if head.get("title") else "",
                                  f"About: {head.get('logline')}" if head.get("logline") else "") if x)
    lines = "\n".join(f"{i}. {t.replace(chr(10), ' / ')}" for i, t in enumerate(texts, start=1))
    user = f"Translate from {NAMES[src]} to {NAMES[dst]}.\n{film}\n\n{lines}".replace("\n\n\n", "\n\n")
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


async def _block(head: dict, src: str, dst: str, texts: list[str], model: str | None) -> list[str]:
    for _ in range(TRIES):
        try:
            raw = await llm_client.complete(_prompt(head, src, dst, texts), model=model, temperature=0.2, max_tokens=8000)
        except Exception as e:
            logger.warning("Studio-Übersetzen: Text-KI-Fehler: %s", e)
            raise jobs.JobFailed("provider_failed") from e
        try:
            return parse(raw, len(texts))
        except BadAnswer:
            continue
    raise jobs.JobFailed("bad_answer")


def start(pid: str, dst: str, data) -> dict:
    subtitles.language(dst)
    data = data if isinstance(data, dict) else {}
    src = subtitles.language(data.get("from"))
    if src == dst:
        raise plan.PlanError("studio_subtitles_same_language")
    source = subtitles.load(pid, src)["cues"]
    if not source:
        raise plan.PlanError("studio_subtitles_empty")
    target = subtitles.load(pid, dst)
    if target["cues"] and data.get("replace") is not True:
        raise plan.PlanError("studio_subtitles_not_empty", 409)
    head = plan.get_head(pid)
    model = head["models"]["text"] or None
    revision = target["revision"]

    def work() -> dict:
        texts: list[str] = []
        for i in range(0, len(source), BLOCK):
            part = [c["text"] for c in source[i:i + BLOCK]]
            texts += asyncio.run(_block(head, src, dst, part, model))
        cues = [{**c, "text": fit(t)} for c, t in zip(source, texts, strict=True)]
        with project_lock(pid):
            try:
                subtitles.write(pid, dst, subtitles.clean_cues(cues), revision, "translation", origin=src)
            except plan.PlanError as e:
                raise jobs.JobFailed("changed") from e
        return {"count": len(cues), "from": src, "language": dst}

    return jobs.start(pid, "translate", f"subtitles:{pid}:{dst}", "", work, busy_code="studio_subtitles_running")
