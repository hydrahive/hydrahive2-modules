// Deutsche Texte des Reiters Entrümpeln.
export const deb = {
  state: "Stand", off: "Abgeschaltet", by_us: "davon von der Werkstatt", todo: "Empfohlen, noch an",
  backup: "Sicherung", none: "noch keine", read_at: "Zuletzt gelesen",
  lists: "Vergleich mit", lists_of: "{{n}} passenden von {{all}} Listen", no_list: "keiner passenden Liste",
  never: "Noch nicht gelesen.", read: "Vom Fernseher lesen", check_update: "Nach Update prüfen",
  undo_all: "Alles zurück", working: "Läuft … {{step}}",
  back_on: "{{n}} App(s), die die Werkstatt abgeschaltet hatte, sind wieder an – vermutlich durch ein Firmware-Update. "
    + "Haken setzen und wieder abschalten.",
  step: { container: "Bauumgebung starten", lists: "Listen holen", packages: "Apps lesen", guard: "Schutz prüfen",
    backup: "Stand sichern", batch: "Schub {{n}}", restore: "Zurückstellen", read: "Stand lesen", other: "…" },
  explain: "Abgeschaltet wird nur, nichts wird gelöscht. Empfohlen ist, was die Mehrheit der Listen von Fernsehern "
    + "mit derselben Firmware abschaltet – und keine davon bewusst anlässt. Vor dem Abschalten prüft der Fernseher "
    + "selbst, ob eine App für Eingänge oder Einstellungen gebraucht wird.",
  title: "Vorinstallierte Apps auf „{{name}}“", empty: "Erst „Vom Fernseher lesen“.",
  others: "Weitere ({{n}}): schon aus, umstritten oder nur von wenigen Listen abgeschaltet",
  of: "{{of}} von {{n}}", kept: "{{n}}× bewusst an",
  of_hint: "So viele der passenden Listen schalten die App ab bzw. lassen sie bewusst an.",
  pick_suggested: "Empfohlene anhaken ({{n}})", switch_off: "Ausgewählte abschalten ({{n}})",
  switch_on: "Wieder einschalten ({{n}})",
  confirm_off: "{{n}} App(s) jetzt am Fernseher abschalten?\n\n{{list}}\n\nNichts wird gelöscht. Vorher wird der Stand "
    + "gesichert; geht etwas schief, schaltet die Werkstatt alles aus diesem Schritt wieder ein.",
  confirm_on: "{{n}} App(s) wieder einschalten?\n\n{{list}}",
  confirm_undo: "Alles wieder einschalten, was die Werkstatt auf diesem Fernseher abgeschaltet hat ({{n}})?",
  mark: { off: "aus", todo: "noch an", locked: "gesperrt", on: "an" },
  lock: { core: "Teil von Android – bleibt immer an.", home: "Startbildschirm – dafür ist „Auf den Fernseher "
    + "schieben“ bzw. „Zurück zum Original“ zuständig." },
  group: { tracking: "Tracking und Fernwartung", ads: "Werbung und Inhalte", demo: "Ladendemo und Hotelmodus",
    home: "Startbildschirm und Bildschirmschoner", help: "Hilfe und Anleitungen", other: "Sonstiges" },
}

// Fehlertexte des Reiters (werden in err.* eingemischt).
export const debErr = {
  tvw_debloat_blocked: "Mindestens eine gewählte App braucht der Fernseher für Eingänge oder Einstellungen (oder "
    + "es ließ sich nicht prüfen). Es wurde nichts abgeschaltet.",
  tvw_debloat_locked: "Diese App ist gesperrt und bleibt an.",
  tvw_debloat_bad_package: "Bitte erst Apps auswählen.",
  tvw_debloat_nothing: "Die Werkstatt hat auf diesem Fernseher nichts abgeschaltet.",
  tvw_debloat_home_changed: "Nach dem Abschalten hat sich der Startbildschirm geändert. Alles aus diesem Schritt ist "
    + "wieder an.",
  tvw_debloat_not_off: "Eine App ließ sich nicht abschalten. Alles aus diesem Schritt ist wieder an.",
  tvw_debloat_restore_incomplete: "Zurückstellen hat nicht ganz geklappt. Bitte „Alles zurück“ und „Nach Update "
    + "prüfen“ nutzen.",
  tvw_debloat_not_on: "Eine App ließ sich nicht wieder einschalten. Bitte noch einmal versuchen.",
  tvw_debloat_read_failed: "Vom Fernseher ließ sich keine App-Liste lesen.",
  tvw_debloat_lists_failed: "Die Listen von cleanyourtv ließen sich nicht lesen.",
}
