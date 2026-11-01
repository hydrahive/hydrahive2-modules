/** Zeitangaben für die Oberfläche (Sekunden seit 1970 → deutsch/englisch lesbar). */
export function when(ts: number | null | undefined, lang: string): string {
  if (!ts) return "–"
  return new Date(ts * 1000).toLocaleString(lang.startsWith("de") ? "de-DE" : "en-GB",
    { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })
}

export function dayLabel(day: string, lang: string): string {
  const [y, m, d] = day.split("-").map(Number)
  return new Date(y, m - 1, d).toLocaleDateString(lang.startsWith("de") ? "de-DE" : "en-GB",
    { weekday: "short", day: "2-digit", month: "2-digit" })
}

export function hourLabel(ts: number): string {
  const d = new Date(ts * 1000)
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`
}
