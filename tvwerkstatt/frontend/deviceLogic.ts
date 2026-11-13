/** Reine Logik der Geräteliste (ohne React), damit sie einzeln testbar ist. */
import type { TvwDevice } from "./api"

/** Prüft gerade, wartet auf Freigabe am Fernseher, gescheitert oder ruhig. */
export type CheckView = "checking" | "authorize" | "failed" | "idle"

export function checkView(d: TvwDevice): CheckView {
  const c = d.check
  if (c?.state === "running") return c.step === "authorize" ? "authorize" : "checking"
  if (c?.state === "failed") return "failed"
  return "idle"
}

/** Läuft irgendwo ein Prüfauftrag → öfter nachsehen. */
export function anyChecking(devices: TvwDevice[]): boolean {
  return devices.some((d) => d.check?.state === "running")
}

/** „Android TV“ / „Google TV“ aus der gelesenen Art; unbekannt → leer. */
export function kindKey(kind?: string): string {
  return kind === "google_tv" || kind === "android_tv" ? `kind.${kind}` : ""
}

/** IPv4-Adresse im Heimnetz grob vorprüfen (der Server prüft genau). */
export function looksLikeAddress(a: string): boolean {
  const m = a.trim().match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/)
  return !!m && m.slice(1).every((x) => Number(x) <= 255)
}

/** Ist unser Startbildschirm gerade Home? */
export function ourHome(d: TvwDevice): boolean {
  return d.current_home === "com.gathin.tvhome"
}
