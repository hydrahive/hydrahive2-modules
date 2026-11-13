import { describe, expect, it } from "vitest"
import type { TvwApp } from "./api"
import {
  clockText, greetingKey, moodAt, moveInDock, nudge, sameLook, setLabel, textOn, tiles, toggleDock, toggleHidden,
} from "./desktopLogic"
import { tvwerkstattI18n } from "./i18n"
import { DEFAULT_LOOK } from "./testLook"

const app = (package_: string, label: string): TvwApp => ({ package: package_, label, version: "1", has_banner: 1,
  color: "#101010" })
const APPS = [app("com.netflix.ninja", "Netflix"), app("com.plexapp.android", "Plex"), app("tv.emby.embyatv", "Emby"),
  app("com.google.android.youtube.tv", "YouTube")]
const L = { ...DEFAULT_LOOK, columns: 2, rows_below_dock: 1 }

describe("TV-Werkstatt: Desktop (Logik)", () => {
  it("Standard-Aussehen gleich wie im Backend (look.py DEFAULT)", () => {
    const files = import.meta.glob("../backend/look.py", { query: "?raw", import: "default", eager: true })
    const src = Object.values(files).join("")
    for (const [k, v] of Object.entries(DEFAULT_LOOK)) {
      const py = typeof v === "boolean" ? (v ? "True" : "False") : Array.isArray(v) ? "[]"
        : typeof v === "object" ? "{}" : typeof v === "string" ? `"${v}"` : String(v)
      expect(src, k).toMatch(new RegExp(`"${k}": ${py.replace(/[[\]{}]/g, "\\$&")},`))
    }
  })

  it("leere Leiste: erste Apps nach Namen füllen sie (wie fill_dock)", () => {
    const { dock, grid } = tiles(APPS, L)
    expect(dock.map((t) => t.label)).toEqual(["Emby", "Netflix"])
    expect(grid.map((t) => t.label)).toEqual(["Plex", "YouTube"])
  })

  it("Leiste in eigener Reihenfolge, Rest nach Namen, Ausgeblendetes fehlt, eigene Namen", () => {
    const look = { ...L, dock: ["com.plexapp.android", "com.netflix.ninja"], hidden: ["tv.emby.embyatv"],
      labels: { "com.netflix.ninja": "Filme" } }
    const { dock, grid } = tiles(APPS, look)
    expect(dock.map((t) => t.label)).toEqual(["Plex", "Filme"])
    expect(grid.map((t) => t.label)).toEqual(["YouTube"])
  })

  it("Kacheln pro Reihe und Reihen unter der Leiste begrenzen", () => {
    expect(tiles(APPS, { ...L, columns: 1, rows_below_dock: 0 }).grid).toEqual([])
    expect(tiles(APPS, { ...L, columns: 1 }).dock).toHaveLength(1)
  })

  it("in die Leiste nehmen, herausnehmen, ausblenden", () => {
    let l = toggleDock(L, "com.netflix.ninja")
    expect(l.dock).toEqual(["com.netflix.ninja"])
    l = toggleHidden(l, "com.netflix.ninja")
    expect(l.dock).toEqual([]) ; expect(l.hidden).toEqual(["com.netflix.ninja"])
    l = toggleDock(l, "com.netflix.ninja")
    expect(l.hidden).toEqual([]); expect(l.dock).toEqual(["com.netflix.ninja"])
    expect(toggleDock(l, "com.netflix.ninja").dock).toEqual([])
  })

  it("ziehen und hoch/runter", () => {
    const l = { ...L, dock: ["a.b.c", "d.e.f", "g.h.i"] }
    expect(moveInDock(l, "g.h.i", "a.b.c").dock).toEqual(["g.h.i", "a.b.c", "d.e.f"])
    expect(moveInDock(l, "x.y.z", "a.b.c")).toBe(l)
    expect(nudge(l, "d.e.f", -1).dock).toEqual(["d.e.f", "a.b.c", "g.h.i"])
    expect(nudge(l, "a.b.c", -1)).toBe(l)
    expect(nudge(l, "g.h.i", 1)).toBe(l)
  })

  it("eigener Name: gekürzt, leer entfernt ihn", () => {
    expect(setLabel(L, "a.b.c", "  Kino  ").labels).toEqual({ "a.b.c": "Kino" })
    expect(setLabel(L, "a.b.c", "x".repeat(40)).labels["a.b.c"]).toHaveLength(24)
    expect(setLabel({ ...L, labels: { "a.b.c": "Kino" } }, "a.b.c", "").labels).toEqual({})
  })

  it("Tageszeit, Uhr, Gruß", () => {
    expect([6, 12, 18, 23, 3].map(moodAt)).toEqual(["morning", "morning", "evening", "night", "night"])
    expect(clockText(new Date(2026, 10, 13, 20, 14), "24")).toBe("20:14")
    expect(clockText(new Date(2026, 10, 13, 20, 14), "12")).toMatch(/08:14/)
    expect([8, 14, 21].map(greetingKey)).toEqual(["desk.greet_morning", "desk.greet_day", "desk.greet_evening"])
  })

  it("Schrift auf der Kachel: dunkel auf hellen Farben, sonst hell", () => {
    expect(textOn("#ffffff")).toBe("#111111")
    expect(textOn("#000000")).toBe("#ffffff")
    expect(textOn("#e50914")).toBe("#ffffff")
    expect(textOn("kaputt")).toBe("#ffffff")
  })

  it("geändert erkennen", () => {
    expect(sameLook(L, { ...L })).toBe(true)
    expect(sameLook(L, { ...L, columns: 5 })).toBe(false)
  })

  it("alle Texte des Desktops in beiden Sprachen", () => {
    const keys = (o: object) => Object.keys(o).sort()
    expect(keys(tvwerkstattI18n.de.tvwerkstatt.desk)).toEqual(keys(tvwerkstattI18n.en.tvwerkstatt.desk))
    expect(keys(tvwerkstattI18n.de.tvwerkstatt.tab)).toEqual(keys(tvwerkstattI18n.en.tvwerkstatt.tab))
  })
})
