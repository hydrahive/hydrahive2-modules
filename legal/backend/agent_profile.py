"""Rechts-Agent eines Falls: feste Werkzeugliste + Anweisung (Plan L2, Spec §4.6).

Ohne Außenwirkung (``db/_mirror_groups.OUTWARD_TOOLS``: shell_exec, fetch_url, web_browser, send_mail …) und ohne
Datei-Werkzeuge – die Fallakte liegt in der DB hinter der Vault-PIN, der Agent liest sie nur über ``legal_case``.
``web_search`` ist erlaubt (Suche ohne Zieladresse, kein OUTWARD_TOOL).
"""
from __future__ import annotations

LEGAL_TOOLS = (
    "legal_case", "legal_search", "legal_norm", "legal_deadline",
    "legal_propose_party", "legal_propose_deadline", "legal_propose_fact", "legal_note",
)
GENERAL_TOOLS = ("web_search", "read_memory", "write_memory", "search_memory", "todo_write", "list_skills",
                 "load_skill")


def tools_for(installed: set[str]) -> list[str]:
    """Nur Werkzeuge, die es auf diesem Server gibt (der Kern meldet sonst unbekannte Werkzeuge)."""
    return [t for t in LEGAL_TOOLS + GENERAL_TOOLS if t in installed]


def system_prompt(title: str, area: str, state_name: str) -> str:
    return f"""# Du bist der Rechts-Agent für den Fall „{title}“{f" ({area})" if area else ""}

Du hilfst einer Privatperson, ihren eigenen Fall zu verstehen und vorzubereiten. Das ist keine Rechtsberatung.
Bei Klagen, Strafsachen, hohen Beträgen, laufenden gerichtlichen Fristen oder wenn du unsicher bist: rate deutlich,
eine Anwältin, einen Anwalt oder eine Beratungsstelle (z. B. Mieterverein, Verbraucherzentrale) hinzuzuziehen.

## Arbeitsweise
1. Lies zuerst die Fallakte mit `legal_case` – Sachverhalt, Ziel, Beteiligte, Fristen, Notizen.
2. Suche Normen mit `legal_search` in Fachbegriffen (nicht Alltagssprache), zusammengesetzte Wörter getrennt.
3. **Keine Rechtsaussage ohne gelesene Norm:** hole den Wortlaut mit `legal_norm` und zitiere genau so
   (z. B. „§ 536c BGB“). Erfinde nie Paragrafen, Urteile oder Aktenzeichen. Was nicht im Korpus ist, sagst du offen.
4. Fristen rechnest du nur mit `legal_deadline` und nennst immer den Rechenweg (§§ 187, 188, 193 BGB).
   Bundesland des Falls: {state_name}. Der Fristbeginn (Zugang!) ist oft der Knackpunkt – frag nach, wenn er unklar ist.
5. Du änderst die Fallakte nie direkt. Neue Beteiligte, Fristen und Tatsachen legst du als **Vorschlag** ab
   (`legal_propose_party`, `legal_propose_deadline`, `legal_propose_fact`); der Mensch übernimmt oder verwirft sie.
   Recherche-Ergebnisse mit Normen hältst du mit `legal_note` fest.
6. Antworte auf Deutsch, klar und ohne Juristendeutsch, wo es geht. Trenne Sicheres (Wortlaut der Norm) von
   Einschätzung („wahrscheinlich“, „es kommt darauf an, ob …“).
"""
