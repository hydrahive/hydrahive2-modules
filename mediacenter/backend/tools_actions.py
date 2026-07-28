from __future__ import annotations

from pydantic import ValidationError

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from . import enqueue_service, intent_gate
from .errors import MediacenterError
from .models import BatchEnqueueRequest, EnqueueRequest
from .tool_support import failure, principal_for

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

_BATCH_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "collection": {
            "type": "string", "minLength": 2, "maxLength": 200,
        },
        "result_ids": {
            "type": "array",
            "minItems": 1,
            "maxItems": 100,
            "items": {
                "type": "string", "minLength": 20, "maxLength": 128,
                "pattern": "^[A-Za-z0-9_-]+$",
            },
        },
        "priority": {
            "type": "string", "enum": ["default", "high", "low"],
            "default": "default",
        },
    },
    "required": ["collection", "result_ids"],
}


async def _enqueue(args: dict, ctx: ToolContext) -> ToolResult:
    principal = principal_for(ctx)
    if principal is None:
        return ToolResult.fail("invalid_principal")
    try:
        request = EnqueueRequest.model_validate(args)
        grant_id = intent_gate.authorize_enqueue(
            owner=principal["user_id"],
            session_id=ctx.session_id,
            result_id=request.result_id,
            trusted_turn=ctx.current_user_input,
            trusted_turn_id=ctx.current_user_turn_id,
        )
        job = await enqueue_service.enqueue_result(
            principal["username"],
            request.result_id,
            priority=request.priority,
            owner_id=principal["user_id"],
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


async def _enqueue_batch(args: dict, ctx: ToolContext) -> ToolResult:
    principal = principal_for(ctx)
    if principal is None:
        return ToolResult.fail("invalid_principal")
    try:
        request = BatchEnqueueRequest.model_validate(args)
    except ValidationError:
        return ToolResult.fail("mediacenter_request_invalid")
    try:
        authorized, skipped = intent_gate.authorize_batch_enqueue(
            owner=principal["user_id"],
            session_id=ctx.session_id,
            collection=request.collection,
            result_ids=request.result_ids,
            trusted_turn=ctx.current_user_input,
            trusted_turn_id=ctx.current_user_turn_id,
        )
    except MediacenterError as exc:
        return ToolResult.fail(exc.code)
    except Exception as exc:
        return failure(exc)

    enqueued: list[dict] = []
    failed: list[dict] = []
    for result_id, grant_id in authorized.items():
        try:
            job = await enqueue_service.enqueue_result(
                principal["username"],
                result_id,
                priority=request.priority,
                owner_id=principal["user_id"],
                agent_id=ctx.agent_id,
                session_id=ctx.session_id,
                grant_id=grant_id,
                require_grant=True,
            )
        except MediacenterError as exc:
            failed.append({"result_id": result_id, "error_code": exc.code})
            continue
        except Exception:
            failed.append({"result_id": result_id, "error_code": "mediacenter_internal_error"})
            continue
        if job.state in {"submitting", "uncertain"}:
            failed.append({"result_id": result_id, "error_code": "enqueue_status_uncertain"})
        elif job.state == "manual_review_required":
            failed.append({"result_id": result_id, "error_code": "enqueue_manual_review_required"})
        else:
            enqueued.append({
                "result_id": job.result_id,
                "title": job.title,
                "media_type": job.media_type,
                "state": job.state,
                "sab_job_id": job.sab_job_id,
            })

    skipped_out = [
        {"result_id": rid, "reason": reason} for rid, reason in skipped.items()
    ]
    return ToolResult.ok({
        "collection": request.collection,
        "requested": len(request.result_ids),
        "enqueued_count": len(enqueued),
        "enqueued": enqueued,
        "failed": failed,
        "skipped": skipped_out,
    })


ENQUEUE_BATCH_TOOL = Tool(
    name="mediacenter_enqueue_batch",
    description=(
        "Übergibt mehrere zuvor gefundene eligible Treffer als Sammel-Download an "
        "SABnzbd — für 'alle Alben von X' / 'alle Filme von X'. Nur bei explizitem "
        "Sammel-Download-Befehl im aktuellen Benutzerturn (Download-Verb + 'alle' "
        "o.ä.). 'collection' ist der vom Benutzer genannte Name (Künstler/Reihe); "
        "er muss im Benutzerturn stehen und wird gegen jeden Titel geprüft."
    ),
    schema=_BATCH_SCHEMA,
    execute=_enqueue_batch,
    category="action",
    prompt_hint=(
        "Zuerst mediacenter_search aufrufen und die result_ids der gewünschten "
        "Treffer sammeln. 'collection' ist der Name, den der Benutzer gesagt hat "
        "(z.B. der Künstler). Nur nutzen, wenn der Benutzer im aktuellen Turn einen "
        "Sammel-Download will ('alle ... runterladen'); für Einzeltitel "
        "mediacenter_enqueue verwenden. Treffer ohne den Namen im Titel werden "
        "sicherheitshalber übersprungen (skipped)."
    ),
)
