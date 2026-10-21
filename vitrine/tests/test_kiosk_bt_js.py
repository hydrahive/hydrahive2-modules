"""S7 Bluetooth-Seite am Kiosk: Knubbel vor „Chat“, Suche, Tippen koppelt, Code groß, KEIN Entfernen (Node + Mini-DOM)."""
from __future__ import annotations

import json
import shutil
import subprocess

import pytest
from test_kiosk_page_js import DOM, HOME, MACHINE, _data, _m

pytestmark = pytest.mark.skipif(not shutil.which("node"), reason="node fehlt")

EXTRA = r"""
let NOW = 1000000; Date.now = () => NOW;
let BT = null, BTPOST = {status: 202};
const realFetch = fetch;
fetch = async (u, o) => {
  if (u.startsWith("bluetooth")) {
    calls.push({url: u.split("?")[0], method: (o && o.method) || "GET", body: o && o.body ? JSON.parse(o.body) : null});
    if (o && o.method === "POST") {
      if (BTPOST.status !== 202) return {ok: false, status: BTPOST.status, json: async () => ({detail: {code: BTPOST.code}})};
      return {ok: true, status: 202, json: async () => ({})};
    }
    return {ok: true, status: 200, json: async () => JSON.parse(JSON.stringify(BT))};
  }
  return realFetch(u, o);
};
"""

STEPS = r"""
const tick = () => new Promise((r) => setTimeout(r, 0));
const rows = (id) => document.getElementById(id).children.map((r) => ({
  text: r.children.length ? r.children.map((c) => c.textContent) : [r.textContent], click: typeof r.onclick === "function",
  cls: r.className}));
const page = () => ({
  shown: main.children.filter((c) => c.style.display !== "none").map((c) => c.id.slice(2)),
  bt: document.getElementById("bt").style.display,
  chat: document.getElementById("chat").style.display,
  knubbel: document.getElementById("knubbel").all("button").map((b) => b.textContent),
  scan: [document.getElementById("bt-scan").textContent, document.getElementById("bt-scan").disabled,
         document.getElementById("bt-scan").style.display],
  hint: document.getElementById("bt-hinweis").textContent,
  code: document.getElementById("bt-code").textContent,
  list: rows("bt-liste"), more: rows("bt-weitere"),
  moreBtn: [document.getElementById("bt-mehr").textContent, document.getElementById("bt-mehr").style.display],
  btCalls: calls.filter((c) => c.url.startsWith("bluetooth")),
});
(async () => {
  DATA = __DATA__; BT = __BT__;
  __SCRIPT__
  for (let i = 0; i < 5; i++) await tick();
  const out = {start: page(), steps: []};
  for (const s of __STEPS__) {
    if (s[0] === "knubbel") document.getElementById("knubbel").all("button")[s[1]].onclick();
    if (s[0] === "scan") document.getElementById("bt-scan").onclick();
    if (s[0] === "mehr") document.getElementById("bt-mehr").onclick();
    if (s[0] === "zeile") document.getElementById("bt-liste").children[s[1]].onclick();
    if (s[0] === "stand") BT = s[1];
    if (s[0] === "post") BTPOST = s[1];
    if (s[0] === "laden") await btLoad();
    if (s[0] === "warten") { NOW += s[1] * 1000; await load(); }
    for (let i = 0; i < 8; i++) await tick();
    out.steps.push(page());
  }
  console.log(JSON.stringify(out));
})();
"""

A3, A4 = "B4:EE:25:ED:70:7F", "B4:EE:25:EE:72:7F"
RAPOO = {"name": "RAPOO KB", "addresses": [A3, A4], "kind": "keyboard", "rssi": -56, "bars": 4, "paired": True,
         "connected": True, "more": False}
MAUS = {"name": "MX Anywhere", "addresses": ["C0:11:22:33:44:55"], "kind": "mouse", "rssi": -70, "bars": 3,
        "paired": False, "connected": False, "more": False}
FERN = {"name": "Unbekanntes Gerät", "addresses": ["66:DD:27:7F:DB:9A"], "kind": "other", "rssi": -95, "bars": 1,
        "paired": False, "connected": False, "more": True}


def _bt(**over):
    v = {"available": True, "adapter": {"name": "hydrahive-master", "powered": True}, "window_left": 0,
         "devices": [RAPOO, MAUS, FERN], "weak_signal": False, "pairing": None, "error": None}
    v.update(over)
    return v


def _run(data: dict, steps: list, bt: dict | None = None) -> dict:
    from backend import kiosk
    html = kiosk.page("K")
    script = "\n".join(part.split("</script>", 1)[0] for part in html.split("<script>")[1:])
    js = (DOM + EXTRA + STEPS.replace("__DATA__", json.dumps(data)).replace("__BT__", json.dumps(bt or _bt()))
          .replace("__STEPS__", json.dumps(steps)).replace("__SCRIPT__", script))
    js = js.replace("const fetch = async", "let fetch = async", 1)
    out = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=30, check=True)
    return json.loads(out.stdout.strip().splitlines()[-1])


PAGES = {"messages": 1, "home": 1, "hydra": 1, "tasks": 2, "github": 2, "machine": 2, "mining": 2}


def _d(bt=True, chat=True):
    lay = {"order": list(PAGES), "hidden": [], "messages_max": 3, "mining_in_machine": True, "pages": dict(PAGES),
           "chat_enabled": chat, "bluetooth_enabled": bt, "return_seconds": 120}
    return _data([_m(1)], 1, [], home=HOME, machine=MACHINE, layout=lay)


def test_knubbel_vor_chat_seite_versteckt_und_ohne_laden():
    r = _run(_d(), [])
    assert r["start"]["knubbel"] == ["●", "○", "Bluetooth", "Chat"] and r["start"]["bt"] == "none"
    assert r["start"]["btCalls"] == [], "ohne geöffnete Seite fragt der Kiosk Bluetooth nicht ab"


def test_aus_kein_knubbel():
    assert _run(_d(bt=False), [])["start"]["knubbel"] == ["●", "○", "Chat"]


def test_klick_zeigt_seite_mit_gekoppelten_ohne_entfernen():
    s = _run(_d(), [["knubbel", 2]])["steps"][0]
    assert s["bt"] == "" and s["shown"] == [] and s["knubbel"] == ["○", "○", "●", "Chat"]
    assert [c["url"] for c in s["btCalls"]] == ["bluetooth"]
    assert s["scan"] == ["Gerät koppeln", False, ""]
    assert len(s["list"]) == 1 and s["list"][0]["text"][0] == "RAPOO KB" and "verbunden" in s["list"][0]["text"]
    assert not s["list"][0]["click"], "gekoppeltes Gerät: kein Klick"
    blob = json.dumps(s)
    assert "Entfernen" not in blob and "remove" not in blob, "am Kiosk gibt es kein Entfernen"


def test_suche_starten():
    s = _run(_d(), [["knubbel", 2], ["scan"]])["steps"][-1]
    assert [(c["url"], c["method"]) for c in s["btCalls"] if c["method"] == "POST"] == [("bluetooth/scan", "POST")]


def test_offenes_fenster_tippen_koppelt_erste_adresse():
    r = _run(_d(), [["knubbel", 2], ["zeile", 1]], bt=_bt(window_left=87))
    s0, s1 = r["steps"]
    assert s0["scan"][:2] == ["Suche läuft – noch 87 s", True]
    assert [x["text"][0] for x in s0["list"]] == ["RAPOO KB", "MX Anywhere"] and s0["list"][1]["click"]
    assert not s0["list"][0]["click"]
    assert [c["body"] for c in s1["btCalls"] if c["url"] == "bluetooth/pair"] == [{"address": "C0:11:22:33:44:55"}]


def test_weitere_geraete_zugeklappt_und_aufklappbar():
    r = _run(_d(), [["knubbel", 2], ["mehr"]], bt=_bt(window_left=60))
    s0, s1 = r["steps"]
    assert s0["more"] == [] and s0["moreBtn"][1] == "" and "Weitere Geräte (1)" in s0["moreBtn"][0]
    assert [x["text"][0] for x in s1["more"]] == ["Unbekanntes Gerät"] and s1["more"][0]["click"]


def test_ohne_fenster_keine_neuen_geraete_und_kein_klick():
    s = _run(_d(), [["knubbel", 2]])["steps"][0]
    assert all(not x["click"] for x in s["list"]) and s["moreBtn"][1] == "none"


def test_code_gross_und_waehrend_koppeln_keine_zweite_kopplung():
    bt = _bt(window_left=50, pairing={"address": "C0:11:22:33:44:55", "passkey": "042137"})
    s = _run(_d(), [["knubbel", 2]], bt=bt)["steps"][0]
    assert "042137" in s["code"] and "Auf der Tastatur eintippen, dann Enter" in s["code"]
    assert "koppelt …" in s["list"][1]["text"] and not s["list"][1]["click"]
