// Hydra-Labor L3 (Probe ansehen): Texte de/en. Wird in i18n.ts zusammengeführt.
export const probeDe = {
  probe: {
    title: "Probe ansehen",
    intro: "Hier siehst du dein Labor als eigenes HydraHive im Browser – mit eigener Anmeldung und leeren Daten, nur aus deinem Heimnetz erreichbar. Nach Änderungen einfach neu bauen.",
    build: "Probe bauen", rebuild: "Neu bauen", start: "Probe starten", stop: "Probe stoppen", open: "Probe öffnen",
    copy: "Kopieren", user: "Benutzer", password: "Passwort",
    login_hint: "Die Probe hat eine eigene Anmeldung. Melde dich dort mit diesen Daten an:",
    where: "Die Probe läuft (Port {{port}}).",
    lab_off: "Das Labor ist aus. Bitte zuerst starten.",
  },
  job: {
    probe_build: "Probe wird gebaut – etwa eine Minute …", probe_start: "Probe wird gestartet …",
    probe_stop: "Probe wird gestoppt …",
  },
  err: {
    labor_probe_build_failed: "Die Probe ließ sich nicht bauen. Bitte im Labor-Chat nachsehen lassen, ob die Oberfläche fehlerfrei ist.",
    labor_probe_not_built: "Die Probe ist noch nicht gebaut. Bitte zuerst „Probe bauen“ wählen.",
    labor_probe_start_failed: "Die Probe ist nicht angelaufen. Bitte neu bauen und noch einmal starten.",
    labor_probe_nginx_failed: "Die Probe läuft, ist aber im Browser nicht erreichbar. Bitte noch einmal starten.",
    labor_probe_bad_address: "Das Labor hat eine unerwartete Netzadresse. Bitte das Labor stoppen und wieder starten.",
    labor_probe_no_address: "Das Labor hat gerade keine Netzadresse. Bitte das Labor stoppen und wieder starten.",
    labor_probe_bad_host: "Die Adresse dieses Servers ist ungewöhnlich. Bitte HydraHive über seine normale Adresse öffnen.",
    labor_probe_login_required: "Der Zugang zur Probe ist abgelaufen. Bitte im Labor erneut „Probe öffnen“ wählen.",
  },
}

export const probeEn: typeof probeDe = {
  probe: {
    title: "Preview",
    intro: "See your lab as a separate HydraHive in the browser – with its own login and empty data, reachable only from your home network. After changes, just rebuild.",
    build: "Build preview", rebuild: "Rebuild", start: "Start preview", stop: "Stop preview", open: "Open preview",
    copy: "Copy", user: "User", password: "Password",
    login_hint: "The preview has its own login. Sign in there with:",
    where: "The preview is running (port {{port}}).",
    lab_off: "The lab is off. Please start it first.",
  },
  job: {
    probe_build: "Building preview – about a minute …", probe_start: "Starting preview …",
    probe_stop: "Stopping preview …",
  },
  err: {
    labor_probe_build_failed: "The preview could not be built. Please ask in the lab chat to check that the interface has no errors.",
    labor_probe_not_built: "The preview is not built yet. Please choose “Build preview” first.",
    labor_probe_start_failed: "The preview did not start. Please rebuild and start again.",
    labor_probe_nginx_failed: "The preview is running but not reachable in the browser. Please start it again.",
    labor_probe_bad_address: "The lab has an unexpected network address. Please stop and start the lab.",
    labor_probe_no_address: "The lab has no network address right now. Please stop and start the lab.",
    labor_probe_bad_host: "This server's address looks unusual. Please open HydraHive via its normal address.",
    labor_probe_login_required: "Access to the preview has expired. Please choose “Open preview” in the lab again.",
  },
}
