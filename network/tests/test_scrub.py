"""Geheimnisse (UniFi-Felder mit x_) werden auf jeder Ebene verworfen."""
from __future__ import annotations

from backend.scrub import scrub


def test_verwirft_x_felder_ueberall():
    raw = {"name": "Heimnetz", "x_passphrase": "geheim", "nested": [{"x_key": "a", "ok": 1, "deep": {"x_y": 2, "z": 3}}],
           "list": ["x_bleibt_als_wert"]}
    assert scrub(raw) == {"name": "Heimnetz", "nested": [{"ok": 1, "deep": {"z": 3}}], "list": ["x_bleibt_als_wert"]}


def test_andere_werte_unveraendert():
    assert scrub([1, "a", None, {"b": True}]) == [1, "a", None, {"b": True}]
    assert scrub("x_text") == "x_text"
