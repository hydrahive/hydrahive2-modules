"""Zusammenbau der Statuszentrale (S2): ruft die Quellen, schwärzt jeden Text, hält ein festes Schema und einen
Zwischenspeicher (lokal 5 s, GitHub 60 s). Fehlt/scheitert eine Quelle → Bereich None, der Rest bleibt.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable

log = logging.getLogger(__name__)
AREAS = ("message", "hydra", "tasks", "machine", "mining", "github")
TTL = {"github": 60.0}
TTL_DEFAULT = 5.0


def _project_token(ref: str) -> str | None:
    from hydrahive.projects import config as project_config

    from . import dash_github
    p = dash_github.find_project(ref, project_config.list_all())
    return dash_github.token_of(p) if p else None


def github_source(cfg: dict) -> Callable[[], dict]:
    def fn() -> dict:
        from . import dash_github
        token = _project_token(cfg.get("github_project") or "")
        out = dash_github.open_prs(list(cfg.get("github_repos") or []), token)
        return {"__secret__": token, **out} if token else out
    return fn


def default_sources(data_dir, cfg: dict) -> dict[str, Callable[[], Any]]:
    from . import dash_sources as ds
    return {"message": lambda: ds.message(data_dir), "hydra": ds.hydra,
            "tasks": lambda: ds.tasks(cfg.get("tasks_user") or "till"), "machine": ds.machine,
            "mining": ds.mining, "github": github_source(cfg)}


def _hh_secrets(user: str) -> Callable[[], set[str]]:
    def fn() -> set[str]:
        from hydrahive.credentials.redaction import egress_secrets
        return egress_secrets(user, None)
    return fn


def _hh_redact(s: str) -> str:
    from hydrahive.credentials.redaction import redact_detected
    return redact_detected(s)


def _clean(value: Any, secrets: list[str], redact: Callable[[str], str]) -> Any:
    if isinstance(value, str):
        for s in secrets:
            value = value.replace(s, "[REDACTED]")
        return redact(value)
    if isinstance(value, dict):
        return {k: _clean(v, secrets, redact) for k, v in value.items()}
    if isinstance(value, list):
        return [_clean(v, secrets, redact) for v in value]
    return value


class Builder:
    def __init__(self, sources: dict[str, Callable[[], Any]], *, secrets: Callable[[], set[str]] | None = None,
                 redact: Callable[[str], str] | None = None, clock: Callable[[], float] = time.monotonic):
        self._sources, self._clock = sources, clock
        self._secrets = secrets or (lambda: set())
        self._redact = redact or _hh_redact
        self._cache: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def _area(self, name: str, now: float, extra: set[str]) -> Any:
        hit = self._cache.get(name)
        if hit and now - hit[0] < TTL.get(name, TTL_DEFAULT):
            return hit[1]
        try:
            raw = self._sources[name]() if name in self._sources else None
        except Exception as e:  # noqa: BLE001 – eine Quelle darf die Seite nie umwerfen
            log.warning("Statuszentrale: Bereich %s fehlgeschlagen (%s)", name, type(e).__name__)
            raw = None
        if isinstance(raw, dict) and "__secret__" in raw:
            raw = dict(raw)
            tok = raw.pop("__secret__")
            if tok:
                extra.add(tok)
        val = _clean(raw, sorted({s for s in self._secrets() | extra if s and len(s) >= 6}, key=len, reverse=True),
                     self._redact)
        self._cache[name] = (now, val)
        return val

    def get(self) -> dict:
        with self._lock:
            now, extra = self._clock(), set()
            out = {name: self._area(name, now, extra) for name in AREAS}
        out["updated"] = time.strftime("%H:%M:%S")
        return out


_builders: dict[tuple, Builder] = {}


def build(data_dir, cfg: dict) -> dict:
    key = (str(data_dir), cfg.get("tasks_user"), cfg.get("github_project"), tuple(cfg.get("github_repos") or ()))
    b = _builders.get(key)
    if b is None:
        _builders.clear()
        b = _builders[key] = Builder(default_sources(data_dir, cfg), secrets=_hh_secrets(cfg.get("tasks_user") or "till"))
    return b.get()
