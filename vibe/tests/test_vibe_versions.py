"""Baustein 5: Zeitmaschine – Version je Zug, Klartext, Änderungsansicht, Zurück (PLAN-V1.md).

Gegen ECHTES Git in einem Temp-Ordner (Bridge ersetzt nur den Weg `incus exec`). Verhalten gemessen am 5.11.2026
(git 2.53): `read-tree --reset -u` stellt einen Stand her (ohne leeren Commit nötig), `revert --no-commit` hinterlässt
bei Konflikt REVERT_HEAD, `revert --abort` räumt auf, ein verschachteltes Repo wird zum Gitlink (160000).
"""
from __future__ import annotations

import asyncio
import subprocess

import pytest
from backend import versions
from gitbridge import Bridge, clean_env

MODEL_OK = True


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def work(tmp_path):
    w = tmp_path / "work"
    w.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(w)], check=True, env=clean_env(tmp_path))
    (w / ".gitignore").write_text("node_modules\ndist\n")
    (w / "a.txt").write_text("a\n")
    return w


@pytest.fixture
def vm(work, monkeypatch):
    bridge = Bridge(work)
    monkeypatch.setattr(versions, "_run", bridge.run)
    run(versions.commit_turn("p1", "Start", kind="start"))
    return bridge


def write(work, name, text):
    p = work / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def ids():
    return [v["commit_id"] for v in run(versions.history("p1"))]


# --- Version je Zug --------------------------------------------------------------------------------------------

def test_erste_version_ist_start(vm):
    h = run(versions.history("p1"))
    assert len(h) == 1 and h[0]["summary"] == "Start" and h[0]["kind"] == "start"


def test_zug_mit_aenderung_erzeugt_version(vm, work):
    write(work, "a.txt", "neu\n")
    v = run(versions.commit_turn("p1", "Text geändert", kind="turn"))
    assert v is not None and v["summary"] == "Text geändert" and v["kind"] == "turn"
    assert len(run(versions.history("p1"))) == 2


def test_zug_ohne_aenderung_erzeugt_keine_leere_version(vm):
    assert run(versions.commit_turn("p1", "Nichts", kind="turn")) is None
    assert len(run(versions.history("p1"))) == 1


def test_neueste_zuerst(vm, work):
    write(work, "a.txt", "1\n")
    run(versions.commit_turn("p1", "eins", kind="turn"))
    write(work, "a.txt", "2\n")
    run(versions.commit_turn("p1", "zwei", kind="turn"))
    assert [v["summary"] for v in run(versions.history("p1"))] == ["zwei", "eins", "Start"]


def test_versionsliste_mit_grenze(vm, work):
    for i in range(5):
        write(work, "a.txt", f"{i}\n")
        run(versions.commit_turn("p1", f"v{i}", kind="turn"))
    assert len(run(versions.history("p1", limit=3))) == 3


# --- Klartext ---------------------------------------------------------------------------------------------------

@pytest.mark.parametrize(("raw", "want"), [
    ("Hintergrund dunkelblau gemacht\n\nHier der Rest.", "Hintergrund dunkelblau gemacht"),
    ("   \n\n  Erste echte Zeile  \nZweite", "Erste echte Zeile"),
    ("**Knopf größer**", "Knopf größer"),
    ("# Titel der Änderung", "Titel der Änderung"),
    ("- Eintrag als Liste", "Eintrag als Liste"),
    ("a" * 300, "a" * 99 + "…"),
    ("Mit\x00Nullbyte\x1b[31mFarbe", "MitNullbyteFarbe"),
    ("Tab\tund\rUmbruch", "Tab und Umbruch"),
    ("", "Änderung"), ("   \n  ", "Änderung"), ("\x00\x01", "Änderung"),
])
def test_kurztext_aus_der_antwort(raw, want):
    assert versions.summary_from(raw) == want


def test_kurztext_ohne_zusaetzlichen_ki_aufruf():
    """Der Text kommt aus der Antwort selbst, kein Modellaufruf (SPEC.md: Version = erste Zeile der Antwort)."""
    import inspect
    src = inspect.getsource(versions.summary_from)
    assert "llm" not in src.lower() and "complete" not in src.lower()


def test_kurztext_kann_kein_git_argument_sein(vm, work):
    """Ein Text, der wie eine Option aussieht, darf nie als Option bei Git ankommen."""
    write(work, "a.txt", "x\n")
    v = run(versions.commit_turn("p1", "--amend --author=Evil", kind="turn"))
    assert v["summary"] == "--amend --author=Evil"
    assert len(run(versions.history("p1"))) == 2


def test_commit_traegt_vibe_als_autor(vm, work):
    write(work, "a.txt", "x\n")
    run(versions.commit_turn("p1", "t", kind="turn"))
    out = subprocess.run(["git", "log", "-1", "--format=%an <%ae>"], cwd=work, capture_output=True, text=True,
                         env=clean_env(work.parent)).stdout.strip()
    assert out == "Vibe <vibe@localhost>"
