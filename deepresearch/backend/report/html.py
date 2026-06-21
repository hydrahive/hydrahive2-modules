"""Setzt den self-contained Editorial-HTML-Report zusammen (Struktur 1:1 nach odysseus)."""
from __future__ import annotations

import html as _html
import re
from urllib.parse import urlparse

from . import images, markdown_render
from .script import JS
from .styles import CSS


def _esc(s: str) -> str:
    return _html.escape(s or "", quote=True)


def _domain(url: str) -> str:
    try:
        host = urlparse(url).hostname or ""
    except ValueError:
        host = ""
    return host[4:] if host.startswith("www.") else host


def _strip_leading_h1(md: str) -> str:
    """Hero zeigt den Titel — eine führende '# …'-Zeile aus dem Body entfernen."""
    lines = md.lstrip("\n").splitlines()
    if lines and lines[0].lstrip().startswith("# "):
        return "\n".join(lines[1:]).lstrip("\n")
    return md


def _inject_images(body_html: str, imgs: list[str]) -> str:
    """Ein Sektionsbild nach jedem 2. </h2> einsetzen, solange Bilder da sind."""
    if not imgs:
        return body_html
    state = {"count": 0, "i": 0}

    def repl(_m: re.Match) -> str:
        state["count"] += 1
        out = "</h2>"
        if state["count"] % 2 == 0 and state["i"] < len(imgs):
            out += (
                f'<div class="section-image"><img src="{_esc(imgs[state["i"]])}" '
                f'loading="lazy" alt="" onerror="this.closest(\'.section-image\').remove()"></div>'
            )
            state["i"] += 1
        return out

    return re.sub(r"</h2>", repl, body_html)


def _toc(headings: list[markdown_render.Heading]) -> str:
    if not headings:
        return ""
    items = "".join(
        f'<a class="depth-{h.level}" href="#{h.id}">{_esc(h.text)}</a>' for h in headings
    )
    return f'<aside class="toc-sidebar"><nav>{items}</nav></aside>'


def _stats_bar(stats: dict) -> str:
    pairs = [
        (f'{stats.get("duration_s", "?")}s', "Dauer"),
        (str(stats.get("rounds", "?")), "Runden"),
        (str(stats.get("queries", "?")), "Queries"),
        (str(stats.get("sources", stats.get("urls", "?"))), "Quellen"),
        (_esc(str(stats.get("model", "default"))), "Modell"),
    ]
    cells = "".join(f'<div class="stat"><span class="stat-value">{v}</span> {k}</div>' for v, k in pairs)
    return f'<div class="stats-bar">{cells}</div>'


def _sources(sources: list[dict]) -> str:
    if not sources:
        return ""
    items = "".join(
        f'<a href="{_esc(s["url"])}" target="_blank" rel="noopener noreferrer">'
        f'<span class="snum">{i + 1}</span>{_esc(s.get("title") or s["url"])}'
        f'<span class="sdomain">{_esc(_domain(s["url"]))}</span></a>'
        for i, s in enumerate(sources)
    )
    return (
        '<div class="sources-panel"><details open>'
        f'<summary>Quellen ({len(sources)})</summary>'
        f'<div class="sources-list">{items}</div></details></div>'
    )


_TOOLBAR = (
    '<div class="toolbar"><div class="dropdown">'
    '<button id="btn-export">⤓ Export ▾</button>'
    '<div class="menu" id="export-menu">'
    '<button id="btn-pdf">Als PDF drucken</button>'
    '<button id="btn-html">HTML laden</button>'
    "</div></div></div>"
)


def generate_report_html(question: str, result: dict) -> str:
    markdown = _strip_leading_h1(result.get("markdown", "") or "")
    sources = result.get("sources", []) or []
    stats = result.get("stats", {}) or {}

    body_html, headings = markdown_render.render(markdown)
    hero, section_imgs = images.pick_images(sources)
    body_html = _inject_images(body_html, section_imgs)

    hero_image = (
        f'<div class="hero-image"><img src="{_esc(hero)}" alt="" loading="eager" '
        f'onerror="this.closest(\'.hero-image\').remove()"></div>' if hero else ""
    )

    return (
        "<!doctype html><html lang='de'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{_esc(question)}</title><style>" + CSS + "</style></head><body>"
        + _TOOLBAR
        + f'<header class="hero"><div class="hero-label">HydraHive — Deep Research</div><h1>{_esc(question)}</h1></header>'
        + hero_image
        + _stats_bar(stats)
        + '<div class="layout">'
        + _toc(headings)
        + f'<main class="content">{body_html}{_sources(sources)}'
        + '<div class="report-footer">Erstellt mit HydraHive Deep Research</div>'
        + "</main></div>"
        + "<script>" + JS + "</script></body></html>"
    )
