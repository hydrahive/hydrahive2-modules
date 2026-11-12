"""Vorschlag des Agenten prüfen und in einen Board-Graphen umsetzen (Etappe 3a).

Der Agent liefert nur Inhalte, keine Koordinaten:

- ``nodes``: ``key`` (Kürzel), ``type`` (Art aus catalog.SUBTYPES), ``label``,
  optional ``note`` und beim Eingabefeld ``placeholder``.
- ``edges``: ``from``, ``to`` und an Bedingungen ``branch`` (ja oder nein).

``build_graph`` prüft das und liefert den Graphen im Format der Zeichenfläche
(``graph_json``), mit Positionen aus ``layout.arrange``. Jeder Fehler trägt einen
Code und einen Text, mit dem der Agent seinen Vorschlag berichtigen kann.
"""
from __future__ import annotations

import re

from . import layout
from .catalog import SUBTYPES, WITH_PLACEHOLDER

MAX_NODES = 80
MAX_EDGES = 400
MAX_LABEL = 200
MAX_NOTE = 2000
MAX_PLACEHOLDER = 200
_KEY = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
_NODE_TYPES = {"layout": "layoutNode", "flow": "flowNode", "build": "buildNode"}
# Anschlüsse wie in frontend/nodes.tsx: Event und Notiz haben keinen Eingang, Anzeige und Notiz
# keinen Ausgang, die Bedingung hat die Ausgänge „true“ und „false“. Eine Verbindung an einem
# Anschluss, den es nicht gibt, könnte die Oberfläche nicht zeichnen.
_NO_INPUT = frozenset({"event", "note"})
_NO_OUTPUT = frozenset({"display", "note"})
_BRANCHES = {"yes": "true", "ja": "true", "true": "true", "no": "false", "nein": "false", "false": "false"}
_EDGE_STYLE = {"stroke": "#818cf8", "strokeWidth": 2}  # wie neue Verbindungen in frontend/useBoard.ts


class ProposalError(ValueError):
    """Der Vorschlag ist nicht verwendbar. ``message`` ist für den Agenten gedacht."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _text(value: object, limit: int, code: str, what: str, *, required: bool = False) -> str:
    if value is None and not required:
        return ""
    if not isinstance(value, str):
        raise ProposalError(code, f"{what} fehlt oder ist kein Text.")
    text = value.strip()
    if required and not text:
        raise ProposalError(code, f"{what} darf nicht leer sein.")
    if len(text) > limit:
        raise ProposalError(code, f"{what} ist zu lang ({len(text)} Zeichen, höchstens {limit}).")
    return text


def _node(raw: object, seen: dict[str, dict]) -> dict:
    if not isinstance(raw, dict):
        raise ProposalError("invalid_shape", "Jeder Baustein muss ein Objekt mit key, type und label sein.")
    key = raw.get("key")
    if not isinstance(key, str) or not _KEY.match(key):
        raise ProposalError(
            "invalid_key", f"Ungültiges Kürzel {key!r}: 1 bis 40 Zeichen aus Buchstaben, Ziffern, _ und -.")
    if key in seen:
        raise ProposalError("duplicate_key", f"Das Kürzel „{key}“ kommt mehrfach vor. Jedes Kürzel nur einmal vergeben.")
    subtype = raw.get("type")
    entry = SUBTYPES.get(subtype) if isinstance(subtype, str) else None
    if entry is None:
        raise ProposalError(
            "unknown_type", f"Unbekannte Art {subtype!r} bei „{key}“. Bekannt sind: {', '.join(SUBTYPES)}.")
    node = {
        "key": key, "kind": entry.kind, "subtype": subtype,
        "label": _text(raw.get("label"), MAX_LABEL, "invalid_label", f"Die Beschriftung von „{key}“", required=True),
        "note": _text(raw.get("note"), MAX_NOTE, "invalid_note", f"Die Notiz von „{key}“"),
    }
    placeholder = raw.get("placeholder")
    if subtype in WITH_PLACEHOLDER:
        node["placeholder"] = _text(placeholder, MAX_PLACEHOLDER, "invalid_placeholder", f"Der Platzhalter von „{key}“")
    elif placeholder not in (None, ""):
        allowed = ", ".join(sorted(WITH_PLACEHOLDER))
        raise ProposalError("invalid_placeholder", f"„{key}“ hat keinen Platzhalter. Den gibt es nur bei: {allowed}.")
    return node


def _edge(raw: object, nodes: dict[str, dict]) -> tuple[str, str, str]:
    if not isinstance(raw, dict):
        raise ProposalError("invalid_shape", "Jede Verbindung muss ein Objekt mit from und to sein.")
    src, dst = raw.get("from"), raw.get("to")
    for end in (src, dst):
        if not isinstance(end, str) or end not in nodes:
            raise ProposalError("unknown_edge_node", f"Verbindung {src!r} → {dst!r}: den Baustein {end!r} gibt es nicht.")
    if src == dst:
        raise ProposalError("self_edge", f"„{src}“ ist mit sich selbst verbunden.")
    source, target = nodes[src]["subtype"], nodes[dst]["subtype"]
    if target in _NO_INPUT:
        raise ProposalError(
            "no_input", f"„{dst}“ ({SUBTYPES[target].name}) hat keinen Eingang, dorthin führt keine Verbindung.")
    if source in _NO_OUTPUT:
        raise ProposalError(
            "no_output", f"„{src}“ ({SUBTYPES[source].name}) hat keinen Ausgang, von dort geht keine Verbindung ab.")
    branch = raw.get("branch")
    if source != "condition":
        if branch not in (None, ""):
            raise ProposalError("branch_not_allowed", f"„{src}“ ist keine Bedingung: branch (ja/nein) weglassen.")
        return src, dst, "out"
    if branch in (None, ""):
        raise ProposalError(
            "branch_required", f"„{src}“ ist eine Bedingung: Die Verbindung zu „{dst}“ braucht branch ja oder nein.")
    handle = _BRANCHES.get(str(branch).strip().lower())
    if handle is None:
        raise ProposalError("invalid_branch", f"branch {branch!r} bei „{src}“ → „{dst}“ ist weder ja noch nein.")
    return src, dst, handle


def build_graph(nodes: object, edges: object) -> dict:
    """Geprüfter Vorschlag als Graph ``{"nodes": [...], "edges": [...]}`` für ``graph_json``.

    Die Breite der Bausteine ist fest, die Höhe richtet sich in der Oberfläche nach dem Inhalt.
    Löst ``ProposalError`` aus, wenn der Vorschlag nicht verwendbar ist.
    """
    if edges is None:
        edges = []
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise ProposalError("invalid_shape", "nodes und edges müssen Listen sein.")
    if not nodes:
        raise ProposalError("no_nodes", "Der Vorschlag enthält keine Bausteine.")
    if len(nodes) > MAX_NODES:
        raise ProposalError(
            "too_many_nodes", f"{len(nodes)} Bausteine sind zu viele, höchstens {MAX_NODES}. Den Entwurf aufteilen.")
    if len(edges) > MAX_EDGES:
        raise ProposalError("too_many_edges", f"{len(edges)} Verbindungen sind zu viele, höchstens {MAX_EDGES}.")

    parsed: dict[str, dict] = {}
    for raw in nodes:
        node = _node(raw, parsed)
        parsed[node["key"]] = node
    links = list(dict.fromkeys(_edge(raw, parsed) for raw in edges))  # doppelte Verbindungen zählen einmal

    boxes = layout.arrange(
        list(parsed.values()), [{"from": src, "to": dst, "handle": handle} for src, dst, handle in links])
    return {
        "nodes": [
            {
                "id": key, "type": _NODE_TYPES[node["kind"]],
                "position": {"x": boxes[key]["x"], "y": boxes[key]["y"]}, "width": boxes[key]["width"],
                "data": {name: value for name, value in node.items() if name != "key"},
            }
            for key, node in parsed.items()
        ],
        "edges": [
            {
                "id": f"e{index}-{src}-{dst}", "source": src, "target": dst, "sourceHandle": handle,
                "targetHandle": "in", "animated": True, "style": dict(_EDGE_STYLE),
            }
            for index, (src, dst, handle) in enumerate(links, start=1)
        ],
    }
