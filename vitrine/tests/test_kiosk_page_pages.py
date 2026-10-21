"""S5: Seiten der Statuszentrale – feste Zuordnung, Knubbel, nie selbst blättern, nach Ruhe zurück auf Seite 1."""
from __future__ import annotations

import json
import shutil
import subprocess

import pytest
from test_kiosk_page_js import DOM, HOME, MACHINE, MINING, _data, _m

pytestmark = pytest.mark.skipif(not shutil.which("node"), reason="node fehlt")

CLOCK = r"""
let NOW = 1000000;
Date.now = () => NOW;
const listeners = {};
document.addEventListener = (ev, fn) => { (listeners[ev] = listeners[ev] || []).push(fn); };
"""

STEPS = r"""
const tick = () => new Promise((r) => setTimeout(r, 0));
const page = () => ({
  shown: main.children.filter((c) => c.style.display !== "none").map((c) => c.id.slice(2)),
  knubbel: document.getElementById("knubbel").all("button").map((b) => b.textContent),
  knubbelBox: document.getElementById("knubbel").style.display,
});
(async () => {
  DATA = __DATA__;
  __SCRIPT__
  for (let i = 0; i < 5; i++) await tick();
  const out = {start: page(), steps: []};
  for (const step of __STEPS__) {
    if (step[0] === "klick") document.getElementById("knubbel").all("button")[step[1]].onclick();
    if (step[0] === "zeit") NOW += step[1] * 1000;
    if (step[0] === "maus") (listeners["mousemove"] || []).forEach((f) => f());
    if (step[0] === "laden") { await load(); }
    if (step[0] === "daten") DATA = Object.assign(DATA, step[1]);
    for (let i = 0; i < 5; i++) await tick();
    out.steps.push({...page(), fetches: calls.length});
  }
  console.log(JSON.stringify(out));
})();
"""


def _run(data: dict, steps: list) -> dict:
    from backend import kiosk
    html = kiosk.page("K")
    script = "\n".join(part.split("</script>", 1)[0] for part in html.split("<script>")[1:])
    js = DOM + CLOCK + STEPS.replace("__DATA__", json.dumps(data)).replace("__STEPS__", json.dumps(steps)).replace("__SCRIPT__", script)
    out = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=30, check=True)
    return json.loads(out.stdout.strip().splitlines()[-1])


HYDRA = {"service": "active", "agents": 1, "errors_last_hour": 0, "errors": []}
TASKS = {"open": 2, "in_progress": 0, "top": []}
PAGES = {"messages": 1, "home": 1, "hydra": 1, "tasks": 2, "github": 2, "machine": 2, "mining": 2}


def _full(**layout):
    lay = {"order": ["messages", "home", "hydra", "tasks", "github", "machine", "mining"], "hidden": [],
           "messages_max": 3, "mining_in_machine": True, "pages": dict(PAGES), "return_seconds": 120,
           "chat_enabled": False, "bluetooth_enabled": False}   # S5 prüft nur die Seiten; Chat (S6)/Bluetooth (S7) eigen
    lay.update(layout)
    return _data([_m(1)], 1, [], home=HOME, hydra=HYDRA, tasks=TASKS, machine=MACHINE, mining=MINING,
                 github={"prs": [], "error": None}, layout=lay)


def test_voreinstellung_seite_1_und_zwei_knubbel():
    r = _run(_full(), [])
    assert r["start"]["shown"] == ["messages", "home", "hydra"]
    assert r["start"]["knubbel"] == ["●", "○"] and r["start"]["knubbelBox"] != "none"


def test_klick_wechselt_ohne_anfrage():
    r = _run(_full(), [["klick", 1], ["klick", 0]])
    s1, s2 = r["steps"]
    assert s1["shown"] == ["tasks", "github", "machine"] and s1["knubbel"] == ["○", "●"]
    assert s2["shown"] == ["messages", "home", "hydra"]
    assert s1["fetches"] == s2["fetches"] == 1, "nur der erste Datenabruf – Blättern fragt den Server nicht"


def test_nur_eine_seite_keine_knubbel():
    r = _run(_full(pages={a: 1 for a in PAGES}), [])
    assert r["start"]["knubbel"] == [] and r["start"]["knubbelBox"] == "none"


def test_drei_seiten_drei_knubbel():
    r = _run(_full(pages=dict(PAGES, machine=3)), [["klick", 2]])
    assert r["start"]["knubbel"] == ["●", "○", "○"] and r["steps"][0]["shown"] == ["machine"]


def test_leere_seite_zaehlt_nicht():
    """Seite 2 nur mit ausgeschalteten Bereichen → nicht belegt, kein Knubbel."""
    r = _run(_full(hidden=["tasks", "github", "machine", "mining"]), [])
    assert r["start"]["knubbel"] == [] and r["start"]["shown"] == ["messages", "home", "hydra"]


def test_gewaehlte_seite_wird_leer_naechste_belegte():
    """Seite 3 hatte nur „Rechner“; der fällt weg → Seite 3 gibt es nicht mehr, es geht auf die erste belegte."""
    r = _run(_full(pages=dict(PAGES, machine=3)), [["klick", 2], ["daten", {"machine": None}], ["laden"]])
    last = r["steps"][2]
    assert last["shown"] == ["messages", "home", "hydra"] and last["knubbel"] == ["●", "○"]


def test_nach_ruhe_zurueck_auf_seite_1_aber_nie_vorher():
    r = _run(_full(), [["klick", 1], ["zeit", 60], ["laden"], ["zeit", 61], ["laden"]])
    assert r["steps"][2]["shown"] == ["tasks", "github", "machine"], "nach 60 s noch Seite 2 – nie selbst blättern"
    assert r["steps"][4]["shown"] == ["messages", "home", "hydra"], "nach > 120 s ohne Eingabe → Seite 1"


def test_maus_haelt_die_seite():
    r = _run(_full(), [["klick", 1], ["zeit", 100], ["maus"], ["zeit", 100], ["laden"]])
    assert r["steps"][4]["shown"] == ["tasks", "github", "machine"], "Eingabe vor 100 s → bleibt auf Seite 2"
