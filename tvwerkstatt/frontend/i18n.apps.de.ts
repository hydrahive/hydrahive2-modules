// Deutsche Texte des Reiters Apps.
export const apps = {
  store_title: "Play Store am Fernseher", search: "Suchen", search_ph: "z. B. Kodi, Mediathek …",
  store_hint: "Die Suche öffnet den Play Store direkt am Fernseher. Installieren bestätigst du dort mit der "
    + "Fernbedienung – das lässt Google nur am Gerät zu.",
  search_bad: "Bitte nur Buchstaben, Ziffern, Leerzeichen und . , & ' + - (höchstens 60 Zeichen).",
  opened: "Der Play Store ist am Fernseher offen.",
  title: "Selbst installierte Apps auf „{{name}}“", read: "Vom Fernseher lesen", read_at: "gelesen {{at}}",
  empty: "Erst „Vom Fernseher lesen“.", off: "abgeschaltet", open: "Im Store öffnen", uninstall: "Deinstallieren",
  uninstall_confirm: "„{{name}}“ jetzt vom Fernseher deinstallieren? Ihre Daten auf dem Fernseher gehen dabei verloren. "
    + "Neu installieren geht über den Play Store.",
  src_store: "Play Store", src_other: "andere Quelle", src_locked: "geschützt",
  preinstalled_hint: "Vorinstallierte Apps stehen nicht hier, sondern unter „Entrümpeln“ (dort nur abschalten).",
  job: { store_read: "Apps werden gelesen …", store_open: "Play Store wird geöffnet …",
    store_uninstall: "Wird deinstalliert …" },
}

// Fehlertexte des Reiters (werden in err.* eingemischt).
export const appsErr = {
  tvw_store_bad_query: "Bitte einen Suchtext eingeben: Buchstaben, Ziffern, Leerzeichen und . , & ' + -.",
  tvw_store_bad_package: "Diese App gibt es so nicht.",
  tvw_store_failed: "Der Play Store ließ sich am Fernseher nicht öffnen bzw. die App nicht entfernen.",
  tvw_store_locked: "Diese App ist geschützt (Startbildschirm, Play Store oder Android selbst).",
  tvw_store_not_user_app: "Das ist eine vorinstallierte App. Sie lässt sich unter „Entrümpeln“ abschalten.",
}
