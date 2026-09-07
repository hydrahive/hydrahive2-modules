from __future__ import annotations

import json
from pathlib import Path

from backend import register


def test_registers_read_only_tools():
    class Context:
        def __init__(self):
            self.tools = []
            self.migrations = []
            self.routers = []

        def register_migrations(self, value):
            self.migrations.append(value)

        def register_router(self, value):
            self.routers.append(value)

        def register_tool(self, value):
            self.tools.append(value)

    context = Context()
    register(context)
    assert [tool.name for tool in context.tools] == [
        "opentor_status", "opentor_search", "opentor_fetch", "opentor_extract_iocs",
    ]
    assert context.migrations == ["migrations"]
    assert len(context.routers) == 1


def test_manifest_is_disabled_by_default():
    manifest = json.loads((Path(__file__).parents[1] / "manifest.json").read_text())
    assert manifest["default_agent_tools"] is False
    assert manifest["has_service"] is True
    assert "opentor.read" in manifest["permissions"]
