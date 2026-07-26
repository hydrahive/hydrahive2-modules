from __future__ import annotations

import json
from pathlib import Path

from backend import register


def test_module_registers_all_four_tools():
    class Context:
        def __init__(self):
            self.tools = []

        def register_migrations(self, value):
            pass

        def register_router(self, value):
            pass

        def register_tool(self, value):
            self.tools.append(value)

    context = Context()
    register(context)
    assert [tool.name for tool in context.tools] == [
        "mediacenter_search", "mediacenter_enqueue",
        "mediacenter_queue", "mediacenter_history",
    ]


def test_manifest_enables_default_agent_tools():
    manifest = json.loads(
        (Path(__file__).resolve().parents[1] / "manifest.json").read_text()
    )
    assert manifest["version"] == "0.4.0"
    assert manifest["default_agent_tools"] is True
