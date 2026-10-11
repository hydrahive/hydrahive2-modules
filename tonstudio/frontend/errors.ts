import i18n from "@/i18n"

// Fehlercodes aus backend/routes.py. Der Kern übersetzt coded-Fehler über den Namespace "errors"; die
// Modul-Bundles werden dort flach (Object.assign) gemischt, deshalb hier ein Deep-Merge, damit die Kern-Texte
// erhalten bleiben.
const de = {
  song_not_found: "Song nicht gefunden",
  version_conflict: "Der Song wurde inzwischen woanders geändert (Stand {{current}}). Bitte neu laden.",
  invalid_song: "Ungültige Song-Daten: {{message}}",
  song_format_unknown: "Song-Format unbekannt: {{message}}",
  source_outside_project: "Eine Clip-Quelle liegt außerhalb des Projekts",
  upload_rejected: "Upload abgelehnt: {{message}}",
  clip_not_found: "Clip nicht gefunden",
  file_not_found: "Datei nicht gefunden",
  invalid_request: "Ungültiger Auftrag: {{message}}",
  unknown_model: "Unbekanntes Modell: {{model}}",
  generation_failed: "Erzeugen fehlgeschlagen: {{message}}",
}
const en = {
  song_not_found: "Song not found",
  version_conflict: "The song was changed elsewhere (version {{current}}). Please reload.",
  invalid_song: "Invalid song data: {{message}}",
  song_format_unknown: "Unknown song format: {{message}}",
  source_outside_project: "A clip source lies outside the project",
  upload_rejected: "Upload rejected: {{message}}",
  clip_not_found: "Clip not found",
  file_not_found: "File not found",
  invalid_request: "Invalid request: {{message}}",
  unknown_model: "Unknown model: {{model}}",
  generation_failed: "Generation failed: {{message}}",
}

let done = false
export function registerTonstudioErrors(): void {
  if (done) return
  done = true
  i18n.addResourceBundle("de", "errors", de, true, false)
  i18n.addResourceBundle("en", "errors", en, true, false)
}

export function errText(e: unknown): string {
  return e instanceof Error ? e.message : String(e)
}
