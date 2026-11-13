/** Reine Logik des Reiters Desktop (ohne React): was die Vorschau zeigt und wie Änderungen das Aussehen ändern. */
import type { Mood, TvwApp, TvwLook } from "./api"

export interface Tile { pkg: string; label: string; color: string; hasImage: boolean }

/** Kacheln wie auf dem Fernseher: erst die Leiste in ihrer Reihenfolge, dann die übrigen nach Namen; ausgeblendete fehlen.
 *  Ist die Leiste leer, füllt cleanyourtv sie mit den ersten Apps (fill_dock). */
export function tiles(apps: TvwApp[], look: TvwLook): { dock: Tile[]; grid: Tile[] } {
  const byPkg = new Map(apps.map((a) => [a.package, a]))
  const tile = (a: TvwApp): Tile => ({
    pkg: a.package, label: look.labels[a.package] || a.label || a.package, color: a.color || "#243047",
    hasImage: !!a.color,
  })
  const shown = apps.filter((a) => !look.hidden.includes(a.package))
  const docked = look.dock.map((p) => byPkg.get(p)).filter((a): a is TvwApp => !!a && !look.hidden.includes(a.package))
  const rest = shown.filter((a) => !look.dock.includes(a.package))
    .sort((x, y) => tile(x).label.localeCompare(tile(y).label, "de"))
  const cols = Math.max(1, look.columns)
  const dockTiles = (docked.length ? docked : rest).slice(0, cols).map(tile)
  const used = new Set(dockTiles.map((t) => t.pkg))
  const grid = rest.filter((a) => !used.has(a.package)).slice(0, cols * look.rows_below_dock).map(tile)
  return { dock: dockTiles, grid }
}

/** App in die Leiste nehmen (ans Ende) oder herausnehmen. */
export function toggleDock(look: TvwLook, pkg: string): TvwLook {
  const dock = look.dock.includes(pkg) ? look.dock.filter((p) => p !== pkg) : [...look.dock, pkg]
  return { ...look, dock, hidden: look.hidden.filter((p) => p !== pkg) }
}

/** App ausblenden oder wieder zeigen (ausgeblendet heißt: auch nicht in der Leiste). */
export function toggleHidden(look: TvwLook, pkg: string): TvwLook {
  if (look.hidden.includes(pkg)) return { ...look, hidden: look.hidden.filter((p) => p !== pkg) }
  return { ...look, hidden: [...look.hidden, pkg], dock: look.dock.filter((p) => p !== pkg) }
}

/** In der Leiste verschieben: `from` an die Stelle von `to` (Ziehen) – unbekannte Pakete ändern nichts. */
export function moveInDock(look: TvwLook, from: string, to: string): TvwLook {
  const d = [...look.dock]
  const i = d.indexOf(from)
  const j = d.indexOf(to)
  if (i < 0 || j < 0 || i === j) return look
  d.splice(i, 1)
  d.splice(j, 0, from)
  return { ...look, dock: d }
}

/** Eine Stelle hoch/runter (für Tastatur und Fernbedienung, statt Ziehen). */
export function nudge(look: TvwLook, pkg: string, by: -1 | 1): TvwLook {
  const i = look.dock.indexOf(pkg)
  const j = i + by
  if (i < 0 || j < 0 || j >= look.dock.length) return look
  return moveInDock(look, pkg, look.dock[j])
}

/** Eigener Name: leer = Name der App. */
export function setLabel(look: TvwLook, pkg: string, name: string): TvwLook {
  const labels = { ...look.labels }
  const v = name.trim().slice(0, 24)
  if (v) labels[pkg] = v
  else delete labels[pkg]
  return { ...look, labels }
}

/** Tageszeit wie cleanyourtv (fester Bezugstag): 5–11 Morgen, 11–19 Tag (zählt zum Morgen), 19–22 Abend, sonst Nacht. */
export function moodAt(hour: number): Mood {
  if (hour >= 5 && hour < 17) return "morning"
  if (hour >= 17 && hour < 22) return "evening"
  return "night"
}

/** Uhr und Datum wie auf dem Fernseher. */
export function clockText(d: Date, format: TvwLook["clock_format"]): string {
  const h12 = format === "12"
  return d.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit", hour12: h12 })
}

/** Gruß nach Tageszeit (cleanyourtv zeigt ihn über der Uhr). */
export function greetingKey(hour: number): string {
  if (hour >= 5 && hour < 12) return "desk.greet_morning"
  if (hour >= 12 && hour < 18) return "desk.greet_day"
  return "desk.greet_evening"
}

export function sameLook(a: TvwLook, b: TvwLook): boolean {
  return JSON.stringify(a) === JSON.stringify(b)
}

/** Schrift hell oder dunkel, je nach Helligkeit der Kachelfarbe (sonst weiße Schrift auf weißer Kachel). */
export function textOn(hex: string): string {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex.trim())
  if (!m) return "#ffffff"
  const n = parseInt(m[1], 16)
  const lum = 0.2126 * ((n >> 16) & 255) + 0.7152 * ((n >> 8) & 255) + 0.0722 * (n & 255)
  return lum > 150 ? "#111111" : "#ffffff"
}
