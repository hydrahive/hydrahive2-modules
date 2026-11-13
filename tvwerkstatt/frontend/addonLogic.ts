/** Reine Logik des Reiters Zusätze (ohne React), einzeln testbar. */
import type { TvwAddon } from "./api"

export type AddonFilter = "all" | "none" | "dream" | "installed"
export const FILTERS: AddonFilter[] = ["all", "none", "dream", "installed"]

/** Filter wie die Demo: alle, ohne Rechte, Bildschirmschoner, installiert; dazu Suche in Name und Beschreibung. */
export function visible(items: TvwAddon[], f: AddonFilter, q: string): TvwAddon[] {
  const s = q.trim().toLowerCase()
  return items.filter((a) => (f === "all" || (f === "none" && !a.permissions.length) || (f === "dream" && a.dream)
    || (f === "installed" && !!a.installed)) && (!s || `${a.name} ${a.what}`.toLowerCase().includes(s)))
}

/** Rechte zum Anzeigen: nach dem Bau die der fertigen App, vorher die aus dem Manifest. */
export function shownPerms(a: TvwAddon): { name: string; level: string }[] {
  if (!a.installed) return a.permissions
  const lv = new Map(a.permissions.map((p) => [p.name, p.level]))
  return a.installed.permissions.map((n) => ({ name: n, level: lv.get(n) ?? "" }))
}

/** Läuft der Zusatz auf diesem Fernseher? (unbekanntes SDK → ja, der Server prüft genau). */
export function fits(a: TvwAddon, sdk?: number): boolean {
  return !sdk || !a.min_sdk || sdk >= a.min_sdk
}

/** Bildadresse eines Zusatzes (ohne api.ts, damit Tests den Client nicht laden). */
export function addonImagePath(addon: string): string {
  return `/api/modules/tvwerkstatt/addons/${encodeURIComponent(addon)}/image`
}

/** Android-Version zum minSdk (für die Anzeige „ab Android 8“). */
export function androidOf(sdk: number): string {
  return ({ 26: "8", 27: "8.1", 28: "9", 29: "10", 30: "11", 31: "12", 32: "12L", 33: "13", 34: "14" } as
    Record<number, string>)[sdk] ?? String(sdk)
}
