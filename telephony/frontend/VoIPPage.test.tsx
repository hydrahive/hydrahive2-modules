import { readFileSync } from "node:fs"
import { describe, expect, it } from "vitest"

/**
 * Die Seite läuft im Cockpit-Vollbildrahmen (Layout.tsx: <main className="… overflow-hidden">). Dort muss die Seite
 * selbst scrollen – sonst ist alles unter dem Bildschirmrand unerreichbar (Till, 25.10.: „kann nicht runter scrollen“).
 * Gleiches Muster wie Haushaltsbuch/Mediacenter: Shell füllt die Höhe, <main> scrollt.
 */
const src = readFileSync(new URL("./VoIPPage.tsx", import.meta.url), "utf8")

describe("VoIP-Seite scrollt im Cockpit", () => {
  it("Shell füllt die Höhe als Spalte und schneidet selbst ab", () => {
    const shell = src.match(/<CockpitShell[^>]*>/)?.[0] ?? ""
    for (const c of ["flex", "h-full", "min-h-0", "flex-col", "overflow-hidden"]) expect(shell).toContain(c)
  })
  it("<main> ist der Scrollbereich", () => {
    const main = src.match(/<main className="([^"]*)"/)?.[1] ?? ""
    for (const c of ["min-h-0", "flex-1", "overflow-y-auto"]) expect(main.split(" ")).toContain(c)
  })
  it("Inhalt bleibt mittig und begrenzt", () => {
    expect(src).toContain("mx-auto max-w-7xl")
  })
})
