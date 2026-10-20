"""Echter Lauf: mitgeliefertes Archify + Node (+ Chromium, falls da). Übersprungen, wenn Node fehlt."""
from __future__ import annotations

import json
import shutil

import pytest
from backend import runner

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="Node fehlt")

CANDIDATE = {
    "schema_version": 2, "diagram_type": "workflow",
    "meta": {"title": "Probe", "locale": "en", "quality_profile": "showcase", "output": "diagramm.html"},
    "lanes": [{"id": "a", "label": "Agent"}, {"id": "t", "label": "Werkzeug"}],
    "mainPath": ["start", "tun", "ende"],
    "nodes": [
        {"id": "start", "lane": "a", "col": 0, "type": "external", "label": "Agent fragt"},
        {"id": "tun", "lane": "t", "col": 1, "type": "backend", "label": "Diagramm bauen"},
        {"id": "ende", "lane": "a", "col": 2, "type": "frontend", "label": "Antwort"},
    ],
    "edges": [{"from": "start", "to": "tun"}, {"from": "tun", "to": "ende"}],
}


def test_real_archify_builds_a_checked_diagram(tmp_path):
    res = runner.build("workflow", json.dumps(CANDIDATE), work=tmp_path)
    assert res.ok, res.detail
    assert "Diagramm bauen" in res.html and "<svg" in res.html
    assert "http://" not in res.html.replace("http://www.w3.org/", "")


def test_real_archify_reports_schema_errors(tmp_path):
    broken = dict(CANDIDATE, nodes=[{"id": "x"}])
    res = runner.build("workflow", json.dumps(broken), work=tmp_path)
    assert not res.ok and res.code == "diagram_invalid" and "schema" in res.detail
