"""Kiosk (Statuszentrale, Etappe S1): Seite für den Browser auf dem Gehäuse-Display und der „Zurück“-Knopf.

Der Kiosk-Browser hat keinen HydraHive-Login. Er kommt über die Geräte-Routen des Kerns (`/api/module-device/vitrine/…`,
mit Rate-Limit) und braucht den Kiosk-Schlüssel (<daten>/kiosk.key, 0600, vom Installer erzeugt). Zusätzlich gilt: nur von
127.0.0.1/::1. S1 zeigt nur einen Platzhalter ohne Daten; die Statuszentrale mit Daten folgt in S2.
"""
from __future__ import annotations

import hmac
import html
from pathlib import Path

from renderer import mode

MIN_KEY = 32
LOCAL = frozenset({"127.0.0.1", "::1"})


def key_ok(data_dir: Path, given: str | None) -> bool:
    try:
        want = (data_dir / "kiosk.key").read_text().strip()
    except OSError:
        return False
    if len(want) < MIN_KEY or not given:
        return False
    return hmac.compare_digest(want.encode(), given.encode())


def local_ok(host: str | None) -> bool:
    return host in LOCAL


def back(data_dir: Path) -> None:
    mode.request_back(data_dir)


def page(key: str) -> str:
    k = html.escape(key, quote=True)
    return f"""<!doctype html><html lang="de"><meta charset="utf-8"><title>Vitrine</title>
<style>
html,body{{margin:0;height:100%;background:#0b1220;color:#e8eef8;font-family:"DejaVu Sans",sans-serif;cursor:default}}
body{{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:48px}}
h1{{font-size:80px;margin:0}}#uhr{{font-size:180px;font-weight:bold}}#datum{{font-size:48px;color:#8d9ab0}}
p{{font-size:40px;color:#8d9ab0;text-align:center;max-width:900px}}
button{{font-size:56px;padding:28px 70px;border-radius:20px;border:3px solid #69d7ff;background:#151c2b;color:#e8eef8}}
</style>
<h1>🐉 Statuszentrale</h1><div id="uhr"></div><div id="datum"></div>
<p>Hier erscheinen bald Meldungen, Agenten, Aufgaben und der Zustand des Rechners.</p>
<button id="zurueck">Zurück zum Video</button>
<script>
const k = "{k}";
function tick() {{
  const d = new Date();
  document.getElementById("uhr").textContent = d.toLocaleTimeString("de-DE", {{hour: "2-digit", minute: "2-digit"}});
  document.getElementById("datum").textContent = d.toLocaleDateString("de-DE", {{weekday: "long", day: "numeric", month: "long"}});
}}
tick(); setInterval(tick, 1000);
document.getElementById("zurueck").onclick = () => fetch("back?k=" + encodeURIComponent(k), {{method: "POST"}});
</script></html>"""
