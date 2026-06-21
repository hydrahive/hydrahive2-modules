"""Setzt den self-contained Editorial-HTML-Report zusammen."""
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
                f'<figure class="shot"><img src="{_esc(imgs[state["i"]])}" '
                f'loading="lazy" alt="" onerror="this.closest(\'figure\').remove()"></figure>'
            )
            state["i"] += 1
        return out

    return re.sub(r"</h2>", repl, body_html)


def _toc(headings: list[markdown_render.Heading]) -> str:
    if not headings:
        return ""
    items = "".join(
        f'<a class="lvl{h.level}" href="#{h.id}">{_esc(h.text)}</a>' for h in headings
    )
    return f'<nav class="toc"><div class="toc-title">Inhalt</div>{items}</nav>'


def _stats_bar(stats: dict) -> str:
    pairs = [
        (f'{stats.get("duration_s", "?")}s', "Dauer"),
        (str(stats.get("rounds", "?")), "Runden"),
        (str(stats.get("queries", "?")), "Queries"),
        (str(stats.get("sources", stats.get("urls", "?"))), "Quellen"),
        (_esc(str(stats.get("model", "default"))), "Modell"),
    ]
    cells = "".join(f"<div class='stat'><b>{v}</b><span>{k}</span></div>" for v, k in pairs)
    return f'<div class="stats">{cells}</div>'


def _sources(sources: list[dict]) -> str:
    if not sources:
        return ""
    items = "".join(
        f'<li><a href="{_esc(s["url"])}" target="_blank" rel="noopener noreferrer">'
        f'{_esc(s.get("title") or s["url"])}</a> '
        f'<span class="dom">{_esc(_domain(s["url"]))}</span></li>'
        for s in sources
    )
    return (
        f'<details class="sources" open><summary>Quellen ({len(sources)})</summary>'
        f"<ol>{items}</ol></details>"
    )


_TOOLBAR = (
    '<div class="toolbar"><div style="position:relative">'
    '<button id="btn-export">⤓ Export ▾</button>'
    '<div class="menu" id="export-menu">'
    '<button id="btn-pdf">Als PDF drucken</button>'
    '<button id="btn-html">HTML laden</button>'
    "</div></div></div>"
)


def generate_report_html(question: str, result: dict) -> str:
    markdown = result.get("markdown", "") or ""
    sources = result.get("sources", []) or []
    stats = result.get("stats", {}) or {}

    body_html, headings = markdown_render.render(markdown)
    hero, section_imgs = images.pick_images(sources)
    body_html = _inject_images(body_html, section_imgs)

    hero_html = (
        f'<img class="hero-img" src="{_esc(hero)}" alt="" loading="eager" '
        f'onerror="this.remove()">' if hero else ""
    )

    return (
        "<!doctype html><html lang='de'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{_esc(question)}</title><style>" + CSS + "</style></head><body>"
        + _TOOLBAR
        + '<div class="wrap"><header class="hero">'
        + '<p class="eyebrow">HydraHive — Deep Research</p>'
        + f"<h1>{_esc(question)}</h1>"
        + hero_html
        + _stats_bar(stats)
        + "</header>"
        + '<div class="layout">'
        + _toc(headings)
        + f'<main class="content">{body_html}{_sources(sources)}'
        + '<div class="foot">Erstellt mit HydraHive Deep Research</div>'
        + "</main></div></div>"
        + "<script>" + JS + "</script></body></html>"
    )
