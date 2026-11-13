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

/** Läuft irgendwo ein Auftrag am Fernseher (prüfen, aufspielen, zurück) → öfter nachsehen, Knöpfe sperren. */
export function anyChecking(devices: TvwDevice[]): boolean {
  return devices.some((d) => d.check?.state === "running" || d.action?.state === "running")
}

export const ACTION_STEPS = ["container", "verify", "push", "start", "switch"] as const

/** Was am Fernseher gerade passiert oder zuletzt schiefging. */
export type ActionView = "installing" | "restoring" | "failed" | "idle"

export function actionView(d: TvwDevice): ActionView {
  const a = d.action
  if (a?.state === "running") return a.kind === "install" ? "installing" : "restoring"
  if (a?.state === "failed") return "failed"
  return "idle"
}

/** Aufspielen geht nur mit fertigem Bau, offenem Debugging und bekanntem Original. */
export function canInstall(d: TvwDevice, hasBuild: boolean): boolean {
  return hasBuild && d.adb_state === "open" && !!d.stock_home
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
