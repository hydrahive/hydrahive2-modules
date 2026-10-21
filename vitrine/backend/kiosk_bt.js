// Bluetooth am Gehäuse (S7) – wird von kiosk.page() in die Seite eingebettet (eine Datei, keine externen Quellen).
// Eigene Seite zwischen den Seiten 1–3 und dem Chat. Gerät suchen, Tippen koppelt, Code groß. KEIN Abkoppeln am Kiosk
// (SPEC S7: niemand soll im Vorbeigehen die Tastatur entkoppeln) – das geht nur im Cockpit. Texte nur per textContent.
let btOn = false, btWindow = 0, btMoreOpen = false, btTimer = null;
const BT_ERR = {window_closed: "Das Kopplungsfenster ist zu – bitte „Gerät koppeln“ drücken.",
                not_seen: "Gerät nicht mehr in der Suche – bitte neu suchen.", unavailable: "Bluetooth ist gerade nicht verfügbar."};
const BT_KIND = {keyboard: "⌨", mouse: "🖱", headphones: "🎧", speaker: "🔊", phone: "📱", other: "•"};
function btEnabled(lay) { return lay.bluetooth_enabled !== false; }
function btBusy() { return btOn && btWindow > 0; }       // offenes Fenster hält die Seite (wie bt_busy im Dienst)
$("bt").style.display = "none";
function btShow(on) {
  btOn = on;
  $("bt").style.display = on ? "" : "none";
  if (on) { if (typeof chatOn !== "undefined" && chatOn) chatShow(false); $("bereiche").style.display = "none"; btLoad(); }
  else if (!(typeof chatOn !== "undefined" && chatOn)) $("bereiche").style.display = "";
  clearInterval(btTimer); btTimer = on ? setInterval(btLoad, 2000) : null;
  if (lastData) render(lastData);
}
function btBars(n) { return "▮".repeat(n) + "▯".repeat(Math.max(0, 4 - n)); }
function btRow(d, open, pairing) {
  const r = document.createElement("div");
  r.className = "bt-zeile" + (d.paired ? " gekoppelt" : "");
  const busy = pairing && d.addresses.includes(pairing);
  const n = document.createElement("span"); n.className = "bt-name"; n.textContent = d.name;
  const a = document.createElement("span"); a.className = "bt-art"; a.textContent = BT_KIND[d.kind] || "•";
  const s = document.createElement("span"); s.className = "bt-signal";
  s.textContent = btBars(d.bars) + (d.rssi != null ? "  " + d.rssi + " dBm" : "");
  const z = document.createElement("span"); z.className = "bt-zustand";
  z.textContent = busy ? "koppelt …" : d.connected ? "verbunden" : d.paired ? "gekoppelt" : "antippen zum Koppeln";
  r.append(n, a, s, z);
  if (!d.paired && open && !pairing) r.onclick = () => btPair(d.addresses[0]);
  return r;
}
function btRender(v) {
  const list = $("bt-liste"), more = $("bt-weitere"); list.replaceChildren(); more.replaceChildren();
  if (!v.available) {
    btWindow = 0; $("bt-scan").style.display = "none"; $("bt-mehr").style.display = "none"; $("bt-code").textContent = "";
    $("bt-hinweis").textContent = "";
    return line(list, "Bluetooth ist gerade nicht verfügbar", "aus");
  }
  btWindow = v.window_left || 0;
  const open = btWindow > 0, pairing = v.pairing && v.pairing.address;
  $("bt-scan").style.display = "";
  $("bt-scan").disabled = open;
  $("bt-scan").textContent = open ? "Suche läuft – noch " + btWindow + " s" : "Gerät koppeln";
  const hints = [];
  if (v.weak_signal) hints.push("Sehr schwacher Empfang – Antennen am Rechner prüfen");
  if (v.error) hints.push(v.error);
  if (btHint) hints.push(btHint);
  $("bt-hinweis").textContent = hints.join("  ·  ");
  $("bt-code").replaceChildren();
  if (v.pairing && v.pairing.passkey) {
    const c = document.createElement("div"); c.className = "bt-zahl"; c.textContent = v.pairing.passkey;
    const t = document.createElement("div"); t.className = "klein"; t.textContent = "Auf der Tastatur eintippen, dann Enter";
    $("bt-code").append(c, t);
  }
  const main = v.devices.filter((d) => d.paired || (open && !d.more));
  const extra = open ? v.devices.filter((d) => !d.paired && d.more) : [];
  for (const d of main) list.appendChild(btRow(d, open, pairing));
  if (!main.length) line(list, open ? "Suche läuft – Gerät in den Kopplungsmodus bringen" : "Keine gekoppelten Geräte", "aus");
  $("bt-mehr").style.display = extra.length ? "" : "none";
  $("bt-mehr").textContent = (btMoreOpen ? "▾ " : "▸ ") + "Weitere Geräte (" + extra.length + ")";
  if (btMoreOpen) for (const d of extra) more.appendChild(btRow(d, open, pairing));
}
let btHint = "", btLast = null;
async function btLoad() {
  try {
    const r = await fetch("bluetooth?k=" + encodeURIComponent(k), {cache: "no-store"});
    if (!r.ok) throw new Error(r.status);
    btLast = await r.json();
  } catch (e) { btLast = {available: false, devices: []}; }
  btRender(btLast);
}
async function btPost(path, body) {
  btHint = "";
  try {
    const r = await fetch(path + "?k=" + encodeURIComponent(k), {method: "POST", headers: {"Content-Type": "application/json"},
                                                                body: JSON.stringify(body || {})});
    if (!r.ok) {
      let code = "unavailable";
      try { code = (await r.json()).detail.code; } catch (e) { /* bleibt unavailable */ }
      btHint = BT_ERR[code] || BT_ERR.unavailable;
    }
  } catch (e) { btHint = BT_ERR.unavailable; }
  await btLoad();
}
function btPair(addr) { lastInput = Date.now(); return btPost("bluetooth/pair", {address: addr}); }
$("bt-scan").onclick = () => { lastInput = Date.now(); btPost("bluetooth/scan"); };
$("bt-mehr").onclick = () => { btMoreOpen = !btMoreOpen; if (btLast) btRender(btLast); };
