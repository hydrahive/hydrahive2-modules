/** Microsoft-Anmeldung (M1b): reine Logik ohne React – Abfrage-Takt, Zustände, Texte zu Fehlercodes. */

export type FlowState = "idle" | "starting" | "waiting" | "done" | "expired" | "denied" | "error"

export interface FlowStart {
  flow_id: string
  user_code: string
  verification_uri: string
  expires_in: number
  interval: number
}

/** Antwort von GET /microsoft/flows/{id} → Zustand der Oberfläche. */
export function nextState(answer: { state: string }): FlowState {
  switch (answer.state) {
    case "pending": return "waiting"
    case "done": return "done"
    case "expired": return "expired"
    case "denied": return "denied"
    default: return "error"
  }
}

/** Abstand zwischen zwei Abfragen: nie schneller als Microsoft erlaubt, mindestens 2 s, höchstens 30 s. */
export function pollDelayMs(interval: number): number {
  const s = Number.isFinite(interval) ? interval : 5
  return Math.min(30, Math.max(2, s)) * 1000
}

/** Nur Microsoft-Adressen als Link öffnen (der Server prüft das auch). */
export function safeLink(uri: string): string {
  return /^https:\/\/(www\.)?(microsoft\.com|login\.microsoft\.com|login\.microsoftonline\.com|aka\.ms)\//.test(uri)
    ? uri : "https://microsoft.com/devicelogin"
}

/** Fehlercode der API (detail.code) beim Start → Text-Schlüssel in i18n (ms.err.*). */
export function startErrorKey(code: string | undefined): string {
  if (code === "microsoft_not_configured") return "ms.err.notConfigured"
  if (code === "too_many_flows") return "ms.err.tooMany"
  if (code === "microsoft") return "ms.err.microsoft"
  return "ms.err.generic"
}

/** Ist eine Adresse wahrscheinlich ein privates Microsoft-Konto? (Nur Vorauswahl – der Server entscheidet.) */
export function looksMicrosoft(address: string): boolean {
  const d = address.split("@")[1]?.toLowerCase() ?? ""
  return /^(outlook|hotmail|live|msn)\.[a-z.]+$/.test(d)
}

/** Fehlercode einer API-Antwort (der Kern-Client hängt detail.code als err.code an), sonst undefined. */
export function errorCode(e: unknown): string | undefined {
  const c = (e as { code?: unknown } | null)?.code
  return typeof c === "string" && c ? c : undefined
}
