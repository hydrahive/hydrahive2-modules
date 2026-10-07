"""Ghostwriter G2: Schätzung und Kosten (Spec §9.4). Keine eigenen Preise im Modul – nur der Kern-Tarif."""
from __future__ import annotations

from backend import _cost, ghost


def test_tokens_from_text_is_chars_by_four():
    assert _cost.tokens("") == 0
    assert _cost.tokens("abcd" * 10) == 10


def test_scene_estimate_sections_and_tokens():
    m = ghost.Material("s" * 32, "fill", "S" * 400, "P" * 800)
    e = _cost.scene_estimate(m, length_words=1500, chunk_words=500)
    assert e["sections"] == 3
    assert e["output_tokens"] == int(1500 * 1.6)
    # Eingabe: Material je Abschnitt + wachsender „so weit geschrieben“-Teil
    assert e["input_tokens"] >= 3 * (1200 // 4)


def test_sections_capped_at_max():
    m = ghost.Material("s" * 32, "fill", "", "")
    assert _cost.scene_estimate(m, length_words=6000, chunk_words=200)["sections"] == ghost.MAX_SECTIONS


def test_cost_known_model_uses_core_pricing():
    # Sonnet 4.x im Kern: 0.3 / 1.5 Mikro-Cent je Token
    assert _cost.cost_micros("claude-sonnet-4-6", tokens_in=1000, tokens_out=1000) == 1800


def test_cost_unknown_model_is_none():
    assert _cost.cost_micros("irgendwer/modell-x", tokens_in=1000, tokens_out=1000) is None
    assert _cost.cost_micros("", tokens_in=1000, tokens_out=1000) is None
