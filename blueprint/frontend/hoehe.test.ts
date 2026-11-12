// Die Zeichenfläche darf nie höher werden als das Fenster. Der Editor liegt in einer Spalte unter den
// Meldungen der Seite. Ohne min-h-0 bestimmt dort der längste Inhalt (die Baustein-Palette) die Höhe:
// Die Zeichenfläche reicht dann unter den Fensterrand, Steuerknöpfe und Übersichtskarte sind abgeschnitten.
// Im Browser gemessen am 12.11.2026 (Editor 895 px in einem Behälter von 844 px).
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { describe, expect, it } from "vitest"

const read = (name: string) => readFileSync(join(__dirname, name), "utf8")
const classesOf = (source: string, marker: string) => {
  const at = source.indexOf(marker)
  expect(at, marker).toBeGreaterThan(0)
  return source.slice(at, at + 200).match(/className=[{"`]+([^"`]+)/)?.[1].split(/\s+/) ?? []
}

describe("Höhe der Zeichenfläche", () => {
  it("der Editor darf in seiner Spalte schrumpfen", () => {
    const column = classesOf(read("BoardEditor.tsx"), "<div className=\"flex min-h-0 min-w-0 flex-1 flex-col\">")
    expect(column).toEqual(expect.arrayContaining(["flex", "flex-col", "flex-1", "min-h-0", "min-w-0"]))
  })

  it("die Zeile aus Editor und Chat daneben lässt nichts überstehen", () => {
    const row = classesOf(read("BoardEditor.tsx"), "return (\n    <div className=\"flex ")
    expect(row).toEqual(expect.arrayContaining(["flex", "flex-1", "min-h-0", "min-w-0"]))
    expect(row).not.toContain("flex-col")
  })

  it("die Zeile mit Palette, Zeichenfläche und rechter Spalte ebenso", () => {
    const row = classesOf(read("BoardEditor.tsx"), "<div className=\"flex min-h-0 flex-1 overflow-hidden\">")
    expect(row).toEqual(expect.arrayContaining(["min-h-0", "flex-1", "overflow-hidden"]))
  })

  it("der Behälter der Seite neben der Board-Liste lässt nichts überstehen", () => {
    const column = classesOf(read("BlueprintPage.tsx"), "<div className=\"flex min-h-0 min-w-0 flex-1 flex-col")
    expect(column).toEqual(expect.arrayContaining(["min-h-0", "flex-col"]))
  })

  it("die Seite füllt den Platz, den das Cockpit ihr gibt, statt eine feste Fensterhöhe zu rechnen", () => {
    // Fest gerechnet (100vh - 3.5rem) war die Seite höher als ihr Platz: 844 px in 757 px (gemessen bei 900 px
    // Fensterhöhe). Steuerknöpfe und Übersichtskarte lagen unter dem Rand, die Seite ließ sich rollen.
    const page = read("BlueprintPage.tsx")
    expect(page).not.toMatch(/100d?vh/)
    const root = classesOf(page, "return (\n    <div className=\"flex ")
    expect(root).toEqual(expect.arrayContaining(["h-full", "min-h-0", "overflow-hidden"]))
  })
})
