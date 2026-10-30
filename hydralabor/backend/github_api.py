"""GitHub-Zugriffe (PLAN-L2.md Baustein 7): nur feste Adressen (api.github.com, github.com/login/…), Zeitlimits,
Token nur im Kopf `Authorization`, nie in URL oder Log. `request` ist der einzige Weg nach außen (Tests ersetzen ihn).
"""
from __future__ import annotations

import httpx

API = "https://api.github.com"
_ALLOWED = ("https://api.github.com/", "https://github.com/login/device/code", "https://github.com/login/oauth/access_token")
_TIMEOUT = httpx.Timeout(20.0, connect=10.0)


class GitHubError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


async def request(method: str, url: str, *, token: str = "", data: dict | None = None,
                  json: dict | None = None) -> tuple[int, dict, dict]:
    if not url.startswith(_ALLOWED):
        raise GitHubError("labor_github_url")
    headers = {"Accept": "application/json", "User-Agent": "HydraHive-Labor"}
    if url.startswith(API):
        headers["Accept"] = "application/vnd.github+json"
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=False) as c:
            r = await c.request(method, url, headers=headers, data=data, json=json)
    except httpx.HTTPError:
        raise GitHubError("labor_github_unreachable") from None
    try:
        body = r.json()
    except ValueError:                  # leer oder kein JSON
        body = {}
    return r.status_code, body if isinstance(body, dict) else {"items": body}, {k.lower(): v for k, v in r.headers.items()}
