// Deutsche Texte des Reiters Zusätze.
export const add = {
  on_tv: "Auf „{{name}}“", none_yet: "Noch keine Zusätze von der Werkstatt.", catalog: "Katalog",
  no_catalog: "Der Katalog kommt aus cleanyourtv am festen Stand. Einmal laden, dann ist er da.",
  load: "Katalog laden", search: "Suchen …", working: "Läuft … {{step}}",
  explain: "Jeder Zusatz wird in der Bauumgebung aus dem Quelltext gebaut und von der Werkstatt installiert. "
    + "Installationsskripte der Zusätze laufen nicht, Sonderrechte vergibt die Werkstatt nicht – was ein Zusatz "
    + "danach braucht, steht in seiner Beschreibung. Gelb und Rot markieren Rechte, die mehr dürfen.",
  filter: { all: "Alle", none: "Ohne Rechte", dream: "Bildschirmschoner", installed: "Installiert" },
  step: { container: "Bauumgebung starten", catalog: "Katalog holen", fetch: "Quelle holen",
    verify: "Bauwerkzeug prüfen", build: "Bauen", collect: "Ergebnis prüfen", push: "Auf den Fernseher",
    remove: "Entfernen" },
  dream: "Bildschirmschoner", installed: "installiert", no_perms: "keine Rechte",
  too_old: "Braucht Android {{v}} oder neuer.", install: "Bauen & installieren", rebuild: "Neu bauen",
  remove: "Entfernen",
  confirm_install: "„{{name}}“ bauen und auf den Fernseher installieren?\n\nRechte: {{perms}}\n\nDauert beim "
    + "ersten Mal etwa eine Minute.",
  confirm_remove: "„{{name}}“ vom Fernseher entfernen?",
  perm: { INTERNET: "Internet", ACCESS_NETWORK_STATE: "Netzstatus", SYSTEM_ALERT_WINDOW: "über Apps einblenden",
    RECEIVE_BOOT_COMPLETED: "startet beim Einschalten", FOREGROUND_SERVICE: "läuft im Hintergrund",
    FOREGROUND_SERVICE_SPECIAL_USE: "Hintergrund (Sonderfall)", FOREGROUND_SERVICE_DATA_SYNC: "Hintergrund (Abgleich)",
    WRITE_SECURE_SETTINGS: "ändert Systemeinstellungen", PACKAGE_USAGE_STATS: "sieht App-Nutzung",
    ACCESS_COARSE_LOCATION: "ungefährer Standort", BLUETOOTH: "Bluetooth", BLUETOOTH_ADMIN: "Bluetooth steuern",
    BLUETOOTH_CONNECT: "Bluetooth verbinden", WAKE_LOCK: "hält wach", SCHEDULE_EXACT_ALARM: "genaue Wecker" },
}

// Fehlertexte des Reiters (werden in err.* eingemischt).
export const addErr = {
  tvw_addons_catalog_failed: "Der Katalog ließ sich nicht lesen.",
  tvw_addon_unknown: "Diesen Zusatz gibt es im Katalog nicht.",
  tvw_addon_remove_failed: "Der Zusatz ließ sich nicht entfernen.",
}
