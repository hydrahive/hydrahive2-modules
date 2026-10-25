"""Schritt 6: finaler Langform-Markdown-Bericht (per Streaming, ausführlich)."""
from __future__ import annotations

from . import budgets, prompts
from .llm import ask_streamed
from .models import RunState


def _n(count: int, one: str, many: str) -> str:
    return f"{count} {one if count == 1 else many}"


def no_findings_text(state: RunState) -> str:
    """Bericht ohne Quellen – sagt in einfachen Worten, warum (statt still „nichts gefunden“)."""
    head = f"# {state.question}\n\n*Keine verwertbaren Quellen gefunden.*"
    checked = state.empty_pages + state.irrelevant + state.unreadable
    if not checked:
        return head
    lines = [f"{_n(len(state.urls_seen), 'Seite', 'Seiten')} gefunden, {checked} davon gelesen:"]
    if state.unreadable:
        lines.append(f"- {_n(state.unreadable, 'Seite konnte', 'Seiten konnten')} nicht ausgewertet werden "
                     "(die Antwort des Modells war unvollständig).")
    if state.irrelevant:
        lines.append(f"- {_n(state.irrelevant, 'Seite passte', 'Seiten passten')} nicht zur Frage.")
    if state.empty_pages:
        lines.append(f"- {_n(state.empty_pages, 'Seite war', 'Seiten waren')} nicht abrufbar oder ohne Text.")
    return head + "\n\n" + "\n".join(lines)


async def write_report(state: RunState) -> str:
    """Erzeugt den finalen Markdown-Bericht. Fällt auf den Arbeitsbericht zurück."""
    if not state.findings:
        return no_findings_text(state)
    system = prompts.SYSTEM.format(date=prompts.today_str())
    md = await ask_streamed(
        prompts.final_report(state.question, state.report_md, state.category),
        model=state.model,
        system=system,
        max_tokens=budgets.REPORT,
        temperature=0.5,
    )
    md = md.strip()
    # Schwaches Modell lieferte zu wenig → Arbeitsbericht ist besser als nichts
    if len(md) < 200:
        return state.report_md.strip() or md or f"# {state.question}\n\n*Bericht konnte nicht erzeugt werden.*"
    return md
