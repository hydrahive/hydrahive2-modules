// Texte der TV-Werkstatt (de/en). Einfach, ohne Fachwörter des Servers.
const de = {
  tvwerkstatt: {
    title: "TV-Werkstatt",
    subtitle: "Startbildschirm und Zusätze für deinen Fernseher bauen und hinüberschieben.",
    devices: "Fernseher",
    no_devices: "Noch kein Fernseher eingetragen.",
    adb: {
      open: "Debugging offen", closed: "Debugging zu", unauthorized: "Freigabe am Fernseher fehlt", unknown: "nicht geprüft",
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
    },
  },
}

const en = {
  tvwerkstatt: {
    title: "TV Workshop",
    subtitle: "Build a home screen and add-ons for your TV and push them over.",
    devices: "TVs",
    no_devices: "No TV added yet.",
    adb: {
      open: "Debugging open", closed: "Debugging closed", unauthorized: "Not allowed on the TV yet", unknown: "not checked",
    },
    container: {
      missing: "not set up", stopped: "ready (resting)", running: "running", unknown: "state unknown",
    },
    setup: {
      title: "Build environment",
      explain: "The workshop builds in a sealed-off area on this server. It may reach the internet and only the TVs "
        + "you added, not the server or other devices at home. Setting up downloads about 1 GB and takes a few minutes.",
      license: "I accept Google's license terms for the Android tools (Android SDK License).",
      start: "Set up workshop",
      retry: "Try again",
      running: "Setting up … step {{n}} of {{total}}",
      failed_at: "Stopped at: {{step}}",
      ready: "The workshop is set up. It rests while nothing is being built.",
      stop: "Stop",
      remove: "Remove workshop",
      remove_confirm: "Really remove the workshop? The tools are deleted, the signing key stays saved. You can set it "
        + "up again at any time.",
    },
    step: {
      network: "Create sealed-off network",
      container: "Start build environment",
      user: "Prepare user",
      packages: "Download base packages",
      tools: "Download and check Android tools",
      sdk: "Download Android components",
      keystore: "Take over signing key",
      probe: "Check sealing",
      stop: "Let build environment rest",
      done: "Done",
    },
    err: {
      general: "That did not work. Please try again later.",
      tvw_no_incus: "This server has no container environment. The TV Workshop needs it for building.",
      tvw_busy: "Something is already running. Please wait a moment.",
      tvw_license_required: "Please accept the license terms first.",
      tvw_interrupted: "Setting up was interrupted (for example by a restart). Please try again.",
      tvw_setup_failed: "Setting up failed at one step.",
      tvw_checksum_mismatch: "The downloaded Android tools do not match Google's checksum. To be safe, nothing was "
        + "unpacked.",
      tvw_launch_failed: "The build environment could not be created.",
      tvw_no_storage_pool: "There is no storage set up on the server for the build environment.",
      tvw_container_down: "The build environment does not respond.",
      tvw_container_remove_failed: "The build environment could not be removed.",
      tvw_no_address: "The build environment did not get a network address.",
      tvw_net_open: "The sealing does not hold: the build environment reaches something that must be blocked. To be "
        + "safe, nothing continues here.",
      tvw_dns_failed: "The build environment cannot resolve names on the internet.",
      tvw_net_probe_failed: "The sealing check could not be run.",
      tvw_network_missing: "The sealed-off network is missing.",
      tvw_incus_failed: "The sealed-off network could not be set up.",
      tvw_subnet_unavailable: "There is no free address range for the sealed-off network.",
      tvw_acl_dirty: "The block list contains duplicate rules. Please remove the workshop and set it up again.",
      tvw_bad_address: "This address does not fit a TV on the home network.",
    },
  },
}

export const tvwerkstattI18n = { de, en }
