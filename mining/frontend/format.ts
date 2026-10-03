// Reine Formatierer — ohne App-Importe, damit sie in Tests laufen.

const UNITS: [number, string][] = [
  [1e12, "TH/s"], [1e9, "GH/s"], [1e6, "MH/s"], [1e3, "kH/s"], [1, "H/s"],
]

export function formatHashrate(hs: number | null | undefined): string {
  if (hs === null || hs === undefined || !Number.isFinite(hs) || hs <= 0) return "—"
  const [div, unit] = UNITS.find(([d]) => hs >= d) ?? [1, "H/s"]
  const v = hs / div
  return `${v >= 100 ? v.toFixed(0) : v >= 10 ? v.toFixed(1) : v.toFixed(2)} ${unit}`
}

export function formatMoney(v: number | null | undefined, currency: "EUR" | "USD", locale = "de-DE"): string {
  if (v === null || v === undefined || !Number.isFinite(v)) return "—"
  return new Intl.NumberFormat(locale, { style: "currency", currency, minimumFractionDigits: 2, maximumFractionDigits: 3 }).format(v)
}

export function formatPercent(v: number, locale = "de-DE"): string {
  return new Intl.NumberFormat(locale, { style: "percent", maximumFractionDigits: 1 }).format(v)
}

/** Minuten seit einem ISO-Zeitpunkt (für „Stand vor X min“); null wenn unbekannt. */
export function minutesSince(iso: string | null, now: number = Date.now()): number | null {
  if (!iso) return null
  const t = Date.parse(iso)
  if (Number.isNaN(t)) return null
  return Math.max(0, Math.floor((now - t) / 60000))
}

/** Älter als 15 min = der Hintergrundabruf (alle 5 min) klappt gerade nicht. */
export function isStale(iso: string | null, now: number = Date.now()): boolean {
  const m = minutesSince(iso, now)
  return m === null || m > 15
}
