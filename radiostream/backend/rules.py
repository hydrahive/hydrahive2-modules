"""Mix-Regeln (PLAN-PROGRAMM.md „Mixe“) → SQL-Bedingung über `module_radiostream_tracks t`.

- Genres stehen oft zu mehreren in einem Feld („Pop;Rock“, „Pop; Rock“). Verglichen wird je einzelnes Genre, ohne
  Groß-/Kleinschreibung: das Feld wird zu „;pop;rock;“ normalisiert und auf „;rock;“ geprüft – „Rock“ trifft so nicht
  „Rockabilly“ oder „Hard Rock“.
- Interpret trifft Interpret oder Album-Interpret. Ordner = oberster Ordner der Freigabe (ganzer Name).
- Bedingungen gleicher Art sind ODER, verschiedene Arten UND. Ausschließen gilt immer.
- Lange Titel (> 15 min, z. B. Hörbücher) nur mit allow_long. Unbekannte Dauer gilt nicht als lang.
Werte gehen nur als Parameter in die Abfrage, nie als Text.
"""
from __future__ import annotations

LONG_S = 900
DECADES = range(1900, 2100, 10)
LIST_KEYS = ("genres", "artists", "folders", "exclude_genres", "exclude_artists", "exclude_folders")
KEYS = (*LIST_KEYS, "decades", "year_from", "year_to")
MAX_ITEMS = 100
MAX_LEN = 200
# Voreinstellung „Ausgeschlossen von Alles“. Hörbücher heißen in echten Bibliotheken sehr unterschiedlich (gemessen .2,
# 31.10.: „Kids; Audiobooks“, „Hoerbuch“, „Speech“, „Audio Drama“, „Spoken Word“ …) – daher Wortteile, dazu ganze
# Genres. „Non-Music“ und leer sind NICHT dabei: darunter auch echte Musik (Filmmusik, Konzerte). Ordner schlägt die
# Oberfläche aus der Bibliothek vor (folder_suggestions), sie stehen nicht fest im Code.
DEFAULT_EXCLUDE = {"genres": ["Speech", "Audio Drama", "Kids"],
                   "genre_parts": ["audiobook", "hörbuch", "hoerbuch", "hörspiel", "hoerspiel", "spoken"],
                   "folders": []}
_GENRES = "(';' || replace(replace(lower(t.genre), '; ', ';'), ' ;', ';') || ';')"


class RuleError(ValueError):
    def __init__(self, code: str = "radiostream_rule_invalid") -> None:
        super().__init__(code)
        self.code = code


def _clean_list(v) -> list[str]:
    if not isinstance(v, list) or len(v) > MAX_ITEMS:
        raise RuleError()
    out: list[str] = []
    seen: set[str] = set()
    for x in v:
        if not isinstance(x, str) or len(x) > MAX_LEN:
            raise RuleError()
        x = x.strip()
        if not x:
            raise RuleError()
        if x.lower() not in seen:
            seen.add(x.lower())
            out.append(x)
    return out


def validate(rule: dict) -> dict:
    """Regel prüfen und bereinigen (Leerzeichen, doppelte Einträge). Unbekannte Schlüssel → Fehler."""
    if not isinstance(rule, dict) or any(k not in KEYS for k in rule):
        raise RuleError()
    out: dict = {}
    for k in LIST_KEYS:
        if k in rule:
            out[k] = _clean_list(rule[k])
            if k.endswith("folders") and any("/" in f for f in out[k]):
                raise RuleError()
    if "decades" in rule:
        d = rule["decades"]
        if not isinstance(d, list) or any(not isinstance(x, int) or isinstance(x, bool) or x not in DECADES for x in d):
            raise RuleError()
        out["decades"] = sorted(set(d))
    for k in ("year_from", "year_to"):
        if k in rule and rule[k] is not None:
            if not isinstance(rule[k], int) or isinstance(rule[k], bool) or not 1000 <= rule[k] <= 2100:
                raise RuleError()
            out[k] = rule[k]
    return out


def _like_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _genre_any(genres: list[str], args: list) -> str:
    args.extend(f";{g.lower()};" for g in genres)
    return "(" + " OR ".join(f"instr({_GENRES}, ?) > 0" for _ in genres) + ")"


def _artist_any(artists: list[str], args: list) -> str:
    parts = []
    for a in artists:
        parts.append("(lower(t.artist) = ? OR lower(t.album_artist) = ?)")
        args.extend([a.lower(), a.lower()])
    return "(" + " OR ".join(parts) + ")"


def _folder_any(folders: list[str], args: list) -> str:
    args.extend(f"{_like_escape(f)}/%" for f in folders)
    return "(" + " OR ".join("t.rel_path LIKE ? ESCAPE '\\'" for _ in folders) + ")"


def where(rule: dict, *, exclude: dict, allow_long: bool) -> tuple[str, list]:
    """(Bedingung, Parameter) für `... FROM module_radiostream_tracks t WHERE <Bedingung>`."""
    args: list = []
    parts = ["t.state = 'ok'"]
    if not allow_long:
        parts.append(f"(t.duration_s IS NULL OR t.duration_s <= {LONG_S})")
    if rule.get("genres"):
        parts.append(_genre_any(rule["genres"], args))
    if rule.get("artists"):
        parts.append(_artist_any(rule["artists"], args))
    if rule.get("folders"):
        parts.append(_folder_any(rule["folders"], args))
    if rule.get("decades"):
        parts.append("(" + " OR ".join("(t.year >= ? AND t.year <= ?)" for _ in rule["decades"]) + ")")
        for d in rule["decades"]:
            args.extend([d, d + 9])
    if rule.get("year_from") is not None:
        parts.append("t.year >= ?")
        args.append(rule["year_from"])
    if rule.get("year_to") is not None:
        parts.append("t.year <= ?")
        args.append(rule["year_to"])
    ex_genres = [*rule.get("exclude_genres", []), *exclude.get("genres", [])]
    if ex_genres:
        parts.append("NOT " + _genre_any(ex_genres, args))
    parts_ex = exclude.get("genre_parts", [])
    if parts_ex:
        parts.append("NOT (" + " OR ".join("instr(lower(t.genre), ?) > 0" for _ in parts_ex) + ")")
        args.extend(p.lower() for p in parts_ex)
    if rule.get("exclude_artists"):
        parts.append("NOT " + _artist_any(rule["exclude_artists"], args))
    ex_folders = [*rule.get("exclude_folders", []), *exclude.get("folders", [])]
    if ex_folders:
        parts.append("NOT " + _folder_any(ex_folders, args))
    return " AND ".join(parts), args


def matches_default_exclude(genre: str) -> bool:
    g = (genre or "").lower()
    return any(p in g for p in DEFAULT_EXCLUDE["genre_parts"])
