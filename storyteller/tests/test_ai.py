"""KI-Vorschlag: richtiger Kontext, ändert keine Datei, Fehler lesbar, Grenzen und Drosselung."""
from __future__ import annotations

import pytest
from conftest import MOD_PREFIX, PROJECT_ID

from backend import ai, storage

P = f"{MOD_PREFIX}/projects/{PROJECT_ID}"


@pytest.fixture
def fake_llm(monkeypatch):
    calls = []

    async def fake_complete(messages, model=None, temperature=0.7, max_tokens=4096):
        calls.append({"messages": messages, "model": model, "max_tokens": max_tokens})
        return "  Kürzerer Text.  "
    monkeypatch.setattr(ai, "complete", fake_complete)
    return calls


def _book_with_text(text="Gregor erwachte. Es regnete lange. Die Mutter klopfte."):
    b = storage.create_book(PROJECT_ID, {"title": "T", "kind": "novel", "language": "de", "audience": "Erwachsene"})
    st = storage.get_structure(PROJECT_ID, b["id"])
    sid = st["parts"][0]["chapters"][0]["scenes"][0]
    storage.save_scene(PROJECT_ID, b["id"], sid, {"text": text, "summary": "Erwachen"}, base_version=1)
    st["entities"] = [
        {"id": "a" * 32, "kind": "character", "name": "Gregor", "aliases": [], "description": "Reisender", "fields": []},
        {"id": "b" * 32, "kind": "character", "name": "Grete", "aliases": [], "description": "Schwester", "fields": []},
    ]
    storage.save_structure(PROJECT_ID, b["id"], st, base_version=st["version"])
    return b, sid


def test_suggest_returns_trimmed_proposal_and_changes_nothing(client, auth_headers, fake_llm):
    b, sid = _book_with_text()
    before = storage.get_scene(PROJECT_ID, b["id"], sid)
    r = client.post(f"{P}/books/{b['id']}/ai/suggest", json={"scene_id": sid, "action": "shorten", "selection": "Es regnete lange."}, headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json()["proposal"] == "Kürzerer Text."
    assert storage.get_scene(PROJECT_ID, b["id"], sid) == before


def test_prompt_contains_book_context_and_only_matching_profiles(client, auth_headers, fake_llm):
    b, sid = _book_with_text()
    client.post(f"{P}/books/{b['id']}/ai/suggest", json={"scene_id": sid, "action": "rewrite", "selection": "Es regnete lange."}, headers=auth_headers)
    text = "\n".join(m["content"] for m in fake_llm[0]["messages"])
    assert "Es regnete lange." in text and "Roman" in text and "Deutsch" in text and "Erwachsene" in text
    assert "Reisender" in text and "Schwester" not in text


def test_model_from_request_then_book_then_default(client, auth_headers, fake_llm):
    b, sid = _book_with_text()
    body = {"scene_id": sid, "action": "shorten", "selection": "Es regnete lange."}
    client.post(f"{P}/books/{b['id']}/ai/suggest", json=body, headers=auth_headers)
    assert fake_llm[-1]["model"] is None
    storage.update_book(PROJECT_ID, b["id"], {"model": "buch/modell"}, base_version=storage.get_book(PROJECT_ID, b["id"])["version"])
    client.post(f"{P}/books/{b['id']}/ai/suggest", json=body, headers=auth_headers)
    assert fake_llm[-1]["model"] == "buch/modell"
    client.post(f"{P}/books/{b['id']}/ai/suggest", json={**body, "model": "anfrage/modell"}, headers=auth_headers)
    assert fake_llm[-1]["model"] == "anfrage/modell"


def test_llm_error_is_readable(client, auth_headers, monkeypatch):
    async def broken(*a, **k):
        raise ValueError("Anthropic-Auth fehlt — API-Key oder OAuth-Login auf der LLM-Seite")
    monkeypatch.setattr(ai, "complete", broken)
    b, sid = _book_with_text()
    r = client.post(f"{P}/books/{b['id']}/ai/suggest", json={"scene_id": sid, "action": "shorten", "selection": "Es regnete lange."}, headers=auth_headers)
    assert r.status_code == 502
    assert "Anthropic-Auth fehlt" in r.json()["detail"]["message"]


def test_empty_answer_is_an_error_not_an_empty_suggestion(client, auth_headers, monkeypatch):
    async def empty(*a, **k):
        return "   "
    monkeypatch.setattr(ai, "complete", empty)
    b, sid = _book_with_text()
    r = client.post(f"{P}/books/{b['id']}/ai/suggest", json={"scene_id": sid, "action": "shorten", "selection": "Es regnete lange."}, headers=auth_headers)
    assert r.status_code == 502


def test_limits_and_bad_action(client, auth_headers, fake_llm):
    b, sid = _book_with_text()
    url = f"{P}/books/{b['id']}/ai/suggest"
    assert client.post(url, json={"scene_id": sid, "action": "delete_all", "selection": "x"}, headers=auth_headers).status_code == 422
    assert client.post(url, json={"scene_id": sid, "action": "shorten", "selection": "x" * (ai.MAX_SELECTION + 1)}, headers=auth_headers).status_code == 422
    assert client.post(url, json={"scene_id": sid, "action": "shorten", "selection": ""}, headers=auth_headers).status_code == 422
    assert client.post(url, json={"scene_id": sid, "action": "continue", "selection": ""}, headers=auth_headers).status_code == 200
    assert fake_llm[-1]["max_tokens"] == ai.MAX_TOKENS


def test_rate_limit_per_user(client, auth_headers, fake_llm, monkeypatch):
    monkeypatch.setattr(ai, "RATE_PER_MINUTE", 3)
    b, sid = _book_with_text()
    url = f"{P}/books/{b['id']}/ai/suggest"
    body = {"scene_id": sid, "action": "shorten", "selection": "Es regnete lange."}
    codes = [client.post(url, json=body, headers=auth_headers).status_code for _ in range(4)]
    assert codes == [200, 200, 200, 429]


def test_previous_summaries_are_included(client, auth_headers, fake_llm):
    b, first = _book_with_text()
    st = storage.get_structure(PROJECT_ID, b["id"])
    s2 = storage.add_scene(PROJECT_ID, b["id"], st["parts"][0]["chapters"][0]["id"], title="Zwei")["scene"]
    client.post(f"{P}/books/{b['id']}/ai/suggest", json={"scene_id": s2["id"], "action": "continue", "selection": ""}, headers=auth_headers)
    text = "\n".join(m["content"] for m in fake_llm[-1]["messages"])
    assert "Erwachen" in text


def test_only_one_request_per_user_and_book_at_a_time(monkeypatch):
    """Spec §4: höchstens 1 Anfrage gleichzeitig je Nutzer und Buch; danach wieder frei (auch nach Fehler)."""
    import asyncio
    b, sid = _book_with_text()
    gate = asyncio.Event()

    async def slow(messages, model=None, temperature=0.7, max_tokens=4096):
        await gate.wait()
        return "ok"
    monkeypatch.setattr(ai, "complete", slow)

    async def run():
        first = asyncio.create_task(ai.suggest("u", PROJECT_ID, b["id"], sid, "continue", "", None))
        await asyncio.sleep(0)
        try:  # ohne Sperre würde die zweite Anfrage auf das Modell warten → kurz begrenzen statt hängen
            await asyncio.wait_for(ai.suggest("u", PROJECT_ID, b["id"], sid, "continue", "", None), timeout=1)
            raise AssertionError("zweite Anfrage hätte abgelehnt werden müssen")
        except ai.AiError as exc:
            assert exc.code == "ai_busy" and exc.status == 409
        except asyncio.TimeoutError:
            raise AssertionError("zweite Anfrage wurde nicht sofort abgelehnt") from None
        other_user = asyncio.create_task(ai.suggest("v", PROJECT_ID, b["id"], sid, "continue", "", None))
        await asyncio.sleep(0)
        gate.set()
        assert (await first)["proposal"] == "ok" and (await other_user)["proposal"] == "ok"
        assert (await ai.suggest("u", PROJECT_ID, b["id"], sid, "continue", "", None))["proposal"] == "ok"

        async def broken(*a, **k):
            raise RuntimeError("weg")
        monkeypatch.setattr(ai, "complete", broken)
        with pytest.raises(ai.AiError):
            await ai.suggest("u", PROJECT_ID, b["id"], sid, "continue", "", None)
        assert ("u", b["id"]) not in ai._busy
    asyncio.run(run())


def test_continue_writes_after_the_cursor_anchor_not_at_the_end(client, auth_headers, fake_llm):
    """Weiterschreiben mitten in der Szene: Text vor dem Anker ist „davor“, der Rest „danach“, keine Markierung."""
    b, sid = _book_with_text("Anfang hier. Mitte dort. Schluss am Ende.")
    r = client.post(f"{P}/books/{b['id']}/ai/suggest", json={"scene_id": sid, "action": "continue", "selection": "Anfang hier."}, headers=auth_headers)
    assert r.status_code == 200, r.text
    prompt = fake_llm[-1]["messages"][1]["content"]
    assert "Text davor:\nAnfang hier." in prompt and "Text danach:\n Mitte dort. Schluss am Ende." in prompt
    assert "MARKIERTER TEXT" not in prompt and "Weiterschreiben ab hier." in prompt
    client.post(f"{P}/books/{b['id']}/ai/suggest", json={"scene_id": sid, "action": "continue", "selection": "gibt es nicht"}, headers=auth_headers)
    prompt = fake_llm[-1]["messages"][1]["content"]
    assert "Text davor:\nAnfang hier. Mitte dort. Schluss am Ende." in prompt and "Text danach" not in prompt


@pytest.mark.parametrize("raw, clean", [
    ("# Gekürzte Fassung\n\nEr erwachte.", "Er erwachte."),
    ("## Gekürzte Fassung (überarbeitete Version)\n\nEr erwachte.\n", "Er erwachte."),
    ("Hier ist die gekürzte Fassung:\n\nEr erwachte.", "Er erwachte."),
    ("**Überarbeitete Version:**\nEr erwachte.", "Er erwachte."),
    ("<think>hm</think>\n\"Er erwachte.\"", "Er erwachte."),
    ("Er erwachte. Dann: nichts.", "Er erwachte. Dann: nichts."),          # normaler Text bleibt
    ("»Was ist mit mir?« dachte er.", "»Was ist mit mir?« dachte er."),    # deutsche Anführung bleibt
    ("Er sah ihn an.\n\n## Zweiter Teil\nDanach.", "Er sah ihn an.\n\n## Zweiter Teil\nDanach."),  # nur vorne
])
def test_clean_proposal_strips_heading_and_preamble_only_at_the_start(raw, clean):
    assert ai.clean_proposal(raw) == clean


def test_suggest_returns_proposal_without_heading(client, auth_headers, monkeypatch):
    """Im echten Ablauf: Modell antwortet mit Überschrift → beim Nutzer kommt nur der Text an."""
    b, sid = _book_with_text()

    async def chatty(messages, model=None, temperature=0.7, max_tokens=4096):
        return "# Gekürzte Fassung\n\nEs regnete."
    monkeypatch.setattr(ai, "complete", chatty)
    r = client.post(f"{P}/books/{b['id']}/ai/suggest", json={"scene_id": sid, "action": "shorten", "selection": "Es regnete lange."}, headers=auth_headers)
    assert r.status_code == 200 and r.json()["proposal"] == "Es regnete."
