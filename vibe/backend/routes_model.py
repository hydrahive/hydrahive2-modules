"""Modell eines Vibe-Projekts: Liste, Wahl, Wechsel. Mit Agenten-Templates (Kern) nur aus der Kette von
`modul-schnell` (backend/model_choice.py); ohne Templates wie früher direkt am Agenten (agents/_managed.py: FREE)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from hydrahive.api.middleware.auth import AuthPrincipal, require_admin_principal
from hydrahive.api.middleware.errors import coded
from pydantic import BaseModel, ConfigDict, Field

from . import chat, model_choice, state

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
    cfg = agent_config.get(agent_id) or {}
    return model_choice.current(cfg, chat.session_id(agent_id)) if cfg else ""


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
    """Wählbare Modelle. Mit Template (Kern ab den Agenten-Templates): nur die Kette von `modul-schnell`,
    `default` = Primär. Sonst wie früher: alle Modelle der eingerichteten Anbieter, `default` = Standardmodell;
    `default_listed` sagt, ob es in der Live-Liste steht (hydratest 6.11.: claude-sonnet-4-6 ohne Anthropic-Login)."""
    chain = model_choice.template_chain()
    if chain:
        return {"default": chain[0], "default_listed": True, "items": model_choice.items(chain)}
    from hydrahive.llm import registry
    items = [{"id": m.id, "label": m.label, "provider": m.provider} for m in await registry.list_models("chat")]
    default = _default_model()
    listed = any(i["id"] == default for i in items)
    if default and not listed:                              # das Standardmodell steht nicht immer in der Live-Liste
        items.insert(0, {"id": default, "label": default, "provider": "standard"})
    return {"default": default, "default_listed": listed or not items[1:], "items": items}


@router.post("/projects/{project_id}/model")
def set_model(project_id: str, p: Admin, body: ModelChoice) -> dict:
    """Modell eines Projekts wechseln (gilt ab der nächsten Nachricht). Alles andere am Agenten bleibt gesperrt.
    Gebunden: nur Modelle der Kette, gespeichert als Sitzungsmodell des Vibe-Chats."""
    from hydrahive.agents import config as agent_config
    from hydrahive.agents._validation import AgentValidationError, validate_model
    row = _own(project_id, p)
    chosen = body.model.strip()
    agent = agent_config.get(row["agent_id"]) or {}
    chain = model_choice.chain_of(agent)
    if chain:
        if chosen not in chain:
            raise coded(status.HTTP_400_BAD_REQUEST, "vibe_model_unavailable")
        model_choice.set_session_model(chat.ensure_session(row, p.username), chain, chosen)
        return {"model": chosen}
    # Altbestand ohne Template: Das Standardmodell steht nicht immer in der Live-Liste, ist aber das, was das System
    # selbst nimmt – also erlaubt. Auch bleibt ein schon gesetztes Modell wählbar, wenn nur die Liste gerade fehlt.
    if chosen == _default_model() or chosen == agent.get("llm_model"):
        _write_model(row["agent_id"], chosen)                     # agent_config.update prüft erneut gegen die Live-Liste
    else:
        try:
            validate_model(chosen)
        except AgentValidationError:
            raise coded(status.HTTP_400_BAD_REQUEST, "vibe_model_unavailable") from None
        agent_config.update(row["agent_id"], llm_model=chosen)
    return {"model": chosen}
