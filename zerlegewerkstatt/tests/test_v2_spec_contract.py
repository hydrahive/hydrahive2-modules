from __future__ import annotations

import re
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[1]
V2_DOCUMENTS = (
    "SPEC-V2.md",
    "SPEC-V2-ARCHITEKTUR.md",
    "SPEC-V2-UX.md",
    "PLAN-V2.md",
)
LEGACY_DOCUMENTS = ("SPEC.md", "SPEC-E2.md")
APPROVAL = "**Status:** Freigegeben am 03.11.2026"
HISTORICAL = "> **Historischer Stand (Modul 0.4.0)"


def test_v2_documents_are_approved_and_cross_linked() -> None:
    for name in V2_DOCUMENTS:
        path = MODULE_ROOT / name
        text = path.read_text(encoding="utf-8")

        assert text.startswith("# "), name
        assert APPROVAL in text, name
        assert "TBD" not in text, name
        assert "TODO" not in text, name

        for target in re.findall(r"\[[^]]+\]\(([^)#]+\.md)(?:#[^)]+)?\)", text):
            assert (path.parent / target).is_file(), f"{name}: {target}"


def test_legacy_specs_are_marked_as_historical() -> None:
    for name in LEGACY_DOCUMENTS:
        text = (MODULE_ROOT / name).read_text(encoding="utf-8")

        assert HISTORICAL in text, name
        assert "SPEC-V2.md" in text, name
        assert "nicht mehr die Zielarchitektur" in text, name
