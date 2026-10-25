import type { CallEntry } from "./types"

/** Reine Logik der Anruf-Karte (getestet in callsLogic.test.ts). */

/** Sekunden bis zum Ende des Testfensters (0 = zu). */
export function secondsLeft(testUntil: string | null, now: number = Date.now()): number {
  if (!testUntil) return 0
  const end = Date.parse(testUntil)
  return Number.isFinite(end) ? Math.max(0, Math.ceil((end - now) / 1000)) : 0
}

/** Der jüngste Testanruf, der noch auf „Ton gehört?“ wartet. */
export function pendingTest(calls: CallEntry[]): CallEntry | null {
  return calls.find((c) => c.is_test && c.heard === null && c.result !== "busy") ?? null
}

export type CallTone = "ok" | "warn" | "idle"

export function callTone(c: CallEntry): CallTone {
  if (c.result === "answered" || c.result === "caller_hangup" || c.result === "hung_up") return "ok"
  if (c.result === "rejected" || c.result === "cancelled") return "idle"
  return "warn"
}

/** Zeit kurz und lokal (heute nur Uhrzeit). */
export function shortTime(iso: string, now: Date = new Date()): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ""
  const sameDay = d.toDateString() === now.toDateString()
  return sameDay
    ? d.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" })
    : d.toLocaleString("de-DE", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })
}
