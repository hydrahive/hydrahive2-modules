"""S7 Bluetooth-Seite am Kiosk, Teil 2: Hinweise, nicht verfügbar, Text statt HTML, Seitenwechsel, Rückkehr, Klick-Sperre."""
from __future__ import annotations

import json
import shutil
import subprocess

import pytest
from test_kiosk_bt_js import EXTRA, MAUS, _bt, _d, _run
from test_kiosk_page_js import DOM

pytestmark = pytest.mark.skipif(not shutil.which("node"), reason="node fehlt")


def test_fehler_vom_server_als_hinweis():
    r = _run(_d(), [["knubbel", 2], ["post", {"status": 409, "code": "window_closed"}], ["scan"]], bt=_bt())
    assert "Kopplungsfenster ist zu" in r["steps"][-1]["hint"]


def test_schwaches_signal_und_dienstfehler():
    s = _run(_d(), [["knubbel", 2]], bt=_bt(weak_signal=True, error="MX nicht gekoppelt: AuthenticationFailed"))["steps"][0]
    assert "Antennen am Rechner prüfen" in s["hint"] and "AuthenticationFailed" in s["hint"]


def test_nicht_verfuegbar():
    s = _run(_d(), [["knubbel", 2]], bt={"available": False, "devices": []})["steps"][0]
    assert s["scan"][2] == "none" and "nicht verfügbar" in json.dumps(s["list"], ensure_ascii=False)


def test_namen_nur_als_text():
    bad = dict(MAUS, name="<img src=x onerror=alert(1)>", paired=True)
    s = _run(_d(), [["knubbel", 2]], bt=_bt(devices=[bad]))["steps"][0]
    assert s["list"][0]["text"][0] == "<img src=x onerror=alert(1)>"


def test_chat_knubbel_verlaesst_bluetooth():
    s = _run(_d(), [["knubbel", 2], ["knubbel", 3]])["steps"][-1]
    assert s["bt"] == "none" and s["chat"] == "" and s["knubbel"] == ["○", "○", "Bluetooth", "●"]


def test_seiten_knubbel_verlaesst_bluetooth():
    r = _run(_d(), [["knubbel", 2], ["knubbel", 0]])
    s = r["steps"][-1]
    assert s["bt"] == "none" and s["shown"] == r["start"]["shown"] and "messages" in s["shown"]


def test_rueckkehr_nur_ohne_offenes_fenster():
    r = _run(_d(), [["knubbel", 2], ["warten", 200]], bt=_bt(window_left=90))
    assert r["steps"][-1]["bt"] == "", "Fenster offen → Seite bleibt"
    r = _run(_d(), [["knubbel", 2], ["warten", 200]])
    assert r["steps"][-1]["bt"] == "none", "Fenster zu → nach der Rückkehrzeit wieder Seite 1"


def test_fenster_geht_zu_neue_geraete_nicht_mehr_klickbar():
    """Stand wechselt von offen auf zu: Die Seite baut neu, kein ungekoppeltes Gerät darf noch einen Klick haben."""
    r = _run(_d(), [["knubbel", 2], ["stand", _bt(window_left=0)], ["laden"]], bt=_bt(window_left=5))
    assert r["steps"][0]["list"][1]["click"], "vorher (Fenster offen) klickbar"
    last = r["steps"][-1]
    assert [x["text"][0] for x in last["list"]] == ["RAPOO KB"] and not any(x["click"] for x in last["list"])


def test_btrow_klickt_ohne_fenster_nie():
    """Zweite Schicht: btRow selbst gibt einem neuen Gerät ohne offenes Fenster keinen Klick (auch wenn es in der Liste wäre)."""
    from backend import kiosk
    html = kiosk.page("K")
    script = "\n".join(part.split("</script>", 1)[0] for part in html.split("<script>")[1:])
    js = (DOM + EXTRA + "DATA = " + json.dumps(_d()) + "; BT = " + json.dumps(_bt()) + ";\n" + script
          + "\nconst r = btRow(" + json.dumps(MAUS) + ", false, null); console.log(JSON.stringify(typeof r.onclick));")
    js = js.replace("const fetch = async", "let fetch = async", 1)
    out = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=30, check=True)
    assert json.loads(out.stdout.strip().splitlines()[-1]) != "function"
