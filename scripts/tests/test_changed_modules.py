"""Auswahl der zu testenden Module (scripts/changed_modules.py). Nur stdlib + pytest."""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import changed_modules as cm  # noqa: E402

KNOWN = {"haushaltsbuch", "cryptoboard", "zerlegewerkstatt"}


def test_pr_on_haushaltsbuch_tests_haushaltsbuch_not_only_zerlegewerkstatt():
    """Der Fehler vom 19.11.: ein Haushaltsbuch-PR wurde gar nicht getestet."""
    files = ["haushaltsbuch/backend/import_completion.py", "haushaltsbuch/frontend/api.ts"]
    assert cm.select(files, KNOWN, run_all=False) == ["haushaltsbuch"]


def test_two_modules_both_tested():
    files = ["haushaltsbuch/backend/x.py", "cryptoboard/backend/read_port.py"]
    assert cm.select(files, KNOWN, run_all=False) == ["cryptoboard", "haushaltsbuch"]


def test_markdown_only_change_tests_nothing():
    assert cm.select(["haushaltsbuch/SPEC-V9.md"], KNOWN, run_all=False) == []


def test_ci_or_script_change_tests_everything():
    assert cm.select([".github/workflows/module-tests.yml"], KNOWN, run_all=False) == sorted(KNOWN)
    assert cm.select(["scripts/changed_modules.py"], KNOWN, run_all=False) == sorted(KNOWN)


def test_push_to_main_tests_everything():
    assert cm.select([], KNOWN, run_all=True) == sorted(KNOWN)


def test_unknown_top_level_folder_ignored():
    assert cm.select(["docs/x.py", "README.md"], KNOWN, run_all=False) == []


def test_module_info_detects_tests_and_frontend(tmp_path):
    (tmp_path / "m" / "tests").mkdir(parents=True)
    (tmp_path / "m" / "tests" / "test_a.py").write_text("")
    (tmp_path / "m" / "frontend").mkdir()
    (tmp_path / "m" / "frontend" / "index.tsx").write_text("")
    info = cm.module_info("m", tmp_path)
    assert info == {"module": "m", "pytest": True, "frontend": True, "vitest": False, "deps": ""}
    (tmp_path / "n").mkdir()
    assert cm.module_info("n", tmp_path) == {"module": "n", "pytest": False, "frontend": False, "vitest": False, "deps": ""}


def _manifest(root, module_id, deps=None):
    (root / module_id).mkdir(parents=True, exist_ok=True)
    data = {"id": module_id, "version": "1.0.0"}
    if deps is not None:
        data["dependencies"] = deps
    (root / module_id / "manifest.json").write_text(json.dumps(data))


def test_change_in_dependency_also_tests_dependent(tmp_path):
    # Befund 19.11.2026: atelier importiert ../videoeditor/* — ändert ein PR nur
    # videoeditor, muss atelier mitgetestet werden.
    _manifest(tmp_path, "videoeditor")
    _manifest(tmp_path, "atelier", ["videoeditor"])
    _manifest(tmp_path, "tasks")
    known = {"videoeditor", "atelier", "tasks"}
    assert cm.select(["videoeditor/frontend/api.ts"], known, run_all=False, root=tmp_path) == ["atelier", "videoeditor"]
    assert cm.select(["atelier/frontend/x.tsx"], known, run_all=False, root=tmp_path) == ["atelier"]


def test_indirect_dependency_and_cycle(tmp_path):
    _manifest(tmp_path, "a", ["b"])
    _manifest(tmp_path, "b", ["c"])
    _manifest(tmp_path, "c", ["a"])  # Zyklus darf nicht hängen
    assert cm.all_dependencies("a", tmp_path) == ["b", "c"]
    assert cm.select(["c/x.py"], {"a", "b", "c"}, run_all=False, root=tmp_path) == ["a", "b", "c"]


def test_module_info_lists_dependencies_for_frontend_mount(tmp_path):
    _manifest(tmp_path, "videoeditor")
    _manifest(tmp_path, "atelier", ["videoeditor"])
    assert cm.module_info("atelier", tmp_path)["deps"] == "videoeditor"
    assert cm.module_info("videoeditor", tmp_path)["deps"] == ""


def test_broken_or_odd_manifest_means_no_dependencies(tmp_path):
    (tmp_path / "x").mkdir()
    (tmp_path / "x" / "manifest.json").write_text("{kaputt")
    _manifest(tmp_path, "y", "videoeditor")  # String statt Liste
    _manifest(tmp_path, "z", ["ok", 5])
    assert cm.dependencies("x", tmp_path) == []
    assert cm.dependencies("y", tmp_path) == []
    assert cm.dependencies("z", tmp_path) == ["ok"]


def test_real_repo_atelier_depends_on_videoeditor():
    assert "videoeditor" in cm.module_info("atelier")["deps"]
