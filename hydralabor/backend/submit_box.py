"""Einreichen – Teil im Container (PLAN-L2.md Baustein 4): Änderungen messen, sichern, Tests, Bündel abholen.

Alles läuft als Nutzer `labor` im Labor-Container. Texte des Nutzers (Titel) gehen nur über Umgebungsvariablen an git,
nie in den Befehl. Das Bündel ist nicht vertrauenswürdig: Größe begrenzt, Kopfzeile geprüft, im Container gelöscht.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import container, incus
from .jobs import parse_test

REPO = {"core": "/work/hydrahive2", "modules": "/work/hydrahive2-modules"}
MAX_BUNDLE = 50 * 1024 * 1024
_BUNDLE = "/tmp/hh-labor.bundle"
_LOGIN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
_MODULE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,62}$")
_HEADS = (b"# v2 git bundle\n", b"# v3 git bundle\n")


class SubmitError(RuntimeError):
    def __init__(self, code: str, detail: object = None):
        super().__init__(code)
        self.code = code
        self.detail = detail


async def _exec(target: str, script: str, *, env: dict[str, str] | None = None, timeout: float = 120) -> tuple[int, str]:
    args = ["exec", container.NAME, "--cwd", REPO[target], "--user", "1000", "--group", "1000",
            "--env", "HOME=/home/labor"]
    for k, v in (env or {}).items():
        args += ["--env", f"{k}={v}"]
    rc, out, _ = await incus.run(*args, "--", "bash", "-c", script, timeout=timeout)
    return rc, out


async def changes(target: str) -> dict:
    """Geänderte Dateien gegenüber origin/main (gesichert + ungesichert + neu) und Zahl der Zeilen."""
    rc, out = await _exec(target, "# hh-labor-changes\n"
                          "git add -A -N . && git diff --name-only origin/main && echo --STAT-- && "
                          "git diff --numstat origin/main")
    if rc != 0:
        raise SubmitError("labor_submit_git_failed")
    names, _, stat = out.partition("--STAT--\n")
    lines = 0
    for row in stat.splitlines():
        a, _, rest = row.partition("\t")
        d, _, _ = rest.partition("\t")
        lines += 1 if a == "-" else int(a or 0) + int(d or 0)
    return {"files": [n for n in names.splitlines() if n.strip()], "lines": lines}


async def commit(target: str, title: str, login: str, uid: int) -> None:
    if not _LOGIN.match(login or "") or uid < 1:
        raise SubmitError("labor_github_failed")
    who = {"GIT_AUTHOR_NAME": login, "GIT_COMMITTER_NAME": login,
           "GIT_AUTHOR_EMAIL": f"{uid}+{login}@users.noreply.github.com",
           "GIT_COMMITTER_EMAIL": f"{uid}+{login}@users.noreply.github.com", "HH_LABOR_MSG": title}
    rc, _ = await _exec(target, 'git add -A && (git diff --cached --quiet || git commit -q -m "$HH_LABOR_MSG")', env=who)
    if rc != 0:
        raise SubmitError("labor_submit_git_failed")


async def diff(target: str) -> str:
    rc, out = await _exec(target, "# hh-labor-diff\ngit diff origin/main..HEAD")
    if rc != 0:
        raise SubmitError("labor_submit_git_failed")
    return out


def _modules(files: list[str]) -> list[str]:
    mods = sorted({f.split("/", 1)[0] for f in files if "/" in f})
    for m in mods:
        if not _MODULE.match(m):
            raise SubmitError("labor_submit_git_failed")
    return mods


async def run_tests(target: str, files: list[str]) -> dict:
    if target == "core":
        rc, out = await _exec(target, "pytest -q -n 2 -p no:cacheprovider core/tests 2>&1 | tail -n 80", timeout=1800)
        return parse_test(rc, out)
    mods = _modules(files)
    parts = [f'echo "== {m}"; [ -d {m}/tests ] && (cd {m} && pytest -q -p no:cacheprovider tests 2>&1 | tail -n 30) '
             f'|| echo "keine Tests"' for m in mods]
    script = ("# hh-labor-modtests\nset -o pipefail; rc=0; " + "; ".join(f"{p} || rc=1" for p in parts) +
              '; echo "== skripte"; python scripts/check_version_bump.py origin/main && '
              "python scripts/check_test_safety.py || rc=1; exit $rc")
    rc, out = await _exec(target, script, timeout=1800)
    return {"ok": rc == 0, "summary": out.strip().splitlines()[-1] if out.strip() else "", "passed": 0, "failed": 0,
            "failures": [], "output": out[-4000:]}


async def bundle(target: str, workdir: Path) -> Path:
    rc, _ = await _exec(target, f"rm -f {_BUNDLE} && git bundle create -q {_BUNDLE} origin/main..HEAD")
    if rc != 0:
        raise SubmitError("labor_submit_git_failed")
    dest = Path(workdir) / "labor.bundle"
    try:
        rc, _, _ = await incus.run("file", "pull", f"{container.NAME}{_BUNDLE}", str(dest), timeout=300)
    finally:
        await incus.run("exec", container.NAME, "--", "rm", "-f", _BUNDLE)
    if rc != 0 or not dest.exists():
        raise SubmitError("labor_submit_git_failed")
    if dest.stat().st_size > MAX_BUNDLE:
        dest.unlink()
        raise SubmitError("labor_submit_too_big")
    with dest.open("rb") as fh:
        head = fh.read(16)
    if head not in _HEADS:
        dest.unlink()
        raise SubmitError("labor_submit_bundle_invalid")
    return dest
