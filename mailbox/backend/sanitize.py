"""HTML-Mail bereinigen (Spec §6/§11) – strenge Erlaubtliste mit html.parser (keine neue Abhängigkeit).

Nur erlaubte Tags/Attribute kommen durch, alles wird neu geschrieben (nie Roh-HTML weiterreichen). Links: nur
http(s)/mailto/tel, mit target=_blank + rel=noopener. Bilder: cid: → Anhang-URL, data:image (Raster) bleibt,
externe nur mit Freigabe – sonst Platzhalter. Dazu: sandbox-iframe ohne allow-scripts + strenge CSP (zweite Schicht).
"""
from __future__ import annotations

import re
from html import escape
from html.parser import HTMLParser

from .sanitize_css import clean_style

TAGS = {"a", "abbr", "b", "blockquote", "br", "caption", "center", "code", "col", "colgroup", "dd", "del", "div",
        "dl", "dt", "em", "font", "h1", "h2", "h3", "h4", "h5", "h6", "hr", "i", "img", "ins", "kbd", "li", "mark",
        "ol", "p", "pre", "q", "s", "small", "span", "strike", "strong", "sub", "sup", "table", "tbody", "td",
        "tfoot", "th", "thead", "tr", "tt", "u", "ul"}
VOID = {"br", "col", "hr", "img"}
DROP = {"script", "style", "head", "title", "noscript", "template", "svg", "math", "iframe", "object", "embed",
        "frameset", "frame", "applet", "textarea", "select", "button", "xml"}
ATTRS = {"*": {"title", "dir", "lang", "align", "valign", "style", "width", "height", "bgcolor", "color"},
         "a": {"href"}, "img": {"src", "alt"}, "td": {"colspan", "rowspan"}, "th": {"colspan", "rowspan"},
         "table": {"border", "cellpadding", "cellspacing"}, "font": {"face", "size"}, "ol": {"start", "type"},
         "col": {"span"}, "colgroup": {"span"}}
_LINK = re.compile(r"^(https?://|mailto:|tel:)", re.IGNORECASE)
_DATA_IMG = re.compile(r"^data:image/(png|jpe?g|gif|webp|bmp);base64,[A-Za-z0-9+/=\s]+$", re.IGNORECASE)
_CTRL = re.compile(r"[\x00-\x20\x7f]+")
CSP = ("default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'; font-src 'none'; form-action 'none'; "
       "base-uri 'none'; frame-ancestors 'self'")


def csp(*, allow_remote: bool) -> str:
    return CSP.replace("img-src 'self' data:", "img-src 'self' data: https: http:") if allow_remote else CSP


def _norm_url(v: str) -> str:
    return _CTRL.sub("", v or "")


class _Clean(HTMLParser):
    def __init__(self, cid_urls: dict[str, str], allow_remote: bool):
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.skip = 0
        self.open: list[str] = []
        self.cid, self.remote, self.blocked = cid_urls, allow_remote, 0

    def _attrs(self, tag: str, attrs) -> str:
        allowed = ATTRS["*"] | ATTRS.get(tag, set())
        out = []
        for k, v in attrs:
            k = (k or "").lower()
            if k not in allowed or v is None:
                continue
            if k == "style":
                v = clean_style(v)
                if not v:
                    continue
            elif k == "href":
                v = _norm_url(v)
                if not _LINK.match(v):
                    continue
            elif k == "src":
                v = self._src(v)
                if v is None:
                    continue
            out.append(f' {k}="{escape(v, quote=True)}"')
        if tag == "a" and any(x.startswith(" href=") for x in out):
            out.append(' target="_blank" rel="noopener noreferrer nofollow"')
        if tag == "img" and not any(x.startswith(" src=") for x in out) and self._was_remote:
            out.append(' data-mbx-blocked="1"')
        if tag == "img" and self.remote:
            out.append(' referrerpolicy="no-referrer"')
        return "".join(out)

    _was_remote = False

    def _src(self, v: str) -> str | None:
        v = _norm_url(v)
        self._was_remote = False
        if v.lower().startswith("cid:"):
            return self.cid.get(v[4:].strip("<>"))
        if _DATA_IMG.match(v):
            return v
        if re.match(r"^https?://", v, re.IGNORECASE):
            if self.remote:
                return v
            self.blocked += 1
            self._was_remote = True
        return None

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in DROP:
            self.skip += 1
            return
        if self.skip or tag not in TAGS:
            return
        self._was_remote = False
        self.out.append(f"<{tag}{self._attrs(tag, attrs)}>")
        if tag not in VOID:
            self.open.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag.lower() not in VOID and self.open and self.open[-1] == tag.lower():
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in DROP:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip or tag not in self.open:
            return
        while self.open:
            t = self.open.pop()
            self.out.append(f"</{t}>")
            if t == tag:
                break

    def handle_data(self, data):
        if not self.skip:
            self.out.append(escape(data, quote=False))


def clean(html: str, *, cid_urls: dict[str, str] | None = None, allow_remote: bool = False) -> dict:
    p = _Clean(cid_urls or {}, allow_remote)
    try:
        p.feed((html or "").replace("\x00", ""))
        p.close()
    except (ValueError, AssertionError, IndexError):
        pass
    p.out.extend(f"</{t}>" for t in reversed(p.open))
    return {"html": "".join(p.out), "blocked_images": p.blocked}


def page(body: str) -> str:
    return ('<!doctype html><html><head><meta charset="utf-8"><meta name="referrer" content="no-referrer">'
            '<style>body{font-family:sans-serif;margin:12px;word-wrap:break-word}img{max-width:100%;height:auto}'
            'img[data-mbx-blocked]{display:inline-block;min-width:24px;min-height:24px;background:#eee}</style>'
            f"</head><body>{body}</body></html>")
