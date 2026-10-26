/** S8 Licht – gleiche Vorgaben und Prüfung wie renderer/light_config.py (Dienst + Server). */
export const LIGHT_STATES = ["error", "warning", "done", "working"] as const
export const LIGHT_EFFECTS = ["static", "breathing", "flashing", "off"] as const
export const LIGHT_SEASONS = ["spring", "summer", "autumn", "winter"] as const
export type LightStateId = (typeof LIGHT_STATES)[number]
export type LightEffect = (typeof LIGHT_EFFECTS)[number]
export type LightSeason = (typeof LIGHT_SEASONS)[number]

export interface LightLook { effect: LightEffect; color: string }
export interface LightStateCfg extends LightLook { speed: number; brightness: number | null; enabled?: boolean; seconds?: number }
export interface LightCfg {
  enabled: boolean
  brightness: number
  night_off: boolean
  error_blink_seconds: number
  states: Record<LightStateId, LightStateCfg>
  seasons_enabled: boolean
  seasons: Record<LightSeason, LightLook>
  rest_effect: LightEffect
  rest_color: string
}

export interface LightStatus {
  available: boolean
  device?: string | null
  state?: string | null
  color?: string | null
  effect?: string | null
  label?: string
  preview?: string | null
  error?: string | null
  updated?: number
  preview_states?: string[]
}

export const DEFAULT_LIGHT: LightCfg = {
  enabled: true, brightness: 80, night_off: true, error_blink_seconds: 20,
  states: {
    error: { effect: "flashing", color: "FF0000", speed: 70, brightness: null },
    warning: { effect: "static", color: "FFB000", speed: 50, brightness: null },
    done: { effect: "static", color: "00FF40", speed: 50, brightness: null, enabled: false, seconds: 5 },
    working: { effect: "breathing", color: "0060FF", speed: 30, brightness: null },
  },
  seasons_enabled: true,
  seasons: {
    spring: { effect: "static", color: "8CFF66" }, summer: { effect: "static", color: "FFD7A0" },
    autumn: { effect: "static", color: "FF8C1A" }, winter: { effect: "static", color: "C8E0FF" },
  },
  rest_effect: "static", rest_color: "FFD7A0",
}

const HEX = /^#?([0-9A-Fa-f]{6})$/

/** "#ff8800" → "FF8800"; sonst null (wie light_config.color). */
export function lightColor(v: unknown): string | null {
  const m = typeof v === "string" ? HEX.exec(v) : null
  return m ? m[1].toUpperCase() : null
}

/** Für <input type="color"> (braucht "#rrggbb"). */
export const toPicker = (c: string) => `#${(lightColor(c) ?? "000000").toLowerCase()}`

const intIn = (v: unknown, lo: number, hi: number) => typeof v === "number" && Number.isInteger(v) && v >= lo && v <= hi
const effectOk = (e: unknown) => (LIGHT_EFFECTS as readonly unknown[]).includes(e)

/** Fehlerschlüssel (leer = gültig) – gleiche Grenzen wie der Server. */
export function lightErrors(l: LightCfg): string[] {
  const e: string[] = []
  if (!intIn(l.brightness, 0, 100)) e.push("brightness")
  if (!intIn(l.error_blink_seconds, 0, 600)) e.push("error_blink_seconds")
  for (const s of LIGHT_STATES) {
    const c = l.states[s]
    if (!c || !effectOk(c.effect) || lightColor(c.color) !== c.color || !intIn(c.speed, 0, 100)
      || !(c.brightness === null || intIn(c.brightness, 0, 100))) e.push(`states.${s}`)
    if (s === "done" && (!intIn(c?.seconds, 2, 60) || typeof c?.enabled !== "boolean")) e.push("states.done")
  }
  for (const s of LIGHT_SEASONS) {
    const c = l.seasons[s]
    if (!c || !effectOk(c.effect) || lightColor(c.color) !== c.color) e.push(`seasons.${s}`)
  }
  if (!effectOk(l.rest_effect) || lightColor(l.rest_color) !== l.rest_color) e.push("rest")
  return [...new Set(e)]
}

/** Alte Config ohne Licht → Vorgaben; fehlende Teile ergänzen. */
export function normalizeLight(raw: Partial<LightCfg> | undefined | null): LightCfg {
  const r = raw ?? {}
  return {
    ...DEFAULT_LIGHT, ...r,
    states: Object.fromEntries(LIGHT_STATES.map((s) => [s, { ...DEFAULT_LIGHT.states[s], ...(r.states?.[s] ?? {}) }])) as LightCfg["states"],
    seasons: Object.fromEntries(LIGHT_SEASONS.map((s) => [s, { ...DEFAULT_LIGHT.seasons[s], ...(r.seasons?.[s] ?? {}) }])) as LightCfg["seasons"],
  }
}
