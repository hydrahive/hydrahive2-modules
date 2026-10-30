"""Auslieferer der Probe – läuft IM LABOR als Nutzer `labor` (nicht auf dem Server), PLAN-L3.md.

- Dateien aus dem gebauten Frontend (`dist`: assets/, Bilder aus public/, favicon …), alle anderen Pfade →
  `index.html` (SPA). Nichts außerhalb von `dist` (auch nicht über Verknüpfungen).
- `/api/...` gestreamt an das Probe-Backend (127.0.0.1:8002), Methode/Kopf/Body/Query unverändert –
  außer dem Cookie `hh_labor_probe` des echten Servers, der hier nichts verloren hat.
Start: python front.py <dist> <backend-url> <port>
"""
from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from starlette.applications import Starlette
from starlette.background import BackgroundTask
from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse, Response, StreamingResponse
from starlette.routing import Route

LAB_COOKIE = "hh_labor_probe"
_HOP = {"connection", "keep-alive", "transfer-encoding", "upgrade", "proxy-connection", "te", "trailer", "host",
        "content-length"}
_NOT_BUILT = "<html><body><p>Die Probe ist noch nicht gebaut. Bitte im Hydra-Labor „Probe bauen“ wählen.</p></body></html>"


def _strip_lab_cookie(value: str) -> str:
    keep = [c.strip() for c in value.split(";") if c.strip() and not c.strip().startswith(LAB_COOKIE + "=")]
    return "; ".join(keep)


def make_app(dist: Path, backend: str, *, transport: httpx.AsyncBaseTransport | None = None) -> Starlette:
    dist = Path(dist).resolve()
    assets = dist / "assets"
    client = httpx.AsyncClient(base_url=backend, transport=transport, timeout=httpx.Timeout(None, connect=5.0))

    async def api(request: Request) -> Response:
        headers = [(k, v) for k, v in request.headers.items() if k.lower() not in _HOP]
        headers = [(k, _strip_lab_cookie(v)) if k.lower() == "cookie" else (k, v) for k, v in headers]
        headers = [(k, v) for k, v in headers if not (k.lower() == "cookie" and not v)]
        req = client.build_request(request.method, request.url.path, params=request.url.query,
                                   headers=headers, content=await request.body())
        try:
            resp = await client.send(req, stream=True)
        except httpx.HTTPError:
            return Response("Probe-Backend nicht erreichbar", status_code=502)
        out = [(k, v) for k, v in resp.headers.multi_items() if k.lower() not in _HOP]
        sr = StreamingResponse(resp.aiter_raw(), status_code=resp.status_code, background=BackgroundTask(resp.aclose))
        sr.raw_headers = [(k.encode("latin-1"), v.encode("latin-1")) for k, v in out]
        return sr

    async def static(request: Request) -> Response:
        index = dist / "index.html"
        if not index.is_file():
            return HTMLResponse(_NOT_BUILT, status_code=503)
        # Wie nginx auf dem Server (try_files $uri … /index.html): jede Datei aus dist, sonst index.html (SPA).
        f = (dist / request.url.path.lstrip("/")).resolve()
        if f.is_file() and dist in f.parents:
            immutable = assets in f.parents                     # nur gehashte Bündel dürfen ewig im Cache bleiben
            return FileResponse(f, headers={"Cache-Control": "public, max-age=31536000, immutable" if immutable
                                            else "no-cache"})
        return FileResponse(index, headers={"Cache-Control": "no-cache"})

    @asynccontextmanager
    async def lifespan(_app):
        yield
        await client.aclose()

    methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]
    return Starlette(routes=[Route("/api/{rest:path}", api, methods=methods),
                             Route("/{rest:path}", static, methods=["GET", "HEAD"])], lifespan=lifespan)


if __name__ == "__main__":                                       # pragma: no cover - Start im Labor
    import uvicorn
    uvicorn.run(make_app(Path(sys.argv[1]), sys.argv[2]), host="0.0.0.0", port=int(sys.argv[3]), log_level="warning")
