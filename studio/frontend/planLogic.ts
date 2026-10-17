import type { ImportPreview, Plan, Scene, Selection } from "./planApi"

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

const KNOWN = new Set(["studio_plan_exists", "studio_nothing_to_import", "studio_element_invalid", "studio_not_found", "studio_project_not_found",
  "studio_too_many_shots", "studio_decompose_failed", "studio_decompose_has_media", "studio_decompose_busy",
  "studio_job_running", "studio_variant_unknown", "studio_video_needs_image"])

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
