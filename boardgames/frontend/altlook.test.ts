// Alter Look entfernt (Plan PLAN-module-altlook): keine zinc-Grautöne, keine violett/indigo/purple/fuchsia-Akzente,
// keine white/x-Flächen und -Ränder, keine .box/rgbFor-Bereichsfarben. Statt dessen Cockpit-Farben und Farbstufen des Kerns.
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

const QUELLEN = dateien(__dirname).map((p) => ({ p: p.slice(__dirname.length + 1), text: readFileSync(p, "utf8") }))
const funde = (re: RegExp) => QUELLEN.flatMap(({ p, text }) => [...text.matchAll(re)].map((m) => `${p}: ${m[0]}`))

describe("Alter Look entfernt", () => {
  it("keine zinc-Flächen, -Ränder und hellen zinc-Schriften", () => {
    expect(funde(/(?<![\w-])(?:[a-z-]+:)*(?:bg|border(?:-[trblxy])?|ring|divide|from|to|via)-zinc-\d{2,3}(?![\w-])/g)).toEqual([])
    expect(funde(/(?<![\w-])(?:[a-z-]+:)*(?:text|placeholder)-zinc-(?:50|100|200|300|400|500|600)(?![\w-])/g)).toEqual([])
  })
  it("keine violett/indigo/purple/fuchsia-Farben", () => {
    expect(funde(/(?<![\w-])(?:[a-z-]+:)*[a-z]+-(?:violet|indigo|purple|fuchsia)-\d{2,3}(?![\w-])/g)).toEqual([])
  })
  it("keine white/x-Flächen und -Ränder", () => {
    expect(funde(/(?<![\w-])(?:[a-z-]+:)*(?:bg|border(?:-[trblxy])?|divide|ring)-white\/(?:\d+|\[[\d.]+%?\])/g)).toEqual([])
  })
  it("keine bunten Bereichsfarben (rgbFor) – .box/CollapsibleBox sind Kern-Bausteine und dürfen bleiben", () => {
    expect(funde(/rgbFor\(/g)).toEqual([])
  })
})
