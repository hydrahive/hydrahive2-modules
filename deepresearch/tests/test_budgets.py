"""Deep Research ausführlich statt abgeschnitten (SPEC.md, Meldung Till 25.10.2026).

Test-Modell ohne echte Aufrufe: Jede Antwort wird – wie bei einem echten
Modell – nach `max_tokens` Token abgeschnitten (hier 1 Token ≈ 4 Zeichen).
Vorher: Auswertung je Seite mit 700 Token → lange JSON-Antwort bricht ab →
Seite still verworfen → „Keine verwertbaren Quellen gefunden“.
"""
from __future__ import annotations

import json

import pytest

import backend.research.gather as gather_mod
import backend.research.llm as llm_mod
import backend.research.report_writer as report_mod
from backend.research import budgets, run_research
from backend.research.models import RunState

CHARS_PER_TOKEN = 4
LONG_SUMMARY = "Mirtazapin ist ein Antidepressivum. " * 120       # ~4.300 Zeichen ≈ 1.080 Token
LONG_REPORT = "# Mirtazapin\n\n## Executive Summary\n" + ("Ausführlicher Abschnitt mit Belegen. " * 2500)


def _cut(text: str, max_tokens: int) -> str:
    return text[: max_tokens * CHARS_PER_TOKEN]


class Model:
    """Merkt sich die übergebenen Grenzen je Schritt und schneidet wie ein echtes Modell ab."""

    def __init__(self) -> None:
        self.limits: dict[str, int] = {}
        self.streamed: list[int] = []
        self.extract_calls = 0
        self.broken_extracts = 0          # so viele Auswertungen liefern Unsinn

    def _answer(self, content: str) -> tuple[str, str]:
        if "Zerlege die Frage" in content:
            return "plan", '{"category":"general","subquestions":["Was ist Mirtazapin?"]}'
        if "Suchanfragen" in content:
            return "queries", '["mirtazapin wirkung"]'
        if "Extrahiere" in content:
            self.extract_calls += 1
            if self.broken_extracts > 0:
                self.broken_extracts -= 1
                return "extract", "Hier ist meine Auswertung, leider ohne JSON."
            return "extract", json.dumps({"relevant": True, "summary": LONG_SUMMARY, "evidence": "Gelbe Liste"})
        if "Aktualisiere den Arbeitsbericht" in content:
            return "synth", "## Überblick\n" + LONG_SUMMARY + " ([Quelle](https://a.test/1))"
        if "YES oder NO" in content:
            return "stop", "YES"
        if "Schreibe den finalen Bericht" in content:
            return "report", LONG_REPORT
        return "other", ""

    async def complete(self, messages, model=None, temperature=0.7, max_tokens=4096):
        step, text = self._answer(messages[-1]["content"])
        self.limits[step] = max_tokens
        return _cut(text, max_tokens)

    async def stream(self, messages, model=None, temperature=0.7, max_tokens=4096):
        step, text = self._answer(messages[-1]["content"])
        self.limits[step] = max_tokens
        self.streamed.append(max_tokens)
        out = _cut(text, max_tokens)
        for i in range(0, len(out), 500):
            yield out[i:i + 500]


async def _search(query, count=8):
    return [{"title": "Apotheken Umschau", "url": "https://a.test/1", "snippet": "…"}]


async def _fetch(url):
    return ("Mirtazapin: Wirkung, Nebenwirkungen, Dosierung. " * 80, "")


@pytest.fixture
def model(monkeypatch):
    m = Model()
    monkeypatch.setattr(llm_mod, "complete", m.complete)
    monkeypatch.setattr(llm_mod, "stream", m.stream, raising=False)
    monkeypatch.setattr(gather_mod, "searxng_search", _search)
    monkeypatch.setattr(gather_mod, "fetch_page", _fetch)
    return m


def test_grenzen_grosszuegig() -> None:
    assert budgets.PLAN >= 4_000
    assert budgets.QUERIES >= 2_000
    assert budgets.EXTRACT >= 8_000
    assert budgets.SYNTHESIZE >= 16_000
    assert budgets.REPORT >= 32_000
    assert budgets.STOP >= 50
    assert budgets.MAX_TIME_S >= 900


@pytest.mark.asyncio
async def test_lange_auswertung_wird_nicht_abgeschnitten(model) -> None:
    result = await run_research(RunState(question="was ist mirtazipin"), min_rounds=1, max_rounds=1)
    assert result["stats"]["sources"] == 1
    assert result["stats"]["unreadable"] == 0
    assert "Keine verwertbaren Quellen" not in result["markdown"]


@pytest.mark.asyncio
async def test_jeder_schritt_bekommt_seine_grenze(model) -> None:
    await run_research(RunState(question="was ist mirtazipin"), min_rounds=1, max_rounds=1)
    assert model.limits == {
        "plan": budgets.PLAN, "queries": budgets.QUERIES, "extract": budgets.EXTRACT,
        "synth": budgets.SYNTHESIZE, "stop": budgets.STOP, "report": budgets.REPORT,
    }


@pytest.mark.asyncio
async def test_bericht_ueber_streaming_und_vollstaendig(model) -> None:
    result = await run_research(RunState(question="was ist mirtazipin"), min_rounds=1, max_rounds=1)
    assert model.streamed == [budgets.REPORT]
    assert result["markdown"] == LONG_REPORT.strip()          # ~92.000 Zeichen, nichts abgeschnitten


@pytest.mark.asyncio
async def test_kaputte_auswertung_wird_einmal_wiederholt(model) -> None:
    model.broken_extracts = 1
    result = await run_research(RunState(question="was ist mirtazipin"), min_rounds=1, max_rounds=1)
    assert model.extract_calls == 2
    assert result["stats"]["sources"] == 1
    assert result["stats"]["unreadable"] == 0


@pytest.mark.asyncio
async def test_zweimal_kaputt_wird_gezaehlt_und_erklaert(model) -> None:
    model.broken_extracts = 2
    result = await run_research(RunState(question="was ist mirtazipin"), min_rounds=1, max_rounds=1)
    assert model.extract_calls == 2
    assert result["stats"]["sources"] == 0
    assert result["stats"]["unreadable"] == 1
    assert "1 Seite gefunden" in result["markdown"]
    assert "konnte nicht ausgewertet werden" in result["markdown"]


@pytest.mark.asyncio
async def test_nicht_relevant_ist_kein_fehler(model, monkeypatch) -> None:
    async def irrelevant(messages, model=None, temperature=0.7, max_tokens=4096):
        if "Extrahiere" in messages[-1]["content"]:
            return '{"relevant": false}'
        return await m_complete(messages, model, temperature, max_tokens)
    m_complete = model.complete
    monkeypatch.setattr(llm_mod, "complete", irrelevant)
    result = await run_research(RunState(question="was ist mirtazipin"), min_rounds=1, max_rounds=1)
    assert result["stats"]["irrelevant"] == 1
    assert result["stats"]["unreadable"] == 0
    assert "passte nicht zur Frage" in result["markdown"]


@pytest.mark.asyncio
async def test_leere_seiten_werden_gezaehlt(model, monkeypatch) -> None:
    async def empty(url):
        return ("", "")
    monkeypatch.setattr(gather_mod, "fetch_page", empty)
    result = await run_research(RunState(question="was ist mirtazipin"), min_rounds=1, max_rounds=1)
    assert result["stats"]["empty_pages"] == 1
    assert "nicht abrufbar" in result["markdown"]


def test_ohne_funde_ohne_seiten_bleibt_alter_hinweis() -> None:
    md = report_mod.no_findings_text(RunState(question="Frage"))
    assert "Keine verwertbaren Quellen gefunden" in md
    assert "Seite" not in md


def test_prompts_fordern_ausfuehrlichkeit() -> None:
    from backend.research import prompts
    assert "2500 Wörter" in prompts.final_report("F", "M", "general")
    ex = prompts.extract("F", "T", "https://x", "inhalt")
    assert "2-4 Sätze" not in ex and "gründlich" in ex.lower()
    assert "nichts kürzen" in prompts.synthesize("F", "alt", "neu").lower()
