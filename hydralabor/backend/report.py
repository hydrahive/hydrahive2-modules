"""Fehler melden (PLAN-L2.md Baustein 6): Issue mit Versionen und Betriebssystem. Keine Logs in L2.
Der Text geht vorher durch den Geheimnis-Filter des Kerns."""
from __future__ import annotations

import platform

from . import github_api, github_repos, precheck
from .github_api import API
from .submit import _connected, _save, _versions
from .submit_box import SubmitError

MAX_PART = 4000


def _environment() -> dict[str, str]:
    env = {k: v for k, v in _versions().items() if k in ("hydrahive", "hydralabor")}
    try:
        info = platform.freedesktop_os_release()
        env["system"] = info.get("PRETTY_NAME", "") or platform.platform()
    except OSError:
        env["system"] = platform.platform()
    return env


def _clean(text: str) -> str:
    from hydrahive.credentials.redaction import redact_detected
    return redact_detected((text or "").strip())


async def report(target: str, title: str, what: str, expected: str, steps: str) -> dict:
    if target not in github_repos.TARGETS:
        raise SubmitError("labor_submit_target_invalid")
    title = (title or "").strip()
    if not title or len(title) > precheck.MAX_TITLE or not (what or "").strip() or \
            any(len(x or "") > MAX_PART for x in (what, expected, steps)):
        raise SubmitError("labor_submit_text_invalid")
    tok, _, _ = _connected()
    env = _environment()
    body = (f"### Was ist passiert?\n{_clean(what)}\n\n### Was hast du erwartet?\n{_clean(expected) or '–'}\n\n"
            f"### Schritte\n{_clean(steps) or '–'}\n\n### Umgebung\n" +
            "\n".join(f"- {k} {v}" for k, v in env.items()) +
            "\n\n---\nGemeldet über **Hydra-Labor**.\n")
    repo = github_repos.TARGETS[target]
    st, iss, _ = await github_api.request("POST", f"{API}/repos/{repo}/issues", token=tok,
                                          json={"title": _clean(title), "body": body})
    if st != 201 or not iss.get("number"):
        raise SubmitError("labor_report_failed")
    await github_api.request("POST", f"{API}/repos/{repo}/issues/{iss['number']}/labels", token=tok,
                             json={"labels": ["labor"]})
    _save("issue", target, title, "", int(iss["number"]), iss.get("html_url", ""))
    return {"number": int(iss["number"]), "url": iss.get("html_url", "")}
