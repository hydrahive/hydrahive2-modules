"""Hydra-Labor L2 Baustein 4/5: Einreichen von vorne bis hinten (Vorprüfung → Fork → Bündel → Schieben → PR),
gespeichert, Stand aktualisieren. Container, GitHub und Schieben sind Attrappen; die Teile sind einzeln geprüft."""
from __future__ import annotations

import asyncio

import pytest
from backend import github_auth, submit


def run(c):
    return asyncio.run(c)


def test_ohne_github_kein_einreichen(ready):
    github_auth.disconnect()
    with pytest.raises(submit.SubmitError) as e:
        run(submit.submit("core", "Titel", "Text", report=lambda _k: None))
    assert e.value.code == "labor_github_not_connected"


def test_einreichen_komplett(ready, fake_github):
    seen = []
    out = run(submit.submit("core", "Fehler im Chat beheben", "Weil es hakt.", report=seen.append))
    assert seen == ["check", "tests", "fork", "push", "pr"]
    names = [c[0] for c in ready["calls"]]
    assert names == ["changes", "commit", "diff", "tests", "bundle", "push"]
    assert ready["calls"][1] == ("commit", "core", "Fehler im Chat beheben", "nutzer", 4242)
    assert ready["calls"][-1] == ("push", "nutzer/hydrahive2.0", "core", "labor/fehler-im-chat-beheben-20261030-1900", True)
    pr = fake_github.pulls[0]
    assert pr["head"] == "nutzer:labor/fehler-im-chat-beheben-20261030-1900" and pr["base"] == "main"
    assert pr["title"] == "Fehler im Chat beheben" and pr["maintainer_can_modify"] is True
    for part in ("Weil es hakt.", "Hydra-Labor", "5241 passed", "hydralabor 0.2.0"):
        assert part in pr["body"]
    post = next(c for c in fake_github.calls if c["url"].endswith("/repos/hydrahive/hydrahive2.0/pulls"))
    assert post["method"] == "POST"
    assert out["number"] == 100 and out["url"].endswith("/pull/100")
    assert submit.list_submissions()[0] | {} == {**submit.list_submissions()[0], "kind": "pr", "target": "core",
                                                "number": 100, "state": "submitted"}


def test_label_wird_versucht_fehler_egal(ready, fake_github):
    fake_github.fail["POST https://api.github.com/repos/hydrahive/hydrahive2.0/issues/100/labels"] = (403, {})
    run(submit.submit("core", "T", "B", report=lambda _k: None))
    assert any(c["url"].endswith("/issues/100/labels") for c in fake_github.calls)
    assert submit.list_submissions()[0]["number"] == 100


@pytest.mark.parametrize("target", ["plugins", "", "../x"])
def test_ziel_ungueltig(ready, target):
    with pytest.raises(submit.SubmitError) as e:
        run(submit.submit(target, "T", "B", report=lambda _k: None))
    assert e.value.code == "labor_submit_target_invalid"


def test_text_ungueltig(ready):
    with pytest.raises(submit.SubmitError) as e:
        run(submit.submit("core", "", "B", report=lambda _k: None))
    assert e.value.code == "labor_submit_text_invalid"


def test_pr_scheitert(ready, fake_github):
    fake_github.fail["POST https://api.github.com/repos/hydrahive/hydrahive2.0/pulls"] = (422, {"message": "x"})
    with pytest.raises(submit.SubmitError) as e:
        run(submit.submit("core", "T", "B", report=lambda _k: None))
    assert e.value.code == "labor_submit_pr_failed"
    assert submit.list_submissions() == []


def test_ziel_vorschlagen(ready):
    ready["changes"] = {"files": ["radiostream/a.py"], "lines": 1}
    assert run(submit.suggest_target()) in ("core", "modules", "")


def test_stand_aktualisieren(ready, fake_github):
    run(submit.submit("core", "A", "B", report=lambda _k: None))
    run(submit.submit("core", "C", "D", report=lambda _k: None))
    fake_github.pulls[0].update(state="closed", merged=True)
    fake_github.pulls[1].update(state="closed", merged=False)
    run(submit.refresh())
    by_num = {s["number"]: s["state"] for s in submit.list_submissions()}
    assert by_num == {100: "merged", 101: "closed"}
    n = len(fake_github.calls)
    run(submit.refresh())                                          # abgeschlossene werden nicht mehr abgefragt
    assert len(fake_github.calls) == n


def test_token_nie_in_gespeicherten_daten(ready):
    from fake_github import TOKEN
    from hydrahive.db.connection import db
    run(submit.submit("core", "T", "B", report=lambda _k: None))
    with db() as c:
        rows = c.execute("SELECT * FROM module_hydralabor_submissions").fetchall()
    assert TOKEN not in str([tuple(r) for r in rows])


def test_token_ohne_login_gilt_nicht_verbunden(ready):
    from hydrahive.db.connection import db
    with db() as c:
        c.execute("UPDATE module_hydralabor_github SET login = '' WHERE id = 1")
        c.commit()
    with pytest.raises(submit.SubmitError) as e:
        run(submit.submit("core", "T", "B", report=lambda _k: None))
    assert e.value.code == "labor_github_not_connected"


def test_label_labor_gesetzt(ready, fake_github):
    run(submit.submit("core", "T", "B", report=lambda _k: None))
    lab = next(c for c in fake_github.calls if c["url"].endswith("/issues/100/labels"))
    assert lab["json"] == {"labels": ["labor"]} and lab["method"] == "POST"


def test_offener_pr_bleibt_eingereicht(ready, fake_github):
    run(submit.submit("core", "A", "B", report=lambda _k: None))
    fake_github.pulls[0].update(state="open", merged=False)
    run(submit.refresh())
    assert submit.list_submissions()[0]["state"] == "submitted"


def test_versionen_echt(monkeypatch):
    """Kern heißt als Paket hydrahive-core (nicht hydrahive) – sonst stand „hydrahive ?“ im PR (Befund PR #670)."""
    from importlib import metadata
    real = metadata.version
    monkeypatch.setattr(metadata, "version", lambda name: "2.0.0" if name == "hydrahive-core" else real(name))
    v = submit._versions()
    assert v["hydrahive"] == "2.0.0"


def test_versionen_ohne_paket(monkeypatch):
    from importlib import metadata

    def missing(name):
        raise metadata.PackageNotFoundError(name)
    monkeypatch.setattr(metadata, "version", missing)
    assert submit._versions()["hydrahive"] == "?"
