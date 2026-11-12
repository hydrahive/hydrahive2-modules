"""Liste der Bausteine (catalog.py) und die dritte Gruppe „Aufbau“ im Board-Text (Etappe 3a)."""
from __future__ import annotations

import json
import re
from pathlib import Path

from backend import catalog
from backend.render import render_board

FRONTEND = Path(__file__).parents[1] / "frontend"


def node(nid: str, subtype: str, kind: str, label: str, note: str = "") -> dict:
    return {"id": nid, "type": "x", "position": {"x": 1, "y": 2},
            "data": {"kind": kind, "subtype": subtype, "label": label, "note": note}}


def _render(nodes: list[dict], edges: list[dict] | None = None) -> str:
    return render_board({"name": "x"}, json.dumps({"nodes": nodes, "edges": edges or []}))


def test_jeder_baustein_hat_gruppe_und_namen():
    assert catalog.KINDS == ("layout", "flow", "build")
    for subtype, entry in catalog.SUBTYPES.items():
        assert entry.kind in catalog.KINDS, subtype
        assert entry.name.strip(), subtype


def test_aufbau_bausteine_sind_bekannt():
    build = {subtype for subtype, entry in catalog.SUBTYPES.items() if entry.kind == "build"}
    assert build == {"module", "interface", "database", "file", "agent_tool"}


def test_bisherige_bausteine_bleiben():
    kinds = {subtype: entry.kind for subtype, entry in catalog.SUBTYPES.items()}
    for subtype in ("page", "card", "menu_item", "button", "input", "toggle", "heading", "list"):
        assert kinds[subtype] == "layout"
    for subtype in ("event", "action", "datasource", "condition", "display", "note"):
        assert kinds[subtype] == "flow"


def test_liste_stimmt_mit_der_palette_der_oberflaeche_ueberein():
    """Backend und frontend/palette-data.ts kennen dieselben Bausteine, Gruppen und Namen."""
    source = (FRONTEND / "palette-data.ts").read_text(encoding="utf-8")
    palette: dict[str, tuple[str, str]] = {}
    groups = re.findall(r'kind: "(\w+)",\s*label: "[^"]+",\s*items: \[(.*?)\n    \],', source, flags=re.DOTALL)
    assert groups, "Gruppen in palette-data.ts nicht gefunden"
    for kind, items in groups:
        for subtype, label in re.findall(r'subtype: "(\w+)", label: "([^"]+)"', items):
            palette[subtype] = (kind, re.sub(r"\s*\(.*\)$", "", label))
    assert palette == {subtype: (entry.kind, entry.name) for subtype, entry in catalog.SUBTYPES.items()}


def test_platzhalter_bausteine_stimmen_mit_der_palette_ueberein():
    source = (FRONTEND / "palette-data.ts").read_text(encoding="utf-8")
    with_placeholder = set(re.findall(r'subtype: "(\w+)"[^}\n]*hasPlaceholder: true', source))
    assert with_placeholder == set(catalog.WITH_PLACEHOLDER) and with_placeholder


def test_aufbau_steht_als_dritte_gruppe_im_text():
    text = _render([
        node("m", "module", "build", "Ideen-Modul", "Backend und Oberfläche"),
        node("a", "action", "flow", "Speichern"),
        node("p", "page", "layout", "Seite Ideen"),
    ])
    assert text.index("## Layout") < text.index("## Ablauf") < text.index("## Aufbau")
    assert "- B1 Modul: „Ideen-Modul“\n  Notiz: Backend und Oberfläche" in text
    assert text.index("## Aufbau") < text.index("Ideen-Modul")


def test_nur_aufbau_bausteine_fehlen_nicht_mehr_im_text():
    text = _render([node("t", "database", "build", "Tabelle Ideen")])
    assert "1 Bausteine" in text and "## Aufbau" in text and "Datenbank / Tabelle: „Tabelle Ideen“" in text
    assert "## Layout" not in text and "## Ablauf" not in text


def test_baustein_einer_unbekannten_gruppe_steht_beim_ablauf():
    text = _render([node("u", "action", "sonstwas", "Fremde Gruppe"), node("o", "action", "", "Ohne Gruppe")])
    assert text.index("## Ablauf") < text.index("Fremde Gruppe") < text.index("Ohne Gruppe")
