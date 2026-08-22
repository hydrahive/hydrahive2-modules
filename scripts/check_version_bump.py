#!/usr/bin/env python3
"""Verhindert Modul-Änderungen ohne Versionsanhebung.

Hintergrund: Der Modul-Installer entscheidet per Semver, ob ein Update
ausgeliefert wird (`Version(available) > Version(installed)`). Ändert ein
Commit den Inhalt eines Moduls, ohne die Version im manifest.json anzuheben,
sieht der Hub "gleiche Version, nichts zu tun" — die Änderung erreicht die
Kunden nie.

Das ist zweimal real passiert:
  * 2660dcb — lokale Video-Backends (E5) wurden nie ausgeliefert
  * 5beecfb — Media-Cockpit-Workflow des Ateliers fehlte im Cockpit

Aufruf:
    python3 scripts/check_version_bump.py <base-ref>

Exit-Code 1, wenn ein Modul geändert wurde, dessen Version unverändert blieb.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]

# Dateien, die den ausgelieferten Modulinhalt NICHT verändern.
IGNORED_SUFFIXES = (".md",)


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    )
    return result.stdout


def changed_files(base_ref: str) -> list[str]:
    output = _git("diff", "--name-only", f"{base_ref}...HEAD")
    return [line for line in output.splitlines() if line.strip()]


def module_ids() -> set[str]:
    """Verzeichnisse mit manifest.json sind Module."""
    return {
        path.parent.name
        for path in REPO_ROOT.glob("*/manifest.json")
    }


def _version_at(ref: str, module_id: str) -> str | None:
    try:
        raw = _git("show", f"{ref}:{module_id}/manifest.json")
    except subprocess.CalledProcessError:
        return None  # Modul ist neu — keine Vorversion vorhanden
    try:
        return json.loads(raw).get("version")
    except json.JSONDecodeError:
        return None


def touched_modules(files: list[str], known: set[str]) -> set[str]:
    touched = set()
    for path in files:
        head, _, rest = path.partition("/")
        if not rest or head not in known:
            continue
        if path.endswith(IGNORED_SUFFIXES):
            continue
        touched.add(head)
    return touched


def main() -> int:
    if len(sys.argv) != 2:
        print("Aufruf: check_version_bump.py <base-ref>", file=sys.stderr)
        return 2

    base_ref = sys.argv[1]
    known = module_ids()
    touched = touched_modules(changed_files(base_ref), known)

    if not touched:
        print("Keine Modul-Inhalte geändert — nichts zu prüfen.")
        return 0

    failures: list[str] = []
    for module_id in sorted(touched):
        before = _version_at(base_ref, module_id)
        after = _version_at("HEAD", module_id)

        if before is None:
            print(f"  {module_id}: neu ({after}) — ok")
            continue
        if after != before:
            print(f"  {module_id}: {before} → {after} — ok")
            continue
        failures.append(module_id)
        print(f"  {module_id}: {before} unverändert — FEHLER")

    if not failures:
        return 0

    print(
        "\nModule geändert, ohne die Version anzuheben: "
        + ", ".join(failures)
        + "\n\nDer Installer vergleicht per Semver. Bleibt die Version gleich,"
        "\nmeldet der Hub kein Update und die Änderung erreicht niemanden."
        "\n\nHebe die Version im jeweiligen manifest.json an"
        " (Patch für Fixes, Minor für neue Funktionen).",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
