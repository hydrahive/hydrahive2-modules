#!/usr/bin/env python3
"""Erzeugt <modul>/skills/_history.json für alle Module mit eigenen Skills.

Wie scripts/update_skill_history.py im Kern: SHA-256 aller Fassungen aus der
Git-Geschichte plus der aktuellen Datei. Der Skill-Sync des Kerns ersetzt eine
Live-Datei nur, wenn sie einer dieser Fassungen entspricht – sonst gilt sie als
Admin-Änderung. Nach jeder Änderung an einem Modul-Skill laufen lassen.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _versions(rel: str) -> list[str]:
    log = subprocess.run(["git", "-C", str(ROOT), "log", "--follow", "--format=%H", "--name-only", "--", rel],
                         check=True, capture_output=True, text=True).stdout
    lines = [ln for ln in log.splitlines() if ln.strip()]
    shas: list[str] = []
    for commit, path in zip(lines[0::2], lines[1::2]):
        r = subprocess.run(["git", "-C", str(ROOT), "show", f"{commit}:{path}"], capture_output=True)
        if r.returncode:
            continue  # in diesem Commit gelöscht
        sha = hashlib.sha256(r.stdout).hexdigest()
        if sha not in shas:
            shas.append(sha)
    return list(reversed(shas))


def main() -> int:
    # Nur Module, die den Skill-Sync des Kerns nutzen (haben schon eine _history.json).
    for skills in sorted(p.parent for p in ROOT.glob("*/skills/_history.json")):
        history: dict[str, list[str]] = {}
        for f in sorted(skills.glob("*.md")):
            shas = _versions(str(f.relative_to(ROOT)))
            current = hashlib.sha256(f.read_bytes()).hexdigest()
            if current not in shas:
                shas.append(current)
            history[f.name] = shas
        out = skills / "_history.json"
        out.write_text(json.dumps(history, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"{out.relative_to(ROOT)}: {len(history)} Skills, {sum(len(v) for v in history.values())} Fassungen")
    return 0


if __name__ == "__main__":
    sys.exit(main())
