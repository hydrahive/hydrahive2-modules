// Deutsche Texte: HydraHive-App auf Fernsehern und Tablets (Reiter Geräte).
export const app = {
  title: "HydraHive-App", none: "Noch kein Fernseher oder Tablet mit der App gekoppelt.",
  explain: "Die App läuft auf Fernsehern und Tablets und verbindet sich von dort mit HydraHive. Zum Koppeln einen "
    + "Namen eingeben, Code erzeugen und ihn in der App eintippen. Der Code gilt 15 Minuten und nur einmal.",
  name: "Name", name_ph: "z. B. Küche Tablet", new_code: "Code erzeugen", code_for: "Code für „{{name}}“",
  code_valid: "noch {{n}} min gültig", server: "Server", pin: "Fingerabdruck",
  code_hint: "Den Code zeigt die Werkstatt nur jetzt. Die App fragt Server und Code beim ersten Start ab.",
  online: "verbunden", offline: "nicht verbunden", revoked: "gesperrt",
  notice: "Testmeldung", notice_ph: "Testmeldung, z. B. Es hat geklingelt", buttons: "Knöpfe",
  buttons_ph: "Knöpfe, z. B. Ansehen, Später", send: "Schicken",
  revoke: "Sperren", remove: "Entfernen",
  revoke_confirm: "„{{name}}“ sperren? Die App verliert sofort den Zugang und muss neu gekoppelt werden.",
  code_hint_pin: "Die App zeigt beim Koppeln einen Fingerabdruck. Er muss genau so aussehen wie hier, sonst abbrechen.",
  build: "App bauen", build_again: "App neu bauen", download: "App herunterladen",
  build_none: "Die App ist noch nicht gebaut. Das dauert etwa eine Minute, am Fernseher passiert dabei nichts.",
  build_need_setup: "Bauen geht, sobald die Werkstatt eingerichtet ist.",
  build_running: "App wird gebaut … Schritt {{n}} von {{total}}", built: "Gebaut: Version {{v}}",
  download_hint: "Zum Aufspielen von Hand, z. B. auf ein Tablet: Datei aufs Gerät bringen und dort öffnen. "
    + "Das Gerät fragt einmal, ob es Apps aus dieser Quelle erlauben soll.",
  bstep: {
    container: "Bauumgebung starten", fetch: "Werkzeuge holen", verify: "Werkzeuge prüfen", unpack: "Quelltext übertragen",
    build: "Prüfen und bauen", collect: "Ergebnis prüfen",
  },
}

// Fehlertexte (werden in err.* eingemischt).
export const appErr = {
  tvw_app_bad_name: "Bitte einen Namen mit höchstens 40 Zeichen eingeben.",
  tvw_app_name_taken: "Diesen Namen hat schon ein gekoppeltes Gerät.",
  tvw_app_not_found: "Dieses Gerät gibt es nicht (mehr).",
  tvw_app_not_revoked: "Erst sperren, dann entfernen.",
  tvw_app_bad_notice: "Bitte einen Text für die Meldung eingeben.",
  tvw_app_code_invalid: "Der Code ist falsch, abgelaufen oder schon benutzt.",
  tvw_app_bad_event: "Die App hat eine unlesbare Meldung geschickt.",
  tvw_app_event_too_large: "Die Meldung der App war zu groß.",
  tvw_app_notice_not_found: "Diese Einblendung gibt es nicht (mehr).",
  tvw_app_bad_answer: "Diese Antwort passt zu keinem Knopf der Einblendung.",
  tvw_app_no_build: "Die App ist noch nicht gebaut.",
  tvw_app_build_perms: "Die gebaute App verlangt andere Rechte als erwartet. Sie wird nicht angeboten.",
  tvw_app_build_too_large: "Die gebaute App ist unerwartet groß. Sie wird nicht angeboten.",
  tvw_app_build_tests: "Die Prüfungen der App sind fehlgeschlagen oder liefen nicht. Sie wird nicht angeboten.",
}
