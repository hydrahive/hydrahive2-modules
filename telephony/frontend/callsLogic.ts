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

export interface CallsSaver {
  saveCalls: (body: { answer_calls: boolean; greeting: string }) => Promise<unknown>
}

/**
 * Schalter „Anrufe annehmen“ sofort speichern (Till 25.10.: Schalter muss einrasten, ohne extra Speichern-Knopf).
 * Gespeichert wird immer die zuletzt GESPEICHERTE Ansage – eine noch nicht gespeicherte Änderung im Textfeld bleibt
 * Sache des Speichern-Knopfs. Bei Fehler bleibt der alte Wert (Rückgabe: tatsächlich gültiger Zustand).
 */
export async function saveSwitch(api: CallsSaver, next: boolean, savedGreeting: string, previous: boolean):
  Promise<{ value: boolean; error: string | undefined }> {
  try {
    await api.saveCalls({ answer_calls: next, greeting: savedGreeting })
    return { value: next, error: undefined }
  } catch (e) {
    return { value: previous, error: (e as { code?: string }).code ?? "unknown" }
  }
}
