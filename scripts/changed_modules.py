#!/usr/bin/env python3
"""Welche Module muss die CI testen? Ausgabe: JSON-Matrix für GitHub Actions.

Vorher testete die CI fest nur `zerlegewerkstatt/`. Grüne Checks bei PRs auf
andere Module (haushaltsbuch, cryptoboard, …) sagten nichts aus (Befund
19.11.2026, PR #399). Jetzt: jedes Modul, das der PR ändert, bekommt seine
eigene Suite (pytest, ruff, vitest, tsc).

- Pull-Request: Module mit geänderten Dateien seit dem Merge-Base (gleiche Regel
  wie check_version_bump.touched_modules, .md-Änderungen zählen nicht).
- Push auf main / manueller Lauf mit `--all`: alle Module.
- Ändert der PR nur gemeinsame Dateien (.github/, scripts/): alle Module, weil
  die Prüfung selbst betroffen ist.
- Abhängigkeiten (manifest.json „dependencies“, z. B. atelier → videoeditor):
  Ändert sich ein Modul, werden alle Module mitgetestet, die davon abhängen.
  Die Matrix nennt je Modul seine Abhängigkeiten (`deps`), damit die CI deren
  Frontend mit einhängt — sonst entfernt gen-modules.mjs das Modul still und
  vitest findet „keine Tests“.

Läuft ohne HydraHive-Core: nur stdlib.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_version_bump import changed_files, module_ids, touched_modules  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
SHARED_PREFIXES = (".github/", "scripts/")


def dependencies(module_id: str, root: Path = REPO_ROOT) -> list[str]:
    """Direkte Abhängigkeiten laut manifest.json (fehlt/kaputt → keine)."""
    try:
        data = json.loads((root / module_id / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    deps = data.get("dependencies") or []
    return [d for d in deps if isinstance(d, str)] if isinstance(deps, list) else []


def all_dependencies(module_id: str, root: Path = REPO_ROOT) -> list[str]:
    """Alle Abhängigkeiten, auch indirekte (gegen Zyklen geschützt)."""
    seen: list[str] = []
    todo = list(dependencies(module_id, root))
    while todo:
        dep = todo.pop(0)
        if dep == module_id or dep in seen:
            continue
        seen.append(dep)
        todo.extend(dependencies(dep, root))
    return seen


def with_dependents(chosen: set[str], known: set[str], root: Path = REPO_ROOT) -> set[str]:
    """Ergänzt Module, die (auch indirekt) von einem gewählten abhängen."""
    result = set(chosen)
    for module_id in known:
        if module_id not in result and result & set(all_dependencies(module_id, root)):
            result.add(module_id)
    return result


def module_info(module_id: str, root: Path = REPO_ROOT) -> dict:
    """Was hat das Modul zum Testen? (Backend-Tests, Frontend)."""
    base = root / module_id
    tests = base / "tests"
    frontend = base / "frontend"
    return {
        "module": module_id,
        "pytest": tests.is_dir() and any(tests.glob("test_*.py")),
        "frontend": frontend.is_dir() and any(frontend.rglob("*.ts*")),
        "vitest": frontend.is_dir() and any(frontend.rglob("*.test.ts*")),
        "deps": " ".join(all_dependencies(module_id, root)),
    }


def select(files: list[str], known: set[str], *, run_all: bool, root: Path = REPO_ROOT) -> list[str]:
    if run_all or any(f.startswith(SHARED_PREFIXES) for f in files):
        return sorted(known)
    return sorted(with_dependents(touched_modules(files, known), known, root))


def main(argv: list[str]) -> int:
    known = module_ids()
    run_all = "--all" in argv
    base = next((a for a in argv if not a.startswith("--")), None)
    files = [] if run_all or base is None else changed_files(base)
    chosen = select(files, known, run_all=run_all or base is None)
    print(json.dumps({"include": [module_info(m) for m in chosen]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
