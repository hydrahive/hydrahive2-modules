// Ghostwriter G4e – Rahmen des Chat-Fensters ohne React.
import { describe, expect, it } from "vitest"
import { clampWidth, COCKPIT_SESSION_KEY, DOCK_DEFAULT, DOCK_MIN, keepCockpitSession, readDock } from "./chatDock"

describe("chatDock", () => {
  it("begrenzt die Breite auf DOCK_MIN … 60 % des Fensters", () => {
    expect(clampWidth(100, 1500)).toBe(DOCK_MIN)
    expect(clampWidth(2000, 1500)).toBe(900)
    expect(clampWidth(600.4, 1500)).toBe(600)
    expect(clampWidth(500, 400)).toBe(DOCK_MIN)               // schmales Fenster: nie unter DOCK_MIN
    expect(clampWidth(Number.NaN, 1500)).toBe(DOCK_DEFAULT)
  })
  it("liest den gemerkten Zustand robust (kaputt/fehlt → zu, Standardbreite)", () => {
    expect(readDock(JSON.stringify({ open: true, width: 700 }), 1500)).toEqual({ open: true, width: 700 })
    expect(readDock(JSON.stringify({ open: "ja", width: 5000 }), 1500)).toEqual({ open: false, width: 900 })
    expect(readDock("kaputt", 1500)).toEqual({ open: false, width: DOCK_DEFAULT })
    expect(readDock(null, 1500)).toEqual({ open: false, width: DOCK_DEFAULT })
  })
})

describe("keepCockpitSession", () => {
  const mem = (init: Record<string, string> | null) => {
    const data = new Map<string, string>(init ? [[COCKPIT_SESSION_KEY, JSON.stringify(init)]] : [])
    return { getItem: (k: string) => data.get(k) ?? null, setItem: (k: string, v: string) => { data.set(k, v) }, read: () => JSON.parse(data.get(COCKPIT_SESSION_KEY) ?? "{}") }
  }
  it("stellt den Merker des Projekts wieder her, andere Projekte bleiben wie sie sind", () => {
    const s = mem({ p1: "cockpit", p2: "andere" })
    const restore = keepCockpitSession("p1", s)
    s.setItem(COCKPIT_SESSION_KEY, JSON.stringify({ p1: "storyteller", p2: "andere-neu" }))   // Fenster hat überschrieben
    restore()
    expect(s.read()).toEqual({ p1: "cockpit", p2: "andere-neu" })
  })
  it("gab es keinen Merker, wird der des Fensters wieder entfernt; kaputter Wert stört nicht", () => {
    const s = mem(null)
    const restore = keepCockpitSession("p1", s)
    s.setItem(COCKPIT_SESSION_KEY, JSON.stringify({ p1: "storyteller" }))
    restore()
    expect(s.read()).toEqual({})
    const k = mem(null); k.setItem(COCKPIT_SESSION_KEY, "kaputt")
    keepCockpitSession("p1", k)()
    expect(k.read()).toEqual({})
  })
})
