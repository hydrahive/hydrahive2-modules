#!/usr/bin/env python3
"""Hilfe-Guard (Modul-Repo): eine nutzersichtbare Modul-Änderung bringt die Hilfe DESSELBEN Moduls mit
(docs/specs/hilfe-guard.md im Kern-Repo, §2 und §5).

Eigene Kopie des Kern-Skripts scripts/check_help_updated.py mit Modul-Mustern: die Repos bauen getrennt, eine
gemeinsame Datei gibt es nicht. Meldungstext und Ausnahme-Logik sind absichtlich gleich.

Aufruf in CI:  python3 scripts/check_help_updated.py <base-sha> <head-sha>
Die PR-Beschreibung kommt NUR über die Umgebungsvariable PR_BODY, nie über die Kommandozeile – Schutz vor
Script-Injection über PR-Texte. Modus über HILFE_GUARD_MODE: warn (Default) | block.
Das Skript liest nur Git-Daten und schreibt nur nach stdout (und in die Step-Summary). Nur stdlib.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field

# Nutzersichtbar (Spec §2, Module). Tests (*.test.*, tests/, __tests__/) zählen nicht – siehe _TEST.
_MOD = r"([A-Za-z0-9_.-]+)"
_VISIBLE = (
    re.compile(rf"^{_MOD}/frontend/.+\.tsx$"),
    # Deutsche Texte, so wie sie im Repo liegen: i18n.ts, i18n_<teil>.ts, <name>I18n.ts, texts.de.ts, texts.<teil>.de.ts
    # (nicht *.en.ts, z. B. i18n.add.en.ts). Das frühere Muster frontend/i18n/de* traf keine Datei (Review #478).
    re.compile(rf"^{_MOD}/frontend/(?:.+/)?(?![^/]*\.en\.ts$)[^/]*(?:i18n|I18n)[^/]*\.ts$"),   # auch seatsI18n.ts
    re.compile(rf"^{_MOD}/frontend/(?:.+/)?texts(?:\.[^/]+)?\.de\.ts$"),                     # auch texts.ghost.de.ts
)
_MANIFEST = re.compile(rf"^{_MOD}/manifest\.json$")
_TEST = re.compile(r"(^|/)((tests?|__tests__)/.+|[^/]+\.(test|spec)\.[^/]+)$")
_HELP_FILE = re.compile(rf"^{_MOD}/frontend/help/de/[^/]+\.md$")
# Manifest zählt nur, wenn sich ein in der Oberfläche sichtbares Feld ändert (Spec §2). routes/nav/settings gibt es
# im Manifest nicht (core modules/manifest.py) – Review #478.
_MANIFEST_UI_KEYS = ("name", "description", "icon", "nav_group", "vault", "agent_areas")
# Eigene Zeile; [ \t] statt \s, damit der Grund nicht aus der Folgezeile geholt wird.
_EXEMPTION = re.compile(r"^[ \t]*Keine Hilfe nötig:[ \t]*(.*?)[ \t]*$", re.IGNORECASE | re.MULTILINE)
_PLACEHOLDER = "<Begründung>"      # Platzhalter aus der Fehlermeldung zählt nicht als Begründung
_MIN_REASON = 10
_SHOWN = 5


@dataclass
class Result:
    modules: dict[str, list[str]] = field(default_factory=dict)    # Modul → nutzersichtbar geänderte Dateien
    helps: dict[str, list[str]] = field(default_factory=dict)      # Modul → geänderte Hilfe-Dateien
    exemption: str | None = None

    @property
    def missing(self) -> list[str]:
        """Module mit nutzersichtbarer Änderung, aber ohne Hilfe-Datei des eigenen Moduls."""
        return sorted(m for m in self.modules if not self.helps.get(m))

    @property
    def violation(self) -> bool:
        return bool(self.missing) and self.exemption is None

    @property
    def ok(self) -> bool:
        return not self.violation


def _exemption(body: str | None) -> str | None:
    # \r entfernen: Im Browser bearbeitete PR-Texte haben \r\n, sonst zählt das \r zur Begründung (Review Kern #801).
    for match in _EXEMPTION.finditer((body or "").replace("\r", "")):
        reason = match.group(1)
        if len(reason) >= _MIN_REASON and reason != _PLACEHOLDER:
            return reason
    return None


def _visible_module(path: str, ui_manifests: set[str]) -> str | None:
    if _TEST.search(path):
        return None
    for pattern in _VISIBLE:
        match = pattern.match(path)
        if match:
            return match.group(1)
    match = _MANIFEST.match(path)
    if match and match.group(1) in ui_manifests:
        return match.group(1)
    return None


def manifest_ui_changed(base_text: str | None, head_text: str | None) -> bool:
    """True, wenn sich ein sichtbares Manifest-Feld (_MANIFEST_UI_KEYS) ändert. Neues Modul: base fehlt (= keine Felder).
    Gelöschtes oder unlesbares Manifest löst nichts aus."""
    if head_text is None:
        return False
    try:
        head = json.loads(head_text)
        base = json.loads(base_text) if base_text is not None else {}
    except ValueError:
        return False
    if not isinstance(head, dict):
        return False
    if not isinstance(base, dict):
        base = {}
    return any(base.get(key) != head.get(key) for key in _MANIFEST_UI_KEYS)


def evaluate(files: list[str], *, body: str | None, ui_manifests: set[str] | None = None) -> Result:
    ui = ui_manifests or set()
    modules: dict[str, list[str]] = {}
    helps: dict[str, list[str]] = {}
    for path in sorted(files):
        module = _visible_module(path, ui)
        if module:
            modules.setdefault(module, []).append(path)
        help_match = _HELP_FILE.match(path)
        if help_match:
            helps.setdefault(help_match.group(1), []).append(path)
    return Result(modules=modules, helps=helps, exemption=_exemption(body))


def _help_article(module: str) -> str:
    return f"{module}/frontend/help/de/{module}.md"


def _shown(paths: list[str]) -> str:
    return ", ".join(paths[:_SHOWN]) + (" …" if len(paths) > _SHOWN else "")


def message(result: Result) -> str:
    if not result.modules:
        return "Keine nutzersichtbare Änderung – Regel greift nicht."
    missing = result.missing
    if not missing:
        count = sum(len(result.helps[m]) for m in result.modules)
        return f"Hilfe geändert: {count} Hilfe-Datei(en) zur nutzersichtbaren Änderung."
    if result.exemption:
        return f"Nutzersichtbar ohne Hilfe, begründet: {result.exemption}"
    if len(missing) == 1:
        files = result.modules[missing[0]]
        head = f"Hilfe fehlt: {len(files)} nutzersichtbare Datei(en) geändert ({_shown(files)}), keine Hilfe-Datei.\n"
    else:
        lines = [f"Hilfe fehlt: {len(missing)} Module ohne Hilfe-Datei ({', '.join(missing)})."]
        lines += [f"  {m}: {len(result.modules[m])} nutzersichtbare Datei(en) geändert ({_shown(result.modules[m])})"
                  for m in missing]
        head = "\n".join(lines) + "\n"
    target = " und ".join(_help_article(m) for m in missing)
    return (
        head
        + "WARUM: Wiki und PDF-Handbuch entstehen aus den Hilfe-Artikeln – ohne Artikel-Änderung bleibt das Handbuch alt\n"
        "       (Regel docs/specs/hilfe-guard.md).\n"
        f"BEHEBEN: {target} ergänzen\n"
        "         oder in die PR-Beschreibung schreiben: „Keine Hilfe nötig: <Begründung>“."
    )


def exit_code(result: Result, mode: str) -> int:
    return 1 if result.violation and (mode or "").strip().lower() == "block" else 0


def _git(*args: str) -> str:
    return subprocess.run(["git", "-c", "core.quotepath=off", *args], check=True, capture_output=True, text=True,
                          encoding="utf-8").stdout


def _show(ref: str, path: str) -> str | None:
    try:
        return _git("show", f"{ref}:{path}")
    except subprocess.CalledProcessError:
        return None     # Datei existiert an dieser Stelle nicht (neues oder gelöschtes Modul)


def _ui_manifests(files: list[str], base: str, head: str) -> set[str]:
    manifests = [(f, m.group(1)) for f in files if (m := _MANIFEST.match(f))]
    if not manifests:
        return set()
    merge_base = _git("merge-base", base, head).strip()     # wie `base...head` im Diff
    return {module for path, module in manifests
            if manifest_ui_changed(_show(merge_base, path), _show(head, path))}


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        sys.stdout.write("Aufruf: check_help_updated.py <base-sha> <head-sha>\n")
        return 2
    base, head = argv[1], argv[2]
    files = [f for f in _git("diff", "--name-only", f"{base}...{head}").splitlines() if f.strip()]
    result = evaluate(files, body=os.environ.get("PR_BODY", ""), ui_manifests=_ui_manifests(files, base, head))
    mode = os.environ.get("HILFE_GUARD_MODE", "warn")
    text = message(result)
    if result.violation:
        first, _, rest = text.partition("\n")
        level = "error" if exit_code(result, mode) else "warning"
        sys.stdout.write(f"::{level} title=Hilfe-Guard::{first}\n")
        sys.stdout.write(rest + "\n")
    else:
        sys.stdout.write(text + "\n")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(f"### Hilfe-Guard ({mode})\n\n```\n{text}\n```\n")
    return exit_code(result, mode)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
