"""T1c: Schreib-Team je Buch-Projekt – Rollen, Werkzeuge, Anweisungen (Spec schreib-team.md §3)."""
from __future__ import annotations

from backend import team
from backend.agent_tools import TOOLS

FORBIDDEN = {"shell_exec", "file_read", "file_write", "file_patch", "create_specialist", "configure_specialist",
             "write_skill", "delete_skill", "send_mail", "web_browser", "list_projects"}
STORY = {t.name for t in TOOLS}
CORE_OK = {"datamining_search", "datamining_semantic", "datamining_timeline", "read_memory", "search_memory",
           "write_memory", "todo_write", "ask_agent", "list_specialists", "web_search", "fetch_url", "research_report"}


def test_author_plus_seven_helpers_with_unique_keys_and_names():
    assert team.AUTHOR.key == "author"
    keys = [r.key for r in team.HELPERS]
    assert keys == ["plausibility", "research", "editor", "critic", "creative", "structure", "profiles"]
    names = [r.name for r in (team.AUTHOR, *team.HELPERS)]
    assert len(set(names)) == 8 and all(names)


def test_no_developer_tools_anywhere_and_only_known_tools():
    for role in (team.AUTHOR, *team.HELPERS):
        assert not FORBIDDEN & set(role.tools), role.key
        assert set(role.tools) <= STORY | CORE_OK, (role.key, set(role.tools) - STORY - CORE_OK)
        assert {"storyteller_books", "storyteller_outline", "storyteller_read"} <= set(role.tools), role.key


def test_only_author_delegates_and_proposes_everything():
    assert {"ask_agent", "list_specialists"} <= set(team.AUTHOR.tools)
    assert {n for n in STORY if n.startswith("storyteller_propose_")} <= set(team.AUTHOR.tools)
    for h in team.HELPERS:
        assert "ask_agent" not in h.tools and "todo_write" not in h.tools, h.key


def test_helper_write_tools_match_their_job():
    by = {h.key: set(h.tools) for h in team.HELPERS}
    assert by["research"] >= {"web_search", "fetch_url"}
    assert "storyteller_propose_text" in by["editor"]
    assert "storyteller_propose_entity" in by["profiles"]
    assert "storyteller_propose_outline" in by["creative"] and "storyteller_propose_outline" in by["structure"]
    assert not {t for t in by["plausibility"] | by["critic"] if t.startswith("storyteller_propose_")}


def test_every_role_has_a_prompt_with_title_language_and_proposal_rule():
    for role in (team.AUTHOR, *team.HELPERS):
        text = team.prompt_for(role, book_title="Der Leuchtturm")
        assert "Der Leuchtturm" in text and "{book_title}" not in text, role.key
        assert "Deutsch" in text, role.key
        assert "Vorschlag" in text or "nie direkt" in text, role.key
    assert all(h.name in team.prompt_for(team.AUTHOR, book_title="X") for h in team.HELPERS)   # Autor kennt sein Team


def test_tools_available_drops_missing_optional_tools():
    have = STORY | CORE_OK - {"research_report"}
    tools = team.available_tools(next(h for h in team.HELPERS if h.key == "research"), have)
    assert "research_report" not in tools and "web_search" in tools


def test_version_2_gives_note_tools():
    assert team.TEAM_VERSION == 2
    by = {r.key: set(r.tools) for r in (team.AUTHOR, *team.HELPERS)}
    for key, tools in by.items():
        assert "storyteller_notes" in tools, key
    for key in ("author", "plausibility", "research", "editor", "critic", "creative", "structure", "profiles"):
        assert "storyteller_note" in by[key], key


def test_prompts_ask_helpers_to_file_findings_as_notes():
    for role in team.HELPERS:
        assert "storyteller_note" in team.prompt_for(role, book_title="X"), role.key
    assert "storyteller_notes" in team.prompt_for(team.AUTHOR, book_title="X")
