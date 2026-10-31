"""Mix-Regeln. Platzhalter."""
from __future__ import annotations

DEFAULT_EXCLUDE: dict = {}


class RuleError(ValueError):
    pass


def where(rule, *, exclude, allow_long):
    raise NotImplementedError


def validate(rule):
    raise NotImplementedError


def matches_default_exclude(genre):
    raise NotImplementedError
