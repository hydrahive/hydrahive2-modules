"""Ohne eigenes Modell fragt das Modul die Rolle an (Agenten-Templates, Kern E5)."""
from __future__ import annotations


def test_role_kw(monkeypatch):
    from backend.chess_llm import _role_kw
    from hydrahive.llm import client
    monkeypatch.setattr(client, "SUPPORTS_TEMPLATE", True, raising=False)
    assert _role_kw(None, "modul-schnell") == {"template": "modul-schnell"}
    assert _role_kw("claude-sonnet-5", "modul-schnell") == {}
    monkeypatch.delattr(client, "SUPPORTS_TEMPLATE", raising=False)
    assert _role_kw(None, "modul-schnell") == {}
