"""Automatische Anordnung der Bausteine eines Vorschlags (Etappe 3a).

Der Agent liefert nur Inhalte, keine Koordinaten. Hier entsteht daraus ein Bild:

- Layout-Bausteine stehen als Stapel links, von oben nach unten.
- Ablauf-Bausteine stehen rechts daneben in Spalten entlang der Verbindungen.
- Aufbau-Bausteine stehen als eigenes Band darunter, ebenfalls in Spalten.

Kreise werden aufgebrochen: Eine Verbindung, die zurück auf einen Baustein des
gerade verfolgten Wegs zeigt, zählt für die Spalten nicht. Gleiche Eingabe
ergibt gleiche Positionen. Alle Werte liegen auf dem Raster des Boards.
"""
from __future__ import annotations

import math

GRID = 15            # snapGrid der Zeichenfläche (frontend/Canvas.tsx)
WIDTH = 210
COL_GAP = 90
ROW_GAP = 30
BAND_GAP = 60
_LABEL_CHARS, _LABEL_LINE = 24, 18
_NOTE_CHARS, _NOTE_LINE = 30, 15
_BASE = 36           # Rand, Innenabstand und Kopfzeile eines Bausteins
_MIN_HEIGHT = 60     # wie minHeight im Frontend (nodes.tsx)
_CONDITION_EXTRA = 30
_HANDLE_RANK = {"true": 0, "false": 2}


def _lines(text: str, chars: int) -> int:
    return sum(max(1, math.ceil(len(part) / chars)) for part in text.split("\n"))


def _height(node: dict) -> int:
    """Geschätzte Höhe: lange Texte brechen um, die Breite bleibt fest."""
    height = _BASE + _lines(str(node.get("label") or "—"), _LABEL_CHARS) * _LABEL_LINE
    note = str(node.get("note") or "").strip()
    if note:
        height += _lines(note, _NOTE_CHARS) * _NOTE_LINE + 2
    if node.get("subtype") == "condition":
        height += _CONDITION_EXTRA
    return max(_MIN_HEIGHT, math.ceil(height / GRID) * GRID)


def _forward_edges(keys: list[str], succ: dict[str, list[str]]) -> dict[str, list[str]]:
    """Verbindungen ohne die, die einen Kreis schließen (Tiefensuche in Eingabereihenfolge)."""
    forward: dict[str, list[str]] = {key: [] for key in keys}
    state: dict[str, int] = {}  # 1 = auf dem aktuellen Weg, 2 = fertig
    for root in keys:
        if root in state:
            continue
        state[root] = 1
        stack = [(root, iter(succ[root]))]
        while stack:
            node, rest = stack[-1]
            for nxt in rest:
                if state.get(nxt) == 1:
                    continue
                forward[node].append(nxt)
                if nxt not in state:
                    state[nxt] = 1
                    stack.append((nxt, iter(succ[nxt])))
                    break
            else:
                state[node] = 2
                stack.pop()
    return forward


def _columns(keys: list[str], edges: list[dict]) -> list[list[str]]:
    """Bausteine einer Gruppe in Spalten: jeder steht rechts von allen seinen Vorgängern."""
    order = {key: index for index, key in enumerate(keys)}
    succ: dict[str, list[str]] = {key: [] for key in keys}
    handles: dict[tuple[str, str], int] = {}
    for edge in edges:
        src, dst = edge.get("from"), edge.get("to")
        if src not in order or dst not in order or src == dst:
            continue
        if dst not in succ[src]:
            succ[src].append(dst)
        rank = _HANDLE_RANK.get(str(edge.get("handle")), 1)
        handles[(src, dst)] = min(rank, handles.get((src, dst), rank))
    forward = _forward_edges(keys, succ)
    preds: dict[str, list[str]] = {key: [] for key in keys}
    for src, targets in forward.items():
        for dst in targets:
            preds[dst].append(src)

    column: dict[str, int] = {}
    waiting = {key: len(preds[key]) for key in keys}
    ready = [key for key in keys if not waiting[key]]
    while ready:
        node = ready.pop(0)
        column[node] = max((column[p] + 1 for p in preds[node]), default=0)
        for dst in forward[node]:
            waiting[dst] -= 1
            if not waiting[dst]:
                ready.append(dst)

    result: list[list[str]] = [[] for _ in range(max(column.values(), default=-1) + 1)]
    for key in keys:
        result[column[key]].append(key)
    row: dict[str, int] = {}
    for index, members in enumerate(result):
        if index:
            # Wer am weiter oben stehenden Vorgänger hängt, steht selbst weiter oben; „ja“ vor „nein“.
            def anchor(key: str, col: int = index) -> tuple:
                near = [(row[p], handles[(p, key)]) for p in preds[key] if column[p] == col - 1]
                return (*min(near), order[key])
            members.sort(key=anchor)
        row.update({key: position for position, key in enumerate(members)})
    return result


def _place(columns: list[list[str]], heights: dict[str, int], left: int, top: int, boxes: dict) -> int:
    """Spalten ab (left, top) setzen. Liefert die Unterkante des Bands."""
    bottom = top
    for index, members in enumerate(columns):
        y = top
        for key in members:
            boxes[key] = {"x": left + index * (WIDTH + COL_GAP), "y": y, "width": WIDTH, "height": heights[key]}
            y += heights[key] + ROW_GAP
        bottom = max(bottom, y - ROW_GAP)
    return bottom


def arrange(nodes: list[dict], edges: list[dict]) -> dict[str, dict]:
    """Position und Größe je Baustein: ``{kürzel: {"x", "y", "width", "height"}}``.

    ``nodes``: ``key``, ``kind`` (layout, flow, build), ``subtype``, ``label``, ``note``.
    ``edges``: ``from``, ``to``, ``handle`` (bei Bedingungen ``true`` oder ``false``).
    Unbekannte Arten zählen zum Ablauf, Verbindungen ins Leere werden übergangen.
    """
    groups: dict[str, list[str]] = {"layout": [], "flow": [], "build": []}
    heights: dict[str, int] = {}
    for node in nodes:
        key = node.get("key")
        if key is None or key in heights:
            continue
        heights[key] = _height(node)
        kind = node.get("kind")
        groups[kind if kind in groups else "flow"].append(key)

    boxes: dict[str, dict] = {}
    _place([groups["layout"]], heights, 0, 0, boxes)
    left = WIDTH + COL_GAP if groups["layout"] else 0
    flow_bottom = _place(_columns(groups["flow"], edges), heights, left, 0, boxes)
    build_top = flow_bottom + BAND_GAP if groups["flow"] else 0
    _place(_columns(groups["build"], edges), heights, left, build_top, boxes)
    return boxes
