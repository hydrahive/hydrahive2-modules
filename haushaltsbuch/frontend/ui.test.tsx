// Task 0dda5420: Leer-Zustände im Haushaltsbuch zeigen das eigene Hydra-Bild des Moduls statt eines Symbols.
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"
import { EmptyState } from "./ui"

describe("EmptyState (Haushaltsbuch)", () => {
  it("zeigt das Leer-Bild als Deko, dazu Titel und Text", () => {
    const html = renderToStaticMarkup(<EmptyState title="Noch keine Buchungen" text="Erfasse die erste." />)
    expect(html).toMatch(/<img[^>]*src="[^"]*leer[^"]*\.webp"[^>]*alt=""/)
    expect(html).toContain("Noch keine Buchungen")
    expect(html).toContain("Erfasse die erste.")
    expect(html).not.toContain("lucide-inbox")
  })
  it("das Bild liegt im Modul", () => {
    expect(readFileSync(join(__dirname, "assets", "leer.webp")).length).toBeGreaterThan(1000)
  })
})
