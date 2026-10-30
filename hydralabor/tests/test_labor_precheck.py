"""Hydra-Labor L2 Baustein 4a: Vorprüfung vor dem Einreichen (geschützte Pfade, Geheimnisse, Größe, Ziel)."""
from __future__ import annotations

import pytest
from backend import precheck


@pytest.mark.parametrize(("files", "target"), [(["core/src/hydrahive/x.py"], "core"),
                                               (["frontend/src/a.tsx", "core/tests/t.py"], "core"),
                                               (["radiostream/backend/a.py"], "modules"),
                                               (["hydralabor/frontend/b.tsx", "hydralabor/manifest.json"], "modules")])
def test_ziel_aus_dateien(files, target):
    assert precheck.guess_target({"core": files} if target == "core" else {"modules": files}) == target


def test_ziel_beide_geaendert_kein_vorschlag():
    assert precheck.guess_target({"core": ["a.py"], "modules": ["b/c.py"]}) == ""
    assert precheck.guess_target({}) == ""


@pytest.mark.parametrize("path", [".github/workflows/x.yml", "installer/update.sh", "scripts/check_spec.py",
                                  "LICENSE", "SECURITY.md", "docs/specs/neu.md"])
def test_geschuetzt_kern(path):
    assert precheck.protected("core", [path, "core/src/ok.py"]) == [path]


@pytest.mark.parametrize("path", [".github/workflows/x.yml", "scripts/check_version_bump.py", "hub.json",
                                  "LICENSE", "scripts/tests/test_nav_area.py"])
def test_geschuetzt_module(path):
    assert precheck.protected("modules", [path, "radiostream/backend/a.py"]) == [path]


@pytest.mark.parametrize("path", ["core/src/hydrahive/installer.py", "docs/guide.md", "frontend/scripts/gen.mjs",
                                  "radiostream/scripts/x.sh", "core/tests/test_license.py"])
def test_nicht_geschuetzt(path):
    assert precheck.protected("core", [path]) == [] and precheck.protected("modules", [path]) == []


@pytest.mark.parametrize("secret", ["ghp_" + "a" * 36, "gho_" + "B" * 36, "github_pat_" + "c" * 40,
                                    "sk-ant-" + "d" * 40, "-----BEGIN OPENSSH PRIVATE KEY-----\nabc\n-----END OPENSSH PRIVATE KEY-----",
                                    "ghs_" + "e" * 36, "ghu_" + "f" * 36, "ghr_" + "g" * 36])
def test_geheimnis_im_diff(secret):
    diff = f"+++ b/x.py\n+TOKEN = '{secret}'\n"
    found = precheck.secrets(diff)
    assert found and all(secret not in f for f in found)            # Fundstelle wird nicht im Klartext gezeigt


def test_geheimnis_nur_in_hinzugefuegten_zeilen():
    assert precheck.secrets("-OLD = 'ghp_" + "a" * 36 + "'\n+neu = 1\n") == []
    assert precheck.secrets(" kontext ghp_" + "a" * 36 + "\n") == []


def test_kein_geheimnis():
    assert precheck.secrets("+x = 'hallo welt'\n+y = 'sk-kurz'\n") == []


@pytest.mark.parametrize(("files", "lines", "ok"), [(50, 3000, True), (51, 10, False), (5, 3001, False)])
def test_groesse(files, lines, ok):
    assert (precheck.size_problem(files, lines) == "") is ok


def test_titel_und_text_begrenzt():
    with pytest.raises(precheck.PrecheckError):
        precheck.check_text("", "x")
    with pytest.raises(precheck.PrecheckError):
        precheck.check_text("a" * 121, "x")
    with pytest.raises(precheck.PrecheckError):
        precheck.check_text("Titel", "x" * 4001)
    assert precheck.check_text("  Titel  ", "  Text ") == ("Titel", "Text")


@pytest.mark.parametrize(("title", "slug"), [("Fehler im Chat beheben!", "fehler-im-chat-beheben"),
                                             ("Äpfel & Öl über Straße", "aepfel-oel-ueber-strasse"),
                                             ("x" * 80, "x" * 40), ("!!!", "aenderung")])
def test_branchname(title, slug):
    assert precheck.branch_name(title, "20261030-1712") == f"labor/{slug}-20261030-1712"
