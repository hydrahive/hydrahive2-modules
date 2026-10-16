// Vitrine-Kalenderregeln im Browser: Anzeige-Text, Prüfung (gleich wie renderer/calendar.py), neue Regeln.
export type Kind = "range" | "easter" | "advent" | "season" | "time"
export type Season = "spring" | "summer" | "autumn" | "winter"

export interface Rule {
  id: string
  name: string
  kind: Kind
  enabled: boolean
  priority: number
  videos: string[]
  from?: string
  to?: string
  season?: Season
  offset_from?: number
  offset_to?: number
}

export interface Template {
  name: string
  kind: Kind
  priority: number
  from?: string
  to?: string
  season?: Season
  offset_from?: number
  offset_to?: number
}

type T = (key: string, opts?: Record<string, unknown>) => string

const MD = /^(\d{2})-(\d{2})$/
const HM = /^([01]\d|2[0-3]):[0-5]\d$/
const DAYS = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

export function validMonthDay(s?: string): boolean {
  const m = MD.exec(s ?? "")
  if (!m) return false
  const mo = Number(m[1])
  const d = Number(m[2])
  return mo >= 1 && mo <= 12 && d >= 1 && d <= DAYS[mo - 1]
}

const md = (s?: string) => (s ? `${s.slice(3, 5)}.${s.slice(0, 2)}.` : "?")

export function describeRule(r: Rule, t: T): string {
  switch (r.kind) {
    case "range": return `${md(r.from)} – ${md(r.to)}`
    case "time": return `${r.from} – ${r.to}`
    case "season": return t(`season.${r.season}`)
    case "advent": return t("kind.advent")
    case "easter": return t("easter_range", { from: r.offset_from, to: r.offset_to })
  }
}

export function ruleErrors(r: Rule): string[] {
  const errs: string[] = []
  if (!r.name.trim()) errs.push("name")
  if (r.kind === "range") {
    if (!validMonthDay(r.from)) errs.push("from")
    if (!validMonthDay(r.to)) errs.push("to")
  } else if (r.kind === "time") {
    if (!HM.test(r.from ?? "")) errs.push("from")
    if (!HM.test(r.to ?? "")) errs.push("to")
  } else if (r.kind === "easter") {
    const a = Number(r.offset_from)
    const b = Number(r.offset_to)
    if (!Number.isInteger(a) || !Number.isInteger(b) || a < -120 || b > 120 || a > b) errs.push("offset")
  } else if (r.kind === "season" && !["spring", "summer", "autumn", "winter"].includes(r.season ?? "")) {
    errs.push("season")
  }
  return errs
}

function newId(): string {
  return Math.random().toString(36).slice(2, 10).padEnd(8, "0") + Date.now().toString(36)
}

const DEFAULTS: Record<Kind, Partial<Rule>> = {
  range: { from: "12-24", to: "12-26" },
  time: { from: "18:00", to: "23:00" },
  season: { season: "autumn" },
  easter: { offset_from: -2, offset_to: 1 },
  advent: {},
}

export function newRule(kind: Kind): Rule {
  return { id: newId(), name: "", kind, enabled: true, priority: 20, videos: [], ...DEFAULTS[kind] }
}

export function fromTemplate(tpl: Template): Rule {
  return { ...tpl, id: newId(), enabled: true, videos: [] }
}

export function sizeLabel(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}


/** Zahleneingabe auf den erlaubten Bereich begrenzen, ganzzahlig (leeres/ungültiges Feld → Minimum). */
export function clamp(v: number, lo: number, hi: number): number {
  return Number.isFinite(v) ? Math.min(hi, Math.max(lo, Math.round(v))) : lo
}
