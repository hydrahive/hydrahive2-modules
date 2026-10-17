import { describe, expect, it } from "vitest"
import { errorText, fileOf, importAmounts, moveScene, paletteFromText, sceneOf, showImport } from "./planLogic"
import type { ImportPreview, Plan } from "./planApi"

const t = (k: string) => `T:${k}`
const preview = (p: Partial<ImportPreview>): ImportPreview => ({ available: true, scenes: 2, shots: 3, elements: 1, look: true, plan_exists: false, ...p })

describe("Planen – Logik", () => {
  it("Szenen hoch/runter, Ränder und Unbekanntes ändern nichts", () => {
    const order = ["a", "b", "c"]
    expect(moveScene(order, "b", -1)).toEqual(["b", "a", "c"])
    expect(moveScene(order, "b", 1)).toEqual(["a", "c", "b"])
    expect(moveScene(order, "a", -1)).toEqual(order)
    expect(moveScene(order, "c", 1)).toEqual(order)
    expect(moveScene(order, "x", 1)).toEqual(order)
    expect(moveScene(order, "b", -1)).not.toBe(order)
    expect(order).toEqual(["a", "b", "c"])                       // Eingabe bleibt unverändert
  })

  it("Dateipfad aus Projektordner und relativem Pfad", () => {
    expect(fileOf("/data/w", "atelier/x.png")).toBe("/data/w/atelier/x.png")
    expect(fileOf("/data/w/", "x.png")).toBe("/data/w/x.png")
    expect(fileOf("/data/w", null)).toBe("")
    expect(fileOf("", "x.png")).toBe("")
  })

  it("Übernahme anbieten nur, wenn das Atelier Daten hat und das Studio noch leer ist", () => {
    expect(showImport(null)).toBe(false)
    expect(showImport(preview({}))).toBe(true)
    expect(showImport(preview({ plan_exists: true }))).toBe(false)
    expect(showImport(preview({ available: false }))).toBe(false)
  })

  it("Fehler: bekannte Codes übersetzt, sonst die Meldung, sonst ein Standardtext", () => {
    expect(errorText(t, new Error("studio_plan_exists"))).toBe("T:err.studio_plan_exists")
    expect(errorText(t, new Error("Netz weg"))).toBe("Netz weg")
    expect(errorText(t, "kaputt")).toBe("T:load_failed")
  })

  it("Farbpalette aus Text: getrennt durch Komma oder Leerzeichen, höchstens 12", () => {
    expect(paletteFromText("#111, #222  #333,,")).toEqual(["#111", "#222", "#333"])
    expect(paletteFromText(Array.from({ length: 20 }, (_, i) => `#${i}`).join(","))).toHaveLength(12)
    expect(paletteFromText("  ")).toEqual([])
  })

  it("Mengen der Übernahme mit Einzahl/Mehrzahl über count", () => {
    const tc = (k: string, o?: Record<string, unknown>) => `${k}=${o?.count}`
    expect(importAmounts(tc, preview({ scenes: 1, shots: 0, elements: 2 }))).toEqual({ scenes: "scene_count=1", shots: "shot_count=0", elements: "figure_count=2" })
  })

  it("Szene zur Auswahl (Szene oder Shot)", () => {
    const plan = { scenes: [{ id: "s1" }, { id: "s2" }] } as unknown as Plan
    expect(sceneOf(plan, { kind: "scene", id: "s2" })?.id).toBe("s2")
    expect(sceneOf(plan, { kind: "shot", sceneId: "s1", id: "x" })?.id).toBe("s1")
    expect(sceneOf(plan, { kind: "head" })).toBeNull()
    expect(sceneOf(null, { kind: "scene", id: "s1" })).toBeNull()
  })
})
