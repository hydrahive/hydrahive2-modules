"""Inline-CSS von HTML-Mails filtern: nur harmlose Eigenschaften, keine URLs, keine Ausdrücke, keine Positionierung.

Erlaubtliste statt Verbotsliste: alles Unbekannte fällt weg (auch neue Tricks).
"""
from __future__ import annotations

import re

PROPS = {"color", "background-color", "font-weight", "font-style", "font-size", "font-family", "text-align",
         "text-decoration", "line-height", "vertical-align", "white-space", "word-break", "border", "border-top",
         "border-bottom", "border-left", "border-right", "border-color", "border-style", "border-width",
         "border-collapse", "border-spacing", "border-radius", "padding", "padding-top", "padding-bottom",
         "padding-left", "padding-right", "margin", "margin-top", "margin-bottom", "margin-left", "margin-right",
         "width", "max-width", "min-width", "height", "max-height", "min-height", "letter-spacing", "text-indent",
         "text-transform", "list-style-type", "table-layout"}
_VALUE_OK = re.compile(r"^[#A-Za-z0-9%.,\s\-\"'()]*$")
_BAD = re.compile(r"(url|expression|image|attr|var|env|calc|@|\\|javascript|behavior|-moz-binding)", re.IGNORECASE)


def clean_style(style: str) -> str:
    out = []
    for decl in (style or "").split(";"):
        if ":" not in decl:
            continue
        prop, value = decl.split(":", 1)
        prop, value = prop.strip().lower(), value.strip()
        if prop not in PROPS or not value or len(value) > 200:
            continue
        if _BAD.search(value) or not _VALUE_OK.match(value):
            continue
        if "(" in value and not re.fullmatch(r"[^()]*rgba?\([0-9.,\s%]+\)[^()]*", value):
            continue
        out.append(f"{prop}:{value}")
    return ";".join(out)
