from __future__ import annotations

from hydrahive.api.middleware.users import create as create_user
from hydrahive.api.middleware.users import delete as delete_user
from hydrahive.api.middleware.users import get_by_username
from hydrahive.tools.base import ToolContext

from backend import tools_read
from backend.models import SearchResponse


def _ctx(tmp_path, username="alice"):
    return ToolContext(
        session_id="session-1", agent_id="agent-1", user_id=username,
        workspace=tmp_path, current_user_input="Suche einen Film",
        current_user_turn_id="turn-1",
    )


def _owner_id(username="alice"):
    return get_by_username(username)["user_id"]


async def test_search_tool_accepts_runner_username_and_uses_stable_owner(
    tmp_path, monkeypatch
):
    user = get_by_username("alice")
    ctx = ToolContext(
        session_id="session-1", agent_id="agent-1", user_id="alice",
        workspace=tmp_path, current_user_input="Suche einen Film",
        current_user_turn_id="turn-1",
    )
    seen = []

    async def search(username, request, **kwargs):
        seen.append((username, kwargs))
        return SearchResponse(total=0, eligible=0, results=[])

    monkeypatch.setattr(tools_read.service, "search_indexer", search)
    result = await tools_read.SEARCH_TOOL.execute(
        {"query": "Film", "media_type": "movie"}, ctx
    )

    assert result.success is True
    assert seen == [("alice", {"owner_id": user["user_id"]})]


async def test_recreated_username_gets_new_media_owner(tmp_path, monkeypatch):
    username = "recreated-mediacenter-user"
    seen_owners = []

    async def search(_username, _request, **kwargs):
        seen_owners.append(kwargs["owner_id"])
        return SearchResponse(total=0, eligible=0, results=[])

    monkeypatch.setattr(tools_read.service, "search_indexer", search)
    try:
        first_owner = create_user(username, "testpass123")
        first = await tools_read.SEARCH_TOOL.execute(
            {"query": "Film", "media_type": "movie"}, _ctx(tmp_path, username)
        )
        delete_user(username)
        second_owner = create_user(username, "testpass123")
        second = await tools_read.SEARCH_TOOL.execute(
            {"query": "Film", "media_type": "movie"}, _ctx(tmp_path, username)
        )
    finally:
        delete_user(username)

    assert first.success is True
    assert second.success is True
    assert first_owner != second_owner
    assert seen_owners == [first_owner, second_owner]


def test_read_tool_schemas_are_closed_and_bounded():
    schema = tools_read.SEARCH_TOOL.schema
    assert schema["additionalProperties"] is False
    assert schema["properties"]["limit"]["maximum"] == 50
    assert set(schema["properties"]["media_type"]["enum"]) == {
        "movie", "tv", "book", "audiobook", "audioplay", "music"
    }
    assert tools_read.QUEUE_TOOL.schema["additionalProperties"] is False


async def test_search_tool_uses_immutable_owner_and_returns_sanitized_data(
    tmp_path, monkeypatch
):
    ctx = _ctx(tmp_path)
    seen = []

    async def search(username, request, **kwargs):
        seen.append((username, request, kwargs))
        return SearchResponse(total=0, eligible=0, results=[])

    monkeypatch.setattr(tools_read.service, "search_indexer", search)
    result = await tools_read.SEARCH_TOOL.execute(
        {"query": "Film", "media_type": "movie", "limit": 10}, ctx
    )
    assert result.success is True
    assert result.output == {"total": 0, "eligible": 0, "results": []}
    assert seen[0][0] == "alice"
    assert seen[0][2]["owner_id"] == _owner_id()
    assert "url" not in str(result.output).lower()


async def test_search_tool_rejects_extra_network_fields_without_call(tmp_path, monkeypatch):
    called = False

    async def search(*args, **kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(tools_read.service, "search_indexer", search)
    result = await tools_read.SEARCH_TOOL.execute(
        {"query": "Film", "media_type": "movie", "url": "https://evil.invalid"},
        _ctx(tmp_path),
    )
    assert result.success is False
    assert result.error == "mediacenter_request_invalid"
    assert called is False


async def test_queue_and_history_use_owner_and_limit_output(tmp_path, monkeypatch):
    ctx = _ctx(tmp_path)
    seen = []

    async def jobs(username, mode, **kwargs):
        seen.append((username, mode, kwargs))
        return []

    monkeypatch.setattr(tools_read.job_service, "list_jobs", jobs)
    queue = await tools_read.QUEUE_TOOL.execute({}, ctx)
    history = await tools_read.HISTORY_TOOL.execute({}, ctx)
    assert queue.output == {"count": 0, "jobs": []}
    assert history.output == {"count": 0, "jobs": []}
    assert seen == [
        ("alice", "queue", {"limit": 50, "owner_id": _owner_id()}),
        ("alice", "history", {"limit": 50, "owner_id": _owner_id()}),
    ]
