"""Vitrine-Modul: Gehäuse-Display. Der Renderer läuft als eigener Dienst (hydrahive2-vitrine, siehe
extension/install.sh), damit das Bild auch bei Neustarts von HydraHive weiterläuft. Im HydraHive-Prozess:
Routen, Werkzeug display_message (standardmäßig aus), Butler-Aktion „Auf Vitrine anzeigen“ und der Job,
der Fehler und Hydra-Status für die Einblendungen bereitstellt."""
from __future__ import annotations


def register(ctx) -> None:
    from . import butler, notify, tools
    from .routes import router
    ctx.register_router(router)
    ctx.register_tool(tools.DISPLAY_TOOL)
    ctx.register_butler_action(butler.ACTION)
    ctx.register_job("notify", notify.job, interval_seconds=30, initial_delay_seconds=20)
