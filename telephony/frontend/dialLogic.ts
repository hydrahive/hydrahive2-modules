/** Reine Logik „Anrufen“ (Etappe 3, getestet in DialPanel.test.tsx). */

const ERRORS = new Set(["number_emergency", "number_premium", "number_foreign", "number_invalid",
  "number_no_area_code", "not_registered", "line_busy", "too_fast", "daily_limit"])
const STATES = new Set(["calling", "ringing", "answered", "ended"])

export function dialErrorKey(code: string | undefined): string {
  return code && ERRORS.has(code) ? `dial.error.${code}` : "dial.error.unknown"
}

export function dialStateKey(state: string): string {
  return `dial.state.${STATES.has(state) ? state : "calling"}`
}

/** Eingabe filtern: Ziffern, +, Leerzeichen und - / ( ) – keine * und # (FRITZ!Box-Steuercodes). Max. 40 Zeichen. */
export function cleanNumberInput(raw: string): string {
  return raw.replace(/[^0-9+\s\-/()]/g, "").slice(0, 40)
}
