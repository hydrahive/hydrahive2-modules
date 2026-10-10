"""SSE-Kanal für die Brille: GET /api/modules/vr/events (Login nötig)."""
from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from .hub import TooManyConnections, hub

router = APIRouter()
Auth = Annotated[tuple[str, str], Depends(require_auth)]
KEEPALIVE_SECONDS = 20.0


@router.get("/events")
async def events_stream(auth: Auth) -> StreamingResponse:
    """Ereignisse für die Brille des angemeldeten Nutzers. Hält offen, Keepalive alle 20 s."""
    user = auth[0]
    try:
        queue = hub.subscribe(user)
    except TooManyConnections:
        raise coded(status.HTTP_429_TOO_MANY_REQUESTS, "too_many_connections")

    async def _gen():
        try:
            yield ": connected\n\n"
            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=KEEPALIVE_SECONDS)
                    yield f"data: {payload}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            hub.unsubscribe(user, queue)

    return StreamingResponse(
        _gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/status")
def connection_status(auth: Auth) -> dict:
    return {"headsets": hub.connected(auth[0])}
