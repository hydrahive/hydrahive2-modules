// Chat am Gehäuse (S6) – wird von kiosk.page() in die Seite eingebettet (eine Datei, keine externen Quellen).
// Eigene Seite nach den Seiten 1–3. Tippen auf einer anderen Seite holt den Chat; Enter schickt, Escape leert.
// Antworten nur als Text (textContent), nie als HTML.
let chatOn = false, chatSending = false;
const CHAT_ERR = {busy: "Hydra antwortet noch – bitte kurz warten.", unavailable: "Hydra ist gerade nicht erreichbar.",
                  invalid: "Bitte 1 bis 2000 Zeichen."};
function chatEnabled(lay) { return lay.chat_enabled !== false; }
$("chat").style.display = "none";                      // Start: Seite 1, Chat verborgen
function chatShow(on) {
  chatOn = on;
  $("chat").style.display = on ? "" : "none";
  $("bereiche").style.display = on ? "none" : "";
  if (on) { $("c-eingabe").focus(); chatHistory(); }
  if (lastData) render(lastData);                       // Knubbel und Seiten passend zeichnen
}
function chatLine(role, text) {
  const d = document.createElement("div");
  d.className = role === "user" ? "c-user" : "c-hydra";
  d.textContent = text;
  $("c-verlauf").appendChild(d);
}
async function chatHistory() {
  try {
    const r = await fetch("chat?k=" + encodeURIComponent(k), {cache: "no-store"});
    if (!r.ok) return;
    const h = await r.json();
    $("c-verlauf").replaceChildren();
    for (const m of h.messages) chatLine(m.role, m.text);
    $("c-verlauf").scrollTop = $("c-verlauf").scrollHeight;
  } catch (e) { /* Verlauf ist Zugabe */ }
}
async function chatSend() {
  const t = $("c-eingabe").value.trim();
  if (!t || chatSending) return;
  chatSending = true; $("c-eingabe").disabled = true; $("c-status").textContent = "Hydra denkt …";
  try {
    const r = await fetch("chat?k=" + encodeURIComponent(k), {method: "POST", headers: {"Content-Type": "application/json"},
                                                            body: JSON.stringify({text: t})});
    if (!r.ok) {
      let code = "unavailable";
      try { code = (await r.json()).detail.code; } catch (e) { /* bleibt unavailable */ }
      $("c-status").textContent = CHAT_ERR[code] || CHAT_ERR.unavailable;
      return;
    }
    $("c-eingabe").value = ""; $("c-status").textContent = "";
    await chatHistory();
  } catch (e) {
    $("c-status").textContent = CHAT_ERR.unavailable;
  } finally {
    chatSending = false; $("c-eingabe").disabled = false; $("c-eingabe").focus();
  }
}
document.addEventListener("keydown", (e) => {
  if (!lastData || !chatEnabled(lastData.layout || {}) || e.ctrlKey || e.altKey || e.metaKey) return;
  if (chatOn) {
    if (e.key === "Enter") { e.preventDefault(); chatSend(); }
    else if (e.key === "Escape") { e.preventDefault(); $("c-eingabe").value = ""; }
    else if (e.key.length === 1 && document.activeElement !== $("c-eingabe") && !$("c-eingabe").disabled) {
      e.preventDefault(); $("c-eingabe").value += e.key; $("c-eingabe").focus();   // Feld ohne Fokus: Zeichen nicht verlieren
    }
    return;
  }
  if (e.key.length === 1) {                              // druckbares Zeichen: Chat holen, Zeichen ins Feld
    e.preventDefault();
    chatShow(true);
    $("c-eingabe").value += e.key;
  }
});
