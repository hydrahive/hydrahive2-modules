"""Modell eines Vibe-Projekts: Liste, Wahl, Wechsel. Das Modell ist das einzige freie Feld des festen Vibe-Agenten
(Kern agents/_managed.py: FREE). Standardmodell des Systems gilt, wenn nichts gewählt wird."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from hydrahive.api.middleware.auth import AuthPrincipal, require_admin_principal
from hydrahive.api.middleware.errors import coded
from pydantic import BaseModel, ConfigDict, Field

from . import state

router = APIRouter()
Admin = Annotated[AuthPrincipal, Depends(require_admin_principal)]


class ModelChoice(BaseModel):
    model_config = ConfigDict(extra="ignore")
    model: str = Field(min_length=1, max_length=200)


def _own(pid: str, p: AuthPrincipal) -> dict:
    row = state.get_row(pid)
    if row is None or row["owner"] != p.username:
        raise coded(status.HTTP_404_NOT_FOUND, "vibe_project_not_found")
    return row


def _default_model() -> str:
    from hydrahive.llm.client import default_model
    return default_model()


def _model_of(agent_id: str) -> str:
    from hydrahive.agents import config as agent_config
    cfg = agent_config.get(agent_id)
    return str((cfg or {}).get("llm_model") or "")


def _write_model(agent_id: str, model: str) -> None:
    """Nur das Feld llm_model, direkt (wie _managed.set_managed im Kern)."""
    from hydrahive.agents._config_utils import get, save_atomic
    from hydrahive.agents._paths import config_path
    from hydrahive.db._utils import now_iso
    cfg = get(agent_id)
    if not cfg:
        raise coded(status.HTTP_404_NOT_FOUND, "vibe_project_not_found")
    cfg["llm_model"] = model
    cfg["updated_at"] = now_iso()
    save_atomic(config_path(agent_id), cfg)


@router.get("/models")
async def list_models(p: Admin) -> dict:
    """Modelle der eigenen Anbieter für die Auswahl. `default` ist das Standardmodell des Systems.
    `default_listed` sagt, ob es in der Live-Liste der eingerichteten Anbieter steht: wenn nicht, hat der Server dafür
    vermutlich keinen Zugang (hydratest 6.11.: claude-sonnet-4-6 ohne Anthropic-Login) und der Chat bräche mit einer Meldung ab."""
    from hydrahive.llm import registry
    items = [{"id": m.id, "label": m.label, "provider": m.provider} for m in await registry.list_models("chat")]
    default = _default_model()
    listed = any(i["id"] == default for i in items)
    if default and not listed:                              # das Standardmodell steht nicht immer in der Live-Liste
        items.insert(0, {"id": default, "label": default, "provider": "standard"})
    return {"default": default, "default_listed": listed or not items[1:], "items": items}


@router.post("/projects/{project_id}/model")
def set_model(project_id: str, p: Admin, body: ModelChoice) -> dict:
    """Modell eines Projekts wechseln (gilt ab der nächsten Nachricht). Alles andere am Agenten bleibt gesperrt."""
    from hydrahive.agents import config as agent_config
    from hydrahive.agents._validation import AgentValidationError, validate_model
    row = _own(project_id, p)
    chosen = body.model.strip()
    agent = agent_config.get(row["agent_id"]) or {}
    # Das Standardmodell steht nicht immer in der Live-Liste, ist aber das, was das System selbst nimmt – also erlaubt.
    # Auch bleibt ein schon gesetztes Modell wählbar, wenn nur die Liste gerade fehlt.
    if chosen == _default_model() or chosen == agent.get("llm_model"):
        _write_model(row["agent_id"], chosen)                     # agent_config.update prüft erneut gegen die Live-Liste
    else:
        try:
            validate_model(chosen)
        except AgentValidationError:
            raise coded(status.HTTP_400_BAD_REQUEST, "vibe_model_unavailable") from None
        agent_config.update(row["agent_id"], llm_model=chosen)
    return {"model": chosen}
