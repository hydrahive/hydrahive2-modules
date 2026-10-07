"""Denktext (<think>…</think>) von Reasoning-Modellen darf nie im Buch landen (Fix 0.6.1, Task 3d7e9782)."""
from __future__ import annotations

import pytest
from backend import ghost
from backend._think import ThinkFilter, strip_think
from backend.ai import clean_proposal

THOUGHT = "<think>" + "Ich überlege, wie Mia sich fühlt. " * 30 + "</think>\n\n"
BODY = "Mia stand am Fenster und sah dem Licht zu. " * 10


def _run_filter(text: str, size: int) -> str:
    f = ThinkFilter()
    out = "".join(f.feed(text[i:i + size]) for i in range(0, len(text), size))
    return out + f.end()


@pytest.mark.parametrize("size", [1, 3, 7, 20, 1000])
def test_filter_removes_long_thought_whatever_the_chunking(size):
    assert _run_filter(THOUGHT + BODY, size) == "\n\n" + BODY


@pytest.mark.parametrize("size", [1, 2, 5])
def test_filter_handles_tags_split_across_pieces_and_case(size):
    text = "Vorher. <THINK>geheim</Think> Nachher. <thinking>auch geheim</thinking>Ende."
    assert _run_filter(text, size) == "Vorher.  Nachher. Ende."


def test_filter_drops_unclosed_thought_at_end():
    assert _run_filter("Anfang. <think>bricht ab wegen max_tokens", 4) == "Anfang. "


def test_filter_keeps_normal_text_with_angle_brackets():
    text = "Er schrieb a < b und <b>fett</b> und <thin ist kein Tag."
    assert _run_filter(text, 3) == text


def test_filter_holds_back_only_while_a_tag_could_start():
    f = ThinkFilter()
    assert f.feed("Hallo <th") == "Hallo "
    assert f.feed("ema>") == "<thema>"


def test_strip_think_closed_and_unclosed():
    assert strip_think("<think>a</think>Text") == "Text"
    assert strip_think("Text<think>offen bis zum Ende") == "Text"
    assert strip_think("A<thinking>x</thinking>B<think>y</think>C") == "ABC"
    assert strip_think("ohne") == "ohne"


def test_clean_proposal_drops_unclosed_thought():
    assert clean_proposal("<think>" + "lang " * 200) == ""
    assert clean_proposal("<think>x</think>\n\"Er erwachte.\"") == "Er erwachte."


async def test_write_scene_never_streams_thought(monkeypatch):
    """Nachbau des gemeldeten Fehlers: 600+ Zeichen Denktext vor dem Text, Stücke zu 20 Zeichen."""
    text = THOUGHT + BODY

    async def fake_stream(messages, model=None, temperature=0.7, max_tokens=4096):
        for i in range(0, len(text), 20):
            yield text[i:i + 20]

    monkeypatch.setattr(ghost, "stream", fake_stream)
    m = ghost.Material("s", "fill", "sys", "prompt")
    pieces = [p async for p in ghost.write_scene(m, model=None, length_words=60, chunk_words=60)]
    out = "".join(pieces)
    assert "<think" not in out and "überlege" not in out
    assert out.strip().startswith("Mia stand am Fenster")


async def test_write_scene_thought_in_the_middle_of_a_section(monkeypatch):
    text = BODY + "<think>" + "nochmal nachdenken " * 40 + "</think>" + "Dann ging sie schlafen. " * 3

    async def fake_stream(messages, model=None, temperature=0.7, max_tokens=4096):
        for i in range(0, len(text), 13):
            yield text[i:i + 13]

    monkeypatch.setattr(ghost, "stream", fake_stream)
    m = ghost.Material("s", "fill", "sys", "prompt")
    out = "".join([p async for p in ghost.write_scene(m, model=None, length_words=60, chunk_words=60)])
    assert "nachdenken" not in out and "<think" not in out and "Dann ging sie schlafen." in out


def test_filter_end_releases_held_back_text_and_drops_partial_close():
    f = ThinkFilter()
    assert f.feed("Er schrieb ein Herz: <") == "Er schrieb ein Herz: "
    assert f.end() == "<"
    g = ThinkFilter()
    assert g.feed("Text<think>denkt noch</thi") == "Text"
    assert g.end() == ""                                 # offener Block samt halbem Schlusstag fällt weg


async def test_write_scene_releases_text_held_back_at_the_very_end(monkeypatch):
    for text in (BODY + "und dann <", "Kurz <"):          # langer Abschnitt (gesendet) und kurzer (nur im Puffer)
        async def fake_stream(messages, model=None, temperature=0.7, max_tokens=4096, text=text):
            for i in range(0, len(text), 9):
                yield text[i:i + 9]
        monkeypatch.setattr(ghost, "stream", fake_stream)
        m = ghost.Material("s", "fill", "sys", "prompt")
        out = "".join([p async for p in ghost.write_scene(m, model=None, length_words=60, chunk_words=60)])
        assert out.rstrip().endswith("<"), text
