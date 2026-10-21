"""M1 Schritt 9: HTML-Mail bereinigen (Spec §6/§11). Erlaubtliste, keine Skripte, externe Bilder erst nach Klick."""
from __future__ import annotations

import pytest

CID = {"logo123": "/api/modules/mailbox/attachments/7/1"}


def _s(html, **kw):
    from backend import sanitize
    return sanitize.clean(html, cid_urls=kw.pop("cid", CID), **kw)


@pytest.mark.parametrize("evil", [
    "<script>alert(1)</script>", "<SCRIPT SRC=//x.example/a.js></SCRIPT>", "<svg onload=alert(1)>",
    "<img src=x onerror=alert(1)>", "<body onload=alert(1)>", "<iframe src='https://x.example'></iframe>",
    "<object data=x></object>", "<embed src=x>", "<form action=https://x.example><input name=p></form>",
    "<meta http-equiv=refresh content='0;url=https://x.example'>", "<base href='https://x.example/'>",
    "<link rel=stylesheet href=https://x.example/a.css>", "<a href='javascript:alert(1)'>x</a>",
    "<a href='JaVaScRiPt:alert(1)'>x</a>", "<a href=' java\tscript:alert(1)'>x</a>", "<a href='vbscript:x'>x</a>",
    "<a href='data:text/html,<script>alert(1)</script>'>x</a>", "<img src='javascript:alert(1)'>",
    "<math><mtext><table><mglyph><style><img src=x onerror=alert(1)>", "<style>@import 'https://x.example/a.css'</style>",
    "<div style=\"background:url('https://x.example/t.gif')\">x</div>", "<div style='behavior:url(x.htc)'>x</div>",
    "<div style='width:expression(alert(1))'>x</div>", "<template><script>alert(1)</script></template>",
    "<noscript><img src=x onerror=alert(1)></noscript>", "<!--<script>alert(1)</script>-->",
"<p xmlns:xlink='x' xlink:href='javascript:x'>x</p>",
    "<img srcset='https://x.example/a.png 1x'>", "<video poster='https://x.example/p.png'></video>",
    "<table background='https://x.example/bg.png'><tr><td>x</td></tr></table>", "<input autofocus onfocus=alert(1)>",
])
def test_gefaehrliches_ist_weg(evil):
    out = _s(evil)["html"].lower()
    for bad in ("<script", "onerror", "onload", "onmouseover", "onfocus", "javascript:", "vbscript:", "<iframe",
                "<object", "<embed", "<form", "<input", "<meta", "<base", "<link", "expression(", "behavior:",
                "@import", "data:text/html", "x.example", "<svg", "<math", "<template", "xlink"):
        assert bad not in out, (evil, out)


def test_harmloses_bleibt():
    out = _s("<p>Hallo <b>Till</b>, <i>bitte</i> <a href='https://shop.example/x?a=1&b=2'>hier</a>.</p>"
             "<table><tr><td style='color:#333;font-weight:bold'>Zelle</td></tr></table><ul><li>eins</li></ul>")["html"]
    assert "<b>Till</b>" in out and "<i>bitte</i>" in out and "<li>eins</li>" in out and "<td" in out
    assert 'href="https://shop.example/x?a=1&amp;b=2"' in out
    assert 'rel="noopener noreferrer nofollow"' in out and 'target="_blank"' in out
    assert "color:#333" in out and "font-weight:bold" in out


def test_mailto_und_tel_erlaubt():
    out = _s("<a href='mailto:a@b.de'>m</a><a href='tel:+491234'>t</a><a href='ftp://x'>f</a>")["html"]
    assert "mailto:a@b.de" in out and "tel:+491234" in out and "ftp:" not in out


def test_externe_bilder_gesperrt_und_gezaehlt():
    r = _s("<img src='https://track.example/p.gif' width=1 height=1><img src='http://cdn.example/logo.png' alt='Logo'>")
    assert "track.example" not in r["html"] and "cdn.example" not in r["html"]
    assert r["blocked_images"] == 2 and r["html"].count("data-mbx-blocked") == 2
    assert 'alt="Logo"' in r["html"]


def test_externe_bilder_nach_freigabe():
    r = _s("<img src='https://cdn.example/logo.png'>", allow_remote=True)
    assert 'src="https://cdn.example/logo.png"' in r["html"] and r["blocked_images"] == 0
    assert 'referrerpolicy="no-referrer"' in r["html"]


def test_freigabe_laesst_trotzdem_nur_http():
    r = _s("<img src='javascript:alert(1)'><img src='file:///etc/passwd'>", allow_remote=True)
    assert "javascript" not in r["html"] and "file:" not in r["html"]


def test_cid_wird_zur_anhang_url():
    r = _s("<img src='cid:logo123'><img src='CID:unbekannt'>")
    assert 'src="/api/modules/mailbox/attachments/7/1"' in r["html"] and "unbekannt" not in r["html"]
    assert r["blocked_images"] == 0


def test_data_bilder_nur_als_bild():
    r = _s("<img src='data:image/png;base64,iVBORw0KGgo='><img src='data:image/svg+xml;base64,PHN2Zz4='>")
    assert "data:image/png" in r["html"] and "svg" not in r["html"]


def test_style_block_entfernt_inline_gefiltert():
    r = _s("<style>body{display:none}</style><p style='position:fixed;top:0;color:red;font-size:12px'>x</p>")["html"]
    assert "display:none" not in r and "position" not in r and "color:red" in r and "font-size:12px" in r


def test_kaputtes_html_ohne_ausnahme():
    for html in ("<p><b>offen", "</div></div>", "<<<>>>", "<a href=", "\x00<p>x</p>", "<" * 10000, ""):
        _s(html)


def test_text_ist_maskiert():
    assert "&lt;script&gt;" in _s("<p>&lt;script&gt;</p>")["html"]


def test_csp_header_streng():
    from backend import sanitize
    csp = sanitize.CSP
    assert "default-src 'none'" in csp and "script-src" not in csp.replace("default-src 'none'", "")
    assert "img-src 'self' data:" in csp and "form-action 'none'" in csp and "base-uri 'none'" in csp
    assert "frame-ancestors 'self'" in csp
    assert "https:" in sanitize.csp(allow_remote=True) and "https:" not in sanitize.csp(allow_remote=False)


def test_seite_mit_meta_und_ohne_skript():
    from backend import sanitize
    page = sanitize.page(_s("<p>Hi</p>")["html"])
    assert page.startswith("<!doctype html>") and "<script" not in page.lower()
    assert '<meta name="referrer" content="no-referrer">' in page and "<p>Hi</p>" in page


def test_link_bleibt_ereignis_weg():
    out = _s('<a href="https://x.example" onmouseover="alert(1)" onclick="x()">x</a>')["html"]
    assert out == '<a href="https://x.example" target="_blank" rel="noopener noreferrer nofollow">x</a>'


@pytest.mark.parametrize("href", ["java\x00script:alert(1)", "java\nscript:alert(1)", "\x01javascript:alert(1)",
                                  "  https://ok.example/x  "])
def test_steuerzeichen_in_urls(href):
    """Browser ignorieren Steuerzeichen im Schema – deshalb vor der Prüfung entfernen (nicht nur trimmen)."""
    from backend import sanitize
    assert sanitize._norm_url(href) == href.replace("\x00", "").replace("\n", "").replace("\x01", "").strip()
    out = _s(f'<a href="{href}">x</a>')["html"]
    assert "javascript" not in out.lower()


def test_offene_tags_werden_geschlossen():
    """Nicht geschlossenes <b>/<table> darf nicht in den Rahmen der Webmail „auslaufen“."""
    assert _s("<div><b>fett<table><tr><td>x")["html"] == "<div><b>fett<table><tr><td>x</td></tr></table></b></div>"


@pytest.mark.parametrize("value", ["url(x)", "red url(x)", "expression(alert(1))", "var(--x)", "attr(title)",
                                   "calc(100% - 1px)", "image-set(x)", "rgb(1,2,3) url(x)", "\\75rl(x)"])
def test_css_werte_einzeln(value):
    from backend import sanitize_css
    assert sanitize_css.clean_style(f"color:{value}") == ""


@pytest.mark.parametrize("value", ["rgb(1, 2, 3)", "rgba(0,0,0,0.5)", "#fff", "red", "1px solid rgb(9,9,9)"])
def test_css_farben_erlaubt(value):
    from backend import sanitize_css
    assert sanitize_css.clean_style(f"border:{value}") == f"border:{value}"


def test_css_klammern_nur_fuer_farben():
    from backend import sanitize_css
    assert sanitize_css.clean_style("font-family:x(1)") == ""
    assert sanitize_css.clean_style("width:a(b)") == ""


@pytest.mark.parametrize("value", ["javascript", "-moz-binding", "behavior", "x @import y", "image"])
def test_css_verbotene_woerter_auch_ohne_klammern(value):
    """Erste Schicht (_BAD) unabhängig von der Klammer-Regel prüfen."""
    from backend import sanitize_css
    assert sanitize_css.clean_style(f"font-family:{value}") == ""
