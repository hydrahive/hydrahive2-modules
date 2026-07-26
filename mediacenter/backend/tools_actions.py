from __future__ import annotations

from pydantic import ValidationError

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from . import enqueue_service, intent_gate
from .models import EnqueueRequest
from .tool_support import failure, username_for

_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "result_id": {
            "type": "string", "minLength": 20, "maxLength": 128,
            "pattern": "^[A-Za-z0-9_-]+$",
        },
        "priority": {
            "type": "string", "enum": ["default", "high", "low"],
            "default": "default",
        },
    },
    "required": ["result_id"],
}


async def _enqueue(args: dict, ctx: ToolContext) -> ToolResult:
    username = username_for(ctx)
    if username is None:
        return ToolResult.fail("invalid_principal")
    try:
        request = EnqueueRequest.model_validate(args)
        grant_id = intent_gate.authorize_enqueue(
            owner=ctx.user_id,
            session_id=ctx.session_id,
            result_id=request.result_id,
            trusted_turn=ctx.current_user_input,
            trusted_turn_id=ctx.current_user_turn_id,
        )
        job = await enqueue_service.enqueue_result(
            username,
            request.result_id,
            priority=request.priority,
            owner_id=ctx.user_id,
            agent_id=ctx.agent_id,
            session_id=ctx.session_id,
            grant_id=grant_id,
            require_grant=True,
        )
        if job.state in {"submitting", "uncertain"}:
            return ToolResult.fail("enqueue_status_uncertain")
        if job.state == "manual_review_required":
            return ToolResult.fail("enqueue_manual_review_required")
        return ToolResult.ok({
            "result_id": job.result_id,
            "title": job.title,
            "media_type": job.media_type,
            "state": job.state,
            "sab_job_id": job.sab_job_id,
            "error_code": job.error_code,
        })
    except ValidationError:
        return ToolResult.fail("mediacenter_request_invalid")
    except Exception as exc:
        return failure(exc)


ENQUEUE_TOOL = Tool(
    name="mediacenter_enqueue",
    description=(
        "Übergibt genau einen zuvor gefundenen eligible Mediacenter-Treffer an SABnzbd. "
        "Funktioniert nur bei expliziter Downloadabsicht im aktuellen Benutzerturn."
    ),
    schema=_SCHEMA,
    execute=_enqueue,
    category="action",
    prompt_hint=(
        "Nie bei bloßer Suche aufrufen. Bei quality_preference_required oder "
        "format_preference_required zuerst den Benutzer eindeutig auswählen lassen."
    ),
)
