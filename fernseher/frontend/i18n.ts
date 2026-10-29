// Texte des Moduls Fernseher (de/en). Einfach, ohne Fachwörter, ohne Hinweise auf Terminal oder Dateien.
const de = {
  fernseher: {
    title: "Fernseher",
    subtitle: "Sehen, was läuft, und den Fernseher bedienen.",
    refresh: "Aktualisieren",
    now: { heading: "Läuft gerade", off: "Der Fernseher ist aus.", app: "Eine App ist offen.", volume: "Lautstärke {{volume}}", muted: "stumm" },
    remote: {
      heading: "Fernbedienung", on: "Einschalten", off: "Ausschalten", louder: "Lauter", quieter: "Leiser",
      mute: "Stumm", unmute: "Ton an", channels: "Sender", apps: "Apps", only_admin: "Bedienen darf nur, wer dafür freigeschaltet ist.",
      search: "Sender suchen (Name oder Platz)", no_match: "Kein Sender gefunden.",
    },
    setup: {
      heading: "Einrichten", name: "Name", name_example: "z. B. TV Wohnzimmer", address: "Adresse im Heimnetz",
      address_example: "z. B. 192.168.178.186", address_hint: "Nur Adressen im eigenen Heimnetz sind erlaubt.",
      psk: "Schlüssel", psk_set: "Schlüssel ist gespeichert. Leer lassen, um ihn zu behalten.",
      psk_hint: "Den Schlüssel legst du am Fernseher fest: Einstellungen → Netzwerk → Heimnetzwerk → IP-Steuerung → „Normal und Pre-Shared Key“.",
      limit: "Lauter als … geht nicht", save: "Speichern", saved: "Gespeichert.", test: "Verbindung testen",
      test_ok: "Verbunden mit {{model}} – der Fernseher ist {{power}}.", power_on: "an", power_standby: "aus",
      not_configured: "Noch nicht eingerichtet.", ask_admin: "Ein Admin muss den Fernseher zuerst einrichten.",
    },
    err: {
      general: "Das hat nicht geklappt. Bitte noch einmal versuchen.",
      tv_not_configured: "Der Fernseher ist noch nicht eingerichtet.",
      tv_unreachable: "Der Fernseher antwortet nicht. Ist er an und im Netz?",
      tv_auth_failed: "Der Fernseher lehnt den Schlüssel ab. Bitte prüfen.",
      tv_needs_restart: "Der Fernseher muss einmal ganz neu starten: Netzstecker kurz ziehen, dann wieder einschalten.",
      tv_address_not_local: "Diese Adresse liegt nicht im Heimnetz.",
      tv_psk_missing: "Bitte den Schlüssel eintragen.",
      tv_settings_invalid: "Die Angaben sind nicht gültig.",
      tv_channel_unknown: "Diesen Sender gibt es nicht.",
      tv_channel_ambiguous: "Mehrere Sender passen – bitte genauer angeben.",
      tv_app_unknown: "Diese App ist nicht installiert.",
      tv_volume_limit: "So laut geht es nicht – es gibt eine Obergrenze zum Schutz.",
      tv_volume_invalid: "Die Lautstärke bitte als Zahl angeben.",
      tv_upstream_error: "Der Fernseher meldet einen Fehler.",
      tv_switch_failed: "Der Fernseher hat nicht umgeschaltet. Bitte noch einmal versuchen.",
    },
  },
}

const en = {
  fernseher: {
    title: "TV",
    subtitle: "See what's on and control your TV.",
    refresh: "Refresh",
    now: { heading: "Now playing", off: "The TV is off.", app: "An app is open.", volume: "Volume {{volume}}", muted: "muted" },
    remote: {
      heading: "Remote", on: "Turn on", off: "Turn off", louder: "Louder", quieter: "Quieter",
      mute: "Mute", unmute: "Sound on", channels: "Channels", apps: "Apps", only_admin: "Only people with permission can control the TV.",
      search: "Search channel (name or number)", no_match: "No channel found.",
    },
    setup: {
      heading: "Set up", name: "Name", name_example: "e.g. Living room TV", address: "Address in your home network",
      address_example: "e.g. 192.168.178.186", address_hint: "Only addresses in your own home network are allowed.",
      psk: "Key", psk_set: "A key is saved. Leave empty to keep it.",
      psk_hint: "You set the key on the TV: Settings → Network → Home network → IP control → “Normal and Pre-Shared Key”.",
      limit: "Never louder than", save: "Save", saved: "Saved.", test: "Test connection",
      test_ok: "Connected to {{model}} – the TV is {{power}}.", power_on: "on", power_standby: "off",
      not_configured: "Not set up yet.", ask_admin: "An admin has to set up the TV first.",
    },
    err: {
      general: "That didn't work. Please try again.",
      tv_not_configured: "The TV is not set up yet.",
      tv_unreachable: "The TV doesn't answer. Is it on and connected?",
      tv_auth_failed: "The TV rejects the key. Please check it.",
      tv_needs_restart: "The TV needs a full restart: unplug it briefly, then turn it on again.",
      tv_address_not_local: "This address is not in your home network.",
      tv_psk_missing: "Please enter the key.",
      tv_settings_invalid: "These settings are not valid.",
      tv_channel_unknown: "This channel doesn't exist.",
      tv_channel_ambiguous: "Several channels match – please be more specific.",
      tv_app_unknown: "This app is not installed.",
      tv_volume_limit: "It can't get that loud – there is a safety limit.",
      tv_volume_invalid: "Please give the volume as a number.",
      tv_upstream_error: "The TV reports an error.",
      tv_switch_failed: "The TV didn't switch. Please try again.",
    },
  },
}

export const fernseherI18n = { de, en }
