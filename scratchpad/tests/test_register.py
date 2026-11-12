"""Anmeldung des Moduls: Router, Migrationen und genau die vier Werkzeuge."""
from __future__ import annotations


def test_werkzeuge_sind_angemeldet_und_write_scratchpad_ist_weg():
    from backend import register

    class Ctx:
        def __init__(self):
            self.tools, self.routers, self.migrations = [], [], None

        def register_tool(self, tool):
            self.tools.append(tool.name)

        def register_router(self, router):
            self.routers.append(router)

        def register_migrations(self, rel):
            self.migrations = rel

    ctx = Ctx()
    register(ctx)
    assert sorted(ctx.tools) == ["idea_list", "idea_read", "idea_write", "read_scratchpad"]
    assert ctx.migrations == "migrations" and len(ctx.routers) == 1
