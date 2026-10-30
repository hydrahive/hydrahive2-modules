"""„Zum Labor-Chat“: Sitzung mit dem Labor-Agenten im Labor-Projekt, geöffnet im Projekt-Cockpit (Till 30.10.).

Das Cockpit lässt sich nicht per Adresse auf ein Projekt öffnen; es liest das aktive Projekt und den gewählten
Agenten je Projekt aus den Einstellungen des Nutzers. Das Modul setzt genau diese zwei Werte – sonst nichts.
"""
from __future__ import annotations

PREF_AGENT = "project_selected_agent"          # wie frontend/features/cockpit/project/useProjectAgentSelection.ts


def open_for(username: str, pid: str, aid: str) -> dict:
    from hydrahive.db import sessions as sessions_db
    from hydrahive.db import user_preferences
    s = next((x for x in sessions_db.list_for_user(username, limit=500)
              if x.agent_id == aid and x.project_id == pid), None)
    if s is None:
        s = sessions_db.create(agent_id=aid, user_id=username, project_id=pid, title="Hydra-Labor")
    else:
        sessions_db.touch(s.id)
    layout = dict(user_preferences.get(username).get("cockpit_layout") or {})
    chosen = layout.get(PREF_AGENT)
    layout[PREF_AGENT] = {**(chosen if isinstance(chosen, dict) else {}), pid: aid}
    user_preferences.patch(username, {"active_project_id": pid, "cockpit_layout": layout})
    return {"session_id": s.id, "url": "/projects"}
