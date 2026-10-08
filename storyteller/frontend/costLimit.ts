// A1 – Kostengrenze je Auftrag (Spec kostengrenze.md): reine Hilfen ohne React (costLimit.test.ts).
// Grenze in Tokens, Eingabe + Ausgabe, 0 = aus. Euro nur als Hinweis, wenn der Preis bekannt ist.

export const LIMIT_MIN = 1_000
export const LIMIT_MAX = 20_000_000

interface Tokens { input_tokens: number; output_tokens: number }

export const totalTokens = (e: Tokens) => e.input_tokens + e.output_tokens

/** Liegt die Schätzung über der Grenze? Gleich ist nicht darüber; 0 = aus. */
export function overLimit(est: Tokens | null, limit: number): boolean {
  return !!est && limit > 0 && totalTokens(est) > limit
}

/** Eingabe aus dem Feld: leer/0 = aus; Leerzeichen und Tausenderpunkte erlaubt. */
export function parseLimit(raw: string): { ok: true; value: number } | { ok: false } {
  const s = raw.replace(/[\s.]/g, "")
  if (s === "") return { ok: true, value: 0 }
  if (!/^\d+$/.test(s)) return { ok: false }
  const n = Number(s)
  if (n === 0) return { ok: true, value: 0 }
  return n >= LIMIT_MIN && n <= LIMIT_MAX ? { ok: true, value: n } : { ok: false }
}

/** Grenze ungefähr in Cent – mit dem Preis je Token aus der Schätzung. Unbekannter Preis → null. */
export function limitCents(est: Tokens & { cost_micros: number | null }, limit: number): string | null {
  const total = totalTokens(est)
  if (!limit || est.cost_micros === null || total <= 0) return null
  return ((est.cost_micros / total) * limit / 1000).toFixed(2)
}
