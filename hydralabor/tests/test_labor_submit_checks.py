"""Hydra-Labor L2: Einreichen – Vorprüfung bricht vor dem Schieben ab (nichts geht nach außen)."""
from __future__ import annotations

import asyncio

import pytest
from backend import submit


def run(c):
    return asyncio.run(c)


def test_keine_aenderungen(ready):
    ready["changes"] = {"files": [], "lines": 0}
    with pytest.raises(submit.SubmitError) as e:
        run(submit.submit("core", "T", "B", report=lambda _k: None))
    assert e.value.code == "labor_submit_nothing"
    assert [c[0] for c in ready["calls"]] == ["changes"]


def test_geschuetzter_pfad(ready):
    ready["changes"] = {"files": [".github/workflows/x.yml", "core/a.py"], "lines": 3}
    with pytest.raises(submit.SubmitError) as e:
        run(submit.submit("core", "T", "B", report=lambda _k: None))
    assert e.value.code == "labor_submit_protected" and e.value.detail == [".github/workflows/x.yml"]
    assert "push" not in [c[0] for c in ready["calls"]]


def test_zu_gross(ready):
    ready["changes"] = {"files": [f"f{i}.py" for i in range(51)], "lines": 10}
    with pytest.raises(submit.SubmitError) as e:
        run(submit.submit("core", "T", "B", report=lambda _k: None))
    assert e.value.code == "labor_submit_too_big"


def test_geheimnis_gefunden(ready):
    ready["diff"] = "+key = 'ghp_" + "a" * 36 + "'\n"
    with pytest.raises(submit.SubmitError) as e:
        run(submit.submit("core", "T", "B", report=lambda _k: None))
    assert e.value.code == "labor_submit_secret" and e.value.detail == ["ghp_aa…"]
    assert "tests" not in [c[0] for c in ready["calls"]]


def test_tests_rot(ready):
    ready["tests"] = {"ok": False, "summary": "2 failed, 10 passed", "passed": 10, "failed": 2, "failures": ["a::b"]}
    with pytest.raises(submit.SubmitError) as e:
        run(submit.submit("core", "T", "B", report=lambda _k: None))
    assert e.value.code == "labor_submit_tests_red" and e.value.detail["failed"] == 2
    assert "bundle" not in [c[0] for c in ready["calls"]]
