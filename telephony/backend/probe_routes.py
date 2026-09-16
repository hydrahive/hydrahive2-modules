"""Authenticated API boundary for ephemeral SIP registration probes."""

from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute

from hydrahive.api.middleware.auth import AuthPrincipal, require_principal
from hydrahive.api.middleware.errors import coded
from hydrahive.api.middleware.inbound_ratelimit import check_rate

from .probe_models import RegistrationProbeRequest, RegistrationProbeResponse
from .probe_service import run_registration_probe


class _SanitizedValidationRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def sanitized(request: Request):
            content_length = request.headers.get("content-length")
            try:
                if content_length is None or int(content_length) > 2048:
                    raise coded(
                        status.HTTP_413_CONTENT_TOO_LARGE,
                        "telephony_probe_request_too_large",
                    )
            except ValueError:
                raise coded(
                    status.HTTP_413_CONTENT_TOO_LARGE,
                    "telephony_probe_request_too_large",
                ) from None
            try:
                return await original(request)
            except RequestValidationError:
                raise coded(
                    status.HTTP_422_UNPROCESSABLE_CONTENT,
                    "telephony_probe_request_invalid",
                ) from None

        return sanitized


router = APIRouter(route_class=_SanitizedValidationRoute)
Auth = Annotated[AuthPrincipal, Depends(require_principal)]


@router.post(
    "/spike/registration-test",
    response_model=RegistrationProbeResponse,
)
async def registration_test(
    body: RegistrationProbeRequest,
    auth: Auth,
) -> RegistrationProbeResponse:
    allowed, retry_after = check_rate(
        f"telephony:registration_probe:{auth.user_id}",
        limit=5,
        window=60,
    )
    if not allowed:
        raise coded(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "telephony_probe_rate_limited",
            retry_after=retry_after,
        )
    outcome = await asyncio.to_thread(run_registration_probe, body)
    return RegistrationProbeResponse(outcome=outcome)
