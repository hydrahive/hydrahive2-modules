"""Markdown → sicheres HTML (dep-frei) + Heading-Extraktion fürs Inhaltsverzeichnis.

Bewusst KEINE markdown/nh3-Pakete: wir erzeugen das HTML selbst und emittieren nur
eine feste Allowlist eigener Tags. Aller Text wird vorab ge-escaped, Link-URLs werden
auf http(s) validiert — damit gibt es keinen Injection-Vektor (Inhalt ist LLM-Prosa).

ponytail: deckt die vom Report-Writer erzeugte Markdown-Teilmenge ab (Überschriften,
Absätze, **fett**, *kursiv*, `code`, Links, -/1.-Listen, > Zitate). Keine Tabellen/
Code-Blöcke — bei Bedarf hier erweitern.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass

_HEADING = re.compile(r"^(#{1,3})\s+(.*)$")
_ULI = re.compile(r"^[-*]\s+(.*)$")
_OLI = re.compile(r"^\d+\.\s+(.*)$")
_QUOTE = re.compile(r"^>\s?(.*)$")

_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")
_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_ITALIC = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")
_CODE = re.compile(r"`([^`]+)`")
_BARE_URL = re.compile(r"(?<![\"'>=])(https?://[^\s<)]+)")


@dataclass
class Heading:
    level: int
    id: str
    text: str


def _slug(text: str, used: set[str]) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "section"
    slug, n = base, 2
    while slug in used:
        slug = f"{base}-{n}"
        n += 1
    used.add(slug)
    return slug


def _inline(text: str) -> str:
    """Escape, dann sichere Inline-Auszeichnung. Reihenfolge: Links zuerst (sonst
    würde _BARE_URL die URL im href doppelt verlinken)."""
    text = html.escape(text, quote=False)
    text = _LINK.sub(
        lambda m: f'<a href="{html.escape(m.group(2), quote=True)}" target="_blank" rel="noopener noreferrer">{m.group(1)}</a>',
        text,
    )
    text = _BOLD.sub(r"<strong>\1</strong>", text)
    text = _ITALIC.sub(r"<em>\1</em>", text)
    text = _CODE.sub(r"<code>\1</code>", text)
    text = _BARE_URL.sub(
        lambda m: f'<a href="{html.escape(m.group(1), quote=True)}" target="_blank" rel="noopener noreferrer">{m.group(1)}</a>',
        text,
    )
    return text


def render(markdown: str) -> tuple[str, list[Heading]]:
    """Returnt (html, headings). headings sind h2/h3 fürs TOC."""
    out: list[str] = []
    headings: list[Heading] = []
    used: set[str] = set()
    list_tag: str | None = None
    para: list[str] = []

    def flush_para() -> None:
        if para:
            out.append(f"<p>{' '.join(para)}</p>")
            para.clear()

    def close_list() -> None:
        nonlocal list_tag
        if list_tag:
            out.append(f"</{list_tag}>")
            list_tag = None

    for raw in markdown.splitlines():
        line = raw.rstrip()
        if not line.strip():
            flush_para()
            close_list()
            continue

        m = _HEADING.match(line)
        if m:
            flush_para()
            close_list()
            level = len(m.group(1))
            text = m.group(2).strip()
            hid = _slug(text, used)
            out.append(f'<h{level} id="{hid}">{_inline(text)}</h{level}>')
            if level in (2, 3):
                headings.append(Heading(level=level, id=hid, text=text))
            continue

        m = _QUOTE.match(line)
        if m:
            flush_para()
            close_list()
            out.append(f"<blockquote>{_inline(m.group(1))}</blockquote>")
            continue

        m = _ULI.match(line) or _OLI.match(line)
        if m:
            flush_para()
            want = "ul" if _ULI.match(line) else "ol"
            if list_tag != want:
                close_list()
                out.append(f"<{want}>")
                list_tag = want
            out.append(f"<li>{_inline(m.group(1))}</li>")
            continue

        close_list()
        para.append(_inline(line.strip()))

    flush_para()
    close_list()
    return "\n".join(out), headings
