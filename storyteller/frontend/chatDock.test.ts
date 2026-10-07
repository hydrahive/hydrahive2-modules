// Ghostwriter G4e – Rahmen des Chat-Fensters ohne React.
import { describe, expect, it } from "vitest"
import { clampWidth, DOCK_DEFAULT, DOCK_MIN, readDock } from "./chatDock"

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
