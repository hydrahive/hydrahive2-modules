"""Guard gegen Modul-Tests, die echte Daten löschen können (Vorfall 26.09.2026).

Läuft ohne HydraHive-Core: nur stdlib + pytest.
"""
from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import check_test_safety as guard  # noqa: E402

HELPER_SRC = (SCRIPTS / "_hh_isolation.py").read_text(encoding="utf-8")

GOOD_CONFTEST = textwrap.dedent('''\
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _hh_isolation import only_own_rows  # noqa: E402

    import pytest  # noqa: E402
    from fastapi.testclient import TestClient  # noqa: E402
''')


def _module(root: Path, name: str, conftest: str, test_body: str = "def test_x():\n    pass\n",
            helper: str | None = HELPER_SRC) -> Path:
    tests = root / name / "tests"
    tests.mkdir(parents=True)
    (root / name / "manifest.json").write_text('{"version": "1.0.0"}')
    (tests / "conftest.py").write_text(conftest)
    (tests / "test_a.py").write_text(test_body)
    if helper is not None:
        (tests / "_hh_isolation.py").write_text(helper)
    return tests


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "_hh_isolation.py").write_text(HELPER_SRC)
    return tmp_path


def test_clean_module_passes(repo: Path) -> None:
    _module(repo, "good", GOOD_CONFTEST)
    assert guard.check(repo) == []


@pytest.mark.parametrize("line", [
    'conn.execute("DELETE FROM module_tasks")',
    "c.execute('DELETE FROM module_blueprint_boards')",
    'conn.execute(f"DELETE FROM {spec.table}")',
    'conn.execute(f"DELETE FROM module_haushaltsbuch_{table}")',
])
def test_detects_delete_without_where(repo: Path, line: str) -> None:
    _module(repo, "bad", GOOD_CONFTEST, f"def test_x(conn):\n    {line}\n")
    assert any("DELETE ohne WHERE" in p for p in guard.check(repo))


def test_allows_targeted_delete(repo: Path) -> None:
    body = ('def test_x(conn):\n'
            '    conn.execute("DELETE FROM t WHERE id = ?", (1,))\n'
            '    conn.execute(f"DELETE FROM {t} WHERE rowid > ?", (m,))\n')
    _module(repo, "ok", GOOD_CONFTEST, body)
    assert guard.check(repo) == []


@pytest.mark.parametrize("body", [
    "def test_x(d):\n    for f in d.glob('*.mp3'):\n        f.unlink()\n",
    "def test_x(s):\n    for spec in ENTITIES.values():\n        s.execute(f'DELETE FROM {spec.table} WHERE 1')\n",
    "def test_x(ei):\n    for inst in ei.list_instances():\n        ei.delete_instance(inst)\n",
])
def test_detects_cleanup_loop_over_everything(repo: Path, body: str) -> None:
    _module(repo, "bad", GOOD_CONFTEST, body)
    assert any("Schleife über ALLE" in p for p in guard.check(repo))


def test_detects_rmtree(repo: Path) -> None:
    _module(repo, "bad", GOOD_CONFTEST, "import shutil\ndef test_x(p):\n    shutil.rmtree(p)\n")
    assert any("rmtree" in p for p in guard.check(repo))


def test_detects_missing_or_late_helper(repo: Path) -> None:
    _module(repo, "nohelper", "import pytest\n", helper=None)
    late = "from fastapi.testclient import TestClient\n" + GOOD_CONFTEST
    _module(repo, "late", late)
    _module(repo, "stale", GOOD_CONFTEST, helper="# alte Kopie\n")
    problems = "\n".join(guard.check(repo))
    assert "nohelper/tests/conftest.py lädt _hh_isolation nicht" in problems
    assert "nohelper/tests/_hh_isolation.py fehlt" in problems
    assert "late/tests/conftest.py:1: Import vor _hh_isolation" in problems
    assert "stale/tests/_hh_isolation.py weicht" in problems


def test_detects_conftest_setting_data_dir_itself(repo: Path) -> None:
    conf = GOOD_CONFTEST + 'import os\nos.environ["HH_DATA_DIR"] = "/tmp/x"\n'
    _module(repo, "bad", conf)
    assert any("setzt Datenpfad selbst" in p for p in guard.check(repo))


def _run_helper(tmp_path: Path, code: str) -> subprocess.CompletedProcess:
    fake_prod = tmp_path / "fake-prod"
    (fake_prod / "data").mkdir(parents=True)
    env = {**os.environ, "HH_DATA_DIR": str(fake_prod / "data"),
           "HH_CONFIG_DIR": str(fake_prod / "config"), "PYTHONPATH": str(SCRIPTS)}
    return subprocess.run([sys.executable, "-c", textwrap.dedent(code)], env=env,
                          capture_output=True, text=True, timeout=60)


def test_helper_redirects_env_and_refuses_foreign_paths(tmp_path: Path) -> None:
    res = _run_helper(tmp_path, f'''
        import os
        from pathlib import Path
        import _hh_isolation as iso
        assert os.environ["HH_DATA_DIR"].startswith(str(iso.TEST_ROOT)), os.environ["HH_DATA_DIR"]
        prod = Path({str(tmp_path / "fake-prod")!r})
        assert iso.forbidden_hit(prod / "data" / "sessions.db") is not None
        for bad in (prod / "data" / "sessions.db", Path("/var/lib/hydrahive2/sessions.db")):
            try:
                iso.refuse_real_path(bad)
            except RuntimeError:
                pass
            else:
                raise SystemExit(f"nicht verweigert: {{bad}}")
        iso.refuse_real_path(iso.TEST_ROOT / "data" / "sessions.db")
        print("OK")
    ''')
    assert res.returncode == 0, res.stderr
    assert "OK" in res.stdout


def test_only_own_files_keeps_preexisting_files(tmp_path: Path) -> None:
    res = _run_helper(tmp_path, '''
        import _hh_isolation as iso
        d = iso.TEST_ROOT / "data" / "audio"
        d.mkdir(parents=True)
        (d / "alt.mp3").write_bytes(b"alt")
        with iso.only_own_files(d, "*.mp3"):
            (d / "neu.mp3").write_bytes(b"neu")
        assert sorted(p.name for p in d.iterdir()) == ["alt.mp3"], list(d.iterdir())
        print("OK")
    ''')
    assert res.returncode == 0, res.stderr
    assert "OK" in res.stdout


def test_repo_is_clean() -> None:
    """Der eigentliche Guard: kein Modul im Repo darf breit löschen."""
    problems = guard.check()
    assert not problems, "\n".join(problems)
