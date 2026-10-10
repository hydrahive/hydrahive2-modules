"""C2 – Umbau-Schritte als lesbare Zeilen (Vorschau im Storyteller, Antwort an den Agenten). Deutsch; Englisch kommt
mit den übrigen Texten (A5b)."""
from __future__ import annotations


def _line(i: dict, unit: str, units: str, new_unit: str) -> str:
    name, op = i.get("name", ""), i["op"]
    if op == "rename_chapter":
        return f"Kapitel „{i.get('old', '')}“ umbenennen in „{name}“"
    if op == "add_chapter":
        return f"Neues Kapitel „{name}“ mit {i.get('count', 0)} {units}"
    if op == "add_scene":
        return f"{new_unit} „{name}“ in „{i.get('chapter', '')}“"
    if op == "delete_chapter":
        return f"Kapitel „{name}“ mit {i.get('count', 0)} {units} löschen (Papierkorb)"
    if op == "delete_scene":
        tail = f" – Kapitel „{i.get('chapter', '')}“ geht mit" if i.get("with_chapter") else ""
        return f"{unit} „{name}“ löschen (Papierkorb){tail}"
    if op == "move_scene":
        return f"{unit} „{name}“ verschieben nach „{i.get('chapter', '')}“"
    if op == "move_chapter":
        return f"Kapitel „{name}“ verschieben"
    if op == "set_chapter_summary":
        return f"Kapitel-Zusammenfassung für „{name}“ setzen"
    raise KeyError(op)


def lines(items: list[dict], *, fiction: bool) -> list[str]:
    unit = "Szene" if fiction else "Abschnitt"
    units = "Szene(n)" if fiction else "Abschnitt(e)"
    new_unit = "Neue Szene" if fiction else "Neuer Abschnitt"
    return [_line(i, unit, units, new_unit) for i in items]
