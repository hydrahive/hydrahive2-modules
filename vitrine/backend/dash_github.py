"""„Wartet auf Till“ (S2): offene PRs + CI-Zustand, nur lesend (SPEC-STATUSZENTRALE.md, S2/GitHub).

Token = Git-Token des eingestellten HydraHive-Projekts (gleiche Reihenfolge wie der Kern beim GH_TOKEN). Er hat
Schreibrechte, deshalb hier: nur GET, feste URL-Form auf api.github.com, Repo-Namen geprüft, keine Weiterleitungen,
Zeitlimit 10 s. Der Token steht nur im Authorization-Header — nie im Ergebnis, nie im Log.
"""
from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from typing import Callable

log = logging.getLogger(__name__)
API = "https://api.github.com"
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$")
TIMEOUT, MAX_PRS, TITLE_MAX = 10, 10, 80
ERR_NET, ERR_TOKEN = "GitHub nicht erreichbar", "Kein GitHub-Zugang"

Fetch = Callable[[str, str, dict, float], tuple[int, object]]


def token_of(project: dict) -> str | None:
    for r in (project.get("git_repos") or {}).values():
        if isinstance(r, dict) and r.get("git_token"):
            return r["git_token"]
    return project.get("git_token") or None


def find_project(ref: str, projects: list[dict]) -> dict | None:
    for p in projects:
        if ref and (p.get("id") == ref or p.get("name") == ref):
            return p
    return None


def valid_repo(name: str) -> bool:
    return bool(REPO_RE.fullmatch(name or "")) and not any(part in (".", "..") for part in name.split("/"))


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def _opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(_NoRedirect())


def _urllib_fetch(method: str, url: str, headers: dict, timeout: float) -> tuple[int, object]:
    req = urllib.request.Request(url, method=method, headers=headers)
    try:
        with _opener().open(req, timeout=timeout) as r:
            return r.status, json.loads(r.read(2_000_000) or b"null")
    except urllib.error.HTTPError as e:
        return e.code, None


def ci_state(runs: list[dict]) -> str:
    if not runs:
        return "none"
    if any(r.get("status") != "completed" for r in runs):
        return "running"
    if any(r.get("conclusion") not in ("success", "skipped", "neutral") for r in runs):
        return "red"
    return "green"


def _cut(s, n: int) -> str:
    s = " ".join(str(s or "").split())
    return s if len(s) <= n else s[: n - 1] + "…"


def open_prs(repos: list[str], token: str | None, *, fetch: Fetch = _urllib_fetch) -> dict:
    if not token:
        return {"prs": [], "error": ERR_TOKEN}
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "hydrahive-vitrine"}
    out: list[dict] = []
    try:
        for repo in repos:
            if not valid_repo(repo):
                log.warning("Statuszentrale: Repo-Name abgelehnt")
                continue
            base = f"{API}/repos/{repo}"
            code, prs = fetch("GET", f"{base}/pulls?state=open&per_page=20", headers, TIMEOUT)
            if code != 200 or not isinstance(prs, list):
                return {"prs": out, "error": ERR_NET}
            for p in prs:
                if len(out) >= MAX_PRS:
                    break
                sha = str((p.get("head") or {}).get("sha") or "")
                runs: list = []
                if re.fullmatch(r"[0-9a-fA-F]{6,64}", sha):
                    c, body = fetch("GET", f"{base}/commits/{sha}/check-runs?per_page=50", headers, TIMEOUT)
                    runs = body.get("check_runs", []) if c == 200 and isinstance(body, dict) else []
                out.append({"repo": repo.split("/")[1], "number": int(p.get("number") or 0),
                            "title": _cut(p.get("title"), TITLE_MAX), "draft": bool(p.get("draft")),
                            "ci": ci_state(runs)})
    except (OSError, ValueError, TimeoutError) as e:
        log.warning("Statuszentrale: GitHub-Abruf fehlgeschlagen (%s)", type(e).__name__)
        return {"prs": out, "error": ERR_NET}
    return {"prs": out, "error": None}
