// Vitrine-Kalenderregeln im Browser: Anzeige-Text, Prüfung (gleich wie renderer/calendar.py), neue Regeln.
export type Kind = "range" | "easter" | "advent" | "season" | "time" | "advent_sunday" | "nth_weekday" | "dates"
export interface Period { from: string; to: string }
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
  n?: number
  month?: number
  weekday?: number
  days?: number
  dates?: Period[]
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
  n?: number
  month?: number
  weekday?: number
  days?: number
  dates?: Period[]
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
const ymd = (s?: string) => (s ? `${s.slice(8, 10)}.${s.slice(5, 7)}.${s.slice(0, 4)}` : "?")
const YMD = /^\d{4}-\d{2}-\d{2}$/
const MAX_SPAN_DAYS = 40      // wie renderer/calendar_extra.py

function dayNumber(s: string): number | null {
  if (!YMD.test(s)) return null
  const d = new Date(`${s}T00:00:00Z`)
  return Number.isNaN(d.getTime()) || d.toISOString().slice(0, 10) !== s ? null : d.getTime() / 86_400_000
}

/** Termine als Textzeilen „JJJJ-MM-TT JJJJ-MM-TT“ – ein Zeitraum je Zeile (Leerzeilen zählen nicht). */
export function parseDates(text: string): Period[] {
  return text.split("\n").map((l) => l.trim()).filter(Boolean).map((l) => {
    const [from = "", to = ""] = l.split(/\s+/)
    return { from, to }
  })
}

export function formatDates(dates?: Period[]): string {
  return (dates ?? []).map((p) => `${p.from} ${p.to}`).join("\n")
}

export function describeRule(r: Rule, t: T): string {
  switch (r.kind) {
    case "range": return `${md(r.from)} – ${md(r.to)}`
    case "time": return `${r.from} – ${r.to}`
    case "season": return t(`season.${r.season}`)
    case "advent": return t("kind.advent")
    case "easter": return t("easter_range", { from: r.offset_from, to: r.offset_to })
    case "advent_sunday": return t("advent_n", { n: r.n })
    case "nth_weekday": return t("nth_weekday_desc", { n: t(`nth.${r.n}`), weekday: t(`weekday.${r.weekday}`), month: t(`month.${r.month}`) })
    case "dates": {
      const d = r.dates ?? []
      return t("dates_desc", { count: d.length, first: ymd(d[0]?.from), last: ymd(d[d.length - 1]?.to) })
    }
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
  } else if (r.kind === "advent_sunday" && ![1, 2, 3, 4].includes(Number(r.n))) {
    errs.push("n")
  } else if (r.kind === "nth_weekday") {
    const m = Number(r.month), w = Number(r.weekday), n = Number(r.n)
    if (!Number.isInteger(m) || m < 1 || m > 12) errs.push("month")
    if (!Number.isInteger(w) || w < 0 || w > 6) errs.push("weekday")
    if (![-1, 1, 2, 3, 4, 5].includes(n)) errs.push("n")
    if (r.days !== undefined && (!Number.isInteger(Number(r.days)) || Number(r.days) < 1 || Number(r.days) > 31)) errs.push("days")
  } else if (r.kind === "dates") {
    const bad = (r.dates ?? []).some((p) => {
      const a = dayNumber(p.from), b = dayNumber(p.to)
      return a === null || b === null || a > b || b - a > MAX_SPAN_DAYS
    })
    if (bad || (r.dates ?? []).length > 40) errs.push("dates")
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
  advent_sunday: { n: 1 },
  nth_weekday: { month: 5, weekday: 6, n: 2 },
  dates: { dates: [] },
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


/** Zustand der Vitrine für die Statuskarte. `no_display`: Dienst läuft, Display meldet sich nicht am USB. */
export type DisplayState = "loading" | "stopped" | "no_display" | "night" | "running"

export function displayState(st: { running: boolean; connected: boolean; night: string | null } | null): DisplayState {
  if (!st) return "loading"
  if (!st.running) return "stopped"
  if (!st.connected) return "no_display"
  return st.night ? "night" : "running"
}
