// Farbstufen des Kerns (Kern-PR #658): keine festen Cockpit-Dunkeltöne mehr, stattdessen
// rgb(var(--hh-s-<stufe>,<Rückfall>)) – folgt neuen Kernen, sieht auf alten Kernen aus wie vorher.
import { readdirSync, readFileSync, statSync } from "node:fs"
import { join } from "node:path"
import { describe, expect, it } from "vitest"

function dateien(dir: string): string[] {
  return readdirSync(dir).flatMap((n) => {
    const p = join(dir, n)
    if (statSync(p).isDirectory()) return dateien(p)
    return /\.(tsx?|css)$/.test(n) && !/\.test\.tsx?$/.test(n) ? [p] : []
  })
}

/** Neutrales Dunkelblau/-grau der alten Cockpit-Flächen (Auswahl-Töne #1c2940/#30243a ausgenommen). */
function istNeutralDunkel(h: string): boolean {
  if (["1c2940", "30243a"].includes(h.toLowerCase())) return false
  // Druckvorschau (LetterPrint): bewusst neutrales Papier-Grau, kein Cockpit-Ton.
  if (h.toLowerCase() === "2b313c") return false
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16))
  const max = Math.max(r, g, b), min = Math.min(r, g, b)
  const hell = (max + min) / 2 / 255
  const satt = max === min ? 0 : (max - min) / (255 - Math.abs(max + min - 255))
  return hell < 0.25 && satt < 0.42
}

const QUELLEN = dateien(__dirname).map((p) => ({ p: p.slice(__dirname.length + 1), text: readFileSync(p, "utf8") }))

describe("Farbstufen", () => {
  it("keine festen neutralen Dunkeltöne für Flächen und Ränder", () => {
    const funde = QUELLEN.flatMap(({ p, text }) =>
      [...text.matchAll(/(?:bg|border(?:-[trblxy])?|from|to|via|ring|divide)-\[#([0-9a-fA-F]{6})\]/g)]
        .filter((m) => istNeutralDunkel(m[1])).map((m) => `${p}: ${m[0]}`))
    expect(funde).toEqual([])
  })
  it("kein zu schwacher Nebentext (#8d9ab0, #718097 … → #9aa7bc)", () => {
    const funde = QUELLEN.flatMap(({ p, text }) =>
      [...text.matchAll(/text-\[#(8d9ab0|7d8aa0|718097|718096|68758a|607188)\]/gi)].map((m) => `${p}: ${m[0]}`))
    expect(funde).toEqual([])
  })
  it("jede Stufe hat einen Rückfallwert (sonst durchsichtig auf älteren Kernen)", () => {
    const ohne = QUELLEN.flatMap(({ p, text }) =>
      [...text.matchAll(/var\(--hh-s-[a-z-]+\)/g)].map((m) => `${p}: ${m[0]}`))
    expect(ohne).toEqual([])
  })
})
