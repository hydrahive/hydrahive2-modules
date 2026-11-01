"""Weg erkennen: Kabel, Mobilfunk-Ersatz an der FRITZ!Box, gar nichts."""
from __future__ import annotations

import pytest
from backend import classify


@pytest.mark.parametrize("loss,link,ip,path", [
    (None, "Up", "37.24.1.2", "unknown"),
    (100.0, "Up", "37.24.1.2", "none"),
    (0.0, "Up", "37.24.1.2", "cable"),
    (40.0, "Up", "37.24.1.2", "cable"),
    (0.0, "Down", "37.24.1.2", "mobile"),
    (0.0, "Up", "100.72.3.4", "mobile"),
    (0.0, "Up", "10.20.30.40", "mobile"),
    (0.0, None, None, "unknown"),
    (0.0, "Up", None, "cable"),
    (0.0, "Up", "kaputt", "cable"),
])
def test_weg(loss, link, ip, path):
    assert classify.path(loss, link, ip) == path


@pytest.mark.parametrize("mn,avg,path", [(0, 0, "none"), (None, None, "unknown"), (7, 9.5, "cable"),
                                         (18, 33.7, "mobile"), (22, 29.0, "mobile"), (0, 20.6, "unknown"),
                                         (17, 20.0, "cable")])
def test_vermutung_fuer_alte_stunden(mn, avg, path):
    assert classify.guess_hour(mn, avg) == path
