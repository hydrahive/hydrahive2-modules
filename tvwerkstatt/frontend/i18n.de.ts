// Deutsche Texte der TV-Werkstatt. Einfach, ohne Fachwörter des Servers.
export const de = {
  tvwerkstatt: {
    title: "TV-Werkstatt",
    subtitle: "Startbildschirm und Zusätze für deinen Fernseher bauen und hinüberschieben.",
    devices: "Fernseher",
    no_devices: "Noch kein Fernseher eingetragen.",
    adb: {
      open: "Debugging offen", closed: "Debugging zu", unauthorized: "Freigabe am Fernseher fehlt", unknown: "nicht geprüft",
    },
    kind: { android_tv: "Android TV", google_tv: "Google TV" },
    device: {
      need_setup: "Fernseher lassen sich eintragen, sobald die Werkstatt eingerichtet ist.",
      add_title: "Fernseher hinzufügen",
      add_explain: "Am Fernseher muss das Debugging über das Netzwerk eingeschaltet sein. Beim ersten Prüfen fragt der "
        + "Fernseher „Debugging zulassen?“ – bitte mit der Fernbedienung bestätigen. Am Fernseher wird dabei nichts "
        + "verstellt, nur gelesen.",
      name: "Name", name_ph: "z. B. Wohnzimmer", address: "Adresse im Heimnetz",
      add: "Hinzufügen und prüfen",
      checking: "Wird geprüft …",
      authorize: "Bitte jetzt am Fernseher „Debugging zulassen?“ bestätigen (am besten „Immer zulassen“).",
      check: "Erneut prüfen",
      remove: "Entfernen",
      remove_confirm: "Fernseher aus der Werkstatt entfernen? Am Fernseher selbst ändert sich nichts.",
      our_home: "Startbildschirm der Werkstatt ist aktiv",
    },
    build: {
      title: "Startbildschirm",
      explain: "Baut den Startbildschirm von cleanyourtv aus einem festen, geprüften Stand. Am Fernseher passiert dabei "
        + "nichts. Ein Bau dauert etwa eine Minute.",
      need_setup: "Bauen geht, sobald die Werkstatt eingerichtet ist.",
      start: "Startbildschirm bauen", again: "Neu bauen",
      running: "Wird gebaut … Schritt {{n}} von {{total}}",
      done: "Gebaut und geprüft.",
      version: "Version {{v}}", hash: "Prüfsumme {{h}}", source: "Quelle: cleanyourtv, Stand {{c}}",
      log: "Protokoll anzeigen",
    },
    bstep: {
      container: "Bauumgebung starten", fetch: "Quelle holen", verify: "Quelle prüfen", build: "Bauen",
      collect: "Ergebnis prüfen", done: "Fertig",
    },
    install: {
      start: "Auf den Fernseher schieben",
      confirm: "Startbildschirm jetzt auf den Fernseher schieben? Danach ist er Home; der bisherige Startbildschirm wird "
        + "nur abgeschaltet, nicht gelöscht. „Zurück zum Original“ geht jederzeit.",
      restore: "Zurück zum Original",
      restore_confirm: "Wieder den ursprünglichen Startbildschirm verwenden? Der Startbildschirm der Werkstatt bleibt "
        + "installiert, ist aber nicht mehr Home.",
      running: "Wird aufgespielt … {{step}}",
      restoring: "Original wird zurückgeholt …",
      need_build: "Zum Aufspielen zuerst unten den Startbildschirm bauen.",
    },
    istep: {
      container: "Bauumgebung starten", verify: "Gebaute App prüfen", push: "Auf den Fernseher übertragen",
      start: "Neuen Startbildschirm starten", switch: "Home umstellen", restore: "Original zurückholen",
    },
    container: {
      missing: "nicht eingerichtet", stopped: "bereit (ruht)", running: "läuft", unknown: "Zustand unbekannt",
    },
    setup: {
      title: "Bauumgebung",
      explain: "Die Werkstatt baut in einem abgeschotteten Bereich auf diesem Server. Er darf ins Internet und nur an "
        + "die eingetragenen Fernseher, nicht an den Server oder andere Geräte zu Hause. Einrichten lädt etwa 1 GB und "
        + "dauert einige Minuten.",
      license: "Ich nehme die Lizenzbedingungen von Google für die Android-Werkzeuge an (Android SDK License).",
      start: "Werkstatt einrichten",
      retry: "Nochmal versuchen",
      running: "Wird eingerichtet … Schritt {{n}} von {{total}}",
      failed_at: "Hängen geblieben bei: {{step}}",
      ready: "Die Werkstatt ist eingerichtet. Sie ruht, solange nichts gebaut wird.",
      stop: "Anhalten",
      remove: "Werkstatt abbauen",
      remove_confirm: "Werkstatt wirklich abbauen? Die Werkzeuge werden gelöscht, der Schlüssel zum Signieren bleibt "
        + "gesichert. Einrichten geht danach jederzeit wieder.",
    },
    step: {
      network: "Abgeschottetes Netz anlegen",
      container: "Bauumgebung starten",
      user: "Benutzer vorbereiten",
      packages: "Grundpakete laden",
      tools: "Android-Werkzeuge laden und prüfen",
      sdk: "Android-Bausteine laden",
      keystore: "Schlüssel zum Signieren übernehmen",
      probe: "Abschottung prüfen",
      stop: "Bauumgebung ruhen lassen",
      done: "Fertig",
    },
    err: {
      general: "Das hat nicht geklappt. Bitte später noch einmal versuchen.",
      tvw_no_incus: "Auf diesem Server gibt es keine Container-Umgebung. Die TV-Werkstatt braucht sie für den Bau.",
      tvw_busy: "Es läuft gerade schon etwas. Bitte kurz warten.",
      tvw_license_required: "Bitte zuerst die Lizenzbedingungen annehmen.",
      tvw_interrupted: "Das Einrichten wurde unterbrochen (z. B. durch einen Neustart). Bitte nochmal versuchen.",
      tvw_setup_failed: "Das Einrichten ist an einem Schritt gescheitert.",
      tvw_checksum_mismatch: "Die geladenen Android-Werkzeuge passen nicht zur Prüfsumme von Google. Aus Vorsicht wurde "
        + "nichts entpackt.",
      tvw_launch_failed: "Die Bauumgebung ließ sich nicht anlegen.",
      tvw_no_storage_pool: "Auf dem Server ist kein Speicherplatz für die Bauumgebung eingerichtet.",
      tvw_container_down: "Die Bauumgebung reagiert nicht.",
      tvw_container_remove_failed: "Die Bauumgebung ließ sich nicht abbauen.",
      tvw_no_address: "Die Bauumgebung hat keine Netzwerkadresse bekommen.",
      tvw_net_open: "Die Abschottung greift nicht: Die Bauumgebung erreicht etwas, das gesperrt sein muss. Aus Vorsicht "
        + "geht es hier nicht weiter.",
      tvw_dns_failed: "Die Bauumgebung kann keine Namen im Internet auflösen.",
      tvw_net_probe_failed: "Die Prüfung der Abschottung ließ sich nicht durchführen.",
      tvw_network_missing: "Das abgeschottete Netz fehlt.",
      tvw_incus_failed: "Das abgeschottete Netz ließ sich nicht einrichten.",
      tvw_subnet_unavailable: "Für das abgeschottete Netz ist kein freier Adressbereich da.",
      tvw_acl_dirty: "Die Sperrliste enthält doppelte Regeln. Bitte die Werkstatt abbauen und neu einrichten.",
      tvw_bad_address: "Diese Adresse passt nicht zu einem Fernseher im Heimnetz.",
      tvw_bad_name: "Bitte einen kurzen Namen ohne Sonderzeichen angeben (höchstens 60 Zeichen).",
      tvw_not_set_up: "Bitte zuerst die Werkstatt einrichten.",
      tvw_device_exists: "Ein Fernseher mit dieser Adresse ist schon eingetragen.",
      tvw_device_not_found: "Diesen Fernseher gibt es nicht (mehr).",
      tvw_device_probe_failed: "Der Fernseher ließ sich nicht abfragen.",
      tvw_adb_unauthorized: "Am Fernseher wurde „Debugging zulassen?“ nicht bestätigt. Bitte „Erneut prüfen“ und "
        + "dann am Fernseher bestätigen.",
      tvw_adb_closed: "Der Fernseher antwortet nicht. Ist er an und das Debugging über das Netzwerk eingeschaltet?",
      tvw_sdk_too_old: "Das Android auf diesem Fernseher ist zu alt für den Startbildschirm (mindestens Android 8).",
      tvw_source_failed: "Die Quelle ließ sich nicht holen. Ist das Internet erreichbar?",
      tvw_source_mismatch: "Die Quelle passt nicht zum geprüften Stand. Aus Vorsicht wurde nicht gebaut.",
      tvw_build_failed: "Der Bau ist gescheitert. Das Protokoll zeigt, woran.",
      tvw_build_unreadable: "Die gebaute App ließ sich nicht prüfen.",
      tvw_build_unexpected: "Der Bau hat eine andere App erzeugt als erwartet. Sie wird nicht verwendet.",
      tvw_confirm_required: "Bitte die Rückfrage bestätigen.",
      tvw_no_build: "Es gibt noch keinen fertigen Bau. Bitte zuerst den Startbildschirm bauen.",
      tvw_no_stock_home: "Der ursprüngliche Startbildschirm dieses Fernsehers ist unbekannt. Aus Vorsicht wird nichts "
        + "umgestellt. Bitte „Erneut prüfen“.",
      tvw_build_changed: "Die gebaute App hat sich verändert. Bitte neu bauen.",
      tvw_install_failed: "Das Aufspielen ist gescheitert. Am Fernseher wurde nichts umgestellt.",
      tvw_home_not_started: "Der neue Startbildschirm ließ sich nicht starten. Am Fernseher wurde nichts umgestellt.",
      tvw_home_not_switched: "Home ließ sich nicht umstellen. Der ursprüngliche Startbildschirm ist wieder aktiv.",
      tvw_restore_incomplete: "Der ursprüngliche Startbildschirm ließ sich nicht sicher zurückholen. Bitte am "
        + "Fernseher die Home-Taste drücken und „Erneut prüfen“.",
      tvw_signer_mismatch: "Die gebaute App trägt eine fremde Unterschrift. Auf dem Fernseher ließe sie sich nicht "
        + "einspielen.",
    },
  },
}
