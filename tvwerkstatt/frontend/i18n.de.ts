// Deutsche Texte der TV-Werkstatt. Einfach, ohne Fachwörter des Servers.
import { apps, appsErr } from "./i18n.apps.de"
import { deb, debErr } from "./i18n.deb.de"

export const de = {
  tvwerkstatt: {
    apps,
    deb,
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
      confirm_gtv: "Startbildschirm jetzt auf diesen Google-TV-Fernseher schieben? Vorher wird Googles Einrichtungs-"
        + "Helfer abgeschaltet, sonst würde er Home übernehmen. Die Tasten YouTube und TV-Symbol auf der Fernbedienung "
        + "tun danach nichts mehr. Nichts wird gelöscht; „Zurück zum Original“ schaltet alles wieder ein.",
    },
    istep: {
      container: "Bauumgebung starten", verify: "Gebaute App prüfen", guard: "Fernseher vorbereiten",
      push: "Auf den Fernseher übertragen",
      start: "Neuen Startbildschirm starten", switch: "Home umstellen", restore: "Original zurückholen",
    },
    tab: {
      desktop: "Desktop", debloat: "Entrümpeln", apps: "Apps", addons: "Zusätze", devices: "Geräte", build: "Bauumgebung",
      addons_soon: "Zusätze kommen danach: Katalog von cleanyourtv und eigene Zusätze per GitHub-Adresse.",
    },
    mood: { morning: "Morgen", evening: "Abend", night: "Nacht" },
    desk: {
      choose: "Fernseher wählen", device: "Gerät", model: "Modell", system: "System", debugging: "Debugging",
      on_tv: "Stand auf dem Fernseher", home: "Startbildschirm", home_ours: "Werkstatt", home_original: "Original",
      unknown: "unbekannt", look_state: "Aussehen", look_none: "noch keines", look_current: "aktuell",
      look_old: "geändert, noch nicht geschoben", apps_known: "Apps bekannt", read_apps: "Apps vom Fernseher lesen",
      container: "Container", home_build: "Startbildschirm gebaut",
      preview_note: "Vorschau, kein echtes Bild vom Fernseher. Tageszeit:",
      step_build: "1 · Bauen", step_install: "2 · Auf den Fernseher schieben", push_look: "Nur das Aussehen schieben",
      push_confirm: "Aussehen jetzt auf den Fernseher schieben? Der Startbildschirm startet dabei kurz neu.",
      hint_ready: "Bereit. Änderungen rechts, dann „Nur das Aussehen schieben“ – ohne neuen Bau.",
      hint_dirty: "Geändert. „Speichern“ merkt es sich, „Nur das Aussehen schieben“ bringt es auf den Fernseher.",
      hint_not_ours: "Auf dem Fernseher läuft noch der Original-Startbildschirm. Erst bauen und hinüberschieben.",
      job_read: "Apps werden vom Fernseher gelesen …", job_push: "Aussehen wird auf den Fernseher geschoben …",
      need_setup: "Zuerst unter „Bauumgebung“ die Werkstatt einrichten.",
      need_device: "Zuerst unter „Geräte“ einen Fernseher eintragen.",
      look: "Aussehen", bg_by_time: "Hintergrund je Tageszeit", own_image: "Eigenes Bild für {{mood}} wählen",
      no_image: "Kein Bild – es gilt die Hintergrundfarbe.", remove_image: "Bild entfernen",
      remove_image_confirm: "Dieses Bild entfernen?", dim: "Hintergrund abdunkeln", columns: "Kacheln pro Reihe",
      dock_title: "Apps in der Leiste (ziehen zum Sortieren, Schalter nimmt heraus)", other_apps: "Weitere Apps",
      read_first: "Noch keine Apps bekannt. Links „Apps vom Fernseher lesen“.", in_dock: "In der Leiste",
      hide: "Ausblenden", hidden: "Ausgeblendet", up: "Nach oben", down: "Nach unten", rename: "Name für {{app}}",
      save: "Speichern", discard: "Verwerfen", no_apps: "Noch keine Apps – erst vom Fernseher lesen.",
      pill_inputs: "Eingänge", pill_network: "Netzwerk", pill_settings: "Einstellungen",
      greet_morning: "Guten Morgen", greet_day: "Guten Tag", greet_evening: "Guten Abend",
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
      ...appsErr,
      ...debErr,
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
      tvw_look_invalid: "Diese Einstellung hat einen ungültigen Wert.",
      tvw_look_push_failed: "Das Aussehen ließ sich nicht vollständig auf den Fernseher schreiben.",
      tvw_image_invalid: "Das ist kein lesbares Bild (JPEG, PNG oder WebP).",
      tvw_image_too_large: "Das Bild ist zu groß (höchstens 15 MB).",
      tvw_too_many_images: "Es sind schon 30 Bilder für diesen Fernseher da. Bitte erst eines entfernen.",
      tvw_image_not_found: "Dieses Bild gibt es nicht (mehr).",
      tvw_wifi_owned_by_setup: "Das gespeicherte WLAN gehört Googles Einrichtungs-Helfer. Abschalten würde das WLAN "
        + "löschen. Bitte am Fernseher das WLAN entfernen und neu verbinden, dann noch einmal. Nichts wurde umgestellt.",
      tvw_wifi_unreadable: "Es ließ sich nicht lesen, wem das gespeicherte WLAN gehört. Aus Vorsicht wurde nichts "
        + "umgestellt.",
      tvw_guard_failed: "Die Vorbereitung am Fernseher lief nicht wie erwartet. Der ursprüngliche Startbildschirm ist "
        + "wieder aktiv.",
      tvw_signer_mismatch: "Die gebaute App trägt eine fremde Unterschrift. Auf dem Fernseher ließe sie sich nicht "
        + "einspielen.",
    },
  },
}
