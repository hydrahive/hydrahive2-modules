"""Zeitmaschine: Version je Zug, Änderungsansicht, „Zurück zu hier“, „Nur diese Änderung zurück“ (PLAN-V1.md Baustein 5).

Git läuft IM Container als Nutzer `labor`, aufgerufen als feste Argumentliste (`incus exec … -- git …`), nie durch
eine Shell. Das Modul committet, nicht der Agent: Der könnte es vergessen oder den Verlauf umschreiben. Vor jedem Aufruf
gilt eine feste Konfiguration (`-c`): keine Hooks, keine Signatur, Autor `Vibe`. Was der Agent in `.git/config` oder
`.git/hooks` einträgt, bleibt wirkungslos, weil `-c` Vorrang hat und `core.hooksPath` auf /dev/null zeigt.
"""
from __future__ import annotations

from . import container, incus
from .version_text import (MAX_FILE_BYTES, MAX_SUMMARY, MAX_VIEW_CHARS, VersionError, check_path, check_sha,  # noqa: F401
                           files_text, status_word, summary_from)

UID = "1000"
_FIELD = "\x1f"
_GIT = ["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false", "-c", "core.fsmonitor=false",
        "-c", "user.name=Vibe", "-c", "user.email=vibe@localhost", "-c", "core.quotepath=off",
        "-c", "advice.detachedHead=false"]
_EXCLUDE = (":(exclude,glob)**/node_modules/**", ":(exclude,glob)**/dist/**", ":(exclude,glob)**/.git/**")
_NESTED = ["find", ".", "-mindepth", "2", "-name", ".git", "-not", "-path", "./.git/*", "-not", "-path",
           "*/node_modules/*", "-print0"]
_BIG = ["find", ".", "-path", "./.git", "-prune", "-o", "-path", "*/node_modules", "-prune", "-o", "-path", "*/dist",
        "-prune", "-o", "-type", "f", "-size", f"+{MAX_FILE_BYTES // 1024}k", "-print0"]


async def _run(argv: list[str], *, timeout: float = 60.0, stdin: bytes | None = None, project_id: str = "") -> tuple[int, str, str]:
    """Befehl als Nutzer labor in /work des Containers dieses Projekts."""
    name = container.name_for(project_id)
    args = ["exec", name, "--cwd", "/work", "--user", UID, "--group", UID, "--env", "HOME=/home/labor",
            "--env", "LC_ALL=C.UTF-8", "--env", "GIT_TERMINAL_PROMPT=0", "--", *argv]
    return await incus.run(*args, timeout=timeout, input_bytes=stdin)


async def _git(pid: str, *args: str, stdin: bytes | None = None, timeout: float = 60.0) -> tuple[int, str, str]:
    return await _call([*_GIT, *args], pid, stdin, timeout)


async def _call(argv: list[str], pid: str, stdin: bytes | None = None, timeout: float = 60.0) -> tuple[int, str, str]:
    try:
        return await _run(argv, timeout=timeout, stdin=stdin, project_id=pid)
    except TypeError:                                  # Test-Brücke kennt project_id nicht
        return await _run(argv, timeout=timeout, stdin=stdin)


def _row(line: str) -> dict:
    sha, subject, when = (line.split(_FIELD) + ["", ""])[:3]
    kind = "start" if subject == "Start" else "restore" if subject.startswith("Zurück zu ") else \
        "revert" if subject.startswith("Rückgängig: ") else "turn"
    return {"commit_id": sha, "summary": subject, "kind": kind, "created_at": when}


async def _nested_repos(pid: str) -> list[str]:
    """Ordner mit eigenem .git (Projekt-Agent hat etwas geklont). Git würde sie als Gitlink einbetten oder, ohne
    Commit darin, den ganzen Zug abbrechen. Sie werden vor dem Aufnehmen gefunden und ausgenommen."""
    rc, out, _ = await _call(_NESTED, pid)
    if rc != 0:
        return []
    dirs = []
    for g in out.split("\0"):
        d = g[2:] if g.startswith("./") else g
        if d.endswith("/.git"):
            dirs.append(d[:-5])
    return dirs


async def _stage(pid: str) -> None:
    """Alles aufnehmen außer node_modules/dist/.git und verschachtelten Repos (auch wenn der Agent .gitignore leert),
    dann zu große Dateien wieder herausnehmen."""
    nested = [f":(exclude,literal){d}" for d in await _nested_repos(pid)]
    rc, _, _ = await _git(pid, "add", "-A", "--", ".", *_EXCLUDE, *nested)
    if rc != 0:
        raise VersionError("vibe_git_failed")
    rc, big, _ = await _call(_BIG, pid)
    if rc == 0 and big:
        await _git(pid, "reset", "-q", "--pathspec-from-file=-", "--pathspec-file-nul", "--", stdin=big.encode())
    rc, links, _ = await _git(pid, "ls-files", "--stage", "-z")
    gitlinks = [e.split("\t", 1)[1] for e in links.split("\0") if e.startswith("160000 ") and "\t" in e]
    if gitlinks:                                       # Altlast: früher schon eingebettet
        await _git(pid, "rm", "-q", "--cached", "-f", "--", *gitlinks)


async def commit_turn(pid: str, summary: str, *, kind: str = "turn") -> dict | None:
    """Speichert den Stand als neue Version. Keine Änderung (auch nicht nach Abzug der Ausnahmen) → None."""
    rc, _, _ = await _git(pid, "rev-parse", "--git-dir")
    if rc != 0:
        rc, _, _ = await _git(pid, "init", "-q", "-b", "main")
        if rc != 0:
            raise VersionError("vibe_git_failed")
    await _stage(pid)
    first = (await _git(pid, "rev-parse", "-q", "--verify", "HEAD"))[0] != 0
    rc, _, _ = await _git(pid, "diff", "--cached", "--quiet")
    if rc == 0 and not first:
        return None
    text = summary_from(summary)
    rc, _, _ = await _git(pid, "commit", "-q", "--no-verify", "--allow-empty-message",
                          *(["--allow-empty"] if first else []), "-m", text)      # Startversion auch im leeren Ordner
    if rc != 0:
        raise VersionError("vibe_git_failed")
    return (await history(pid, limit=1))[0] | {"kind": kind}


async def history(pid: str, limit: int = 200) -> list[dict]:
    rc, out, _ = await _git(pid, "log", f"--max-count={int(limit)}", f"--format=%H{_FIELD}%s{_FIELD}%cI")
    rows = [_row(ln) for ln in out.splitlines() if ln.strip()] if rc == 0 else []
    done: list[dict] = []
    for r in reversed(rows):                            # alt → neu: ein „Zurück“ auf ein „Zurück“ findet den Titel schon vor
        done.append(_plain(r, done))
    return list(reversed(done))


def _plain(row: dict, older: list[dict]) -> dict:
    """„Zurück zu 366d3c8“ → „Zurück zu: <Titel jener Version>“ (kein Hash in der Anzeige). `older` sind die älteren,
    schon aufbereiteten Versionen. Ist die Zielversion nicht mehr da, bleibt der Text, wie er ist."""
    prefix = {"restore": "Zurück zu ", "revert": "Rückgängig: "}.get(row["kind"])
    if prefix is None:
        return row
    target = next((r for r in older if r["commit_id"].startswith(row["summary"][len(prefix):].strip())), None)
    if target is None or not target["summary"]:
        return row
    name = target["summary"]
    for p in ("Zurück zu: ", "Rückgängig: "):          # nicht „Zurück zu: Zurück zu: …“ stapeln
        if name.startswith(p):
            name = name[len(p):]
    return {**row, "summary": f"{prefix.rstrip(' :')}: {name}"}


async def _exists(pid: str, sha: str) -> None:
    rc, _, _ = await _git(pid, "cat-file", "-e", f"{check_sha(sha)}^{{commit}}")
    if rc != 0:
        raise VersionError("vibe_version_not_found")


async def changes(pid: str, sha: str) -> dict:
    """Dateiliste einer Version in Klartext (kein Git-Wort)."""
    await _exists(pid, sha)
    rc, out, _ = await _git(pid, "diff-tree", "--no-commit-id", "--name-status", "-r", "-z", "--root", sha)
    parts = [p for p in out.split("\0") if p]
    files, i = [], 0
    while i < len(parts):
        code = parts[i]
        n = 2 if code[:1] in "RC" else 1
        files.append({"path": parts[i + n], "status": status_word(code)})
        i += 1 + n
    return {"text": files_text(len(files)), "files": files}


async def _blob(pid: str, rev: str, path: str) -> tuple[str, bool]:
    rc, out, _ = await _git(pid, "show", f"{rev}:{path}")
    return (out, False) if rc == 0 else ("", False)


async def file_diff(pid: str, sha: str, path: str) -> dict:
    """Vorher/Nachher einer Datei in dieser Version. Binär: ohne Inhalt. Zu lang: gekürzt."""
    check_path(path)
    await _exists(pid, sha)
    rc, num, _ = await _git(pid, "diff-tree", "--no-commit-id", "--numstat", "-r", "--root", sha, "--", path)
    binary = rc == 0 and num.startswith("-\t-\t")
    if binary:
        return {"before": "", "after": "", "binary": True, "truncated": False}
    before, _ = await _blob(pid, f"{sha}~1", path)
    after, _ = await _blob(pid, sha, path)
    cut = len(before) > MAX_VIEW_CHARS or len(after) > MAX_VIEW_CHARS
    return {"before": before[:MAX_VIEW_CHARS], "after": after[:MAX_VIEW_CHARS], "binary": False, "truncated": cut}


async def restore(pid: str, sha: str) -> dict | None:
    """„Zurück zu hier“: Stand der gewählten Version als NEUE Version. Nichts geht verloren."""
    await _exists(pid, sha)
    rc, _, _ = await _git(pid, "read-tree", "--reset", "-u", sha)
    if rc != 0:
        raise VersionError("vibe_git_failed")
    rc, _, _ = await _git(pid, "diff", "--cached", "--quiet")
    if rc == 0:
        return None
    rc, _, _ = await _git(pid, "commit", "-q", "--no-verify", "-m", f"Zurück zu {sha[:7]}")
    if rc != 0:
        raise VersionError("vibe_git_failed")
    return (await history(pid, limit=1))[0] | {"kind": "restore"}


async def revert(pid: str, sha: str) -> dict:
    """„Nur diese Änderung zurück“. Konflikt → abgebrochen, /work unverändert."""
    await _exists(pid, sha)
    rows = await history(pid, limit=100000)
    if rows and rows[-1]["commit_id"] == sha:
        raise VersionError("vibe_revert_start")
    rc, _, _ = await _git(pid, "revert", "--no-commit", sha)
    if rc != 0:
        await _git(pid, "revert", "--abort")
        await _git(pid, "reset", "-q", "--hard", "HEAD")
        return {"ok": False, "code": "vibe_revert_conflict", "version": None}
    rc, _, _ = await _git(pid, "diff", "--cached", "--quiet")
    if rc == 0:
        await _git(pid, "revert", "--abort")
        await _git(pid, "reset", "-q", "--hard", "HEAD")
        return {"ok": False, "code": "vibe_revert_nothing", "version": None}
    rc, _, _ = await _git(pid, "commit", "-q", "--no-verify", "-m", f"Rückgängig: {sha[:7]}")
    if rc != 0:
        raise VersionError("vibe_git_failed")
    return {"ok": True, "version": (await history(pid, limit=1))[0] | {"kind": "revert"}}
