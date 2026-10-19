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
                         this.style = {display: ""}; this.disabled = false; this.onclick = null;
                         this.classList = {add() {}, remove() {}}; }
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
               verlaufText: document.getElementById("m-verlauf").textContent};
  const before = calls.length;
  neu.all("button")[0].onclick();
  for (let i = 0; i < 8; i++) await tick();
  out.after = calls.slice(before);
  out.kopfDanach = document.getElementById("m-kopf").textContent;
  console.log(JSON.stringify(out));
})();
"""


def _data(new, new_count, history):
    return {"messages": {"new": new, "new_count": new_count, "history": history}, "hydra": None, "tasks": None,
            "machine": None, "mining": None, "github": None, "holiday": None, "updated": "12:00:00"}


def _m(i, **kw):
    return {"id": f"{i:012x}", "title": f"T{i}", "text": f"Text {i}", "kind": "info", "count": 1, "time": "12:0" + str(i)} | kw


def _run(data: dict) -> dict:
    html = PAGE.read_text(encoding="utf-8").replace("__KEY__", "K")
    script = html.split("<script>", 1)[1].split("</script>", 1)[0]
    js = DOM + RUN.replace("__DATA__", json.dumps(data)).replace("__SCRIPT__", script)
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
