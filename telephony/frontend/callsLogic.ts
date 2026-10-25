import type { AssistantSettings, CallEntry, CallNotes } from "./types"

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
  if (["answered", "caller_hangup", "hung_up", "assistant_end", "max_duration"].includes(c.result)) return "ok"
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

/** Assistent-Einstellungen geändert? (Leerzeichen am Rand zählen nicht – der Server schneidet sie ab.) */
export function assistantDirty(a: AssistantSettings, b: AssistantSettings): boolean {
  return a.mode !== b.mode || a.assistant_name.trim() !== b.assistant_name.trim()
    || a.assistant_knowledge.trim() !== b.assistant_knowledge.trim() || a.assistant_model !== b.assistant_model
}

/** Notiz in einer Zeile für die Liste: Name · Anliegen (· Rückruf). */
export function noteLine(n: CallNotes): string {
  return [n.name, n.concern, n.callback_wanted ? (n.callback_number ? `Rückruf ${n.callback_number}` : "Rückruf") : ""]
    .filter((x): x is string => Boolean(x)).join(" · ")
}

export function hasNote(c: CallEntry): boolean {
  return Object.keys(c.notes ?? {}).length > 0
}
