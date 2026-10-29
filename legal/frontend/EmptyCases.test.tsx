// Task 0dda5420: Die leere Fall-Übersicht zeigt das eigene Hydra-Bild des Moduls.
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"
import { EmptyCases } from "./EmptyCases"

describe("EmptyCases", () => {
  it("Bild als Deko + Text", () => {
    const html = renderToStaticMarkup(<EmptyCases />)
    expect(html).toMatch(/<img[^>]*src="[^"]*leer[^"]*\.webp"[^>]*alt=""/)
    expect(html).toContain("Noch keine Fälle.")
  })
  it("CaseList nutzt EmptyCases statt reinem Text", () => {
    const src = readFileSync(join(__dirname, "CaseList.tsx"), "utf8")
    expect(src).toContain("<EmptyCases />")
    expect(src).not.toMatch(/<p[^>]*>Noch keine Fälle\.<\/p>/)
  })
  it("das Bild liegt im Modul", () => {
    expect(readFileSync(join(__dirname, "assets", "leer.webp")).length).toBeGreaterThan(1000)
  })
})
