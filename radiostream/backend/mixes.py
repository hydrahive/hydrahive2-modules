"""Mixe und „Ausgeschlossen von Alles“ (PLAN-PROGRAMM.md „Mixe“, „Hörbücher raus“). Regeln: rules.py."""
from __future__ import annotations

import json

from hydrahive.db.connection import db

from . import rules
from .program_base import ProgramError, clean_name, new_id, now

_T = "module_radiostream_mixes"
EX_KEYS = ("genres", "genre_parts", "folders")
SUGGEST_MIN = 20          # Titel je Ordner
SUGGEST_SHARE = 30        # % Titel mit Hörbuch-Genre


def _row(r) -> dict:
    return {**dict(r), "rules": json.loads(r["rules"] or "{}"), "allow_long": bool(r["allow_long"])}


def _checked(rule: dict) -> dict:
    try:
        return rules.validate(rule)
    except rules.RuleError as e:
        raise ProgramError(e.code) from None


def mixes() -> list[dict]:
    with db() as conn:
        rows = conn.execute(f"SELECT * FROM {_T} ORDER BY lower(name), id").fetchall()
    return [_row(r) for r in rows]


def mix(mid: str) -> dict | None:
    with db() as conn:
        r = conn.execute(f"SELECT * FROM {_T} WHERE id = ?", (mid,)).fetchone()
    return _row(r) if r else None


def save_mix(mid: str | None, *, name: str, rules_: dict, allow_long: bool, user: str) -> dict:
    name, rule = clean_name(name), _checked(rules_)
    with db() as conn:
        if mid is None:
            mid = new_id()
            conn.execute(f"INSERT INTO {_T} (id, name, rules, allow_long, created_by, created_at, updated_at) "
                         "VALUES (?, ?, ?, ?, ?, ?, ?)", (mid, name, json.dumps(rule), int(allow_long), user, now(),
                                                         now()))
        elif conn.execute(f"UPDATE {_T} SET name = ?, rules = ?, allow_long = ?, updated_at = ? WHERE id = ?",
                          (name, json.dumps(rule), int(allow_long), now(), mid)).rowcount == 0:
            raise ProgramError("radiostream_mix_not_found")
        conn.commit()
    return mix(mid)  # type: ignore[return-value]


def delete_mix(mid: str) -> None:
    from .program import reset_if_points_to
    with db() as conn:
        conn.execute(f"DELETE FROM {_T} WHERE id = ?", (mid,))
        conn.commit()
    reset_if_points_to("mix", mid)


def preview(rule: dict, *, allow_long: bool) -> dict:
    """Wie viele Titel hätte der Mix, dazu 5 zufällige Beispiele (Ausschluss von „Alles“ gilt für Mixe nicht)."""
    where, args = rules.where(_checked(rule), exclude={}, allow_long=allow_long)
    with db() as conn:
        n = conn.execute(f"SELECT COUNT(*) FROM module_radiostream_tracks t WHERE {where}", args).fetchone()[0]
        ex = conn.execute(f"SELECT t.track_id, t.artist, t.title, t.year, t.genre FROM module_radiostream_tracks t "
                          f"WHERE {where} ORDER BY random() LIMIT 5", args).fetchall()
    return {"count": n, "examples": [dict(r) for r in ex]}


def get_exclude() -> dict:
    with db() as conn:
        r = conn.execute("SELECT exclude_rules, allow_long FROM module_radiostream_station WHERE id = 1").fetchone()
    raw = r["exclude_rules"] if r else None
    return {"rules": json.loads(raw) if raw else dict(rules.DEFAULT_EXCLUDE), "allow_long": bool(r and r["allow_long"])}


def save_exclude(ex: dict, *, allow_long: bool, user: str) -> dict:
    if not isinstance(ex, dict) or any(k not in EX_KEYS for k in ex):
        raise ProgramError("radiostream_rule_invalid")
    clean = {k: _checked({"genres" if k == "genre_parts" else k: ex.get(k, [])}).get(
        "genres" if k == "genre_parts" else k, []) for k in EX_KEYS}
    from . import station
    station.save(user=user)                                     # Zeile anlegen, falls es sie noch nicht gibt
    with db() as conn:
        conn.execute("UPDATE module_radiostream_station SET exclude_rules = ?, allow_long = ? WHERE id = 1",
                     (json.dumps(clean), int(allow_long)))
        conn.commit()
    return get_exclude()


def folder_suggestions() -> list[dict]:
    """Ordner, deren Titel überwiegend Hörbuch-Genres haben – zum Ankreuzen in „Ausgeschlossen von Alles“."""
    parts = rules.DEFAULT_EXCLUDE["genre_parts"]
    whole = [g.lower() for g in rules.DEFAULT_EXCLUDE["genres"]]
    cond = " OR ".join(["instr(lower(genre), ?) > 0"] * len(parts) + ["lower(genre) = ?"] * len(whole))
    with db() as conn:
        rows = conn.execute(
            f"SELECT substr(rel_path, 1, instr(rel_path, '/') - 1) AS folder, COUNT(*) AS n, SUM({cond}) AS hit "
            "FROM module_radiostream_tracks WHERE state = 'ok' AND instr(rel_path, '/') > 0 GROUP BY folder "
            "HAVING n >= ? AND 100.0 * hit / n >= ? ORDER BY n DESC, folder", [*parts, *whole, SUGGEST_MIN,
                                                                               SUGGEST_SHARE]).fetchall()
    return [{"folder": r["folder"], "count": r["n"], "share": round(100 * r["hit"] / r["n"])} for r in rows]
