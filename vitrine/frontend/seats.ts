/** Multiseat M1/M2: Zeilen, Prüfung und Schaltknöpfe der Karte „Zweiter Arbeitsplatz“ (ohne Browser testbar). */
import type { SeatAction, SeatId, SeatsView } from "./api"

export interface SeatRow { id: string; kind: "gpu" | "sound" | "input"; label: string; detail: string }

export function seatRows(v: SeatsView): SeatRow[] {
  const gpus = v.devices.gpus.map((g) => ({
    id: g.id, kind: "gpu" as const, label: g.evdi ? "USB-Display (EVDI)" : `${g.vendor} ${g.pci ?? ""}`.trim(),
    detail: g.outputs.filter((o) => o.connected).map((o) => o.name).join(", "),
  }))
  const sound = v.devices.sound.map((s) => ({ id: s.id, kind: "sound" as const, label: s.name, detail: s.pci }))
  const inputs = v.devices.inputs.map((i) => ({ id: i.id, kind: "input" as const, label: i.name,
    detail: i.bt ? `Bluetooth ${i.bt}` : `USB ${i.usb ?? ""}` }))
  return [...gpus, ...sound, ...inputs]
}

/** Startwerte der Auswahl: gespeichert vor Vorschlag; leer bleibt leer (nicht raten). */
export function initialChoice(v: SeatsView): Record<string, SeatId | null> {
  const out: Record<string, SeatId | null> = {}
  for (const r of seatRows(v)) out[r.id] = v.saved?.assignment[r.id] ?? v.assignment[r.id] ?? null
  return out
}

/** Gründe, warum „Übernehmen“ noch nicht geht (Schlüssel für i18n). Gleiche Regeln wie das Backend (seats.validate). */
export function choiceErrors(v: SeatsView, c: Record<string, SeatId | null>): string[] {
  const errs: string[] = []
  if (Object.values(c).some((s) => s === null)) errs.push("seats_err_open")
  if (v.devices.gpus.some((g) => g.evdi && c[g.id] !== "seat0")) errs.push("seats_err_evdi")
  const real = (s: SeatId) => v.devices.gpus.filter((g) => !g.evdi && c[g.id] === s).length
  if (real("seat0") !== 1 || real("seat1") !== 1) errs.push("seats_err_gpu")
  return errs
}

export const complete = (c: Record<string, SeatId | null>): Record<string, SeatId> =>
  Object.fromEntries(Object.entries(c).filter((e): e is [string, SeatId] => e[1] !== null))

/** Welcher Schaltknopf erscheint: einschalten nur mit gespeicherter, gültiger Zuordnung; ausschalten nur wenn an. */
export function switchAction(v: SeatsView): SeatAction | null {
  if (v.running) return null
  if (v.applied) return "revert"
  return v.saved && !v.saved_error ? "apply" : null
}

/** Ergebnis des letzten Laufs: Schlüssel für den Text + die letzten Zeilen bei Fehler. */
export function runResult(v: SeatsView): { msgKey: string; ok: boolean; detail: string } | null {
  const r = v.last_run
  if (!r || v.running) return null
  const msgKey = r.ok ? `seats_run_ok_${r.action}` : r.action === "apply" && r.exit === 1 ? "seats_run_reverted"
    : r.action === "apply" && r.exit === 2 ? "seats_run_rejected" : `seats_run_fail_${r.action}`
  return { msgKey, ok: r.ok, detail: r.ok ? "" : r.lines.slice(-6).join("\n") }
}
