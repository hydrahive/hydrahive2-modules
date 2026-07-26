from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated, TypeVar

from fastapi import APIRouter, Depends, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.middleware.inbound_ratelimit import check_rate

from . import service
from .errors import (
    IndexerAuthError,
    IndexerResponseError,
    IndexerUnavailable,
    MediacenterConfigError,
    SabAuthError,
    SabResponseError,
    SabUnavailable,
)
from .models import ConnectionTestResponse, ModuleStatus, SearchRequest, SearchResponse

class _SanitizedValidationRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def sanitized(request: Request):
            try:
                return await original(request)
            except RequestValidationError:
                raise coded(
                    status.HTTP_422_UNPROCESSABLE_CONTENT,
                    "mediacenter_request_invalid",
                ) from None

        return sanitized


router = APIRouter(route_class=_SanitizedValidationRoute)
Auth = Annotated[tuple[str, str], Depends(require_auth)]
T = TypeVar("T")


async def _guard(call: Callable[[], Awaitable[T]]) -> T:
    try:
        return await call()
    except MediacenterConfigError as exc:
        raise coded(status.HTTP_503_SERVICE_UNAVAILABLE, exc.code)
    except (
        IndexerAuthError,
        IndexerResponseError,
        IndexerUnavailable,
        SabAuthError,
        SabResponseError,
        SabUnavailable,
    ) as exc:
        raise coded(status.HTTP_502_BAD_GATEWAY, exc.code)


def _rate(username: str, action: str, limit: int) -> None:
    allowed, retry_after = check_rate(
        f"mediacenter:{action}:{username}", limit=limit, window=60
    )
    if not allowed:
        raise coded(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "mediacenter_rate_limited",
            retry_after=retry_after,
        )


@router.get("/status", response_model=ModuleStatus)
def module_status(auth: Auth) -> ModuleStatus:
    username, _ = auth
    return service.connection_status(username)


@router.post("/connections/test", response_model=ConnectionTestResponse)
async def connection_test(auth: Auth) -> ConnectionTestResponse:
    username, _ = auth
    _rate(username, "connection_test", 10)
    return await _guard(lambda: service.test_connections(username))


@router.post("/search", response_model=SearchResponse)
async def search(auth: Auth, body: SearchRequest) -> SearchResponse:
    username, _ = auth
    _rate(username, "search", 30)
    return await _guard(lambda: service.search_indexer(username, body))
