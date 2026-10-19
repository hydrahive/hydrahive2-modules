"""S3: Seitenskript der Statuszentrale wirklich ausführen (Node + Mini-DOM, ohne Zusatzpakete).

Prüft das Verhalten, das die Text-Tests nicht sehen: Meldungen erscheinen, „Gelesen“ schickt genau die ID an `read`,
danach wird neu geladen; „+ n weitere“ und der Verlauf. Ohne Node → übersprungen.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

PAGE = Path(__file__).resolve().parents[1] / "backend" / "kiosk_page.html"
pytestmark = pytest.mark.skipif(not shutil.which("node"), reason="node fehlt")

DOM = r"""
class El {
  constructor(tag, id) { this.tag = tag; this.id = id || ""; this.children = []; this._text = ""; this.className = "";
                         this.style = {display: ""}; this.disabled = false; this.onclick = null; this.parent = null;
                         this.classList = {add() {}, remove() {}}; this.h = 100; }
  getBoundingClientRect() { return {top: 0, bottom: this.h, height: this.h}; }
  insertBefore(c, ref) { this.children = this.children.filter((x) => x !== c); const i = this.children.indexOf(ref);
                         c.parent = this; if (i < 0) this.children.push(c); else this.children.splice(i, 0, c); return c; }
  set textContent(v) { this._text = String(v); this.children = []; }
  get textContent() { return this._text + this.children.map((c) => c.textContent).join(""); }
  appendChild(c) { this.children.push(c); return c; }
  append(...cs) { for (const c of cs) this.children.push(c); }
  replaceChildren() { this.children = []; }
  all(tag) { return this.children.flatMap((c) => (c.tag === tag ? [c] : []).concat(c.all(tag))); }
}
const byId = {};
const document = { body: new El("body"), getElementById(id) { return byId[id] || (byId[id] = new El("div", id)); },
                   createElement(t) { return new El(t); } };
const window = { innerHeight: 1920 };
const AREA_IDS = ["messages", "home", "hydra", "tasks", "github", "machine", "mining"];
const main = document.getElementById("bereiche");
for (const a of AREA_IDS) { const e = document.getElementById("b-" + a); e.tag = "section"; e.parent = main; main.children.push(e); }
const calls = [];
let DATA = null;
const fetch = async (u, o) => {
  calls.push({url: u.split("?")[0], method: (o && o.method) || "GET", body: o && o.body ? JSON.parse(o.body) : null});
  if (u.startsWith("read")) { DATA.messages.new.shift(); DATA.messages.new_count -= 1; return {ok: true, status: 204}; }
  return {ok: true, status: 200, json: async () => JSON.parse(JSON.stringify(DATA))};
};
const setInterval = () => 0;
"""

RUN = r"""
const tick = () => new Promise((r) => setTimeout(r, 0));
(async () => {
  DATA = __DATA__;
  __SCRIPT__
  for (let i = 0; i < 5; i++) await tick();
  const neu = document.getElementById("m-neu");
  const out = {kopf: document.getElementById("m-kopf").textContent, mehr: document.getElementById("m-mehr").textContent,
               buttons: neu.all("button").length, neuText: neu.textContent,
               verlauf: document.getElementById("m-verlauf-box").style.display,
               verlaufText: document.getElementById("m-verlauf").textContent,
               order: main.children.map((c) => c.id.slice(2)),
               shown: main.children.filter((c) => c.style.display !== "none").map((c) => c.id.slice(2)),
               home: document.getElementById("z-list").textContent, homeRows: document.getElementById("z-list").children.map((c) => c.className),
               machine: document.getElementById("r-werte").textContent, rmining: document.getElementById("r-mining").textContent,
               full: document.getElementById("zu-voll").textContent};
  const before = calls.length;
  neu.all("button")[0].onclick();
  for (let i = 0; i < 8; i++) await tick();
  out.after = calls.slice(before);
  out.kopfDanach = document.getElementById("m-kopf").textContent;
  console.log(JSON.stringify(out));
})();
"""


def _data(new, new_count, history, **over):
    d = {"messages": {"new": new, "new_count": new_count, "history": history}, "home": None, "hydra": None, "tasks": None,
         "machine": None, "mining": None, "github": None, "holiday": None, "updated": "12:00:00",
         "layout": {"order": ["messages", "home", "hydra", "tasks", "github", "machine", "mining"], "hidden": [],
                    "messages_max": 3, "mining_in_machine": True}}
    d.update(over)
    return d


def _m(i, **kw):
    return {"id": f"{i:012x}", "title": f"T{i}", "text": f"Text {i}", "kind": "info", "count": 1, "time": "12:0" + str(i)} | kw


def _run(data: dict, heights: dict | None = None) -> dict:
    from backend import kiosk
    html = kiosk.page("K")
    script = "\n".join(part.split("</script>", 1)[0] for part in html.split("<script>")[1:])
    hs = "".join(f'document.getElementById("b-{k}").h = {v};' for k, v in (heights or {}).items())
    js = DOM + hs + RUN.replace("__DATA__", json.dumps(data)).replace("__SCRIPT__", script)
    out = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=30, check=True)
    return json.loads(out.stdout.strip().splitlines()[-1])


def test_gelesen_schickt_id_und_laedt_neu():
    r = _run(_data([_m(1, title="Backup", count=3), _m(2)], 7, [_m(9, title="Alt")]))
    assert r["kopf"] == "Neu (7)" and r["mehr"] == "+ 5 weitere" and r["buttons"] == 2
    assert "Backup  ×3" in r["neuText"] and "Text 1" in r["neuText"]
    assert r["verlauf"] == "" and "Alt" in r["verlaufText"]
    assert r["after"][0] == {"url": "read", "method": "POST", "body": {"id": f"{1:012x}"}}
    assert any(c["url"] == "data" for c in r["after"][1:]), "danach sofort neu laden"
    assert r["kopfDanach"] == "Neu (6)"


def test_keine_meldungen():
    r = _run(_data([_m(1)], 1, []))
    assert r["verlauf"] == "none", "leerer Verlauf ist ausgeblendet"
    assert r["kopfDanach"] == "Meldungen"


MACHINE = {"load": 0.5, "ram": 40, "gpu": 50, "disk_free_pct": 55, "uptime_h": 20}
MINING = {"eur_day": 1.5, "rigs": [{"name": "tillswks", "mining": True}]}
HOME = {"rooms": [{"room": "Wohnzimmer", "temp": "22,4 °C", "hum": "53 %", "battery_low": None, "extra": None, "offline_h": None},
                  {"room": "Küche", "temp": "23,1 °C", "hum": None, "battery_low": "15 %", "extra": None, "offline_h": None},
                  {"room": "Alex Zimmer", "temp": None, "hum": None, "battery_low": None, "extra": None, "offline_h": 13}],
        "error": None}


def test_reihenfolge_und_ausgeblendet():
    lay = {"order": ["home", "machine", "messages", "hydra", "tasks", "github", "mining"], "hidden": ["github"],
           "messages_max": 3, "mining_in_machine": True}
    r = _run(_data([_m(1)], 1, [], home=HOME, machine=MACHINE, mining=MINING, hydra=None, layout=lay,
                   github={"prs": [], "error": None}))                     # Daten da – nur die Einstellung blendet aus
    assert r["order"][:3] == ["home", "machine", "messages"]
    assert "github" not in r["shown"] and "mining" not in r["shown"], "mining_in_machine → eigener Bereich aus"
    assert "Mining 1,50 €/Tag" in r["rmining"] and "● tillswks" in r["rmining"] and "Mining" not in r["machine"]


def test_mining_eigener_bereich():
    lay = {"order": ["messages", "home", "hydra", "tasks", "github", "machine", "mining"], "hidden": [],
           "messages_max": 3, "mining_in_machine": False}
    r = _run(_data([_m(1)], 1, [], machine=MACHINE, mining=MINING, layout=lay))
    assert "mining" in r["shown"] and r["rmining"] == "" and "Last 0.5" in r["machine"]


def test_zuhause_zeilen():
    r = _run(_data([_m(1)], 1, [], home=HOME))
    assert "Wohnzimmer" in r["home"] and "22,4 °C" in r["home"] and "53 %" in r["home"]
    assert "Batterie 15 %" in r["home"] and "nicht erreichbar seit 13 h" in r["home"]
    assert r["homeRows"][1].endswith("warn") and r["homeRows"][2].endswith("aus")


def test_zuhause_fehler_und_leer():
    r = _run(_data([_m(1)], 1, [], home={"rooms": [], "error": "Home Assistant nicht erreichbar"}))
    assert "Home Assistant nicht erreichbar" in r["home"]
    r = _run(_data([_m(1)], 1, [], home={"rooms": [], "error": None}))
    assert "Keine Favoriten" in r["home"]


def test_zu_voll_blendet_von_unten_aus():
    js_h = {"messages": 900, "home": 400, "hydra": 300, "tasks": 300, "github": 300, "machine": 120, "mining": 120}
    r = _run(_data([_m(1)], 1, [], home=HOME, machine=MACHINE, mining=MINING,
                   hydra={"service": "active", "agents": 1, "errors_last_hour": 0, "errors": []},
                   tasks={"open": 1, "in_progress": 0, "top": []}, github={"prs": [], "error": None}), heights=js_h)
    assert r["shown"][:2] == ["messages", "home"]
    assert r["full"].endswith("ausgeblendet (zu voll)") and r["full"][0].isdigit()
    assert len(r["shown"]) < 6
