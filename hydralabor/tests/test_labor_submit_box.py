"""Hydra-Labor L2 Baustein 4b: im Container – Änderungen messen, sichern (Commit), Tests, Bündel abholen."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from backend import submit_box


def run(c):
    return asyncio.run(c)


def execs(fake):
    return [c for c in fake.calls if c[0] == "exec"]


def test_repo_pfade_fest():
    assert submit_box.REPO == {"core": "/work/hydrahive2", "modules": "/work/hydrahive2-modules"}


def test_aenderungen_messen(fake_incus):
    fake_incus.exec_answers["hh-labor-changes"] = (0, "a/x.py\nb/y.tsx\n--STAT--\n3\t1\ta/x.py\n10\t0\tb/y.tsx\n")
    ch = run(submit_box.changes("core"))
    assert ch == {"files": ["a/x.py", "b/y.tsx"], "lines": 14}
    call = execs(fake_incus)[-1]
    assert call[call.index("--user") + 1] == "1000" and call[call.index("--cwd") + 1] == "/work/hydrahive2"
    assert "origin/main" in call[-1]


def test_keine_aenderungen(fake_incus):
    fake_incus.exec_answers["hh-labor-changes"] = (0, "--STAT--\n")
    assert run(submit_box.changes("modules")) == {"files": [], "lines": 0}


def test_binaerdatei_zaehlt_als_eine_zeile(fake_incus):
    fake_incus.exec_answers["hh-labor-changes"] = (0, "bild.png\n--STAT--\n-\t-\tbild.png\n")
    assert run(submit_box.changes("core"))["lines"] == 1


def test_messen_scheitert(fake_incus):
    fake_incus.exec_answers["hh-labor-changes"] = (128, "")
    with pytest.raises(submit_box.SubmitError) as e:
        run(submit_box.changes("core"))
    assert e.value.code == "labor_submit_git_failed"


def test_sichern_mit_autor_von_github(fake_incus):
    run(submit_box.commit("core", "Titel mit 'Anführung'", "nutzer", 4242))
    call = execs(fake_incus)[-1]
    env = [call[i + 1] for i, a in enumerate(call) if a == "--env"]
    assert "GIT_AUTHOR_NAME=nutzer" in env and "GIT_AUTHOR_EMAIL=4242+nutzer@users.noreply.github.com" in env
    assert "GIT_COMMITTER_NAME=nutzer" in env
    assert "HH_LABOR_MSG=Titel mit 'Anführung'" in env                # Text nur über die Umgebung, nicht im Befehl
    assert "Anführung" not in call[-1]
    assert "git add -A" in call[-1] and "git commit" in call[-1]


@pytest.mark.parametrize(("login", "uid"), [("bad name", 1), ("x;rm", 1), ("ok", -1), ("", 1)])
def test_sichern_ungueltiger_login(fake_incus, login, uid):
    with pytest.raises(submit_box.SubmitError):
        run(submit_box.commit("core", "T", login, uid))


def test_diff_holen(fake_incus):
    fake_incus.exec_answers["hh-labor-diff"] = (0, "+++ b/x\n+neu\n")
    assert run(submit_box.diff("modules")) == "+++ b/x\n+neu\n"


def test_tests_kern(fake_incus):
    fake_incus.exec_answers["pytest -q -n 2"] = (0, "5241 passed in 270.0s\n")
    res = run(submit_box.run_tests("core", ["core/src/a.py"]))
    assert res["ok"] is True and res["passed"] == 5241


def test_tests_module_nur_geaenderte_plus_skripte(fake_incus):
    fake_incus.exec_answers["hh-labor-modtests"] = (0, "== radiostream\n12 passed in 1.0s\n== skripte\nok\n")
    res = run(submit_box.run_tests("modules", ["radiostream/backend/a.py", "radiostream/frontend/b.tsx",
                                               "hydralabor/x.py", "README.md"]))
    body = execs(fake_incus)[-1][-1]
    assert "radiostream" in body and "hydralabor" in body and "README" not in body
    assert "check_version_bump.py origin/main" in body and "check_test_safety.py" in body
    assert res["ok"] is True


def test_tests_module_rot(fake_incus):
    fake_incus.exec_answers["hh-labor-modtests"] = (1, "== radiostream\n1 failed, 11 passed in 1.0s\n")
    assert run(submit_box.run_tests("modules", ["radiostream/a.py"]))["ok"] is False


@pytest.mark.parametrize("name", ["../x", "a b", "-rf", ".hidden"])
def test_modulnamen_streng(fake_incus, name):
    with pytest.raises(submit_box.SubmitError):
        run(submit_box.run_tests("modules", [f"{name}/a.py"]))


def test_buendel_abholen_und_loeschen(fake_incus, tmp_path):
    fake_incus.pull_files["hh-labor/tmp/hh-labor.bundle"] = b"# v2 git bundle\n" + b"x" * 100
    dest = run(submit_box.bundle("core", tmp_path))
    assert dest == tmp_path / "labor.bundle" and dest.read_bytes().startswith(b"# v2 git bundle")
    cmds = [" ".join(c) for c in fake_incus.calls]
    assert any("git bundle create -q /tmp/hh-labor.bundle origin/main..HEAD" in c for c in cmds)
    assert any(c.startswith("file pull hh-labor/tmp/hh-labor.bundle") for c in cmds)
    assert any("rm -f /tmp/hh-labor.bundle" in c for c in cmds)


def test_buendel_zu_gross(fake_incus, tmp_path, monkeypatch):
    monkeypatch.setattr(submit_box, "MAX_BUNDLE", 50)
    fake_incus.pull_files["hh-labor/tmp/hh-labor.bundle"] = b"# v2 git bundle\n" + b"x" * 100
    with pytest.raises(submit_box.SubmitError) as e:
        run(submit_box.bundle("core", tmp_path))
    assert e.value.code == "labor_submit_too_big"
    assert not (tmp_path / "labor.bundle").exists()


def test_buendel_kein_buendel(fake_incus, tmp_path):
    fake_incus.pull_files["hh-labor/tmp/hh-labor.bundle"] = b"#!/bin/sh\nrm -rf /\n"
    with pytest.raises(submit_box.SubmitError) as e:
        run(submit_box.bundle("core", tmp_path))
    assert e.value.code == "labor_submit_bundle_invalid"
    assert not Path(tmp_path / "labor.bundle").exists()


def test_neue_dateien_werden_mitgezaehlt(fake_incus):
    """Ohne `git add -N` sieht `git diff` neue, ungesicherte Dateien nicht – die gehören aber dazu."""
    run(submit_box.changes("core"))
    assert "git add -A -N ." in execs(fake_incus)[-1][-1]


def test_leerzeilen_in_namensliste(fake_incus):
    fake_incus.exec_answers["hh-labor-changes"] = (0, "a.py\n\n  \n--STAT--\n1\t0\ta.py\n")
    assert run(submit_box.changes("core"))["files"] == ["a.py"]


@pytest.mark.parametrize("step", ["commit", "diff"])
def test_git_fehler(fake_incus, step):
    fake_incus.exec_answers["git diff origin/main..HEAD" if step == "diff" else "git add -A &&"] = (1, "")
    with pytest.raises(submit_box.SubmitError) as e:
        run(submit_box.commit("core", "T", "nutzer", 1) if step == "commit" else submit_box.diff("core"))
    assert e.value.code == "labor_submit_git_failed"


def test_dateien_ohne_ordner_kein_modul(fake_incus):
    run(submit_box.run_tests("modules", ["README.md", "radiostream/a.py"]))
    body = execs(fake_incus)[-1][-1]
    assert 'echo "== README.md"' not in body and 'echo "== radiostream"' in body


def test_buendel_auch_bei_fehler_im_container_geloescht(fake_incus, tmp_path):
    with pytest.raises(submit_box.SubmitError):
        run(submit_box.bundle("core", tmp_path))                  # nichts zum Abholen → Fehler
    assert ["exec", "hh-labor", "--", "rm", "-f", "/tmp/hh-labor.bundle"] in fake_incus.calls


def test_buendel_anlegen_scheitert(fake_incus, tmp_path):
    fake_incus.exec_answers["git bundle create"] = (128, "")
    fake_incus.pull_files["hh-labor/tmp/hh-labor.bundle"] = b"# v2 git bundle\nalt"
    with pytest.raises(submit_box.SubmitError) as e:
        run(submit_box.bundle("core", tmp_path))
    assert e.value.code == "labor_submit_git_failed" and not (tmp_path / "labor.bundle").exists()
