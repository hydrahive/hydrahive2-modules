"""Fall = Projekt mit Rechts-Agent anlegen, lesen, ändern (Plan L2 Schritt 2, Muster storyteller/team/setup.py).

Reihenfolge: Eingaben prüfen → Modell → Projekt (der Kern legt den Projekt-Agenten mit an) → Fall-Datensatz →
Agent wird Rechts-Agent (Name, Werkzeuge, Anweisung). Scheitert ein Schritt nach dem Projekt, wird das Projekt wieder
gelöscht (der Kern räumt Agent und Arbeitsordner mit ab). Die Rechte prüft die Route, nicht diese Funktion.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from hydrahive.db.connection import db

from . import agent_profile
from .holidays_de import STATES

logger = logging.getLogger(__name__)

STATUSES = ("open", "waiting", "done")
_LIMITS = {"title": 200, "area": 100, "summary": 2000, "facts": 20000, "goal": 2000, "our_ref": 100,
           "their_ref": 100}
_UPDATABLE = set(_LIMITS) | {"status", "state"}
_COLS = ("project_id", "title", "area", "status", "state", "summary", "facts", "goal", "our_ref", "their_ref",
         "created_by", "created_at", "updated_at")


class CaseError(ValueError):
    def __init__(self, code: str, status: int = 400, **params: Any):
        super().__init__(code)
        self.code, self.status, self.params = code, status, params


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def default_model() -> str:
    from hydrahive.llm._config import get_default
    return get_default("chat")


def _clean(fields: dict[str, Any], *, partial: bool) -> dict[str, Any]:
    unknown = set(fields) - _UPDATABLE
    if unknown:
        raise CaseError("field_unknown", fields=sorted(unknown))
    out: dict[str, Any] = {}
    for key, limit in _LIMITS.items():
        if key in fields:
            val = str(fields[key] or "").strip()
            if len(val) > limit:
                raise CaseError("field_too_long", field=key, max=limit)
            out[key] = val
    if not partial and not out.get("title"):
        raise CaseError("title_required")
    if partial and "title" in out and not out["title"]:
        raise CaseError("title_required")
    if "state" in fields or not partial:
        state = str(fields.get("state") or "").strip().upper()
        if state not in STATES:
            raise CaseError("state_invalid", allowed=list(STATES))
        out["state"] = state
    if "status" in fields:
        if fields["status"] not in STATUSES:
            raise CaseError("status_invalid", allowed=list(STATUSES))
        out["status"] = fields["status"]
    return out


def _insert_case(project_id: str, data: dict[str, Any], username: str) -> None:
    now = _now()
    with db() as c:
        c.execute("INSERT INTO module_legal_cases(project_id, title, area, state, summary, facts, goal, our_ref, "
                  "their_ref, created_by, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                  (project_id, data["title"], data.get("area", ""), data["state"], data.get("summary", ""),
                   data.get("facts", ""), data.get("goal", ""), data.get("our_ref", ""), data.get("their_ref", ""),
                   username, now, now))


def _check_model(model: str) -> None:
    from hydrahive.agents._validation import AgentValidationError, validate_model
    try:
        validate_model(model)
    except AgentValidationError:
        raise CaseError("model_unavailable", 400, model=model) from None


def _description(data: dict[str, Any]) -> str:
    parts = [f"Rechtsfall: {data['title']}"]
    if data.get("area"):
        parts.append(f"Rechtsgebiet: {data['area']}")
    parts.append(f"Bundesland: {STATES[data['state']]}")
    if data.get("summary"):
        parts.append(f"Kurz: {data['summary']}")
    parts.append("Fallakte im Modul Recht (Werkzeug legal_case). Keine Rechtsberatung.")
    return "\n".join(parts)


def create_case(username: str, fields: dict[str, Any], *, model: str = "") -> dict[str, Any]:
    data = _clean(fields, partial=False)
    use_model = (model or "").strip() or default_model()
    if not use_model:
        raise CaseError("no_model", 409)
    _check_model(use_model)
    from hydrahive.agents import config as agent_config
    from hydrahive.projects import config as project_config
    from hydrahive.tools import REGISTRY
    name = f"Recht – {data['title']}"[:200]
    project = project_config.create(name, description=_description(data), members=[], llm_model=use_model,
                                    created_by=username, metadata={"legal": {"case": True}})
    pid = project["id"]
    try:
        _insert_case(pid, data, username)
        agent_config.update(project["agent_id"], name=f"{name} — Rechts-Agent"[:200],
                            tools=agent_profile.tools_for(set(REGISTRY)),
                            description="Rechts-Agent dieses Falls (Modul Recht). Liest die Fallakte, sucht Normen, "
                                        "rechnet Fristen, macht nur Vorschläge.")
        agent_config.set_system_prompt(project["agent_id"], agent_profile.system_prompt(
            data["title"], data.get("area", ""), STATES[data["state"]]))
    except Exception:
        logger.exception("Recht: Fall '%s' unvollständig – räume Projekt %s ab", data["title"], pid)
        with db() as c:
            c.execute("DELETE FROM module_legal_cases WHERE project_id = ?", (pid,))
        project_config.delete(pid)
        raise
    logger.info("Recht: Fall angelegt (projekt=%s, agent=%s)", pid, project["agent_id"])
    return {"project_id": pid, "agent_id": project["agent_id"], "case": get_case(pid)}


def get_case(project_id: str) -> dict[str, Any] | None:
    with db() as c:
        row = c.execute(f"SELECT {', '.join(_COLS)} FROM module_legal_cases WHERE project_id = ? "
                        "AND orphaned_at IS NULL", (project_id,)).fetchone()
    return dict(zip(_COLS, row, strict=True)) if row else None


def update_case(project_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    data = _clean(fields, partial=True)
    if not data:
        raise CaseError("nothing_to_update")
    sets = ", ".join(f"{k} = ?" for k in data)
    with db() as c:
        n = c.execute(f"UPDATE module_legal_cases SET {sets}, updated_at = ? WHERE project_id = ? "
                      "AND orphaned_at IS NULL", (*data.values(), _now(), project_id)).rowcount
    if not n:
        raise CaseError("case_not_found", 404)
    return get_case(project_id)


def list_cases(username: str, system_role: str) -> list[dict[str, Any]]:
    from hydrahive.projects import _members_model
    from hydrahive.projects._config_io import get as get_project
    with db() as c:
        rows = c.execute(f"SELECT {', '.join(_COLS)} FROM module_legal_cases WHERE orphaned_at IS NULL "
                         "ORDER BY updated_at DESC").fetchall()
    out = []
    for row in rows:
        case = dict(zip(_COLS, row, strict=True))
        project = get_project(case["project_id"])
        if project is None:
            continue
        role = "admin" if system_role == "admin" else _members_model.role_of(project, username)
        if role:
            out.append({**case, "role": role})
    return out
