/* Vibe: meldet Fehler dieser Seite an die Vibe-Oberfläche (postMessage), damit der Agent sie beheben kann.
 * Wird vom Modul geprüft und bei Bedarf wiederhergestellt – bitte nicht ändern oder löschen. */
(function () {
  var sent = 0;
  function send(kind, message, stack) {
    if (sent >= 20 || !window.parent || window.parent === window) return;
    sent += 1;
    try {
      window.parent.postMessage({
        source: "vibe-report", kind: kind,
        message: String(message || "").slice(0, 2000), stack: String(stack || "").slice(0, 4000),
      }, "*");
    } catch (e) { /* nichts: Meldungen dürfen die App nie stören */ }
  }
  window.addEventListener("error", function (e) { send("error", e.message, e.error && e.error.stack); });
  window.addEventListener("unhandledrejection", function (e) {
    var r = e.reason; send("promise", r && r.message ? r.message : r, r && r.stack);
  });
})();
