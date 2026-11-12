"""Übernahme der alten Zettel-Dateien (user.md, agent.md) in einzelne Ideen."""
from __future__ import annotations

import pytest

USER_SAMPLE = """wetterstation im garten

ich hätte gern eine kleine wetterstation, die ihre werte im dashboard zeigt ?

die anzeige müsste an einer stelle sein, damit ich alles auf einen blick sehe.

welche sensoren sind ausgefallen und liefern nichts mehr
"""

AGENT_SAMPLE = """# Idee: Leihliste für Werkzeug (04.10.2026)

Status: nur Idee, nichts geplant.

**Drei Wege:**
- **A) Papierliste:** bleibt wie sie ist.
- **B) Tabelle im Notizbuch**

---

# Vorratsschrank — Stand 26.09.2026

Deine Idee oben ist als Liste aufgeschrieben.

**Offene Fragen an dich (vor dem Einkauf):**
1. Auch das Regal im Keller mitzählen?

---

# Ältere Einträge (Sammlung)

- Fahrradreparatur 2026-07-03
- Balkonkasten bepflanzen (2026-09-17)
"""


@pytest.fixture
def zettel(setup_test_env):
    """Schreibt alte Dateien für einen Nutzer und räumt den Ordner danach wieder auf."""
    from _hh_isolation import remove_test_tree
    from hydrahive.settings import settings

    made = []

    def write(username: str, user: str | None = None, agent: str | None = None):
        folder = settings.data_dir / "scratchpad" / username
        folder.mkdir(parents=True, exist_ok=True)
        made.append(folder)
        if user is not None:
            (folder / "user.md").write_text(user, encoding="utf-8")
        if agent is not None:
            (folder / "agent.md").write_text(agent, encoding="utf-8")
        return folder

    yield write
    for folder in made:
        remove_test_tree(folder)


def _run(username: str) -> int:
    from backend import legacy_import
    return legacy_import.import_for(username)


def _ideas(username: str) -> list[dict]:
    from backend import store
    return [store.get(username, i["id"]) for i in store.list_ideas(username)]


def test_drei_ueberschriften_ergeben_drei_ideen(zettel):
    zettel("alice", user="# Eins\nText eins\n\n# Zwei\nText zwei\n# Drei\n")
    assert _run("alice") == 3
    ideas = _ideas("alice")
    assert [i["title"] for i in ideas] == ["Eins", "Zwei", "Drei"]
    assert [i["body"] for i in ideas] == ["Text eins", "Text zwei", ""]
    assert {i["status"] for i in ideas} == {"new"} and {i["project_id"] for i in ideas} == {None}


def test_ohne_ueberschrift_eine_idee_mit_titel_aus_erster_zeile(zettel):
    zettel("alice", user="\n\n  schnelle idee  \n\nmehr dazu\nnoch mehr\n")
    assert _run("alice") == 1
    idea = _ideas("alice")[0]
    assert idea["title"] == "schnelle idee"
    assert idea["body"] == "mehr dazu\nnoch mehr"


def test_text_vor_der_ersten_ueberschrift_wird_eigene_idee(zettel):
    zettel("alice", user="lose notiz\ndetails\n\n# Sauber\nInhalt\n")
    assert _run("alice") == 2
    assert [i["title"] for i in _ideas("alice")] == ["lose notiz", "Sauber"]


def test_trennlinien_am_rand_fallen_weg(zettel):
    zettel("alice", user="# A\n\nText\n\n---\n\n# B\n---\nNur B\n---\n")
    _run("alice")
    assert [i["body"] for i in _ideas("alice")] == ["Text", "Nur B"]


def test_ueberschrift_im_codeblock_trennt_nicht(zettel):
    zettel("alice", user="# Skript\n```bash\n# kein Titel\necho hallo\n```\n# Danach\n")
    assert _run("alice") == 2
    ideas = _ideas("alice")
    assert ideas[0]["title"] == "Skript" and "# kein Titel" in ideas[0]["body"]


def test_unterueberschriften_bleiben_im_text(zettel):
    zettel("alice", user="# Groß\n## Klein\nText\n")
    assert _run("alice") == 1
    assert _ideas("alice")[0]["body"] == "## Klein\nText"


def test_herkunft_je_datei(zettel):
    zettel("alice", user="# Meins\n", agent="# Vom Agenten\n")
    assert _run("alice") == 2
    assert {i["title"]: i["origin"] for i in _ideas("alice")} == {"Meins": "user", "Vom Agenten": "agent"}


def test_dateien_heissen_danach_imported_und_zweiter_lauf_legt_nichts_an(zettel):
    folder = zettel("alice", user="# Eins\n", agent="# Zwei\n")
    assert _run("alice") == 2
    assert sorted(p.name for p in folder.iterdir()) == ["agent.md.imported", "user.md.imported"]
    assert (folder / "user.md.imported").read_text(encoding="utf-8") == "# Eins\n"
    assert _run("alice") == 0
    assert len(_ideas("alice")) == 2


def test_abgebrochener_lauf_legt_beim_wiederholen_nichts_doppelt_an(zettel):
    folder = zettel("alice", user="# Eins\n# Zwei\n")
    assert _run("alice") == 2
    (folder / "user.md.imported").rename(folder / "user.md")  # als wäre das Umbenennen ausgefallen
    assert _run("alice") == 0
    assert len(_ideas("alice")) == 2


def test_leere_und_fehlende_dateien(zettel):
    assert _run("niemand") == 0
    folder = zettel("alice", user="   \n\n", agent="---\n")
    assert _run("alice") == 0
    assert _ideas("alice") == []
    assert sorted(p.name for p in folder.iterdir()) == ["agent.md.imported", "user.md.imported"]


def test_langer_titel_wird_gekuerzt_und_bleibt_im_text(zettel):
    long_line = "wort " * 60
    zettel("alice", user=long_line + "\nrest\n")
    _run("alice")
    idea = _ideas("alice")[0]
    assert len(idea["title"]) <= 200
    assert idea["body"].startswith(long_line.strip())


def test_zu_langer_abschnitt_wird_geteilt_statt_abgeschnitten(zettel):
    paragraphs = "\n\n".join(f"Absatz {n} " + "x" * 990 for n in range(120))
    zettel("alice", user="# Riesig\n" + paragraphs + "\n")
    assert _run("alice") == 3
    ideas = _ideas("alice")
    assert [i["title"] for i in ideas] == ["Riesig", "Riesig (Teil 2)", "Riesig (Teil 3)"]
    assert all(len(i["body"]) <= 50_000 for i in ideas)
    assert "\n\n".join(i["body"] for i in ideas) == paragraphs


def test_anderer_nutzer_bleibt_unberuehrt(zettel):
    zettel("alice", user="# Alice\n")
    folder_bob = zettel("bob", user="# Bob\n")
    _run("alice")
    assert _ideas("bob") == []
    assert (folder_bob / "user.md").exists()


def test_aufbau_wie_die_alten_zettel(zettel):
    zettel("alice", user=USER_SAMPLE, agent=AGENT_SAMPLE)
    assert _run("alice") == 4
    ideas = _ideas("alice")
    assert [(i["title"], i["origin"]) for i in ideas] == [
        ("wetterstation im garten", "user"),
        ("Idee: Leihliste für Werkzeug (04.10.2026)", "agent"),
        ("Vorratsschrank — Stand 26.09.2026", "agent"),
        ("Ältere Einträge (Sammlung)", "agent"),
    ]
    assert ideas[0]["body"].startswith("ich hätte gern eine kleine wetterstation")
    assert ideas[0]["body"].endswith("liefern nichts mehr")
    assert ideas[1]["body"].endswith("- **B) Tabelle im Notizbuch**")
    assert "---" not in ideas[2]["body"]
    assert ideas[3]["body"].startswith("- Fahrradreparatur")
