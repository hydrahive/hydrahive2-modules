"""Kiosk lädt sich nach einem Modul-Update selbst neu (Fund 20.10.2026 auf .2).

Damals: Das Update ersetzte die Dateien, während das alte Backend noch lief. Firefox holte die Seite genau in diesem
Moment: neues HTML, aber ohne das neue Chat-Skript. render() warf daraufhin bei jedem Laden „chatOn is not defined“.
Die Seite zeigte 18 Stunden lang „HydraHive antwortet nicht“, obwohl /data immer 200 lieferte, denn sie lädt nur die
Daten neu, nie sich selbst.
Erwartet jetzt:
- Weicht die Version in /data von der Version der Seite ab → Seite neu laden.
- Fehler in render() sind kein „antwortet nicht“. Nach 3 Fehlern in Folge wird die Seite neu geladen.
- Netzfehler → wie bisher „antwortet nicht“, kein Neuladen.
- Neu laden höchstens einmal pro Minute (kaputte Seite → keine Dauerschleife).
(Node + Mini-DOM aus test_kiosk_page_js, ohne Zusatzpakete.)
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from test_kiosk_page_js import DOM, _data, _m

pytestmark = pytest.mark.skipif(not shutil.which("node"), reason="node fehlt")
BACKEND = Path(__file__).resolve().parents[1] / "backend"

HARNESS = DOM.replace("const fetch = async (u, o) => {", """let FAIL = false;
const fetch = async (u, o) => {
  if (FAIL) throw new TypeError("Failed to fetch");""") + r"""
const cls = new Set();
document.body.classList = {add(c) { cls.add(c); }, remove(c) { cls.delete(c); }, contains(c) { return cls.has(c); }};
let NOW = 1000000; Date.now = () => NOW;
const reloads = [];
const location = {reload() { reloads.push(NOW); }};
const store = {};
const sessionStorage = {getItem(k) { return k in store ? store[k] : null; }, setItem(k, v) { store[k] = String(v); }};
"""

RUN = r"""
const tick = () => new Promise((r) => setTimeout(r, 0));
const settle = async () => { for (let i = 0; i < 6; i++) await tick(); };
(async () => {
  DATA = __DATA__;
  __SCRIPT__
  await settle();
  const out = [];
  const snap = (label) => out.push({label, reloads: reloads.length, offline: cls.has("offline"), kaputt: cls.has("kaputt")});
  snap("start");
  for (const s of __STEPS__) {
    if (s[0] === "netz") FAIL = s[1];
    if (s[0] === "version") DATA.page_version = s[1];
    if (s[0] === "zeit") NOW += s[1];
    if (s[0] === "laden") { await load(); await settle(); }
    snap(s.join(" "));
  }
  console.log(JSON.stringify(out));
})();
"""


def _script(html: str) -> str:
    return "\n".join(part.split("</script>", 1)[0] for part in html.split("<script>")[1:])


def _run(html: str, data: dict, steps: list) -> list[dict]:
    js = HARNESS + RUN.replace("__DATA__", json.dumps(data)).replace("__SCRIPT__", _script(html)) \
        .replace("__STEPS__", json.dumps(steps))
    out = subprocess.run(["node", "-e", js], check=False, capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr[-2000:]
    return json.loads(out.stdout.strip().splitlines()[-1])


def _page() -> str:
    from backend import kiosk
    return kiosk.page("K")


def test_gleiche_version_kein_neuladen():
    from backend import kiosk
    r = _run(_page(), _data([_m(1)], 1, [], page_version=kiosk.page_version()), [["laden"], ["laden"]])
    assert [s["reloads"] for s in r] == [0, 0, 0] and not any(s["offline"] or s["kaputt"] for s in r)


def test_neue_version_auf_dem_server_laedt_die_seite_neu():
    from backend import kiosk
    r = _run(_page(), _data([_m(1)], 1, [], page_version=kiosk.page_version()),
             [["version", "anders123"], ["laden"]])
    assert r[-1]["reloads"] == 1 and not r[-1]["offline"]


def test_vorfall_20_10_seite_ohne_chat_skript_laedt_nach_3_fehlern_neu():
    """Altes Backend liefert neues HTML ohne kiosk_chat.js und /data ohne Version (genau wie am 20.10. um 01:55)."""
    html = (BACKEND / "kiosk_page.html").read_text(encoding="utf-8").replace("__KEY__", "K")
    r = _run(html, _data([_m(1)], 1, []), [["laden"], ["laden"]])
    assert all(not s["offline"] for s in r), "Fehler in der Seite ist kein „HydraHive antwortet nicht“"
    assert r[0]["kaputt"], "eigene Anzeige für Fehler in der Seite"
    assert [s["reloads"] for s in r] == [0, 0, 1], "3. Fehler in Folge → neu laden"


def test_vorfall_mit_version_vom_neuen_backend_laedt_sofort_neu():
    """Sobald das neue Backend läuft, meldet /data eine Version. Die alte Seite kennt sie nicht → sofort neu laden."""
    from backend import kiosk
    html = (BACKEND / "kiosk_page.html").read_text(encoding="utf-8").replace("__KEY__", "K")
    r = _run(html, _data([_m(1)], 1, []), [["version", kiosk.page_version()], ["laden"]])
    assert r[-1]["reloads"] == 1


def test_netzfehler_bleibt_offline_ohne_neuladen_und_erholt_sich():
    from backend import kiosk
    r = _run(_page(), _data([_m(1)], 1, [], page_version=kiosk.page_version()),
             [["netz", True], ["laden"], ["laden"], ["laden"], ["laden"], ["netz", False], ["laden"]])
    assert r[4]["offline"] and not r[4]["kaputt"] and r[4]["reloads"] == 0
    assert not r[-1]["offline"] and r[-1]["reloads"] == 0


def test_neuladen_hoechstens_einmal_pro_minute():
    from backend import kiosk
    r = _run(_page(), _data([_m(1)], 1, [], page_version=kiosk.page_version()),
             [["version", "anders"], ["laden"], ["zeit", 5000], ["laden"], ["zeit", 30000], ["laden"],
              ["zeit", 30000], ["laden"]])
    assert [s["reloads"] for s in r if s["label"] == "laden"] == [1, 1, 1, 2]
