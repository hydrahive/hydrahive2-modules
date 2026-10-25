"""Telefon-Assistent zusammenstecken (PLAN-AGENT-2B): Einstellungen + lokale Dienste + Sprachmodell.

``bundle(cid)`` wird bei jedem Anruf frisch gelesen (Schalter/Text ändern ohne Neuanmeldung). Liefert None im Modus
„Nur Ansage“. Das Sprachmodell bekommt nur die Nachrichten aus agent/prompt.py – keine Werkzeuge, keinen Runner.
"""
from __future__ import annotations

from hydrahive.db.connection import db

from .agent.prompt import AgentConfig
from .media import g711, greeting

TEMPERATURE = 0.3
MAX_TOKENS = 400


async def _complete(messages, model=None, temperature=0.7, max_tokens=4096):
    from hydrahive.llm import client
    return await client.complete(messages, model=model, temperature=temperature, max_tokens=max_tokens)


async def _transcribe(pcm16k: bytes) -> str:
    from hydrahive.voice import stt
    return await stt._wyoming_transcribe(pcm16k, "de")


def _llm(model: str):
    def call(messages: list[dict]) -> str:
        return greeting._run(_complete(messages, model=model or None, temperature=TEMPERATURE, max_tokens=MAX_TOKENS))
    return call


def _stt(pcm16k: bytes) -> str:
    return greeting._run(_transcribe(pcm16k))


def _tts(text: str, codec: str) -> bytes:
    """Antworten sind jedes Mal anders – nicht im Ansage-Zwischenspeicher ablegen."""
    try:
        wav, _ = greeting._run(greeting._synthesize(text))
        pcm = greeting._wav_to_pcm8k(wav)
    except Exception:  # noqa: BLE001 - Piper nicht erreichbar → kurzer Ton, das Gespräch geht weiter
        pcm = greeting._tone()
    return g711.encode(pcm[: greeting.MAX_SECONDS * 8000 * 2], codec)


def bundle(cid: str) -> dict | None:
    with db() as c:
        row = c.execute("SELECT call_mode, assistant_name, assistant_knowledge, assistant_model "
                        "FROM module_telephony_connections WHERE id=?", (cid,)).fetchone()
    if not row or row["call_mode"] != "assistant":
        return None
    return {"cfg": AgentConfig(owner_name=row["assistant_name"], knowledge=row["assistant_knowledge"]),
            "llm": _llm(row["assistant_model"]), "stt": _stt, "tts": _tts, "options": {}}

