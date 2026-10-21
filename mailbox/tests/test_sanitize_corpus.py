"""M1 Schritt 9: Bereinigung gegen öffentliche XSS-Muster (SecLists, MIT). Prüft die AUSGABE so, wie ein Browser sie liest:
nur erlaubte Tags/Attribute, nur sichere URLs, keine CSS-Tricks, keine Kommentare/Deklarationen."""
from __future__ import annotations

import re
import urllib.parse
from html.parser import HTMLParser

import pytest
from conftest import FIXTURES

_SAFE_URL = re.compile(r"^(https?://|mailto:|tel:|/api/modules/mailbox/|data:image/(png|jpe?g|gif|webp|bmp);base64,)")


def _patterns() -> list[str]:
    out = []
    for line in (FIXTURES / "xss_seclists.txt").read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("# "):
            out.append(line)
            if "%3c" in line.lower():
                out.append(urllib.parse.unquote(line))
    return out


class _Browserblick(HTMLParser):
    def __init__(self, tags, attrs):
        super().__init__(convert_charrefs=True)
        self.tags, self.attrs, self.bad = tags, attrs, []

    def handle_starttag(self, tag, attrs):
        if tag not in self.tags:
            self.bad.append(("tag", tag))
        ok = self.attrs["*"] | self.attrs.get(tag, set()) | {"target", "rel", "referrerpolicy", "data-mbx-blocked"}
        for k, v in attrs:
            if k not in ok:
                self.bad.append(("attr", k))
            if k in ("href", "src") and v and not _SAFE_URL.match(re.sub(r"[\x00-\x20\x7f]+", "", v).lower()):
                self.bad.append(("url", v))
            if k == "style" and v and re.search(r"url|expression|image|var|attr|calc|@|\\|javascript|behavior|binding", v, re.I):
                self.bad.append(("style", v))
    handle_startendtag = handle_starttag

    def handle_comment(self, data):
        self.bad.append(("comment", data))

    def handle_decl(self, decl):
        self.bad.append(("decl", decl))

    def unknown_decl(self, data):
        self.bad.append(("cdata", data))

    def handle_pi(self, data):
        self.bad.append(("pi", data))


@pytest.mark.parametrize("remote", [False, True])
def test_oeffentliche_xss_muster(remote):
    from backend import sanitize
    pats = _patterns()
    assert len(pats) > 250
    fails = []
    for p in pats:
        out = sanitize.clean(p, allow_remote=remote)["html"]
        b = _Browserblick(sanitize.TAGS, sanitize.ATTRS)
        b.feed(out)
        b.close()
        if b.bad:
            fails.append((p, out, b.bad[:2]))
    assert not fails, fails[:3]
