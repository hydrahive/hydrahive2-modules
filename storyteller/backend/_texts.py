"""A5 – Prompt-Texte von Ghostwriter, Zusammenfassen und Umschreiben an einer Stelle (Spec ki-qualitaet-a5.md §2).

Je Sprache ein Block (heute nur ``de``; Englisch = später ein zweiter Block mit denselben Schlüsseln, Task a8ea02cb (b)).
Je Buchart fertige Wortformen: Roman/Geschichte schreiben Szenen in Romantext, Sachbuch Abschnitte in Sachtext,
Lernbuch Abschnitte in Lehrtext. Für Romane sind die Texte bytegleich zum Stand 0.17.0 (tests/test_prompt_golden.py).
"""
from __future__ import annotations

from dataclasses import dataclass

from ._names import is_fiction

_SECTION = {
    "one": "Abschnitt", "plural": "Abschnitte", "one_acc": "EINEN Abschnitt", "unit_text": "Text des Abschnitts",
    "first": "der erste Abschnitt", "prev_head": "ENDE DES VORIGEN ABSCHNITTS", "this_head": "DIESER ABSCHNITT",
    "this_gen": "dieses Abschnitts", "piece": "Teil", "pieces_head": "BISHERIGE TEILE DIESES ABSCHNITTS",
    "begins": "Der Abschnitt beginnt hier.", "the": "den Abschnitt",
    "summary_focus": "worum es geht und welche Fakten, Begriffe oder Personen neu sind",
    "expand": "mehr Erklärung, Beispiele und Details, etwa doppelt so lang. Nichts erfinden, was dem übrigen Text widerspricht.",
    "continue_fit": "passend zu Inhalt, Gedankengang und Ton",
}
_DE_UNITS = {
    "fiction": {
        "prose": "Romantext", "one": "Szene", "plural": "Szenen", "one_acc": "EINE Szene", "unit_text": "Szenentext",
        "first": "die erste Szene", "prev_head": "ENDE DER VORIGEN SZENE", "this_head": "DIESE SZENE",
        "this_gen": "dieser Szene", "piece": "Abschnitt", "pieces_head": "BISHERIGE ABSCHNITTE DIESER SZENE",
        "begins": "Die Szene beginnt hier.", "the": "die Szene",
        "summary_focus": "was passiert und welche Fakten über Figuren neu sind",
        "expand": "mehr Details, Sinneseindrücke, etwa doppelt so lang. Nichts Neues erfinden, was der Geschichte widerspricht.",
        "continue_fit": "passend zu Handlung, Figuren und Ton",
    },
    "nonfiction": {**_SECTION, "prose": "Sachtext"},
    "learning": {**_SECTION, "prose": "Lehrtext"},
}

_DE = {
    # Ghostwriter (ghost.build_material / write_scene)
    "ghost_system": ("Du bist Ghostwriter für ein Buch ({kind}). Du schreibst {prose} auf {lang} für genau {one_acc}. "
                     "Keine Überschrift, kein Vorspann, keine Erklärung, keine Zusammenfassung am Ende – nur der "
                     "{unit_text}. Halte dich an Steckbriefe und bisherige Handlung und erfinde nichts, was ihnen "
                     "widerspricht. Formuliere eigenständig; bekannte Texte anderer Autoren nicht zitieren oder nachschreiben."),
    "book": "BUCH: {title}. Zielgruppe: {audience}. Idee: {idea}",
    "audience_none": "nicht angegeben",
    "style": "STIL: {style}",
    "profiles": "STECKBRIEFE:",
    "memory": "BISHER GESCHAH:\n{memory}",
    "first": "Dies ist {first} des Buchs.",
    "prev_end": "{prev_head} (wörtlich, schließe nahtlos an):\n…{text}",
    "this": "{this_head}: „{title}“. Inhalt: {summary}",
    "from_interview": "aus dem Interview (passender Teil)",
    "pov": " Perspektive: {pov}.",
    "chapter_line": "- Kapitel „{title}“: {summary}",
    "task_first": "Schreibe den Anfang {this_gen}, etwa {words} Wörter.",
    "task_next": "Schreibe den nächsten {piece} {this_gen}, etwa {words} Wörter.",
    "task_continue": (" Setze genau dort fort, wo der Text aufhört. Nichts wiederholen: keine Gespräche, Fragen oder "
                      "Ereignisse, die oben schon vorkommen – die Handlung geht weiter."),
    "pieces": "{pieces_head} (jeweils der Anfang):",
    "so_far": "SO WEIT GESCHRIEBEN (Ende):",
    "task": "AUFGABE: {task}",
    # Interview als Grundlage (interview_ai)
    "interview_rule": ("Schreibe ausschließlich aus dem, was der Autor im Interview erzählt hat, und aus den "
                       "Zusammenfassungen. Erfinde nichts dazu: keine Namen, Orte, Jahreszahlen oder Ereignisse, die "
                       "dort nicht stehen – eine Lücke bleibt eine Lücke. Schreibe in der Stimme des Autors (Wortwahl, "
                       "Satzlänge, Ich-Form, wenn er so erzählt)."),
    "interview_answers": "INTERVIEW MIT DEM AUTOR (Grundlage des Textes):\n{answers}",
    "interview_voice": "STIMME DES AUTORS (Originalwortlaut, so klingt er):\n{sample}",
    # Zusammenfassen (ghost.summarize_scene) und Kapitel-Zusammenfassung (A5c)
    "summarize": ("Fasse {the} in 2–3 Sätzen auf {lang} zusammen: {summary_focus}. Nur die Zusammenfassung, keine "
                  "Überschrift."),
    "summarize_chapter": ("Fasse das Kapitel in 3–5 Sätzen auf {lang} zusammen, nur aus den Zusammenfassungen seiner "
                          "{plural}: was geschieht, was sich ändert, was offen bleibt. Nichts dazuerfinden. Nur die "
                          "Zusammenfassung, keine Überschrift."),
    "chapter_input": "KAPITEL: {title}\n\n{lines}",
    # Umschreiben (ai.suggest)
    "editor_system": ("Du bist Lektor und Co-Autor für ein Buch. Art: {kind}. Sprache: {lang}. Zielgruppe: {audience}. "
                      "Antworte ausschließlich mit dem neuen Text auf {lang}: keine Überschrift, kein Vorspann wie "
                      "„Hier ist …“, keine Erklärung, keine Anführungszeichen drumherum. Dein Text wird unverändert eingesetzt."),
    "about": "Worum es im Buch geht: {idea}",
    "before_scenes": "Was vorher geschah:",
    "profiles_lower": "Steckbriefe:",
    "text_before": "Text davor:\n{text}",
    "selected": "MARKIERTER TEXT:\n{text}",
    "continue_here": "Weiterschreiben ab hier.",
    "text_after": "Text danach:\n{text}",
    "rewrite": "Formuliere den markierten Text neu: gleicher Inhalt, besserer Fluss, gleiche Länge.",
    "expand": "Baue den markierten Text aus: {expand}",
    "shorten": "Kürze den markierten Text auf etwa die Hälfte. Inhalt und Ton bleiben.",
    "continue": "Schreibe ab der markierten Stelle 1–3 Absätze weiter, {continue_fit}.",
}

_LANGS = {"de": (_DE, _DE_UNITS)}


def _unit_key(kind: str) -> str:
    if is_fiction(kind):
        return "fiction"
    return "learning" if kind == "learning" else "nonfiction"


@dataclass(frozen=True)
class Texts:
    """Prompt-Texte für ein Buch. ``t("schlüssel", wert=…)`` liefert den fertigen Text; Wortformen der Buchart
    (``{one}``, ``{this_gen}`` …) sind schon eingesetzt. ``t.unit`` gibt sie einzeln. Gleich = gleiche Sprache/Buchart."""
    language: str
    kind: str

    @property
    def _pair(self) -> tuple[dict, dict]:
        table, units = _LANGS.get(self.language, _LANGS["de"])   # Englisch folgt (b); bis dahin wie bisher deutsch
        return table, units[_unit_key(self.kind)]

    @property
    def unit(self) -> dict:
        return self._pair[1]

    def __call__(self, key: str, **values) -> str:
        table, unit = self._pair
        return table[key].format(**{**unit, **values})


def texts(book: dict) -> Texts:
    return Texts(book.get("language", "de"), book.get("kind", "novel"))
