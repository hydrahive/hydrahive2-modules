/** Hydra-Labor L2: Typen und reine Hilfen für GitHub, Einreichen und Fehler melden. */
export interface GitHubState { connected: boolean; login: string; pending: boolean; configured: boolean }
export interface DeviceCode { user_code: string; verification_uri: string; expires_in: number }
export interface Submission {
  id: number; kind: "pr" | "issue"; target: string; title: string; number: number; url: string; state: string; created_at: string
}
export type Target = "core" | "modules"

/** Reihenfolge der Meldungen beim Einreichen (backend/submit.py). */
export const SUBMIT_STEPS = ["check", "tests", "fork", "push", "pr"]

export function submitProgress(key: string): number {
  return Math.max(0, SUBMIT_STEPS.indexOf(key))
}

/** PR aus `submit_out` im Zustand – nur wenn wirklich eine Nummer da ist (sonst stehen dort die Fehlergründe). */
export function submitResult(out: Record<string, unknown>): { number: number; url: string } | null {
  return typeof out.number === "number" && typeof out.url === "string" ? { number: out.number, url: out.url } : null
}

export const titleOk = (t: string) => t.trim().length > 0 && t.trim().length <= 120
