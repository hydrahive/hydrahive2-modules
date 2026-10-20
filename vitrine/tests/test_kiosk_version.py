"""Seitenversion des Kiosks: Hash über kiosk_page.html + kiosk_chat.js; steht in der Seite und in /data."""
from __future__ import annotations

import shutil

import pytest

pytest.importorskip("hydrahive")


@pytest.fixture
def files(tmp_path, monkeypatch):
    from backend import kiosk
    for name in ("kiosk_page.html", "kiosk_chat.js"):
        shutil.copy(kiosk.HERE / name, tmp_path / name)
    monkeypatch.setattr(kiosk, "HERE", tmp_path)
    return tmp_path


def test_version_steht_in_der_seite(files):
    from backend import kiosk
    html = kiosk.page("K")
    assert f'const PAGE_VERSION = "{kiosk.page_version()}";' in html
    assert "__VERSION__" not in html and len(kiosk.page_version()) == 16


@pytest.mark.parametrize("name", ["kiosk_page.html", "kiosk_chat.js"])
def test_version_aendert_sich_mit_jeder_der_beiden_dateien(files, name):
    from backend import kiosk
    before = kiosk.page_version()
    (files / name).write_text((files / name).read_text(encoding="utf-8") + "\n// geändert\n", encoding="utf-8")
    assert kiosk.page_version() != before
    assert kiosk.page_version() == kiosk.page_version()
