"""Einreichen (PLAN-L2.md Baustein 4/5): Vorprüfung im Labor → Fork → Bündel → Schieben → PR, gespeichert; Stand.

Reihenfolge so, dass nichts nach außen geht, bevor alles grün ist: erst Änderungen/geschützte Pfade/Größe/
Geheimnisse/Tests im Container, dann erst Fork und Schieben. Der Token kommt nur in github_api/push.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from hydrahive.db.connection import db

from . import github_api, github_auth, github_repos, precheck, push, submit_box
from .github_api import API, GitHubError
from .submit_box import SubmitError

logger = logging.getLogger(__name__)
_T = "module_hydralabor_submissions"
_COLS = ("id", "kind", "target", "title", "branch", "number", "url", "state", "note", "created_at", "updated_at")
_FOOTER = "\n\n---\nEingereicht über **Hydra-Labor** (geprüft im abgeschotteten Labor).\n"


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d-%H%M")


def _workdir() -> Path:
    from hydrahive.settings import settings
    d = settings.data_dir / "hydralabor" / "push"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _versions() -> dict[str, str]:
    from hydrahive.modules.registry import REGISTRY
    out = {}
    try:
        from importlib.metadata import version
        out["hydrahive"] = version("hydrahive-core")     # Paketname des Kerns (core/pyproject.toml)
    except Exception:  # noqa: BLE001 - Version ist nur Zusatzinfo
        out["hydrahive"] = "?"
    for name, m in sorted(REGISTRY.items()):
        if m.manifest is not None:
            out[name] = m.manifest.version
    return out


def _connected() -> tuple[str, str, int]:
    tok = github_auth.token()
    login, uid = github_auth.identity()
    if not tok or not login:
        raise SubmitError("labor_github_not_connected")
    return tok, login, uid


def _save(kind: str, target: str, title: str, branch: str, number: int, url: str) -> None:
    with db() as c:
        c.execute(f"INSERT INTO {_T} (kind, target, title, branch, number, url, state, created_at, updated_at) "
                  "VALUES (?, ?, ?, ?, ?, ?, 'submitted', ?, ?)",
                  (kind, target, title, branch, number, url, _now(), _now()))
        c.commit()


def list_submissions() -> list[dict]:
    with db() as c:
        rows = c.execute(f"SELECT {', '.join(_COLS)} FROM {_T} ORDER BY id DESC LIMIT 100").fetchall()
    return [dict(zip(_COLS, r, strict=True)) for r in rows]


def _body(text: str, tests: dict, ch: dict) -> str:
    v = _versions()
    vers = ", ".join(f"{k} {val}" for k, val in v.items() if k in ("hydrahive", "hydralabor"))
    return (f"{text}\n\n**Prüfung im Labor:** {tests.get('summary') or 'grün'} · {len(ch['files'])} Dateien, "
            f"{ch['lines']} Zeilen\n**Versionen:** {vers}" + _FOOTER)


async def _precheck(target: str, title: str, login: str, uid: int, report: Callable[[str], None]) -> tuple[dict, dict]:
    report("check")
    ch = await submit_box.changes(target)
    if not ch["files"]:
        raise SubmitError("labor_submit_nothing")
    if hit := precheck.protected(target, ch["files"]):
        raise SubmitError("labor_submit_protected", hit)
    if code := precheck.size_problem(len(ch["files"]), ch["lines"]):
        raise SubmitError(code)
    await submit_box.commit(target, title, login, uid)
    if found := precheck.secrets(await submit_box.diff(target)):
        raise SubmitError("labor_submit_secret", found)
    report("tests")
    tests = await submit_box.run_tests(target, ch["files"])
    if not tests["ok"]:
        raise SubmitError("labor_submit_tests_red", tests)
    return ch, tests


async def submit(target: str, title: str, body: str, *, report: Callable[[str], None]) -> dict:
    if target not in github_repos.TARGETS:
        raise SubmitError("labor_submit_target_invalid")
    try:
        title, body = precheck.check_text(title, body)
    except precheck.PrecheckError as e:
        raise SubmitError(str(e)) from None
    tok, login, uid = _connected()
    ch, tests = await _precheck(target, title, login, uid, report)
    report("fork")
    fork = await github_repos.ensure_fork(tok, login, target)
    report("push")
    branch = precheck.branch_name(title, _stamp())
    work = _workdir()
    await push.push_bundle(await submit_box.bundle(target, work), fork=fork, target=target, branch=branch,
                           token=tok, workdir=work)
    report("pr")
    repo = github_repos.TARGETS[target]
    st, pr, _ = await github_api.request("POST", f"{API}/repos/{repo}/pulls", token=tok, json={
        "title": title, "head": f"{login}:{branch}", "base": "main", "body": _body(body, tests, ch),
        "maintainer_can_modify": True})
    if st != 201 or not pr.get("number"):
        raise SubmitError("labor_submit_pr_failed")
    # Label setzen dürfen Fremde meist nicht – Fehler egal, Till setzt es dann.
    await github_api.request("POST", f"{API}/repos/{repo}/issues/{pr['number']}/labels", token=tok,
                             json={"labels": ["labor"]})
    _save("pr", target, title, branch, int(pr["number"]), pr.get("html_url", ""))
    logger.info("Hydra-Labor: PR %s#%s eingereicht", repo, pr["number"])
    return {"number": int(pr["number"]), "url": pr.get("html_url", "")}


async def suggest_target() -> str:
    changed = {}
    for t in github_repos.TARGETS:
        try:
            changed[t] = (await submit_box.changes(t))["files"]
        except SubmitError:
            changed[t] = []
    return precheck.guess_target(changed)


async def refresh() -> None:
    """Offene PRs bei GitHub nachsehen (nur auf Knopfdruck). Abgeschlossene werden nicht mehr abgefragt."""
    tok, _, _ = _connected()
    for s in list_submissions():
        if s["kind"] != "pr" or s["state"] != "submitted":
            continue
        try:
            st, pr, _ = await github_api.request(
                "GET", f"{API}/repos/{github_repos.TARGETS[s['target']]}/pulls/{s['number']}", token=tok)
        except GitHubError:
            continue
        if st != 200 or pr.get("state") != "closed":
            continue
        new = "merged" if pr.get("merged") else "closed"
        with db() as c:
            c.execute(f"UPDATE {_T} SET state = ?, updated_at = ? WHERE id = ?", (new, _now(), s["id"]))
            c.commit()
