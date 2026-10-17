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

const KNOWN = new Set(["studio_plan_exists", "studio_nothing_to_import", "studio_element_invalid", "studio_not_found", "studio_project_not_found"])

/** Fehlertext: bekannte Fehlercodes des Studios übersetzt, sonst die Meldung, sonst ein Standardtext. */
export function errorText(t: (k: string) => string, e: unknown): string {
  if (!(e instanceof Error)) return t("load_failed")
  return KNOWN.has(e.message) ? t(`err.${e.message}`) : e.message || t("load_failed")
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
