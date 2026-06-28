"""Home-Assistant-Modul — Backend.

register(ctx) →
  - Router      (/api/modules/homeassistant/{test,states,states/{id},service,favorites})
  - Agent-Tools ha_list_entities, ha_get_state, ha_render_template, ha_call_service
  - Migrationen (Favoriten-Tabelle, additiv)

URL + Long-Lived-Token kommen aus den System-Settings (homeassistant_url,
homeassistant_token). Der Token verlässt den Server nie — das Frontend spricht
ausschließlich die lokalen Proxy-Routen, nie HA direkt.

Submodule werden als Modul importiert (NICHT `from .tools_write import TOOL`),
damit `backend.tools_write` das Modul bleibt und nicht vom Tool-Objekt
überschattet wird.
"""
from __future__ import annotations

from .routes import router
from . import tools_read, tools_write


def register(ctx) -> None:
    ctx.register_router(router)
    ctx.register_tool(tools_read.LIST_TOOL)
    ctx.register_tool(tools_read.STATE_TOOL)
    ctx.register_tool(tools_read.TEMPLATE_TOOL)
    ctx.register_tool(tools_write.TOOL)
    ctx.register_migrations("migrations")
