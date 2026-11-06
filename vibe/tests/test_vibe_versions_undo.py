"""Baustein 5: Änderungsansicht, „Zurück zu hier“, „Nur diese Änderung zurück“, Dateiregeln (PLAN-V1.md).

Zweiter Teil zu test_vibe_versions.py. Gegen ECHTES Git (siehe dort).
"""
from __future__ import annotations

import asyncio
import subprocess

import pytest
from backend import versions
from gitbridge import Bridge, clean_env


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


def turn(work, name, text, summary):
    p = work / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return run(versions.commit_turn("p1", summary, kind="turn"))


# --- Änderungsansicht -------------------------------------------------------------------------------------------

def test_aenderung_in_klartext(vm, work):
    v = turn(work, "src/neu.ts", "x\n", "neue Datei")
    ch = run(versions.changes("p1", v["commit_id"]))
    assert ch["text"] == "1 Datei geändert" and ch["files"] == [{"path": "src/neu.ts", "status": "neu"}]


@pytest.mark.parametrize(("n", "want"), [(1, "1 Datei geändert"), (2, "2 Dateien geändert"), (5, "5 Dateien geändert")])
def test_klartext_mehrzahl(vm, work, n, want):
    for i in range(n):
        (work / f"f{i}.txt").write_text("x\n")
    v = run(versions.commit_turn("p1", "mehrere", kind="turn"))
    assert run(versions.changes("p1", v["commit_id"]))["text"] == want


def test_klartext_ohne_git_woerter(vm, work):
    v = turn(work, "a.txt", "anders\n", "t")
    text = run(versions.changes("p1", v["commit_id"]))["text"].lower()
    for wort in ("diff", "commit", "insertion", "deletion", "hunk", "patch"):
        assert wort not in text


def test_dateistatus_neu_geaendert_geloescht(vm, work):
    (work / "b.txt").write_text("b\n")
    base = run(versions.commit_turn("p1", "b", kind="turn"))
    (work / "a.txt").write_text("geändert\n")
    (work / "b.txt").unlink()
    (work / "c.txt").write_text("c\n")
    v = run(versions.commit_turn("p1", "mix", kind="turn"))
    st = {f["path"]: f["status"] for f in run(versions.changes("p1", v["commit_id"]))["files"]}
    assert st == {"a.txt": "geändert", "b.txt": "gelöscht", "c.txt": "neu"} and base


def test_vorher_nachher_einer_datei(vm, work):
    v = turn(work, "a.txt", "zeile neu\n", "t")
    d = run(versions.file_diff("p1", v["commit_id"], "a.txt"))
    assert d["before"] == "a\n" and d["after"] == "zeile neu\n" and not d["binary"]


def test_vorher_nachher_neue_und_geloeschte_datei(vm, work):
    v = turn(work, "n.txt", "neu\n", "t")
    d = run(versions.file_diff("p1", v["commit_id"], "n.txt"))
    assert d["before"] == "" and d["after"] == "neu\n"
    (work / "n.txt").unlink()
    v2 = run(versions.commit_turn("p1", "weg", kind="turn"))
    d2 = run(versions.file_diff("p1", v2["commit_id"], "n.txt"))
    assert d2["before"] == "neu\n" and d2["after"] == ""


def test_binaerdatei_ohne_inhalt(vm, work):
    (work / "k.bin").write_bytes(bytes(range(256)) * 4)
    v = run(versions.commit_turn("p1", "bin", kind="turn"))
    d = run(versions.file_diff("p1", v["commit_id"], "k.bin"))
    assert d["binary"] is True and d["before"] == "" and d["after"] == ""


def test_grosse_textdatei_wird_gekuerzt(vm, work):
    (work / "gross.txt").write_text("x" * 500_000)
    v = run(versions.commit_turn("p1", "gross", kind="turn"))
    d = run(versions.file_diff("p1", v["commit_id"], "gross.txt"))
    assert len(d["after"]) <= versions.MAX_VIEW_CHARS and d["truncated"] is True


@pytest.mark.parametrize("pfad", ["../etc/passwd", "/etc/passwd", "a/../../x", "-p", "--output=/tmp/x", "a\nb", ""])
def test_ansicht_lehnt_gefaehrliche_pfade_ab(vm, work, pfad):
    v = turn(work, "a.txt", "x\n", "t")
    with pytest.raises(versions.VersionError) as e:
        run(versions.file_diff("p1", v["commit_id"], pfad))
    assert e.value.code == "vibe_path_invalid"


@pytest.mark.parametrize("cid", ["", "HEAD", "main", "--all", "abc", "../x", "g" * 40, "A" * 40, "0" * 41])
def test_nur_echte_commit_ids(vm, cid):
    with pytest.raises(versions.VersionError) as e:
        run(versions.changes("p1", cid))
    assert e.value.code == "vibe_version_invalid"


def test_unbekannte_version(vm):
    with pytest.raises(versions.VersionError) as e:
        run(versions.changes("p1", "0" * 40))
    assert e.value.code == "vibe_version_not_found"


# --- Zurück zu hier ---------------------------------------------------------------------------------------------

def test_zurueck_stellt_den_stand_her_als_neue_version(vm, work):
    v1 = turn(work, "a.txt", "eins\n", "eins")
    turn(work, "a.txt", "zwei\n", "zwei")
    turn(work, "extra.txt", "x\n", "extra")
    back = run(versions.restore("p1", v1["commit_id"]))
    assert (work / "a.txt").read_text() == "eins\n" and not (work / "extra.txt").exists()
    assert back["kind"] == "restore" and back["summary"].startswith("Zurück zu")
    assert [v["summary"] for v in run(versions.history("p1"))][1:] == ["extra", "zwei", "eins", "Start"]


def test_zurueck_verliert_keine_version(vm, work):
    v1 = turn(work, "a.txt", "eins\n", "eins")
    v2 = turn(work, "a.txt", "zwei\n", "zwei")
    run(versions.restore("p1", v1["commit_id"]))
    ids = {v["commit_id"] for v in run(versions.history("p1"))}
    assert {v1["commit_id"], v2["commit_id"]} <= ids


def test_zurueck_ist_selbst_umkehrbar(vm, work):
    v1 = turn(work, "a.txt", "eins\n", "eins")
    v2 = turn(work, "a.txt", "zwei\n", "zwei")
    run(versions.restore("p1", v1["commit_id"]))
    run(versions.restore("p1", v2["commit_id"]))
    assert (work / "a.txt").read_text() == "zwei\n"


def test_zurueck_auf_den_aktuellen_stand_ohne_aenderung(vm, work):
    v = turn(work, "a.txt", "eins\n", "eins")
    assert run(versions.restore("p1", v["commit_id"])) is None
    assert len(run(versions.history("p1"))) == 2


def test_zurueck_rauemt_ungespeicherte_dateien_weg_aber_nicht_node_modules(vm, work):
    v1 = turn(work, "a.txt", "eins\n", "eins")
    (work / "lose.txt").write_text("nie gespeichert\n")
    (work / "node_modules").mkdir()
    (work / "node_modules" / "p.js").write_text("x\n")
    turn(work, "a.txt", "zwei\n", "zwei")
    run(versions.restore("p1", v1["commit_id"]))
    assert (work / "node_modules" / "p.js").exists()


def test_zurueck_auf_unbekannte_version_aendert_nichts(vm, work):
    """Mutanten-Fund: Ohne Existenzprüfung würde `read-tree` mit einer unbekannten ID scheitern UND vorher nichts
    verhindern. Hier muss die Datei unangetastet bleiben und der Code `vibe_version_not_found` kommen."""
    turn(work, "a.txt", "wichtig\n", "wichtig")
    (work / "lose.txt").write_text("nicht gespeichert\n")
    with pytest.raises(versions.VersionError) as e:
        run(versions.restore("p1", "0" * 40))
    assert e.value.code == "vibe_version_not_found"
    assert (work / "a.txt").read_text() == "wichtig\n" and (work / "lose.txt").exists()


def test_verlauf_zeigt_zurueck_im_klartext_ohne_hash(vm, work):
    """Die Anzeige nennt den Titel der Zielversion, nie den Git-Hash."""
    work.joinpath("a.txt").write_text("1")
    run(versions.commit_turn("p1", "Knopf orange gemacht", kind="turn"))
    first = run(versions.history("p1"))[0]["commit_id"]
    work.joinpath("a.txt").write_text("2")
    run(versions.commit_turn("p1", "Knopf grün gemacht", kind="turn"))
    run(versions.restore("p1", first))
    top = run(versions.history("p1"))[0]
    assert top["kind"] == "restore" and top["summary"] == "Zurück zu: Knopf orange gemacht"
    assert first[:7] not in top["summary"]


def test_verlauf_zurueck_auf_ein_zurueck_zeigt_den_urspruenglichen_titel(vm, work):
    work.joinpath("a.txt").write_text("1")
    run(versions.commit_turn("p1", "Knopf orange gemacht", kind="turn"))
    orange = run(versions.history("p1"))[0]["commit_id"]
    work.joinpath("a.txt").write_text("2")
    run(versions.commit_turn("p1", "Knopf grün gemacht", kind="turn"))
    run(versions.restore("p1", orange))
    back1 = run(versions.history("p1"))[0]["commit_id"]
    work.joinpath("a.txt").write_text("3")
    run(versions.commit_turn("p1", "Knopf rot gemacht", kind="turn"))
    run(versions.restore("p1", back1))
    sums = [v["summary"] for v in run(versions.history("p1"))]
    assert sums[0] == "Zurück zu: Knopf orange gemacht" and sums[2] == "Zurück zu: Knopf orange gemacht"
    assert not any("Zurück zu: Zurück" in x for x in sums)
