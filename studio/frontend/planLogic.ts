import type { ImportPreview, Plan, Scene, Selection, Shot } from "./planApi"

/** Szene in der Reihenfolge um eins nach oben (-1) oder unten (+1). Ränder und Unbekanntes ändern nichts. */
export function moveScene(order: string[], id: string, dir: -1 | 1): string[] {
  const i = order.indexOf(id)
  const j = i + dir
  if (i < 0 || j < 0 || j >= order.length) return order
  const out = [...order]
  ;[out[i], out[j]] = [out[j], out[i]]
  return out
}

/** Absoluter Pfad aus Projektordner und Pfad relativ zum Projekt (für /api/files). */
export function fileOf(base: string, rel: string | null | undefined): string {
  if (!base || !rel) return ""
  return `${base.replace(/\/+$/, "")}/${rel}`
}

/** Übernahme aus dem Atelier anbieten: Atelier hat Daten und das Studio ist noch leer. */
export function showImport(p: ImportPreview | null): boolean {
  return !!p && p.available && !p.plan_exists
}

// Jeder Fehlercode, den das Backend schickt (errors.test.ts prüft das gegen backend/*.py). Unbekannt → Meldung des Clients.
const KNOWN = new Set(["studio_plan_exists", "studio_nothing_to_import", "studio_element_invalid", "studio_not_found", "studio_project_not_found",
  "studio_too_many_shots", "studio_decompose_failed", "studio_decompose_has_media", "studio_decompose_busy",
  "studio_job_running", "studio_variant_unknown", "studio_video_needs_image", "studio_batch_running", "studio_batch_nothing",
  "studio_timeline_invalid", "studio_timeline_conflict", "studio_timeline_not_empty", "studio_timeline_no_shots",
  "studio_idea_invalid", "studio_idea_failed", "studio_book_not_found", "studio_book_empty", "studio_draft_invalid",
  "studio_free_invalid", "studio_free_running", "studio_assign_invalid", "studio_render_empty", "studio_render_queue_full",
  "studio_render_bad_preset", "studio_media_not_found", "studio_speech_needs_text", "studio_references_full",
  "studio_music_needs_text", "studio_music_invalid", "studio_music_running",
  "studio_subtitles_invalid", "studio_subtitles_conflict", "studio_subtitles_not_empty", "studio_subtitles_empty",
  "studio_subtitles_running", "studio_subtitles_no_audio", "studio_subtitles_no_speech", "studio_subtitles_cloud_model",
  "studio_subtitles_same_language", "studio_subtitles_too_long",
  "studio_upload_invalid", "studio_upload_empty", "studio_upload_too_large", "studio_upload_too_many",
  "studio_media_busy", "studio_media_not_own", "studio_describe_no_image", "studio_describe_failed", "studio_describe_no_key",
  "studio_probe_running", "studio_probe_nothing", "studio_probe_missing",
  "studio_film_running", "studio_film_invalid", "studio_film_edited",
  "studio_change_invalid", "studio_change_needs_image"])

/** Fehlertext: bekannte Fehlercodes des Studios übersetzt, sonst die Meldung, sonst ein Standardtext. */
export function errorText(t: (k: string) => string, e: unknown): string {
  if (!(e instanceof Error)) return t("load_failed")
  const code = errorCode(e)
  return code ? t(`err.${code}`) : e.message || t("load_failed")
}

/** Bekannter Fehlercode des Studios (aus `code` des API-Clients oder, ohne Übersetzung, aus der Meldung). */
export function errorCode(e: unknown): string | null {
  if (!(e instanceof Error)) return null
  const code = (e as Error & { code?: string }).code
  if (code && KNOWN.has(code)) return code
  return KNOWN.has(e.message) ? e.message : null
}

/** Farben aus einem Textfeld (Komma oder Leerzeichen getrennt), höchstens 12. */
export function paletteFromText(s: string): string[] {
  return s.split(/[\s,]+/).map((c) => c.trim()).filter(Boolean).slice(0, 12)
}

/** Szene zur aktuellen Auswahl (gewählte Szene oder Szene des gewählten Shots). */
export function sceneOf(plan: Plan | null, sel: Selection | null): Scene | null {
  if (!plan || !sel) return null
  const id = sel.kind === "scene" ? sel.id : sel.kind === "shot" ? sel.sceneId : null
  return plan.scenes.find((s) => s.id === id) ?? null
}

/** Mengen für Angebot und Dialog der Übernahme, je mit Einzahl/Mehrzahl („1 Figur“, „2 Figuren“). */
export function importAmounts(t: (k: string, o?: Record<string, unknown>) => string, p: ImportPreview) {
  return { scenes: t("scene_count", { count: p.scenes }), shots: t("shot_count", { count: p.shots }), elements: t("figure_count", { count: p.elements }) }
}

/** Shot in der Reihenfolge verschieben (wie Szenen). */
export const moveShot = moveScene

/** Gesamtdauer der Szene in Sekunden. */
export function sceneDuration(scene: Scene | null): number {
  return scene ? scene.shots.reduce((sum, s) => sum + (s.duration || 0), 0) : 0
}

/** Hat die Szene Shots mit Bild oder Video? Dann fragt „In Shots zerlegen“ vor dem Ersetzen nach. */
export function hasMedia(scene: Scene | null): boolean {
  return !!scene && scene.shots.some((s) => !!(s.image_rel || s.video_rel))
}

/** Was „Speichern“ im Shot-Formular schickt (Status und Medien ändert nur das Erzeugen; seit 5c mit Sprechtext/Stimme). */
export function shotChanges(s: Shot): Partial<Shot> {
  return { shot: s.shot, prompt: s.prompt, element_ids: s.element_ids, duration: s.duration, speech: s.speech ?? "", voice: s.voice ?? "" }
}
