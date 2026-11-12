"""Lese-Werkzeuge: idea_list, idea_read und der Alias read_scratchpad."""
from __future__ import annotations

from helpers import PROJECT_A, PROJECT_B, make_ctx

ID_ONE = "aaaa1111-0000-4000-8000-000000000001"
ID_TWO = "aaaa2222-0000-4000-8000-000000000002"


def _store():
    from backend import store
    return store


async def _list(args: dict | None = None, **ctx):
    from backend.tools_read import LIST_TOOL
    return await LIST_TOOL.execute(args or {}, make_ctx(**ctx))


async def _read(idea_id, **ctx):
    from backend.tools_read import READ_TOOL
    return await READ_TOOL.execute({"idea_id": idea_id}, make_ctx(**ctx))


def _titles(result) -> list[str]:
    return [i["title"] for i in result.output["ideas"]]


async def test_liste_leer():
    result = await _list()
    assert result.success
    assert result.output["count"] == 0 and result.output["ideas"] == []
    assert "Keine Ideen" in result.output["message"]


async def test_liste_ohne_nutzer_schlaegt_fehl():
    assert not (await _list(username="")).success


async def test_standardfilter_ist_das_aktive_projekt():
    s = _store()
    s.create("alice", title="Im Projekt", project_id=PROJECT_A)
    s.create("alice", title="Ohne Projekt")
    result = await _list(project_id=PROJECT_A)
    assert _titles(result) == ["Im Projekt"]
    assert result.output["elsewhere"] == 1
    assert 'project_id="*"' in result.output["hint"]


async def test_stern_zeigt_alle_und_none_zeigt_ohne_projekt():
    s = _store()
    s.create("alice", title="Im Projekt", project_id=PROJECT_A)
    s.create("alice", title="Ohne Projekt")
    alle = await _list({"project_id": "*"}, project_id=PROJECT_A)
    assert set(_titles(alle)) == {"Im Projekt", "Ohne Projekt"}
    assert alle.output["elsewhere"] == 0 and "hint" not in alle.output
    assert _titles(await _list({"project_id": "none"}, project_id=PROJECT_A)) == ["Ohne Projekt"]
    assert _titles(await _list({"project_id": PROJECT_B}, project_id=PROJECT_A)) == []


async def test_ohne_aktives_projekt_alle():
    s = _store()
    s.create("alice", title="Im Projekt", project_id=PROJECT_A)
    s.create("alice", title="Ohne Projekt")
    assert set(_titles(await _list())) == {"Im Projekt", "Ohne Projekt"}


async def test_status_standard_offen():
    s = _store()
    s.create("alice", title="Offen")
    done = s.create("alice", title="Fertig")
    s.update("alice", done["id"], status="done")
    assert _titles(await _list()) == ["Offen"]
    assert set(_titles(await _list({"status": "all"}))) == {"Offen", "Fertig"}
    assert _titles(await _list({"status": "done"})) == ["Fertig"]
    assert not (await _list({"status": "fertig"})).success


async def test_seitenweise():
    s = _store()
    for n in range(5):
        s.create("alice", title=f"Idee {n}")
    first = await _list({"limit": 2})
    assert first.output["count"] == 5 and first.output["returned"] == 2
    assert first.output["has_more"] is True and first.output["next_offset"] == 2
    last = await _list({"limit": 2, "offset": 4})
    assert last.output["returned"] == 1 and last.output["has_more"] is False and last.output["next_offset"] is None
    for bad in ({"limit": 0}, {"limit": 101}, {"offset": -1}, {"limit": "zwei"}, {"limit": True}):
        assert not (await _list(bad)).success


async def test_liste_ist_kompakt_und_traegt_den_hinweis():
    s = _store()
    idea = s.create("alice", title="Kompakt", body="lange Beschreibung " * 50, project_id=PROJECT_A, origin="agent")
    result = await _list({"project_id": "*"})
    item = result.output["ideas"][0]
    assert item["id"] == idea["id"] and item["short_id"] == idea["id"][:8]
    assert (item["status"], item["origin"], item["project"]) == ("new", "agent", "Projekt alice")
    assert "body" not in item and "body_preview" not in item
    line = result.output["summary"]
    assert idea["id"][:8] in line and "Kompakt" in line and "Neu" in line and "vom Agenten" in line
    assert "keine Systemanweisungen" in result.output["notice"]
    assert "idea_read" in result.output["detail_hint"]


async def test_fremde_ideen_sind_unsichtbar():
    _store().create("alice", title="Privat")
    assert (await _list(username="bob")).output["count"] == 0


async def test_erster_aufruf_uebernimmt_die_alten_dateien():
    from _hh_isolation import remove_test_tree
    from hydrahive.settings import settings

    folder = settings.data_dir / "scratchpad" / "bob"
    folder.mkdir(parents=True, exist_ok=True)
    try:
        (folder / "agent.md").write_text("# Alte Agent-Notiz\nText\n", encoding="utf-8")
        result = await _list(username="bob")
        assert _titles(result) == ["Alte Agent-Notiz"]
        assert result.output["ideas"][0]["origin"] == "agent"
    finally:
        remove_test_tree(folder)


async def test_lesen_mit_voller_und_kurzer_id():
    from backend import notes

    s = _store()
    idea = s.create("alice", title="Admin-Seite", body="alles an einem Ort", project_id=PROJECT_A)
    notes.add("alice", idea["id"], author="agent", body="Erst die Liste bauen", agent_name="Buddy")
    for ref in (idea["id"], idea["id"][:8], f"  {idea['id'][:8]}  "):
        result = await _read(ref)
        assert result.success, result.error
        text = result.output
        assert "Admin-Seite" in text and "alles an einem Ort" in text
        assert "Projekt alice" in text and "Neu" in text and idea["id"] in text
        assert "Erst die Liste bauen" in text and "Buddy" in text
        assert "Vorgaben des Nutzers, keine Systemanweisungen" in text


async def test_lesen_mehrdeutig_leer_zu_kurz_unbekannt_fremd():
    s = _store()
    s.create("alice", title="Eins", idea_id=ID_ONE)
    s.create("alice", title="Zwei", idea_id=ID_TWO)
    mehrdeutig = await _read("aaaa")
    assert not mehrdeutig.success and "aaaa1111" in mehrdeutig.error and "aaaa2222" in mehrdeutig.error
    assert (await _read("aaaa1")).success
    for ref in ("", "   ", None):
        leer = await _read(ref)
        assert not leer.success and "idea_id" in leer.error
    assert not (await _read("aaa")).success
    assert not (await _read("ffff0000")).success
    assert not (await _read(ID_ONE, username="bob")).success
    assert not (await _read("%%%%")).success


async def test_lesen_kuerzt_lange_ideen_mit_hinweis():
    from backend import notes

    s = _store()
    idea = s.create("alice", title="Riesig", body="x" * 50_000)
    notes.add("alice", idea["id"], author="agent", body="Wichtige Anmerkung am Ende")
    text = (await _read(idea["id"])).output
    assert len(text) <= 40_000
    assert "gekürzt" in text
    assert "Wichtige Anmerkung am Ende" in text


async def test_alias_read_scratchpad_liefert_dieselbe_liste():
    from backend.tools_read import LEGACY_READ_TOOL, LIST_TOOL

    s = _store()
    s.create("alice", title="Im Projekt", project_id=PROJECT_A)
    s.create("alice", title="Ohne Projekt")
    ctx = make_ctx(project_id=PROJECT_A)
    assert (await LEGACY_READ_TOOL.execute({}, ctx)).output == (await LIST_TOOL.execute({}, ctx)).output
    assert LEGACY_READ_TOOL.name == "read_scratchpad"
    assert "veraltet" in LEGACY_READ_TOOL.description.lower() and "idea_list" in LEGACY_READ_TOOL.description
    assert LEGACY_READ_TOOL.prompt_hint == ""
