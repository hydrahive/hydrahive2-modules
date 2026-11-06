"""Reine Hilfen der Zeitmaschine: Kurztext, Klartext, Prüfungen von Version und Pfad (kein Git, kein incus)."""
from __future__ import annotations

import re

MAX_SUMMARY = 100
MAX_VIEW_CHARS = 100_000
MAX_FILE_BYTES = 2 * 1024 * 1024
_SHA = re.compile(r"^[0-9a-f]{40}$")
_CTRL = re.compile(r"\x1b\[[0-9;]*[A-Za-z]|[\x00-\x08\x0b-\x1f\x7f]")      # erst Farbfolgen, dann einzelne Zeichen
_LEAD = re.compile(r"^(?:[#>*\-+]+\s+|\*\*|__)")


class VersionError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def summary_from(text: str) -> str:
    """Erste nicht leere Zeile der Antwort, ohne Markdown-Zierde und Steuerzeichen, höchstens 100 Zeichen.
    Kein Modellaufruf: der Text kommt aus der Antwort selbst."""
    for line in _CTRL.sub("", str(text or "").replace("\t", " ").replace("\r", " ")).split("\n"):
        line = _LEAD.sub("", line.strip()).strip().strip("*_").strip()
        if line:
            return line if len(line) <= MAX_SUMMARY else line[:MAX_SUMMARY - 1] + "…"
    return "Änderung"


def check_sha(value: str) -> str:
    """Nur echte, volle Commit-Kennungen (40 Hex-Zeichen). Nie ein Name wie HEAD/main oder eine Option."""
    if not isinstance(value, str) or not _SHA.fullmatch(value):
        raise VersionError("vibe_version_invalid")
    return value


def check_path(value: str) -> str:
    """Relativer Pfad ohne Tricks. Beginnt nie mit `-`, enthält nie `..`, Zeilenumbruch oder NUL."""
    ok = (isinstance(value, str) and value and not value.startswith(("/", "-")) and len(value) <= 400
          and not any(c in value for c in "\n\r\x00") and ".." not in value.split("/"))
    if not ok:
        raise VersionError("vibe_path_invalid")
    return value


def files_text(count: int) -> str:
    return "1 Datei geändert" if count == 1 else f"{count} Dateien geändert"


_STATUS = {"A": "neu", "M": "geändert", "D": "gelöscht", "R": "geändert", "T": "geändert", "C": "neu"}


def status_word(code: str) -> str:
    return _STATUS.get(code[:1], "geändert")
