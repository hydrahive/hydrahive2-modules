#!/usr/bin/env python3
"""Prüft, dass Modul-Tests nie echte Daten löschen können.

Befund 26.09.2026: Eine Testsuite lief versehentlich gegen das Live-System.
Aufräum-Fixtures mit `DELETE FROM <tabelle>` ohne WHERE haben dabei ganze
Tabellen geleert. Jede Modul-Suite ist genauso gebaut, deshalb gelten hier
dieselben Regeln wie im Core:

1. Jede Test-Suite lädt `tests/_hh_isolation.py` als ERSTES in conftest.py,
   also vor fastapi, hydrahive und backend. Die Kopie ist identisch mit
   scripts/_hh_isolation.py.
2. conftest.py setzt HH_DATA_DIR/HH_CONFIG_DIR nicht selbst. Das erledigt der
   Helfer, bevor irgendetwas settings liest.
3. Kein `DELETE FROM <tabelle>` ohne WHERE. Stattdessen `only_own_rows(...)`.
4. Keine Schleife über alle Einträge oder Dateien, die dabei löscht.
   Stattdessen `only_own_files(...)` oder gezielt die eigene ID.
5. Kein direktes `rmtree`. Stattdessen `remove_test_tree(...)`, das nur
   innerhalb des Test-Verzeichnisses löscht.

Aufruf:  python3 scripts/check_test_safety.py      Exit 1 bei Verstößen.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HELPER = "_hh_isolation.py"

BROAD_DELETE = re.compile(r"""DELETE\s+FROM\s+[A-Za-z_{][A-Za-z0-9_.{}\[\]]*\s*["')]""", re.I)
LOOP_ALL = re.compile(
    r"^\s*for\s+.+\s+in\s+.*(\.glob\(|\.rglob\(|\.iterdir\(|\blist_\w*\(\s*\)|\.values\(\))"
)
DELETING = re.compile(r"\.(delete\w*|unlink|remove|rmtree)\(|rmtree\(|os\.remove\(|DELETE\s+FROM", re.I)
RMTREE = re.compile(r"\brmtree\(")
OWN_ENV = re.compile(r"""["'](HH_DATA_DIR|HH_CONFIG_DIR)["']\s*(\]\s*=|:)""")
FIRST_RISKY_IMPORT = re.compile(r"^\s*(from|import)\s+(fastapi|hydrahive|backend)\b")
HELPER_IMPORT = re.compile(r"^\s*(from|import)\s+_hh_isolation\b")


def test_dirs(root: Path = REPO_ROOT) -> list[Path]:
    return sorted(
        d for d in root.glob("*/tests")
        if (d.parent / "manifest.json").is_file() and any(d.glob("test_*.py"))
    )


def _scan_lines(path: Path, lines: list[str], rel: str) -> list[str]:
    problems = []
    for no, line in enumerate(lines, 1):
        if BROAD_DELETE.search(line):
            problems.append(f"{rel}:{no}: DELETE ohne WHERE -> only_own_rows(...): {line.strip()}")
        if RMTREE.search(line):
            problems.append(f"{rel}:{no}: rmtree -> remove_test_tree(...): {line.strip()}")
        if LOOP_ALL.search(line):
            indent = len(line) - len(line.lstrip())
            for body in lines[no:]:
                if body.strip() and len(body) - len(body.lstrip()) <= indent:
                    break
                if DELETING.search(body):
                    problems.append(
                        f"{rel}:{no}: Schleife über ALLE Einträge löscht -> nur eigene: {line.strip()}"
                    )
                    break
    return problems


def check_conftest(tests: Path, helper_src: str, rel_base: Path) -> list[str]:
    rel = tests.relative_to(rel_base)
    conftest = tests / "conftest.py"
    helper = tests / HELPER
    problems = []
    if not helper.is_file():
        problems.append(f"{rel}/{HELPER} fehlt (Kopie von scripts/{HELPER})")
    elif helper.read_text(encoding="utf-8") != helper_src:
        problems.append(f"{rel}/{HELPER} weicht von scripts/{HELPER} ab")
    if not conftest.is_file():
        return problems + [f"{rel}/conftest.py fehlt (muss _hh_isolation laden)"]
    lines = conftest.read_text(encoding="utf-8").splitlines()
    helper_at = next((i for i, l in enumerate(lines) if HELPER_IMPORT.search(l)), None)
    risky_at = next((i for i, l in enumerate(lines) if FIRST_RISKY_IMPORT.search(l)), None)
    if helper_at is None:
        problems.append(f"{rel}/conftest.py lädt _hh_isolation nicht")
    elif risky_at is not None and risky_at < helper_at:
        problems.append(
            f"{rel}/conftest.py:{risky_at + 1}: Import vor _hh_isolation "
            "(Helfer muss zuerst laden)"
        )
    for no, line in enumerate(lines, 1):
        if OWN_ENV.search(line):
            problems.append(f"{rel}/conftest.py:{no}: setzt Datenpfad selbst (macht der Helfer)")
    return problems


def check(root: Path = REPO_ROOT) -> list[str]:
    helper_src = (root / "scripts" / HELPER).read_text(encoding="utf-8")
    problems: list[str] = []
    for tests in test_dirs(root):
        problems += check_conftest(tests, helper_src, root)
        for path in sorted(tests.rglob("*.py")):
            if path.name == HELPER or "__pycache__" in path.parts:
                continue
            lines = path.read_text(encoding="utf-8").splitlines()
            problems += _scan_lines(path, lines, str(path.relative_to(root)))
    return problems


def main() -> int:
    problems = check()
    if problems:
        print("Modul-Tests könnten echte Daten löschen:\n")
        print("\n".join(f"  - {p}" for p in problems))
        print(f"\n{len(problems)} Verstoß/Verstöße. Details: scripts/check_test_safety.py")
        return 1
    print(f"OK: {len(test_dirs())} Modul-Suites isoliert, kein breites Löschen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
