// Task 0dda5420 (Schwung 2): Der Leer-Zustand zeigt das eigene Hydra-Bild des Moduls.
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { describe, expect, it } from "vitest"

const SRC = readFileSync(join(__dirname, "BoardSidebar.tsx"), "utf8")

describe("Leer-Bild (blueprint)", () => {
  it("bindet das eigene Leer-Bild ein", () => {
    expect(SRC).toMatch(/import leerBild from "\.\/assets\/leer\.webp"/)
  })
  it("das Bild steht im Leer-Zustand direkt beim Leer-Text", () => {
    const i = SRC.indexOf("Noch keine Boards")
    expect(i).toBeGreaterThan(0)
    expect(SRC.slice(Math.max(0, i - 400), i)).toContain("<img src={leerBild} alt=\"\"")
  })
  it("das Bild liegt im Modul", () => {
    expect(readFileSync(join(__dirname, "assets", "leer.webp")).length).toBeGreaterThan(1000)
  })
})
