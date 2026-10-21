"""HTML → lesbarer Text (für Volltext, Kurztext und Agenten). Nur Standardbibliothek; Skripte und Stile fallen weg."""
from __future__ import annotations

import re
from html.parser import HTMLParser

_BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "table", "blockquote", "pre", "hr"}
_DROP = {"script", "style", "head", "title", "noscript", "template", "svg"}


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in _DROP:
            self.skip += 1
        elif tag in _BLOCK:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in _DROP:
            self.skip = max(0, self.skip - 1)
        elif tag in _BLOCK:
            self.out.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


def to_text(html: str) -> str:
    p = _Text()
    try:
        p.feed(html)
        p.close()
    except (ValueError, AssertionError):
        pass
    text = "".join(p.out).replace("\xa0", " ")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()
