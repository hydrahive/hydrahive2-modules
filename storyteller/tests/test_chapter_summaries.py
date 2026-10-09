"""A5(c): Kapitel-Zusammenfassung – Ablage, Erzeugen, hierarchisches Gedächtnis (Spec ki-qualitaet-a5.md §2c)."""
from __future__ import annotations

import pytest
from conftest import MOD_PREFIX, PROJECT_ID

from backend import chapter_summaries as cs
from backend import ghost, storage
from backend._book import Conflict
from backend._files import StoryError
from backend._memory import MemoryIndex


def _book(chapters=5, per=2, kind="novel"):
    """``chapters`` Kapitel mit je ``per`` Szenen, jede mit Zusammenfassung „K<i>S<j>.“."""
    b = storage.create_book(PROJECT_ID, {"title": "B", "kind": kind, "language": "de"})
    bid = b["id"]
    st = storage.get_structure(PROJECT_ID, bid)
    part = st["parts"][0]["id"]
    cids, sids = [st["parts"][0]["chapters"][0]["id"]], [[st["parts"][0]["chapters"][0]["scenes"][0]]]
    for c in range(1, chapters):
        r = storage.add_chapter(PROJECT_ID, bid, part, f"Kapitel {c + 1}", "S")
        cids.append(r["chapter"]["id"] if "chapter" in r else
                    next(ch["id"] for p in storage.get_structure(PROJECT_ID, bid)["parts"] for ch in p["chapters"]
                         if r["scene"]["id"] in ch["scenes"]))
        sids.append([r["scene"]["id"]])
    for c in range(chapters):
        for j in range(1, per):
            sids[c].append(storage.add_scene(PROJECT_ID, bid, cids[c], "S", after=sids[c][-1])["scene"]["id"])
        for j, sid in enumerate(sids[c]):
            s = storage.get_scene(PROJECT_ID, bid, sid)
            storage.save_scene(PROJECT_ID, bid, sid, {"title": f"S{c}{j}", "summary": f"K{c}S{j}.", "text": "T."},
                               base_version=s["version"])
    return bid, cids, sids


# --- Ablage ------------------------------------------------------------------------------------------------------

def test_save_and_read_with_version_check():
    bid, cids, _ = _book(chapters=2, per=1)
    assert cs.get_all(PROJECT_ID, bid) == {}
    a = cs.save(PROJECT_ID, bid, cids[0], "  Mia verliert den Vater.  ", base_version=0)
    assert a["summary"] == "Mia verliert den Vater." and a["version"] == 1 and a["updated_at"]
    assert cs.get_all(PROJECT_ID, bid)[cids[0]]["summary"] == "Mia verliert den Vater."
    with pytest.raises(Conflict) as e:
        cs.save(PROJECT_ID, bid, cids[0], "Anders.", base_version=0)
    assert e.value.current["summary"] == "Mia verliert den Vater."
    assert cs.save(PROJECT_ID, bid, cids[0], "Neu.", base_version=1)["version"] == 2


def test_unknown_chapter_and_too_long_text_are_rejected():
    bid, cids, _ = _book(chapters=1, per=1)
    with pytest.raises(StoryError) as e:
        cs.save(PROJECT_ID, bid, "f" * 32, "x", base_version=0)
    assert e.value.status == 404
    with pytest.raises(StoryError):
        cs.save(PROJECT_ID, bid, cids[0], "x" * (cs.MAX_SUMMARY + 1), base_version=0)
    with pytest.raises(StoryError):
        cs.save(PROJECT_ID, bid, "../x", "x", base_version=0)


def test_saving_the_outline_does_not_lose_chapter_summaries():
    """Grund für die eigene Datei: die Oberfläche speichert die Gliederung als Ganzes (toStructure)."""
    bid, cids, _ = _book(chapters=2, per=1)
    cs.save(PROJECT_ID, bid, cids[1], "Zweites Kapitel.", base_version=0)
    st = storage.get_structure(PROJECT_ID, bid)
    st["parts"][0]["chapters"][1]["title"] = "Umbenannt"
    storage.save_structure(PROJECT_ID, bid, st, base_version=st["version"])
    assert cs.get_all(PROJECT_ID, bid)[cids[1]]["summary"] == "Zweites Kapitel."


def test_summaries_of_deleted_chapters_are_hidden_but_kept():
    bid, cids, _ = _book(chapters=2, per=1)
    cs.save(PROJECT_ID, bid, cids[1], "Weg.", base_version=0)
    st = storage.get_structure(PROJECT_ID, bid)
    chs = st["parts"][0]["chapters"]
    chs[0]["scenes"] += chs[1]["scenes"]                  # Szenen wandern mit, das Kapitel fällt weg
    st["parts"][0]["chapters"] = chs[:1]
    storage.save_structure(PROJECT_ID, bid, st, base_version=st["version"])
    assert cs.get_all(PROJECT_ID, bid) == {}
    assert cids[1] in cs._read(PROJECT_ID, bid)          # nichts still gelöscht


def test_empty_text_clears_the_summary():
    bid, cids, _ = _book(chapters=1, per=1)
    cs.save(PROJECT_ID, bid, cids[0], "Etwas.", base_version=0)
    assert cs.save(PROJECT_ID, bid, cids[0], "   ", base_version=1)["summary"] == ""
    assert cids[0] not in cs.get_all(PROJECT_ID, bid)    # leer = wie ohne


# --- Erzeugen ----------------------------------------------------------------------------------------------------

async def test_generate_uses_only_scene_summaries_and_saves_nothing(monkeypatch):
    bid, cids, _ = _book(chapters=2, per=3, kind="nonfiction")
    seen = []

    async def fake_complete(messages, model=None, temperature=0.7, max_tokens=4096):
        seen.append(messages)
        return "<think>hm</think>Kapitel kurz."
    monkeypatch.setattr(cs, "complete", fake_complete)
    out = await cs.generate(PROJECT_ID, bid, cids[1], model=None)
    assert out == {"summary": "Kapitel kurz."}
    assert cs.get_all(PROJECT_ID, bid) == {}                          # Vorschlag: gespeichert wird nichts
    system, user = seen[0][0]["content"], seen[0][1]["content"]
    assert "Abschnitte" in system and "Szene" not in system
    assert "K1S0." in user and "K1S2." in user and "K0S0." not in user and "T." not in user


async def test_generate_needs_scene_summaries(monkeypatch):
    bid, cids, sids = _book(chapters=1, per=1)
    s = storage.get_scene(PROJECT_ID, bid, sids[0][0])
    storage.save_scene(PROJECT_ID, bid, sids[0][0], {"summary": ""}, base_version=s["version"])
    with pytest.raises(StoryError) as e:
        await cs.generate(PROJECT_ID, bid, cids[0], model=None)
    assert e.value.code == "summaries_required"


async def test_generate_empty_answer_is_an_error(monkeypatch):
    bid, cids, _ = _book(chapters=1, per=1)

    async def empty(messages, model=None, temperature=0.7, max_tokens=4096):
        return "  "
    monkeypatch.setattr(cs, "complete", empty)
    with pytest.raises(StoryError) as e:
        await cs.generate(PROJECT_ID, bid, cids[0], model=None)
    assert e.value.code == "llm_empty"


# --- Gedächtnis --------------------------------------------------------------------------------------------------

def test_without_chapter_summaries_memory_stays_scene_by_scene():
    bid, _cids, sids = _book(chapters=5, per=2)
    mem = MemoryIndex.load(PROJECT_ID, bid).memory(sids[4][1], 10_000)
    assert mem.split("\n") == [f"- S{c}{j}: K{c}S{j}." for c in range(5) for j in range(2)][:9]


def _titles(bid):
    return [ch["title"] for ch in storage.get_structure(PROJECT_ID, bid)["parts"][0]["chapters"]]


def test_with_enough_room_everything_stays_scene_by_scene_even_with_chapter_summaries():
    """Keine feste Kapitelzahl (Till 10.10.): Platz entscheidet. Passt alles, bleibt jede Szene drin."""
    bid, cids, sids = _book(chapters=5, per=2)
    for c in range(5):
        cs.save(PROJECT_ID, bid, cids[c], f"Kapitel {c} kurz.", base_version=0)
    mem = MemoryIndex.load(PROJECT_ID, bid).memory(sids[4][1], 10_000)
    assert mem.split("\n") == [f"- S{c}{j}: K{c}S{j}." for c in range(5) for j in range(2)][:9]


def test_when_tight_oldest_chapters_collapse_first_until_it_fits():
    bid, cids, sids = _book(chapters=5, per=4)
    for c in range(5):
        cs.save(PROJECT_ID, bid, cids[c], f"K{c} kurz.", base_version=0)
    t = _titles(bid)
    idx = MemoryIndex.load(PROJECT_ID, bid)
    full = idx.memory(sids[4][3], 10_000)
    one = f"- Kapitel „{t[0]}“: K0 kurz."
    first_collapsed = "\n".join([one] + full.split("\n")[4:])
    assert idx.memory(sids[4][3], len(full)) == full                                 # passt genau: nichts zusammengefasst
    assert idx.memory(sids[4][3], len(first_collapsed)) == first_collapsed          # genau Kapitel 1 zusammengefasst
    assert idx.memory(sids[4][3], len(first_collapsed) - 1).split("\n")[:2] == [one, f"- Kapitel „{t[1]}“: K1 kurz."]


def test_current_chapter_is_never_collapsed():
    """Die Kapitel-Zusammenfassung des aktuellen Kapitels kann Späteres verraten – sie kommt nie ins Gedächtnis."""
    bid, cids, sids = _book(chapters=2, per=6)
    cs.save(PROJECT_ID, bid, cids[1], "Kapitän tot.", base_version=0)   # kurz: Zusammenfassen würde Platz sparen
    idx = MemoryIndex.load(PROJECT_ID, bid)
    for sid in (sids[1][0], sids[1][5]):                                 # erste Szene (noch nichts davor) und letzte
        for limit in (10, 30, 60, 10_000):
            assert "Kapitän" not in idx.memory(sid, limit), (sid, limit)


def test_collapse_only_when_it_saves_room():
    """Ist die Kapitel-Zeile länger als die Szenen, bleiben die Szenen (Zusammenfassen würde nur Platz kosten)."""
    bid, cids, sids = _book(chapters=2, per=3)
    cs.save(PROJECT_ID, bid, cids[0], "Sehr lang. " * 2, base_version=0)  # Kapitel-Zeile 45 Zeichen > 3 Szenen (38)
    idx = MemoryIndex.load(PROJECT_ID, bid)
    full = idx.memory(sids[1][2], 10_000)
    assert idx.memory(sids[1][2], len(full) - 1) == full.split("\n", 1)[1]           # vorn eine Zeile weg, nicht länger


def test_chapter_with_summary_but_without_scene_summaries_shows_its_summary():
    bid, cids, sids = _book(chapters=3, per=2)
    for sid in sids[0]:
        s = storage.get_scene(PROJECT_ID, bid, sid)
        storage.save_scene(PROJECT_ID, bid, sid, {"summary": ""}, base_version=s["version"])
    cs.save(PROJECT_ID, bid, cids[0], "Nur hier steht es.", base_version=0)
    mem = MemoryIndex.load(PROJECT_ID, bid).memory(sids[2][0], 10_000).split("\n")
    assert mem[0] == f"- Kapitel „{_titles(bid)[0]}“: Nur hier steht es." and mem[1] == "- S10: K1S0."


def test_chapter_without_summary_stays_scene_by_scene_even_when_old():
    """Kapitel 1 hat keine Kapitel-Zusammenfassung: es bleibt Szene für Szene, zusammengefasst wird Kapitel 2."""
    bid, cids, sids = _book(chapters=5, per=4)
    cs.save(PROJECT_ID, bid, cids[1], "Eins.", base_version=0)
    idx = MemoryIndex.load(PROJECT_ID, bid)
    full = idx.memory(sids[4][0], 10_000)
    mem = idx.memory(sids[4][0], len(full) - 1).split("\n")
    assert mem[:5] == [f"- S0{j}: K0S{j}." for j in range(4)] + [f"- Kapitel „{_titles(bid)[1]}“: Eins."]


def test_early_book_survives_in_memory_thanks_to_chapter_summaries():
    """Der Zweck: bei knappem Gedächtnis bleibt der Buchanfang als Kapitel-Zeile erhalten."""
    bid, cids, sids = _book(chapters=10, per=4)
    before = MemoryIndex.load(PROJECT_ID, bid).memory(sids[9][3], 450)
    assert "K0" not in before
    for c in range(10):
        cs.save(PROJECT_ID, bid, cids[c], f"Anfang {c}.", base_version=0)
    after = MemoryIndex.load(PROJECT_ID, bid).memory(sids[9][3], 450)
    assert "Anfang 0." in after and "K8S3." in after and "K0S0." not in after and len(after) <= 450
    assert after.count("- Kapitel „") < 9                                         # nur so viele wie nötig


def test_ghost_material_uses_the_hierarchical_memory():
    bid, cids, sids = _book(chapters=4, per=3)
    cs.save(PROJECT_ID, bid, cids[0], "Der Anfang.", base_version=0)
    full = MemoryIndex.load(PROJECT_ID, bid).memory(sids[3][0], 10_000)
    m = ghost.build_material(PROJECT_ID, bid, sids[3][0], memory_chars=len(full) - 1)
    assert "“: Der Anfang." in m.prompt and "K0S0." not in m.prompt
    assert "K0S0." in ghost.build_material(PROJECT_ID, bid, sids[3][0]).prompt   # genug Platz: Szenen bleiben


# --- Routen + Agent ----------------------------------------------------------------------------------------------

def test_routes(client, auth_headers, monkeypatch):
    bid, cids, _ = _book(chapters=1, per=1)
    base = f"{MOD_PREFIX}/projects/{PROJECT_ID}/books/{bid}/chapter-summaries"
    assert client.get(base, headers=auth_headers).json() == {"chapters": {}}
    r = client.put(f"{base}/{cids[0]}", json={"summary": "Kurz.", "base_version": 0}, headers=auth_headers)
    assert r.status_code == 200 and r.json()["version"] == 1
    r = client.put(f"{base}/{cids[0]}", json={"summary": "Alt.", "base_version": 0}, headers=auth_headers)
    assert r.status_code == 409
    assert client.get(base, headers=auth_headers).json()["chapters"][cids[0]]["summary"] == "Kurz."

    async def fake(messages, model=None, temperature=0.7, max_tokens=4096):
        return "Erzeugt."
    monkeypatch.setattr(cs, "complete", fake)
    r = client.post(f"{base}/{cids[0]}/generate", json={}, headers=auth_headers)
    assert r.status_code == 200 and r.json() == {"summary": "Erzeugt."}
    assert client.get(base, headers=auth_headers).json()["chapters"][cids[0]]["summary"] == "Kurz."


async def test_outline_tool_shows_chapter_summary():
    from pathlib import Path

    from hydrahive.tools.base import ToolContext

    from backend.agent_tools import TOOLS
    bid, cids, _ = _book(chapters=2, per=1)
    cs.save(PROJECT_ID, bid, cids[0], "Was in Kapitel 1 geschieht.", base_version=0)
    tool = next(t for t in TOOLS if t.name == "storyteller_outline")
    ctx = ToolContext(session_id="s", agent_id="a", user_id="testuser", workspace=Path("/tmp"), project_id=PROJECT_ID)
    res = await tool.execute({"book_id": bid}, ctx)
    chs = res.output["parts"][0]["chapters"]
    assert chs[0]["summary"] == "Was in Kapitel 1 geschieht." and chs[1]["summary"] == ""
    assert "Kapitel-Zusammenfassung" in tool.description
