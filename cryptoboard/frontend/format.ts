// Zahlen-/Währungs-Formatierung fürs Trading-Dashboard.

const CURRENCY_SYMBOL: Record<string, string> = { eur: "€", usd: "$", gbp: "£", chf: "CHF", btc: "₿" }

export function vsSymbol(vs: string): string {
  return CURRENCY_SYMBOL[vs.toLowerCase()] ?? vs.toUpperCase()
}

export function fmtPrice(value: number | null, vs: string): string {
  if (value == null) return "—"
  const sym = vsSymbol(vs)
  const digits = value >= 1000 ? 0 : value >= 1 ? 2 : value >= 0.01 ? 4 : 8
  return `${sym}${value.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits })}`
}

export function fmtCompact(value: number | null, vs?: string): string {
  if (value == null) return "—"
  const sym = vs ? vsSymbol(vs) : ""
  const abs = Math.abs(value)
  if (abs >= 1e12) return `${sym}${(value / 1e12).toFixed(2)}T`
  if (abs >= 1e9) return `${sym}${(value / 1e9).toFixed(2)}B`
  if (abs >= 1e6) return `${sym}${(value / 1e6).toFixed(2)}M`
  if (abs >= 1e3) return `${sym}${(value / 1e3).toFixed(2)}k`
  return `${sym}${value.toLocaleString()}`
}

export function fmtPct(value: number | null): string {
  if (value == null) return "—"
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`
}

// Tailwind-Klasse für +/- (grün/rot, neutral bei null).
export function trendClass(value: number | null): string {
  if (value == null) return "text-zinc-500"
  return value >= 0 ? "text-emerald-400" : "text-rose-400"
}

export function fmtSupply(value: number | null): string {
  if (value == null) return "—"
  return fmtCompact(value)
}

export function timeAgo(unixSeconds: number): string {
  const diff = Date.now() / 1000 - unixSeconds
  if (diff < 3600) return `${Math.max(1, Math.round(diff / 60))}m`
  if (diff < 86400) return `${Math.round(diff / 3600)}h`
  return `${Math.round(diff / 86400)}d`
}

// Coin-Menge: bis 6 signifikante Nachkommastellen, ohne Trailing-Nullen.
export function fmtQty(value: number | null): string {
  if (value == null) return "—"
  const digits = Math.abs(value) >= 1 ? 4 : 8
  return value.toLocaleString(undefined, { maximumFractionDigits: digits })
}

// P&L mit Vorzeichen, z.B. "+1.234,56 €".
export function fmtSigned(value: number | null, vs: string): string {
  if (value == null) return "—"
  const sign = value > 0 ? "+" : ""
  return `${sign}${fmtPrice(value, vs)}`
}


