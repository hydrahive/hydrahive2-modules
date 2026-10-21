"""S6 Chat-Seite: eigene Seite + Knubbel, Tippen holt den Chat, Enter schickt, Antwort als Text (Node + Mini-DOM)."""
from __future__ import annotations

import json
import shutil
import subprocess

import pytest
from test_kiosk_page_js import DOM, HOME, MACHINE, _data, _m

pytestmark = pytest.mark.skipif(not shutil.which("node"), reason="node fehlt")

EXTRA = r"""
let NOW = 1000000; Date.now = () => NOW;
const listeners = {};
document.addEventListener = (ev, fn) => { (listeners[ev] = listeners[ev] || []).push(fn); };
const key = (k) => { const e = {key: k, ctrlKey: false, altKey: false, metaKey: false, prevented: false,
                                 preventDefault() { this.prevented = true; }};
                     (listeners["keydown"] || []).forEach((f) => f(e)); return e; };
let CHAT = {status: 200, reply: "Hallo Till, 22,4 °C."}, HIST = {messages: []};
const realFetch = fetch;
fetch = async (u, o) => {
  if (u.startsWith("chat")) {
    calls.push({url: "chat", method: (o && o.method) || "GET", body: o && o.body ? JSON.parse(o.body) : null});
    if (o && o.method === "POST") {
      if (CHAT.status !== 200) return {ok: false, status: CHAT.status, json: async () => ({detail: {code: CHAT.code}})};
      HIST.messages.push({role: "user", text: JSON.parse(o.body).text}, {role: "assistant", text: CHAT.reply});
      return {ok: true, status: 200, json: async () => ({reply: CHAT.reply})};
    }
    return {ok: true, status: 200, json: async () => JSON.parse(JSON.stringify(HIST))};
  }
  return realFetch(u, o);
};
"""

STEPS = r"""
const tick = () => new Promise((r) => setTimeout(r, 0));
const page = () => ({
  shown: main.children.filter((c) => c.style.display !== "none").map((c) => c.id.slice(2)),
  chat: document.getElementById("chat").style.display,
  knubbel: document.getElementById("knubbel").all("button").map((b) => b.textContent),
  input: document.getElementById("c-eingabe").value,
  inputDisabled: document.getElementById("c-eingabe").disabled,
  log: document.getElementById("c-verlauf").children.map((c) => [c.className, c.textContent]),
  status: document.getElementById("c-status").textContent,
});
(async () => {
  DATA = __DATA__;
  __SCRIPT__
  for (let i = 0; i < 5; i++) await tick();
  const out = {start: page(), steps: []};
  for (const s of __STEPS__) {
    if (s[0] === "taste") out.steps.push({prevented: key(s[1]).prevented});
    if (s[0] === "knubbel") document.getElementById("knubbel").all("button")[s[1]].onclick();
    if (s[0] === "antwort") Object.assign(CHAT, s[1]);
    for (let i = 0; i < 8; i++) await tick();
    out.steps.push({...page(), posts: calls.filter((c) => c.url === "chat" && c.method === "POST").map((c) => c.body)});
  }
  console.log(JSON.stringify(out));
})();
"""


def _run(data: dict, steps: list) -> dict:
    from backend import kiosk
    html = kiosk.page("K")
    script = "\n".join(part.split("</script>", 1)[0] for part in html.split("<script>")[1:])
    js = (DOM.replace("addEventListener() {}", "addEventListener() {}") + EXTRA
          + STEPS.replace("__DATA__", json.dumps(data)).replace("__STEPS__", json.dumps(steps)).replace("__SCRIPT__", script))
    js = js.replace("const fetch = async", "let fetch = async", 1)
    out = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=30, check=True)
    return json.loads(out.stdout.strip().splitlines()[-1])


PAGES = {"messages": 1, "home": 1, "hydra": 1, "tasks": 2, "github": 2, "machine": 2, "mining": 2}


def _d(chat=True):
    lay = {"order": list(PAGES), "hidden": [], "messages_max": 3, "mining_in_machine": True, "pages": dict(PAGES),
           "chat_enabled": chat, "bluetooth_enabled": False, "return_seconds": 120}   # Bluetooth-Knubbel: test_kiosk_bt_js
    return _data([_m(1)], 1, [], home=HOME, machine=MACHINE, layout=lay)


def test_chat_knubbel_ganz_rechts_und_seite_versteckt():
    r = _run(_d(), [])
    assert r["start"]["knubbel"] == ["●", "○", "Chat"] and r["start"]["chat"] == "none"


def test_ohne_chat_kein_knubbel():
    r = _run(_d(chat=False), [["taste", "a"]])
    assert r["start"]["knubbel"] == ["●", "○"] and r["steps"][-1]["chat"] == "none", "Tippen holt nichts, wenn Chat aus"


def test_klick_auf_chat_zeigt_seite():
    r = _run(_d(), [["knubbel", 2]])
    s = r["steps"][0]
    assert s["chat"] == "" and s["shown"] == [] and s["knubbel"] == ["○", "○", "●"]


def test_tippen_auf_anderer_seite_holt_chat_mit_buchstabe():
    r = _run(_d(), [["taste", "W"]])
    s = r["steps"][-1]
    assert s["chat"] == "" and s["input"] == "W"
    assert s["knubbel"] == ["○", "○", "●"], "Knubbel zeigen den Chat als aktuelle Seite"
    assert r["steps"][0]["prevented"] is True, "Buchstabe nicht doppelt"


def test_sondertasten_holen_den_chat_nicht():
    r = _run(_d(), [["taste", "Shift"], ["taste", "ArrowDown"], ["taste", "F5"]])
    assert r["steps"][-1]["chat"] == "none" and r["steps"][-1]["input"] == ""


def test_enter_schickt_antwort_erscheint():
    r = _run(_d(), [["taste", "H"], ["taste", "i"], ["taste", "Enter"]])
    s = r["steps"][-1]
    assert s["posts"] == [{"text": "Hi"}] and s["input"] == "" and not s["inputDisabled"]
    assert [c for c, _ in s["log"]] == ["c-user", "c-hydra"] and s["log"][1][1] == "Hallo Till, 22,4 °C."


def test_leeres_enter_schickt_nichts_escape_leert():
    r = _run(_d(), [["knubbel", 2], ["taste", "Enter"], ["taste", "x"], ["taste", "Escape"]])
    assert r["steps"][-1]["posts"] == [] and r["steps"][-1]["input"] == ""


def test_busy_fehlerzeile_text_bleibt():
    r = _run(_d(), [["antwort", {"status": 409, "code": "busy"}], ["taste", "x"], ["taste", "Enter"]])
    s = r["steps"][-1]
    assert s["status"] == "Hydra antwortet noch – bitte kurz warten." and s["input"] == "x"


def test_antwort_nur_als_text():
    r = _run(_d(), [["antwort", {"reply": "<img src=x onerror=alert(1)>"}], ["taste", "x"], ["taste", "Enter"]])
    assert r["steps"][-1]["log"][1][1] == "<img src=x onerror=alert(1)>"
