// Reine Logik fürs Verlaufsdiagramm — ohne App-Importe, damit sie in Tests läuft.

export type Metric = "eur" | "pct" | "watt" | "temp"

export interface HistoryCard {
  temp_c: number | null
  power_w: number | null
  util_pct: number | null
}

export interface HistoryPoint {
  ts: string
  mode: "mine" | "benchmark" | "stop"
  coin: string | null
  miner?: string | null
  usd_day: number | null
  pct: number | null
  cards: HistoryCard[]
}

export interface RigHistory {
  id: string
  name: string
  points: HistoryPoint[]
}

export interface HistoryResponse {
  hours: number
  usd_per_eur: number | null
  rigs: RigHistory[]
}

export interface Series {
  key: string
  label: string
  color: string
}

/** Gut unterscheidbar auf dunklem Grund; ab 12 Linien wiederholt mit gestrichelter Linie. */
export const PALETTE = ["#34d399", "#60a5fa", "#f472b6", "#fbbf24", "#a78bfa", "#f87171",
  "#22d3ee", "#a3e635", "#fb923c", "#e879f9", "#2dd4bf", "#facc15"]

/** Ertrag/Leistung gibt es nur je Rechner (Miner liefern nur die Gesamt-Hashrate). */
export function perCard(metric: Metric): boolean {
  return metric === "watt" || metric === "temp"
}

export function seriesFor(rigs: RigHistory[], metric: Metric): Series[] {
  const out: Series[] = []
  for (const rig of rigs) {
    if (perCard(metric)) {
      const n = Math.max(0, ...rig.points.map((p) => p.cards.length))
      for (let i = 0; i < n; i++) {
        out.push({ key: `${rig.id}#${i}`, label: n > 1 ? `${rig.name} · Karte ${i + 1}` : rig.name, color: "" })
      }
    } else {
      out.push({ key: rig.id, label: rig.name, color: "" })
    }
  }
  return out.map((s, i) => ({ ...s, color: PALETTE[i % PALETTE.length] }))
}

function value(p: HistoryPoint, metric: Metric, card: number, usdPerEur: number | null): number | null {
  if (metric === "eur") return p.usd_day !== null && usdPerEur ? p.usd_day / usdPerEur : null
  if (metric === "pct") return p.pct
  const c = p.cards[card]
  if (!c) return null
  return metric === "watt" ? c.power_w : c.temp_c
}

/** Eine Zeile je Zeitpunkt (Minute), Spalten = Serien. Fehlende Werte bleiben null → Lücke. */
export function chartRows(data: HistoryResponse, metric: Metric): Record<string, number | string | null>[] {
  const rows = new Map<number, Record<string, number | string | null>>()
  for (const rig of data.rigs) {
    for (const p of rig.points) {
      const ts = Date.parse(p.ts)
      if (Number.isNaN(ts)) continue
      const row = rows.get(ts) ?? { ts }
      if (perCard(metric)) {
        p.cards.forEach((_, i) => { row[`${rig.id}#${i}`] = value(p, metric, i, data.usd_per_eur) })
      } else {
        row[rig.id] = value(p, metric, 0, data.usd_per_eur)
        row[`${rig.id}:coin`] = p.mode === "mine" ? p.coin : p.mode === "benchmark" ? "benchmark" : null
      }
      rows.set(ts, row)
    }
  }
  return [...rows.values()].sort((a, b) => (a.ts as number) - (b.ts as number))
}

/** Gesamtertrag aller Rechner zum letzten Zeitpunkt (für die Kopfzeile). */
export function latestTotalEur(data: HistoryResponse): number | null {
  if (!data.usd_per_eur) return null
  let sum = 0
  let any = false
  for (const rig of data.rigs) {
    const last = rig.points[rig.points.length - 1]
    if (last?.usd_day != null) { sum += last.usd_day / data.usd_per_eur; any = true }
  }
  return any ? sum : null
}
