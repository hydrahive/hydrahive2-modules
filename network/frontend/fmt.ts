/** Anzeige-Helfer (ohne React): Datenmengen, Laufzeiten, Geschwindigkeit, Signal. */
export function bytes(n: number | null | undefined): string {
  if (n === null || n === undefined) return "–"
  const u = ["B", "KB", "MB", "GB", "TB"]
  let v = n, i = 0
  while (v >= 1000 && i < u.length - 1) { v /= 1000; i++ }
  return `${v >= 100 || i === 0 ? Math.round(v) : v.toFixed(1)} ${u[i]}`.replace(".", ",")
}

export function uptime(s: number | null | undefined, t: (k: string, o?: Record<string, unknown>) => string): string {
  if (s === null || s === undefined) return "–"
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60)
  if (d) return t("dur.dh", { d, h })
  if (h) return t("dur.hm", { h, m })
  return t("dur.m", { m })
}

export function speed(mbit: number | null | undefined): string {
  if (!mbit) return "–"
  return mbit >= 1000 ? `${mbit / 1000} Gbit/s` : `${mbit} Mbit/s`
}

/** Signalstärke (dBm) in 4 Stufen: gut ≥ -60, ok ≥ -70, schwach ≥ -80, sonst schlecht. */
export function signalLevel(dbm: number | null | undefined): "good" | "ok" | "weak" | "bad" | null {
  if (dbm === null || dbm === undefined) return null
  if (dbm >= -60) return "good"
  if (dbm >= -70) return "ok"
  if (dbm >= -80) return "weak"
  return "bad"
}

export function countNodes(n: { children: unknown[] }): number {
  return 1 + (n.children as { children: unknown[] }[]).reduce((s, c) => s + countNodes(c), 0)
}

/** Balken relativ zum größten Wert (0–100 %). */
export function share(v: number, max: number): number {
  return max > 0 ? Math.round((v / max) * 100) : 0
}
