/** Reiter der Vitrine-Seite: welche Einstellung gehört wohin (für „ungespeichert“ und „ungültig“-Punkte). */
import type { VitrineConfig } from "./api"
import { layoutErrors, normalizeDashboard } from "./dashLayout"
import { lightErrors, normalizeLight } from "./light"
import { ruleErrors } from "./rules"

export const TABS = ["overview", "program", "display", "dashboard", "light", "bluetooth"] as const
export type TabId = (typeof TABS)[number]

/** Felder der Einstellung → Reiter. Übersicht und Bluetooth haben keine gespeicherten Felder. */
const FIELDS: Partial<Record<TabId, (keyof VitrineConfig)[]>> = {
  program: ["rules", "default_videos"],
  display: ["night", "rotate_minutes", "fps", "message_seconds", "dashboard_return_seconds"],
  dashboard: ["dashboard"],
  light: ["light"],
}

export function tabFromParam(v: string | null): TabId {
  return (TABS as readonly string[]).includes(v ?? "") ? (v as TabId) : "overview"
}

const same = (a: unknown, b: unknown) => JSON.stringify(a ?? null) === JSON.stringify(b ?? null)

/** Reiter mit ungespeicherten Änderungen (in Reiter-Reihenfolge). */
export function dirtyTabs(saved: VitrineConfig | null, now: VitrineConfig): TabId[] {
  if (!saved) return []
  return TABS.filter((tab) => (FIELDS[tab] ?? []).some((f) => !same(saved[f], now[f])))
}

/** Reiter mit ungültigen Werten (gleiche Prüfung wie beim Speichern). */
export function invalidTabs(c: VitrineConfig): TabId[] {
  const bad: TabId[] = []
  if (c.rules.some((r) => ruleErrors(r).length > 0)) bad.push("program")
  if (layoutErrors(normalizeDashboard(c.dashboard)).length > 0) bad.push("dashboard")
  if (lightErrors(normalizeLight(c.light)).length > 0) bad.push("light")
  return bad
}
